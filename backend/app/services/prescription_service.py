"""Prescription service — create draft, sign, PDF generation."""

from __future__ import annotations

import uuid
from html import escape as _esc
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import FoodRelation, FrequencyCode, TimingSlot
from app.models.clinic import Prescription, PrescriptionItem
from app.repositories import drug_catalogue as dc_repo
from app.repositories import prescriptions as prescriptions_repo

logger = structlog.get_logger(__name__)


class PrescriptionError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ── Structured-timing display composition ───────────────────────────────────────

_FREQUENCY_LABELS: dict[FrequencyCode, str] = {
    FrequencyCode.OD: "Once daily",
    FrequencyCode.BD: "Twice daily",
    FrequencyCode.TDS: "Thrice daily",
    FrequencyCode.QID: "Four times daily",
    FrequencyCode.HS: "At bedtime",
    FrequencyCode.SOS: "As needed",
    FrequencyCode.ALTERNATE_DAYS: "Every alternate day",
    FrequencyCode.WEEKLY: "Once weekly",
    FrequencyCode.BIWEEKLY: "Once every two weeks",
    FrequencyCode.MONTHLY: "Once monthly",
    FrequencyCode.OTHER: "",
}

_FOOD_LABELS: dict[FoodRelation, str] = {
    FoodRelation.BEFORE_FOOD: "before food",
    FoodRelation.AFTER_FOOD: "after food",
    FoodRelation.WITH_FOOD: "with food",
    FoodRelation.EMPTY_STOMACH: "on an empty stomach",
    FoodRelation.ANYTIME: "",
}


def compose_frequency_display(
    *,
    frequency_code: str | None,
    timing_slots: list[str] | None,
    food_relation: str | None,
    fallback: str | None = None,
) -> str:
    """Build the human-readable frequency string shown on the PDF and mobile.

    Composes from the structured fields; falls back to free text (the legacy
    `frequency` value) when the code is OTHER with nothing else set.
    """
    parts: list[str] = []

    if frequency_code:
        label = _FREQUENCY_LABELS.get(FrequencyCode(frequency_code), "")
        if label:
            parts.append(label)

    if timing_slots:
        ordered = [s.value for s in TimingSlot if s.value in set(timing_slots)]
        if ordered:
            parts.append(", ".join(s.capitalize() for s in ordered))

    if food_relation:
        food = _FOOD_LABELS.get(FoodRelation(food_relation), "")
        if food:
            parts.append(food)

    composed = " · ".join(parts)
    if composed:
        return composed
    return (fallback or "").strip()


def _apply_frequency_display(items: list[dict[str, Any]]) -> None:
    """Compose each item's `frequency` display string from its structured fields.

    Mutates each dict in place. Raises PrescriptionError when a line has no
    displayable frequency at all (OTHER + no slots + no free text)."""
    for item in items:
        display = compose_frequency_display(
            frequency_code=item.get("frequency_code"),
            timing_slots=item.get("timing_slots"),
            food_relation=item.get("food_relation"),
            fallback=item.get("frequency"),
        )
        if not display:
            raise PrescriptionError("frequency_required")
        item["frequency"] = display


# ── Drug schedule rule checker (pure — no async/DB, directly unit-testable) ──

_OWNERSHIP_CODES: frozenset[str] = frozenset(
    {
        "consultation_not_found_or_not_owned",
        "doctor_profile_not_found",
        "prescription_not_found_or_not_draft",
        "prescription_not_found_or_not_signable",
    }
)


def check_drug_entry(
    *,
    drug_generic_name: str,
    entry: Any,  # DrugCatalogue or duck-typed stand-in; None = not in catalogue
    doctor_verticals: list[str],
) -> str | None:
    """Return the resolved schedule string or None (drug not in catalogue → passes through).

    Raises PrescriptionError for blocked drugs:
      - drug_prohibited            — CDSCO-banned
      - schedule_x_not_prescribable
      - schedule_h1_not_prescribable_via_telemedicine
      - drug_requires_specialist_vertical
    """
    if entry is None:
        return None
    if entry.is_prohibited:
        raise PrescriptionError("drug_prohibited")
    if entry.drug_schedule == "X":
        raise PrescriptionError("schedule_x_not_prescribable")
    if entry.drug_schedule == "H1":
        raise PrescriptionError("schedule_h1_not_prescribable_via_telemedicine")
    if entry.requires_vertical and entry.requires_vertical not in doctor_verticals:
        raise PrescriptionError("drug_requires_specialist_vertical")
    return str(entry.drug_schedule)


