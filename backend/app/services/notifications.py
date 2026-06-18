"""Notification service — dispatches push, WhatsApp, and email tasks.

Each public function resolves user contact details from the DB, checks the
user's notification preferences, enqueues Celery tasks, and records the
notification in the wn_notifications inbox.

PHI rules:
- Push body must use generic language — no condition names, medication names.
- Task arguments contain only: push_token, phone hash, email address, template
  name, and generic parameter strings. Never raw patient data beyond name/time.
- No PHI in logs — only IDs and template names.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _get_patient_contact(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
) -> tuple[str | None, str | None, str | None, str | None, dict[str, bool]]:
    """Return (name, phone, email, expo_push_token, notification_preferences)."""
    from sqlalchemy import select

    from app.models.clinic import Patient
    from app.models.identity import User

    result = await db.execute(
        select(
            User.name,
            User.phone,
            User.email,
            User.expo_push_token,
            User.notification_preferences,
        )
        .join(Patient, Patient.user_id == User.id)
        .where(Patient.id == patient_id)
    )
    row = result.first()
    if row is None:
        return None, None, None, None, {}
    prefs = row.notification_preferences or {}
    return row.name, row.phone, row.email, row.expo_push_token, prefs


def _first_name(name: str | None) -> str:
    if not name:
        return "there"
    return name.split()[0]


def _ist_str(dt: object) -> str:
    from datetime import datetime, timedelta, timezone

    if not isinstance(dt, datetime):
        return str(dt)
    ist = timezone(timedelta(hours=5, minutes=30))
    return dt.astimezone(ist).strftime("%d %b %Y at %I:%M %p")


def _pref(prefs: dict[str, bool], channel: str) -> bool:
    return bool(prefs.get(channel, True))


# ── Notification inbox record ─────────────────────────────────────────────────


async def _record_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    template_name: str,
    title: str,
    body: str,
    channels: list[str],
    data: dict[str, Any] | None = None,
) -> None:
    """Write a row to wn_notifications for the patient inbox."""
    if not channels:
        return
    from app.repositories import notifications as notif_repo

    try:
        await notif_repo.create(
            db,
            user_id=user_id,
            template_name=template_name,
            title=title,
            body=body,
            channels=channels,
            data=data or {},
        )
        await db.flush()
    except Exception:
        logger.exception("record_notification.failed", template=template_name)


# ── Appointment confirmation ──────────────────────────────────────────────────


async def notify_appointment_confirmed(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Fire push + WhatsApp + email after a consultation is confirmed."""
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.doctor import Doctor
    from app.models.identity import User

    result = await db.execute(
        select(
            Patient.id,
            Patient.user_id,
            Consultation.scheduled_start_at,
            User.name,
            User.phone,
            User.email,
            User.expo_push_token,
            User.notification_preferences,
        )
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(Consultation.id == consultation_id)
    )
    row = result.first()
    if row is None:
        logger.warning("notify_appointment_confirmed.consultation_not_found", consultation_id=str(consultation_id))
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)
    time_str = _ist_str(row.scheduled_start_at)
    date_str = time_str.split(" at ")[0]
    time_only = time_str.split(" at ")[-1] if " at " in time_str else time_str

    channels_sent: list[str] = []
    title = "Appointment confirmed"
    body = "Your Kyros appointment is confirmed. See you soon!"
    data = {"screen": "consultation", "id": str(consultation_id)}

    if _pref(prefs, "push"):
        _dispatch_push(push_token=row.expo_push_token, title=title, body=body, data=data)
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "whatsapp"):
        _dispatch_whatsapp(
            phone=row.phone,
            template_name="appointment_confirmation",
            params=[first, date_str, time_only],
        )
        if row.phone:
            channels_sent.append("whatsapp")

    if _pref(prefs, "email"):
        _dispatch_email(
            to_email=row.email,
            subject="Your Kyros appointment is confirmed",
            html_body=render_email(
                "appointment_confirmation",
                first_name=first,
                time_str=time_str,
            ),
        )
        if row.email:
            channels_sent.append("email")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="appointment_confirmation",
        title=title,
        body=body,
        channels=channels_sent,
        data=data,
    )

    # Tell the doctor too — generic, no patient details (email is an external channel).
    doctor_row = (
        await db.execute(
            select(User.name, User.email)
            .join(Doctor, Doctor.user_id == User.id)
            .join(Consultation, Consultation.doctor_id == Doctor.id)
            .where(Consultation.id == consultation_id)
        )
    ).first()
    if doctor_row is not None and doctor_row.email:
        _dispatch_email(
            to_email=doctor_row.email,
            subject="New confirmed consultation on your Kyros schedule",
            html_body=render_email(
                "doctor_new_booking",
                first_name=_first_name(doctor_row.name),
                time_str=time_str,
            ),
        )


