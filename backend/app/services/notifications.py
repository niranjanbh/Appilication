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
    data = {
        "screen": "consultation",
        "id": str(consultation_id),
        "template_name": "appointment_confirmation",
        "resource_id": str(consultation_id),
    }

    dedup_id = f"appointment_confirmation:{consultation_id}"
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "whatsapp"):
        _dispatch_whatsapp(
            phone=row.phone,
            template_name="appointment_confirmation",
            params=[first, date_str, time_only],
            dedup_id=dedup_id,
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
            dedup_id=dedup_id,
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
            dedup_id=f"doctor_new_booking:{consultation_id}",
        )


# ── Consultation requested (patient acknowledgement) ──────────────────────────


async def notify_consultation_requested(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Acknowledge to the patient that their in-app consultation request was
    received (push + inbox + email).

    No clinical content and no condition name travel on any channel — the message
    is a generic "we've got it, a coordinator will be in touch" receipt.
    """
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.identity import User

    row = (
        await db.execute(
            select(
                Patient.user_id,
                User.name,
                User.email,
                User.expo_push_token,
                User.notification_preferences,
            )
            .join(Patient, Patient.id == Consultation.patient_id)
            .join(User, User.id == Patient.user_id)
            .where(Consultation.id == consultation_id)
        )
    ).first()
    if row is None:
        logger.warning(
            "notify_consultation_requested.consultation_not_found",
            consultation_id=str(consultation_id),
        )
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)

    title = "Request received"
    body = (
        "We've received your consultation request. A care coordinator will assign "
        "the right specialist and time shortly."
    )
    data = {
        "screen": "consultation",
        "id": str(consultation_id),
        "template_name": "consultation_requested",
        "resource_id": str(consultation_id),
    }

    dedup_id = f"consultation_requested:{consultation_id}"
    channels_sent: list[str] = []
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "email"):
        _dispatch_email(
            to_email=row.email,
            subject="We've received your Kyros consultation request",
            html_body=render_email("consultation_requested", first_name=first),
            dedup_id=dedup_id,
        )
        if row.email:
            channels_sent.append("email")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="consultation_requested",
        title=title,
        body=body,
        channels=channels_sent or ["inbox"],
        data=data,
    )


# ── Doctor assigned to a request ──────────────────────────────────────────────


async def notify_doctor_assigned(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Tell the patient a coordinator assigned a doctor + time to their request.

    The patient must now pay to confirm. Push + inbox to the patient (no clinical
    content, no doctor identity in external channels); the assigned doctor gets a
    generic email that a patient has been scheduled with them.
    """
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.doctor import Doctor
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
    data = {
        "screen": "consultation",
        "id": str(consultation_id),
        "template_name": "doctor_assigned",
        "resource_id": str(consultation_id),
    }

    channels_sent: list[str] = []
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=f"doctor_assigned:{consultation_id}",
        )
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

    # Tell the assigned doctor by email — generic, no patient details (external
    # channel). The consult is SCHEDULED pending the patient's payment, so the
    # doctor is told it is provisional.
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
            subject="A patient has been scheduled with you on Kyros",
            html_body=render_email(
                "doctor_consult_assigned",
                first_name=_first_name(doctor_row.name),
                time_str=time_str,
            ),
            # Per-consultation: without this, the constant subject would suppress
            # every assignment after the doctor's first within a 24h window.
            dedup_id=f"doctor_consult_assigned:{consultation_id}",
        )


# ── On-demand consultation (staff-initiated, join now) ─────────────────────────