async def _check_drug_items(
    db: AsyncSession,
    items: list[dict[str, Any]],
    doctor_verticals: list[str],
) -> None:
    """Look up each item in the catalogue and enforce schedule rules.

    Mutates each item dict in-place to add 'drug_schedule' for the repo to store.
    Raises PrescriptionError on the first violation found.
    """
    for item in items:
        entry = await dc_repo.lookup_drug(db, name=item["drug_generic_name"])
        resolved = check_drug_entry(
            drug_generic_name=item["drug_generic_name"],
            entry=entry,
            doctor_verticals=doctor_verticals,
        )
        item["drug_schedule"] = resolved


async def _check_refill_gate(
    db: AsyncSession,
    items: list[dict[str, Any]],
    *,
    patient_id: uuid.UUID,
    consultation_id: uuid.UUID,
) -> None:
    """Raise PrescriptionError if any item requests a refill but the patient has
    no prior completed consultation (re-evaluation gate)."""
    if not any(item.get("refill_allowed") for item in items):
        return
    from app.repositories import consultations as consultations_repo

    has_prior = await consultations_repo.has_prior_completed_consultation(
        db, patient_id=patient_id, exclude_consultation_id=consultation_id
    )
    if not has_prior:
        raise PrescriptionError("refill_requires_prior_consultation")