# ── Doctor assigned to a request ──────────────────────────────────────────────


async def notify_doctor_assigned(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Tell the patient a coordinator assigned a doctor + time to their request.

    The patient must now pay to confirm. Push + inbox only — no clinical content,
    no doctor identity in external channels.
    """
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.identity import User

    row = (
        await db.execute(
            select(
                Patient.user_id,
                Consultation.scheduled_start_at,
                User.name,
                User.expo_push_token,
                User.notification_preferences,
            )
            .join(Patient, Patient.id == Consultation.patient_id)
            .join(User, User.id == Patient.user_id)
            .where(Consultation.id == consultation_id)
        )
    ).first()
    if row is None:
        logger.warning("notify_doctor_assigned.consultation_not_found", consultation_id=str(consultation_id))
        return

    prefs = row.notification_preferences or {}
    time_str = _ist_str(row.scheduled_start_at)
    title = "A specialist has been assigned"
    body = f"Your consultation is scheduled for {time_str}. Pay now to confirm your appointment."
    data = {"screen": "consultation", "id": str(consultation_id)}

    channels_sent: list[str] = []
    if _pref(prefs, "push"):
        _dispatch_push(push_token=row.expo_push_token, title=title, body=body, data=data)
        if row.expo_push_token:
            channels_sent.append("push")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="doctor_assigned",
        title=title,
        body=body,
        channels=channels_sent or ["inbox"],
        data=data,
    )


# ── Staff alerts (ops inbox) ──────────────────────────────────────────────────


def notify_ops_new_inquiry(*, kind: str) -> None:
    """Alert the ops inbox that a new website submission is waiting.

    kind: "booking_inquiry" or "lead". Deliberately content-free — no name,
    phone, or condition. Staff open the coordinator portal for details.
    """
    from app.core.config import settings

    to_email = settings.ops_notify_email or settings.admin_alert_email
    if not to_email:
        return
    kind_label = (
        "consultation request" if kind == "booking_inquiry" else "help query"
    )
    try:
        _dispatch_email(
            to_email=to_email,
            subject=f"[Kyros] New {kind_label} from the website",
            html_body=render_email("ops_new_inquiry", kind_label=kind_label),
        )
    except Exception:
        # A broker outage must not fail the inquiry submission itself.
        logger.exception("notify_ops_new_inquiry_failed", kind=kind)


# ── Appointment reminder ──────────────────────────────────────────────────────


async def notify_appointment_reminder(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Fire push + WhatsApp + email 24h before a consultation."""
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.identity import User

    result = await db.execute(
        select(
            Patient.user_id,
            Consultation.scheduled_start_at,
            User.name,
            User.phone,
            User.email,
            User.expo_push_token,
            User.notification_preferences,
        )
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(Consultation.id == consultation_id)
    )
    row = result.first()
    if row is None:
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)
    time_str = _ist_str(row.scheduled_start_at)
    time_only = time_str.split(" at ")[-1] if " at " in time_str else time_str

    channels_sent: list[str] = []
    title = "Appointment tomorrow"
    body = "Your Kyros appointment is tomorrow. Tap to view details."
    data = {"screen": "consultation", "id": str(consultation_id)}

    if _pref(prefs, "push"):
        _dispatch_push(push_token=row.expo_push_token, title=title, body=body, data=data)
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "whatsapp"):
        _dispatch_whatsapp(
            phone=row.phone,
            template_name="appointment_reminder",
            params=[first, time_only],
        )
        if row.phone:
            channels_sent.append("whatsapp")

    if _pref(prefs, "email"):
        _dispatch_email(
            to_email=row.email,
            subject="Reminder: Your Kyros appointment is tomorrow",
            html_body=render_email(
                "appointment_reminder",
                first_name=first,
                time_str=time_only,
            ),
        )
        if row.email:
            channels_sent.append("email")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="appointment_reminder",
        title=title,
        body=body,
        channels=channels_sent,
        data=data,
    )