async def notify_on_demand_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Tell the patient (push + inbox) and doctor (email) an on-demand consult is ready.

    Staff started this consultation directly; both parties should join now. No
    clinical content travels on any channel.
    """
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.doctor import Doctor
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
        logger.warning(
            "notify_on_demand_consultation.consultation_not_found",
            consultation_id=str(consultation_id),
        )
        return

    prefs = row.notification_preferences or {}
    title = "Your consultation is ready"
    body = "Your doctor is ready for a video consultation now. Tap to join."
    data = {
        "screen": "consultation",
        "id": str(consultation_id),
        "template_name": "on_demand_consultation",
        "resource_id": str(consultation_id),
    }

    channels_sent: list[str] = []
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=f"on_demand_consultation:{consultation_id}",
        )
        if row.expo_push_token:
            channels_sent.append("push")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="on_demand_consultation",
        title=title,
        body=body,
        channels=channels_sent or ["inbox"],
        data=data,
    )

    # Tell the doctor by email — generic, no patient details (external channel).
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
            subject="An on-demand consultation is ready to join",
            html_body=render_email(
                "doctor_new_booking",
                first_name=_first_name(doctor_row.name),
                time_str=_ist_str(row.scheduled_start_at),
            ),
            dedup_id=f"on_demand_doctor:{consultation_id}",
        )


# ── Consultation completed ────────────────────────────────────────────────────


async def notify_consultation_completed(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Tell the patient (push + inbox + email) their consultation is complete.

    Generic language only — no clinical content, doctor notes, or prescription
    details travel on any channel (PHI rule). The patient opens the app for the
    specifics.
    """
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.identity import User

    row = (
        await db.execute(
            select(
                Patient.user_id,
                User.name,
                User.email,
                User.expo_push_token,
                User.notification_preferences,
            )
            .join(Patient, Patient.id == Consultation.patient_id)
            .join(User, User.id == Patient.user_id)
            .where(Consultation.id == consultation_id)
        )
    ).first()
    if row is None:
        logger.warning(
            "notify_consultation_completed.consultation_not_found",
            consultation_id=str(consultation_id),
        )
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)

    title = "Consultation complete"
    body = (
        "Your consultation is complete. Any notes or prescriptions from your "
        "doctor are now available in the app."
    )
    data = {
        "screen": "consultation",
        "id": str(consultation_id),
        "template_name": "consultation_completed",
        "resource_id": str(consultation_id),
    }

    dedup_id = f"consultation_completed:{consultation_id}"
    channels_sent: list[str] = []
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "email"):
        _dispatch_email(
            to_email=row.email,
            subject="Your Kyros consultation is complete",
            html_body=render_email("consultation_completed", first_name=first),
            dedup_id=dedup_id,
        )
        if row.email:
            channels_sent.append("email")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="consultation_completed",
        title=title,
        body=body,
        channels=channels_sent or ["inbox"],
        data=data,
    )


# ── Consultation cancelled / reassigned by staff ──────────────────────────────


async def notify_consultation_cancelled(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    refund_issued: bool,
) -> None:
    """Tell the patient (push + inbox + email) that staff cancelled their
    appointment, noting whether a refund was initiated.

    Generic language only — no clinical content or cancellation reason travels on
    any channel.
    """
    from sqlalchemy import select

    from app.models.clinic import Consultation, Patient
    from app.models.identity import User

    row = (
        await db.execute(
            select(
                Patient.user_id,
                User.name,
                User.email,
                User.expo_push_token,
                User.notification_preferences,
            )
            .join(Patient, Patient.id == Consultation.patient_id)
            .join(User, User.id == Patient.user_id)
            .where(Consultation.id == consultation_id)
        )
    ).first()
    if row is None:
        logger.warning(
            "notify_consultation_cancelled.consultation_not_found",
            consultation_id=str(consultation_id),
        )
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)

    refund_line = (
        " A full refund has been initiated and will reach your account in 5–7 days."
        if refund_issued
        else ""
    )
    title = "Appointment cancelled"
    body = f"Your Kyros appointment has been cancelled.{refund_line}"
    data = {
        "screen": "consultation",
        "id": str(consultation_id),
        "template_name": "consultation_cancelled",
        "resource_id": str(consultation_id),
    }

    dedup_id = f"consultation_cancelled:{consultation_id}"
    channels_sent: list[str] = []
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "email"):
        _dispatch_email(
            to_email=row.email,
            subject="Your Kyros appointment has been cancelled",
            html_body=render_email(
                "consultation_cancelled",
                first_name=first,
                refund_issued="1" if refund_issued else "",
            ),
            dedup_id=dedup_id,
        )
        if row.email:
            channels_sent.append("email")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="consultation_cancelled",
        title=title,
        body=body,
        channels=channels_sent or ["inbox"],
        data=data,
    )