async def create_draft(
    db: AsyncSession,
    *,
    doctor_user_id: uuid.UUID,
    consultation_id: uuid.UUID,
    diagnosis_note: str | None,
    general_instructions: str | None,
    items: list[dict[str, Any]],
) -> Prescription:
    """Create a draft prescription for the consultation.

    Validates that the consultation exists and belongs to this doctor.
    """
    from sqlalchemy import select

    from app.models.clinic import Consultation
    from app.models.doctor import Doctor

    # Resolve doctor row
    result = await db.execute(select(Doctor).where(Doctor.user_id == doctor_user_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise PrescriptionError("doctor_profile_not_found")

    # Validate consultation ownership
    result2 = await db.execute(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.doctor_id == doctor.id,
        )
    )
    consultation = result2.scalar_one_or_none()
    if consultation is None:
        raise PrescriptionError("consultation_not_found_or_not_owned")

    # Schedule and refill enforcement
    await _check_drug_items(db, items, doctor.conditions_treated or [])
    await _check_refill_gate(
        db, items, patient_id=consultation.patient_id, consultation_id=consultation_id
    )
    _apply_frequency_display(items)

    return await prescriptions_repo.create_draft(
        db,
        consultation_id=consultation_id,
        doctor_id=doctor.id,
        patient_id=consultation.patient_id,
        diagnosis_note=diagnosis_note,
        general_instructions=general_instructions,
        items=items,
    )


async def update_draft(
    db: AsyncSession,
    *,
    doctor_user_id: uuid.UUID,
    prescription_id: uuid.UUID,
    diagnosis_note: str | None,
    general_instructions: str | None,
    items: list[dict[str, Any]] | None,
) -> Prescription:
    """Edit a draft prescription. Signed prescriptions never reach this path."""
    from sqlalchemy import select

    from app.db.enums import PrescriptionStatus
    from app.models.doctor import Doctor

    result = await db.execute(select(Doctor).where(Doctor.user_id == doctor_user_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise PrescriptionError("doctor_profile_not_found")

    # Pre-fetch to get patient/consultation context for schedule + refill checks.
    existing_rx = await prescriptions_repo.get_for_doctor(
        db, prescription_id=prescription_id, doctor_id=doctor.id
    )
    if existing_rx is None or existing_rx.status != PrescriptionStatus.DRAFT:
        raise PrescriptionError("prescription_not_found_or_not_draft")

    if items is not None:
        await _check_drug_items(db, items, doctor.conditions_treated or [])
        await _check_refill_gate(
            db,
            items,
            patient_id=existing_rx.patient_id,
            consultation_id=existing_rx.consultation_id,
        )
        _apply_frequency_display(items)

    rx = await prescriptions_repo.update_draft(
        db,
        prescription_id=prescription_id,
        doctor_id=doctor.id,
        diagnosis_note=diagnosis_note,
        general_instructions=general_instructions,
        items=items,
    )
    if rx is None:
        raise PrescriptionError("prescription_not_found_or_not_draft")

    return rx


async def sign_prescription(
    db: AsyncSession,
    *,
    doctor_user_id: uuid.UUID,
    prescription_id: uuid.UUID,
) -> Prescription:
    """Sign the prescription and enqueue PDF generation."""
    from sqlalchemy import select

    from app.models.doctor import Doctor

    result = await db.execute(select(Doctor).where(Doctor.user_id == doctor_user_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise PrescriptionError("doctor_profile_not_found")

    rx = await prescriptions_repo.sign(db, prescription_id=prescription_id, doctor_id=doctor.id)
    if rx is None:
        raise PrescriptionError("prescription_not_found_or_not_signable")

    await _generate_prescription_reminders(db, rx)

    return rx


async def _generate_prescription_reminders(db: AsyncSession, rx: Prescription) -> None:
    """Best-effort: transcribe the signed prescription into patient reminders.

    Generation must never block the clinical sign, so it runs in a SAVEPOINT and
    swallows failures — a failed generation rolls back only the reminders and is
    logged; the signed prescription stands and reminders can be regenerated later.
    """
    from app.models.clinic import Patient
    from app.services import reminder_generation

    try:
        async with db.begin_nested():
            patient = await db.get(Patient, rx.patient_id)
            if patient is None:
                return
            items = await prescriptions_repo.list_items(db, prescription_id=rx.id)
            await reminder_generation.generate_for_prescription(
                db,
                prescription=rx,
                items=items,
                patient_user_id=patient.user_id,
            )
    except Exception:  # noqa: BLE001 — generation is non-critical to signing
        logger.exception(
            "prescription_reminder_generation_failed",
            prescription_id=str(rx.id),
        )


def render_prescription_html(
    prescription: Prescription,
    items: list[PrescriptionItem],
    doctor_name: str,
    nmc_registration_number: str,
    specialty: list[str],
    patient_name: str,
) -> str:
    """Render the IMC-format prescription as HTML for WeasyPrint."""
    signed_at_str = (
        prescription.signed_at.strftime("%d %b %Y, %I:%M %p IST")
        if prescription.signed_at
        else "—"
    )

    items_html = ""
    for item in items:
        duration = f"{item.duration_days} days" if item.duration_days else "Ongoing"
        # `frequency` is the server-composed display string (frequency code +
        # time-of-day slots + food relation). Fall back to recomposing from the
        # structured fields for safety, then to an em-dash.
        frequency_display = item.frequency or compose_frequency_display(
            frequency_code=item.frequency_code,
            timing_slots=item.timing_slots or [],
            food_relation=item.food_relation,
        ) or "—"
        items_html += f"""
        <div class="rx-item">
            <div class="drug-name">{_esc(item.drug_generic_name)}</div>
            <div class="drug-form">{_esc(item.drug_form.capitalize())}</div>
            <div class="drug-detail">
                <span class="label">Dose:</span> {_esc(item.dosage)} &nbsp;|&nbsp;
                <span class="label">Frequency:</span> {_esc(frequency_display)} &nbsp;|&nbsp;
                <span class="label">Duration:</span> {_esc(duration)}
            </div>
            {f'<div class="drug-instructions">{_esc(item.instructions)}</div>' if item.instructions else ''}
        </div>
        """

    diagnosis_section = ""
    if prescription.diagnosis_note:
        diagnosis_section = f"""
        <div class="section">
            <div class="section-label">Diagnosis / Chief Complaint</div>
            <div class="section-value">{_esc(prescription.diagnosis_note)}</div>
        </div>
        """

    general_section = ""
    if prescription.general_instructions:
        general_section = f"""
        <div class="section">
            <div class="section-label">General Instructions</div>
            <div class="section-value">{_esc(prescription.general_instructions)}</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 12px; color: #1A1A1A; margin: 0; padding: 0; }}
  .page {{ padding: 32px 40px; max-width: 760px; margin: 0 auto; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0F3D2E; padding-bottom: 12px; margin-bottom: 20px; }}
  .clinic-name {{ font-size: 20px; font-weight: 700; color: #0F3D2E; }}
  .clinic-sub {{ font-size: 10px; color: #6B6B68; margin-top: 2px; }}
  .header-right {{ text-align: right; font-size: 10px; color: #6B6B68; }}
  .doctor-block {{ margin-bottom: 16px; }}
  .doctor-name {{ font-size: 15px; font-weight: 600; color: #0F3D2E; }}
  .doctor-meta {{ font-size: 11px; color: #6B6B68; margin-top: 2px; }}
  .signed-chip {{ display: inline-block; background: #8FA88E22; color: #0F3D2E; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; margin-top: 4px; }}
  .patient-block {{ background: #FAF1E4; border-radius: 6px; padding: 10px 14px; margin-bottom: 16px; display: flex; gap: 24px; }}
  .patient-field {{ font-size: 11px; }}
  .patient-label {{ color: #6B6B68; }}
  .patient-value {{ font-weight: 600; color: #1A1A1A; }}
  .rx-symbol {{ font-size: 28px; color: #0F3D2E; font-weight: 700; margin-bottom: 8px; }}
  .rx-item {{ border: 1px solid #E5E5E0; border-radius: 6px; padding: 12px 14px; margin-bottom: 10px; }}
  .drug-name {{ font-size: 14px; font-weight: 600; color: #1A1A1A; }}
  .drug-form {{ font-size: 11px; color: #6B6B68; margin-top: 2px; }}
  .drug-detail {{ font-size: 12px; color: #1A1A1A; margin-top: 6px; }}
  .drug-instructions {{ font-size: 11px; color: #6B6B68; margin-top: 4px; font-style: italic; }}
  .label {{ font-weight: 600; }}
  .section {{ margin-bottom: 12px; }}
  .section-label {{ font-size: 10px; font-weight: 700; color: #6B6B68; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .section-value {{ font-size: 12px; color: #1A1A1A; }}
  .footer {{ border-top: 1px solid #E5E5E0; margin-top: 24px; padding-top: 12px; font-size: 10px; color: #6B6B68; text-align: center; }}
  .rx-id {{ font-family: monospace; }}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div>
      <div class="clinic-name">Kyros Clinic</div>
      <div class="clinic-sub">Digital Health Clinic · kyrosclinic.com</div>
    </div>
    <div class="header-right">
      <div>Prescription No: <span class="rx-id">RX-{str(prescription.id).upper()[:8]}</span></div>
      <div>Date: {signed_at_str}</div>
      <div>Version: {prescription.version}</div>
    </div>
  </div>

  <div class="doctor-block">
    <div class="doctor-name">Dr {_esc(doctor_name)}</div>
    <div class="doctor-meta">NMC Reg: {_esc(nmc_registration_number)} &nbsp;|&nbsp; {_esc(', '.join(specialty)) if specialty else 'General Practice'}</div>
    <div class="signed-chip">&#x2713; Digitally signed {signed_at_str}</div>
  </div>

  <div class="patient-block">
    <div class="patient-field"><div class="patient-label">Patient</div><div class="patient-value">{_esc(patient_name)}</div></div>
    <div class="patient-field"><div class="patient-label">Prescription ID</div><div class="patient-value rx-id">{str(prescription.id)[:13]}…</div></div>
  </div>

  {diagnosis_section}

  <div class="rx-symbol">&#8478;</div>
  {items_html}

  {general_section}

  <div class="footer">
    Original digital prescription. Verify at kyrosclinic.com/verify/{prescription.id}<br>
    This prescription is valid for the dispensing of the listed medications only. Not valid for Schedule X / narcotic substances.
  </div>
</div>
</body>
</html>"""