# ── Lab result ready ──────────────────────────────────────────────────────────


async def notify_lab_result_ready(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
) -> None:
    """Fire push + WhatsApp after OCR completes on a lab report."""
    from sqlalchemy import select

    from app.models.clinic import LabReport, Patient
    from app.models.identity import User

    result = await db.execute(
        select(
            Patient.user_id,
            User.name,
            User.phone,
            User.expo_push_token,
            User.notification_preferences,
        )
        .join(Patient, Patient.id == LabReport.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(LabReport.id == lab_report_id)
    )
    row = result.first()
    if row is None:
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)

    channels_sent: list[str] = []
    title = "Lab results ready"
    body = "Your lab report has been processed and is ready to view."
    data = {"screen": "report", "id": str(lab_report_id)}

    if _pref(prefs, "push"):
        _dispatch_push(push_token=row.expo_push_token, title=title, body=body, data=data)
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "whatsapp"):
        _dispatch_whatsapp(
            phone=row.phone,
            template_name="lab_result_ready",
            params=[first],
        )
        if row.phone:
            channels_sent.append("whatsapp")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="lab_result_ready",
        title=title,
        body=body,
        channels=channels_sent,
        data=data,
    )


# ── Pre-consultation report ready ─────────────────────────────────────────────


async def notify_pre_consult_report_ready(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Fire push + WhatsApp after the pre-consultation report is generated."""
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.identity import User

    result = await db.execute(
        select(
            Patient.user_id,
            Consultation.scheduled_start_at,
            User.name,
            User.phone,
            User.expo_push_token,
            User.notification_preferences,
        )
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(Consultation.id == consultation_id)
    )
    row = result.first()
    if row is None:
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)
    time_str = _ist_str(row.scheduled_start_at)
    time_only = time_str.split(" at ")[-1] if " at " in time_str else time_str

    channels_sent: list[str] = []
    title = "Your pre-appointment report is ready"
    body = "Your doctor will review your health summary before the consultation."
    data = {"screen": "pre_consult_report", "id": str(consultation_id)}

    if _pref(prefs, "push"):
        _dispatch_push(push_token=row.expo_push_token, title=title, body=body, data=data)
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "whatsapp"):
        _dispatch_whatsapp(
            phone=row.phone,
            template_name="pre_consult_report_ready",
            params=[first, time_only],
        )
        if row.phone:
            channels_sent.append("whatsapp")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="pre_consult_report_ready",
        title=title,
        body=body,
        channels=channels_sent,
        data=data,
    )


# ── Medication reminder ───────────────────────────────────────────────────────


async def notify_medication_reminder(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    reminder_label: str,
) -> None:
    """Fire push only for a medication reminder (label is never shown in push text)."""
    from sqlalchemy import select

    from app.models.identity import User

    result = await db.execute(
        select(
            User.name,
            User.expo_push_token,
            User.notification_preferences,
        ).where(User.id == user_id)
    )
    row = result.first()
    if row is None:
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)

    channels_sent: list[str] = []
    title = "Medication reminder"
    body = f"Hi {first}, time for your scheduled medication. Tap to log it."
    data = {"screen": "reminders"}

    if _pref(prefs, "push"):
        _dispatch_push(push_token=row.expo_push_token, title=title, body=body, data=data)
        if row.expo_push_token:
            channels_sent.append("push")

    await _record_notification(
        db,
        user_id=user_id,
        template_name="medication_reminder",
        title=title,
        body=body,
        channels=channels_sent,
        data=data,
    )


# ── Task dispatch helpers ─────────────────────────────────────────────────────


def _dispatch_push(
    *,
    push_token: str | None,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> None:
    if not push_token:
        return
    from app.tasks.notification_tasks import send_push_notification_task
    send_push_notification_task.apply_async(
        kwargs={"push_token": push_token, "title": title, "body": body, "data": data or {}},
        queue="notifications",
    )


def _dispatch_whatsapp(
    *,
    phone: str | None,
    template_name: str,
    params: list[str],
) -> None:
    if not phone:
        return
    from app.tasks.notification_tasks import send_whatsapp_task
    send_whatsapp_task.apply_async(
        kwargs={"phone": phone, "template_name": template_name, "params": params},
        queue="notifications",
    )


def _dispatch_email(
    *,
    to_email: str | None,
    subject: str,
    html_body: str,
) -> None:
    if not to_email:
        return
    from app.tasks.notification_tasks import send_email_task
    send_email_task.apply_async(
        kwargs={"to_email": to_email, "subject": subject, "html_body": html_body},
        queue="notifications",
    )


# ── Email templates ───────────────────────────────────────────────────────────
# All styles are inline for Gmail / Outlook / Apple Mail compatibility.
# Colors from Kyros design tokens:
#   Forest   #0F3D2E  — brand primary, header bar, headings
#   Jade     #2D7A5F  — links, secondary accents
#   Ivory    #FAF7F2  — page background
#   Saffron  #E8A430  — CTA button background
#   Stone    #6B6560  — footer, secondary text
#   White    #FFFFFF  — card background


_BASE_OPEN = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#FAF7F2;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#FAF7F2;min-height:100vh;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="560" cellpadding="0" cellspacing="0" border="0"
               style="max-width:560px;width:100%;">
          <!-- Header -->
          <tr>
            <td style="background:#0F3D2E;border-radius:8px 8px 0 0;
                        padding:20px 32px;text-align:center;">
              <span style="font-family:Georgia,'Times New Roman',serif;
                           font-size:22px;color:#FAF7F2;font-style:italic;
                           font-weight:normal;letter-spacing:0.5px;">
                Kyros Clinic
              </span>
            </td>
          </tr>
          <!-- Card body -->
          <tr>
            <td style="background:#FFFFFF;padding:32px 32px 24px 32px;">
              <h1 style="margin:0 0 20px 0;font-family:Georgia,'Times New Roman',serif;
                         font-size:22px;font-weight:normal;color:#0F3D2E;font-style:italic;">
                {heading}
              </h1>
"""

_BASE_CLOSE = """
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:#FFFFFF;border-radius:0 0 8px 8px;
                        border-top:1px solid #E5E0D8;padding:16px 32px;">
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;
                         font-size:11px;color:#6B6560;text-align:center;line-height:1.6;">
                Kyros Clinic · Telemedicine Platform<br>
                This is an automated message. Please do not reply directly to this email.<br>
                <a href="https://kyrosclinic.com/unsubscribe" style="color:#2D7A5F;">
                  Manage notification preferences
                </a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _body_p(text: str) -> str:
    return (
        f'<p style="margin:0 0 16px 0;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;color:#1A1917;line-height:1.6;">{text}</p>'
    )


def _cta_button(label: str, url: str = "https://app.kyrosclinic.com") -> str:
    return (
        f'<p style="text-align:center;margin:24px 0 8px 0;">'
        f'<a href="{url}" style="display:inline-block;background:#E8A430;color:#0F3D2E;'
        f'font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:600;'
        f'text-decoration:none;padding:12px 32px;border-radius:6px;">'
        f'{label}</a></p>'
    )


def _render(*, title: str, heading: str, body_html: str) -> str:
    return (
        _BASE_OPEN.format(title=title, heading=heading)
        + body_html
        + _BASE_CLOSE
    )


def render_email(template_name: str, **kwargs: str) -> str:
    """Render a branded HTML email for the given template name."""
    fn = _EMAIL_TEMPLATES.get(template_name)
    if fn is None:
        return _render(
            title="Kyros Clinic",
            heading="Notification",
            body_html=_body_p("You have a new notification from Kyros Clinic."),
        )
    return fn(**kwargs)


def _tpl_appointment_confirmation(*, first_name: str, time_str: str) -> str:
    return _render(
        title="Your Kyros appointment is confirmed",
        heading="Appointment Confirmed",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                f"Your Kyros appointment is confirmed for "
                f"<strong>{time_str} IST</strong>."
            )
            + _body_p(
                "Your consultation link will be available 15 minutes before the call. "
                "Please complete your pre-consultation questionnaire if you haven&#39;t yet."
            )
            + _cta_button("View Appointment")
            + _body_p("We look forward to seeing you.<br>Team Kyros")
        ),
    )


def _tpl_appointment_reminder(*, first_name: str, time_str: str) -> str:
    return _render(
        title="Reminder: Your Kyros appointment is tomorrow",
        heading="Appointment Tomorrow",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                f"A reminder that your Kyros appointment is tomorrow at "
                f"<strong>{time_str} IST</strong>."
            )
            + _body_p(
                "Please complete your pre-consultation questionnaire before the session "
                "so your doctor can prepare."
            )
            + _cta_button("Complete Questionnaire")
            + _body_p("See you soon,<br>Team Kyros")
        ),
    )


def _tpl_lab_result_ready(*, first_name: str) -> str:
    return _render(
        title="Your Kyros lab results are ready",
        heading="Lab Results Ready",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                "Your lab report has been processed and your results are ready to view "
                "in the Kyros app."
            )
            + _cta_button("View Results")
            + _body_p(
                "Your doctor will review these results at your next consultation.<br>"
                "Team Kyros"
            )
        ),
    )


def _tpl_pre_consult_report_ready(*, first_name: str, time_str: str) -> str:
    return _render(
        title="Your Kyros pre-appointment report is ready",
        heading="Pre-Appointment Report Ready",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                "Your pre-appointment health summary is ready. Your doctor will review it "
                f"before your consultation at <strong>{time_str} IST</strong>."
            )
            + _cta_button("View Report")
            + _body_p("See you soon,<br>Team Kyros")
        ),
    )


def _tpl_medication_reminder(*, first_name: str) -> str:
    return _render(
        title="Medication reminder from Kyros",
        heading="Medication Reminder",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                "This is a reminder to take your scheduled medication. "
                "Open the Kyros app to log your adherence."
            )
            + _cta_button("Log Medication")
            + _body_p("Stay consistent — small steps make a big difference.<br>Team Kyros")
        ),
    )


def _tpl_otp_code(*, otp: str, ttl_minutes: str) -> str:
    return _render(
        title="Your Kyros verification code",
        heading="Verification Code",
        body_html=(
            _body_p("Use this code to verify your Kyros account:")
            + (
                f'<p style="text-align:center;margin:24px 0;font-family:Arial,Helvetica,'
                f"sans-serif;font-size:32px;font-weight:700;letter-spacing:8px;"
                f'color:#0F3D2E;">{otp}</p>'
            )
            + _body_p(
                f"The code is valid for {ttl_minutes} minutes. "
                "Never share it with anyone — Kyros staff will never ask for it."
            )
            + _body_p(
                "If you didn&#39;t request this code, you can safely ignore this email."
            )
        ),
    )


def _tpl_doctor_new_booking(*, first_name: str, time_str: str) -> str:
    return _render(
        title="New confirmed consultation",
        heading="New Consultation Booked",
        body_html=(
            _body_p(f"Hi Dr. {first_name},")
            + _body_p(
                f"A consultation has been confirmed on your schedule for "
                f"<strong>{time_str} IST</strong>."
            )
            + _body_p(
                "Open your Kyros doctor portal to review the patient's "
                "pre-consultation details."
            )
            + _body_p("Team Kyros")
        ),
    )


def _tpl_ops_new_inquiry(*, kind_label: str) -> str:
    # No patient details by design — email is an external channel.
    return _render(
        title=f"New {kind_label} waiting",
        heading="New Website Submission",
        body_html=(
            _body_p(
                f"A new <strong>{kind_label}</strong> was just submitted on "
                f"kyrosclinic.com and is waiting in the queue."
            )
            + _body_p(
                "Open the coordinator portal to view the details and mark it "
                "contacted once you have reached out."
            )
            + _cta_button("Open Inquiry Queue", "https://api.kyrosclinic.com/coord/inquiries")
            + _body_p("Team Kyros")
        ),
    )


_EMAIL_TEMPLATES: dict[str, Callable[..., str]] = {
    "appointment_confirmation": _tpl_appointment_confirmation,
    "appointment_reminder": _tpl_appointment_reminder,
    "lab_result_ready": _tpl_lab_result_ready,
    "pre_consult_report_ready": _tpl_pre_consult_report_ready,
    "medication_reminder": _tpl_medication_reminder,
    "otp_code": _tpl_otp_code,
    "doctor_new_booking": _tpl_doctor_new_booking,
    "ops_new_inquiry": _tpl_ops_new_inquiry,
}