async def notify_consultation_reassigned(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Tell the patient (push + inbox + email) their appointment was moved to a
    new time (and possibly a new specialist) by staff.

    The new time is the only specific detail; no clinical content or doctor
    identity travels on external channels.
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
                User.email,
                User.expo_push_token,
                User.notification_preferences,
            )
            .join(Patient, Patient.id == Consultation.patient_id)
            .join(User, User.id == Patient.user_id)
            .where(Consultation.id == consultation_id)
        )
    ).first()
    if row is None:
        logger.warning(
            "notify_consultation_reassigned.consultation_not_found",
            consultation_id=str(consultation_id),
        )
        return

    prefs = row.notification_preferences or {}
    first = _first_name(row.name)
    time_str = _ist_str(row.scheduled_start_at)

    title = "Appointment rescheduled"
    body = f"Your Kyros appointment has been moved to {time_str}. Tap to view details."
    data = {
        "screen": "consultation",
        "id": str(consultation_id),
        "template_name": "consultation_reassigned",
        "resource_id": str(consultation_id),
    }

    dedup_id = f"consultation_reassigned:{consultation_id}"
    channels_sent: list[str] = []
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "email"):
        _dispatch_email(
            to_email=row.email,
            subject="Your Kyros appointment has been rescheduled",
            html_body=render_email(
                "consultation_reassigned",
                first_name=first,
                time_str=time_str,
            ),
            dedup_id=dedup_id,
        )
        if row.email:
            channels_sent.append("email")

    await _record_notification(
        db,
        user_id=row.user_id,
        template_name="consultation_reassigned",
        title=title,
        body=body,
        channels=channels_sent or ["inbox"],
        data=data,
    )


# ── New consultation request (coordinator triage alert) ───────────────────────


async def notify_coordinator_new_request(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Alert the assigned coordinator that a new in-app consultation request is
    waiting to be triaged (doctor + slot assignment).

    Falls back to the ops inbox when the request could not be routed to a
    coordinator. Deliberately content-free — no patient name or condition travels
    on the email; the coordinator opens the portal for the details.
    """
    from sqlalchemy import select

    from app.core.config import settings
    from app.models.admin import Coordinator
    from app.models.clinic import Consultation
    from app.models.identity import User

    to_email = (
        await db.execute(
            select(User.email)
            .join(Coordinator, Coordinator.user_id == User.id)
            .join(Consultation, Consultation.coordinator_id == Coordinator.id)
            .where(Consultation.id == consultation_id)
        )
    ).scalar_one_or_none()

    # Unrouted request (no active coordinator) → ops inbox backstop.
    if not to_email:
        to_email = settings.ops_notify_email or settings.admin_alert_email
    if not to_email:
        return

    _dispatch_email(
        to_email=to_email,
        subject="[Kyros] New consultation request awaiting assignment",
        html_body=render_email("coordinator_new_request"),
        # Per-consultation: the subject is identical for every request, so without
        # this each coordinator would receive only one alert per 24h window.
        dedup_id=f"coordinator_new_request:{consultation_id}",
    )


# ── Staff alerts (ops inbox) ──────────────────────────────────────────────────


def notify_ops_new_inquiry(*, kind: str, dedup_id: str | None = None) -> None:
    """Alert the ops inbox that a new website submission is waiting.

    kind: "booking_inquiry" or "lead". Deliberately content-free — no name,
    phone, or condition. Staff open the coordinator portal for details.

    ``dedup_id`` (the inquiry/lead id) keeps each distinct submission a distinct
    alert; the subject alone is identical across submissions and would otherwise
    suppress every alert after the first within a 24h window.
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
            dedup_id=f"ops_new_inquiry:{dedup_id}" if dedup_id else None,
        )
    except Exception:
        # A broker outage must not fail the inquiry submission itself.
        logger.exception("notify_ops_new_inquiry_failed", kind=kind)


def notify_booking_inquiry_received(
    *, name: str, email: str | None, dedup_id: str | None = None
) -> None:
    """Acknowledge a public website booking inquiry to the patient by email.

    Pre-account flow — the patient has no user row yet, so this is email-only (no
    inbox, no push). No condition name travels in the message (PHI discipline);
    it is a generic "we've received your request" receipt. A missing email (the
    field is optional on the inquiry form) makes this a no-op.

    ``dedup_id`` (the inquiry id) scopes the idempotency window to this specific
    inquiry so it never collides with the in-app request acknowledgement, which
    shares the same subject line.
    """
    if not email:
        return
    try:
        _dispatch_email(
            to_email=email,
            subject="We've received your Kyros consultation request",
            html_body=render_email(
                "booking_inquiry_received", first_name=_first_name(name)
            ),
            dedup_id=f"booking_inquiry_received:{dedup_id}" if dedup_id else None,
        )
    except Exception:
        # A broker outage must not fail the inquiry submission itself.
        logger.exception("notify_booking_inquiry_received_failed")


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
    data = {
        "screen": "consultation",
        "id": str(consultation_id),
        "template_name": "appointment_reminder",
        "resource_id": str(consultation_id),
    }

    dedup_id = f"appointment_reminder:{consultation_id}"
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "whatsapp"):
        _dispatch_whatsapp(
            phone=row.phone,
            template_name="appointment_reminder",
            params=[first, time_only],
            dedup_id=dedup_id,
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
            dedup_id=dedup_id,
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
    data = {
        "screen": "report",
        "id": str(lab_report_id),
        "template_name": "lab_result_ready",
        "resource_id": str(lab_report_id),
    }

    dedup_id = f"lab_result_ready:{lab_report_id}"
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "whatsapp"):
        _dispatch_whatsapp(
            phone=row.phone,
            template_name="lab_result_ready",
            params=[first],
            dedup_id=dedup_id,
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
    data = {
        "screen": "pre_consult_report",
        "id": str(consultation_id),
        "template_name": "pre_consult_report_ready",
        "resource_id": str(consultation_id),
    }

    dedup_id = f"pre_consult_report_ready:{consultation_id}"
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
        if row.expo_push_token:
            channels_sent.append("push")

    if _pref(prefs, "whatsapp"):
        _dispatch_whatsapp(
            phone=row.phone,
            template_name="pre_consult_report_ready",
            params=[first, time_only],
            dedup_id=dedup_id,
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
    reminder_id: uuid.UUID | None = None,
    occurrence: datetime | None = None,
) -> None:
    """Fire push only for a medication reminder (label is never shown in push text).

    ``reminder_id`` + ``occurrence`` scope the dedup window to one firing of one
    reminder: distinct medications no longer suppress one another, and the same
    scheduled dose fires once even if the (every-5-min) dispatcher sees it on two
    overlapping beat runs. The dispatcher is now schedule-aware, so each dose fires
    at its scheduled time. Without these (legacy callers) the dedup falls back to
    the per-(user,title) window.
    """
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
    data = {"screen": "reminders", "template_name": "medication_reminder"}

    # Per-reminder, per-occurrence when known; otherwise the legacy per-(user,title)
    # window (which collapses all of a user's medication reminders into one).
    if reminder_id is not None and occurrence is not None:
        dedup_id: str | None = f"medication_reminder:{reminder_id}:{occurrence.isoformat()}"
    elif reminder_id is not None:
        dedup_id = f"medication_reminder:{reminder_id}"
    else:
        dedup_id = None
    if _pref(prefs, "push"):
        _dispatch_push(
            push_token=row.expo_push_token, title=title, body=body, data=data,
            dedup_id=dedup_id,
        )
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
    dedup_id: str | None = None,
) -> None:
    if not push_token:
        return
    from app.tasks.notification_tasks import send_push_notification_task
    send_push_notification_task.apply_async(
        kwargs={
            "push_token": push_token,
            "title": title,
            "body": body,
            "data": data or {},
            "dedup_id": dedup_id,
        },
        queue="notifications",
    )


def _dispatch_whatsapp(
    *,
    phone: str | None,
    template_name: str,
    params: list[str],
    dedup_id: str | None = None,
) -> None:
    if not phone:
        return
    from app.tasks.notification_tasks import send_whatsapp_task
    send_whatsapp_task.apply_async(
        kwargs={
            "phone": phone,
            "template_name": template_name,
            "params": params,
            "dedup_id": dedup_id,
        },
        queue="notifications",
    )


def _dispatch_email(
    *,
    to_email: str | None,
    subject: str,
    html_body: str,
    dedup_id: str | None = None,
) -> None:
    if not to_email:
        return
    from app.tasks.notification_tasks import send_email_task
    send_email_task.apply_async(
        kwargs={
            "to_email": to_email,
            "subject": subject,
            "html_body": html_body,
            "dedup_id": dedup_id,
        },
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


def _tpl_doctor_consult_assigned(*, first_name: str, time_str: str) -> str:
    return _render(
        title="A patient has been scheduled with you",
        heading="New Patient Assigned",
        body_html=(
            _body_p(f"Hi Dr. {first_name},")
            + _body_p(
                f"A patient has been scheduled with you for "
                f"<strong>{time_str} IST</strong>, pending their payment confirmation."
            )
            + _body_p(
                "You will receive a final confirmation once the patient completes "
                "payment. Open your Kyros doctor portal to review the details."
            )
            + _body_p("Team Kyros")
        ),
    )


def _tpl_consultation_requested(*, first_name: str) -> str:
    return _render(
        title="We've received your Kyros consultation request",
        heading="Request Received",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                "Thank you — we've received your consultation request. A Kyros care "
                "coordinator will assign the right specialist and a time slot shortly."
            )
            + _body_p(
                "You'll get a notification as soon as your appointment is ready to "
                "confirm. You can track the status anytime in the Kyros app."
            )
            + _cta_button("View in App")
            + _body_p("Team Kyros")
        ),
    )


def _tpl_booking_inquiry_received(*, first_name: str) -> str:
    return _render(
        title="We've received your Kyros consultation request",
        heading="Request Received",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                "Thank you for reaching out to Kyros. We've received your request and "
                "a care coordinator will contact you on your phone within 4 hours to "
                "schedule your consultation."
            )
            + _body_p(
                "If you have any questions in the meantime, simply reply to the "
                "coordinator's call or message."
            )
            + _body_p("Team Kyros")
        ),
    )


def _tpl_consultation_completed(*, first_name: str) -> str:
    return _render(
        title="Your Kyros consultation is complete",
        heading="Consultation Complete",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                "Thank you for consulting with Kyros. Your consultation is now complete."
            )
            + _body_p(
                "Any notes, prescriptions, or care plan your doctor shared are "
                "available in the Kyros app."
            )
            + _cta_button("View in App")
            + _body_p("Take care,<br>Team Kyros")
        ),
    )


def _tpl_consultation_cancelled(*, first_name: str, refund_issued: str = "") -> str:
    refund_p = (
        _body_p(
            "A full refund has been initiated and will reach your original payment "
            "method within 5–7 business days."
        )
        if refund_issued
        else ""
    )
    return _render(
        title="Your Kyros appointment has been cancelled",
        heading="Appointment Cancelled",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                "We're sorry — your Kyros appointment has been cancelled. We "
                "apologise for any inconvenience."
            )
            + refund_p
            + _body_p(
                "You can book a new consultation anytime in the Kyros app, and a "
                "coordinator will help you find the right specialist and time."
            )
            + _cta_button("Book Again")
            + _body_p("Team Kyros")
        ),
    )


def _tpl_consultation_reassigned(*, first_name: str, time_str: str) -> str:
    return _render(
        title="Your Kyros appointment has been rescheduled",
        heading="Appointment Rescheduled",
        body_html=(
            _body_p(f"Hi {first_name},")
            + _body_p(
                f"Your Kyros appointment has been moved to "
                f"<strong>{time_str} IST</strong>."
            )
            + _body_p(
                "No action is needed from you — your payment carries over. Open the "
                "Kyros app to view the updated details."
            )
            + _cta_button("View Appointment")
            + _body_p("See you then,<br>Team Kyros")
        ),
    )


def _tpl_coordinator_new_request() -> str:
    # Content-free by design — no patient details on an external channel.
    return _render(
        title="New consultation request waiting",
        heading="New Consultation Request",
        body_html=(
            _body_p(
                "A new <strong>consultation request</strong> was just submitted in "
                "the Kyros app and is waiting to be assigned a doctor and time slot."
            )
            + _body_p(
                "Open the coordinator portal to review the request and assign a "
                "specialist."
            )
            + _cta_button(
                "Open Request Queue", "https://api.kyrosclinic.com/coord/scheduling"
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
    "doctor_consult_assigned": _tpl_doctor_consult_assigned,
    "consultation_requested": _tpl_consultation_requested,
    "consultation_completed": _tpl_consultation_completed,
    "consultation_cancelled": _tpl_consultation_cancelled,
    "consultation_reassigned": _tpl_consultation_reassigned,
    "booking_inquiry_received": _tpl_booking_inquiry_received,
    "coordinator_new_request": _tpl_coordinator_new_request,
    "ops_new_inquiry": _tpl_ops_new_inquiry,
}
