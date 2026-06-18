"""Doctor-portal repository — all queries scoped to a single doctor.

Every function takes `doctor_id` (the dr_doctors.id UUID) as a mandatory
scope parameter.  None return values mean "not found or not this doctor's
resource" — callers translate to 404 per the cross-user-404 rule.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, LabOrderStatus, NoteType
from app.models.clinic import Consultation, DoctorNote, LabOrder, LabReport, Patient
from app.models.doctor import Availability, Doctor
from app.models.identity import User

# ── Doctor profile ─────────────────────────────────────────────────────────────


async def get_doctor_with_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> tuple[Doctor, User] | None:
    """Return (Doctor, User) for the given user, or None if no doctor profile."""
    result = await db.execute(
        select(Doctor, User)
        .join(User, User.id == Doctor.user_id)
        .where(Doctor.user_id == user_id, Doctor.deleted_at.is_(None))
    )
    row = result.first()
    if row is None:
        return None
    return row.Doctor, row.User


async def update_doctor_profile(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    fields: dict[str, Any],
) -> Doctor | None:
    """Patch allowed doctor profile fields; NMC fields are never updated here.

    `fields` is a dict of column names to new values — only keys present are updated.
    """
    from sqlalchemy import update

    if not fields:
        result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
        return result.scalar_one_or_none()

    fields["updated_at"] = datetime.now(UTC)
    result = await db.execute(
        update(Doctor)
        .where(Doctor.id == doctor_id)
        .values(**fields)
        .returning(Doctor)
    )
    return result.scalar_one_or_none()


# ── Panel patients ─────────────────────────────────────────────────────────────


async def list_panel_patients(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Patient, User]], int]:
    """Patients who have had at least one consultation with this doctor.

    Returns (list of (Patient, User) pairs, total_count).
    search is matched case-insensitively against user.name and user.phone.
    """
    # Subquery: distinct patient_ids that have consulted this doctor
    consulted_sq = (
        select(Consultation.patient_id)
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.deleted_at.is_(None),
        )
        .distinct()
        .scalar_subquery()
    )

    base = (
        select(Patient, User)
        .join(User, User.id == Patient.user_id)
        .where(
            Patient.id.in_(consulted_sq),
            Patient.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
    )

    if search:
        term = f"%{search.lower()}%"
        base = base.where(
            or_(
                func.lower(User.name).like(term),
                User.phone.like(term),
            )
        )

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(User.name).offset(offset).limit(page_size)
    )
    pairs = [(row.Patient, row.User) for row in rows]
    return pairs, total


async def get_panel_patient(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> tuple[Patient, User] | None:
    """Return (Patient, User) if the patient has ever consulted this doctor; else None."""
    consulted_sq = (
        select(Consultation.patient_id)
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.patient_id == patient_id,
            Consultation.deleted_at.is_(None),
        )
        .exists()
    )

    result = await db.execute(
        select(Patient, User)
        .join(User, User.id == Patient.user_id)
        .where(
            Patient.id == patient_id,
            Patient.deleted_at.is_(None),
            User.deleted_at.is_(None),
            consulted_sq,
        )
    )
    row = result.first()
    if row is None:
        return None
    return row.Patient, row.User


async def count_patient_consultations(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> dict[str, int]:
    """Return consultation counts by status bucket for a patient/doctor pair."""
    result = await db.execute(
        select(Consultation.status, func.count().label("n"))
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.patient_id == patient_id,
            Consultation.deleted_at.is_(None),
        )
        .group_by(Consultation.status)
    )
    rows = result.all()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status.value] = row.n
    return counts


# ── Doctor consultations ───────────────────────────────────────────────────────


async def list_doctor_consultations(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    filter_type: str = "upcoming",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Consultation, Patient, User]], int]:
    """List consultations for a doctor with filter_type: today | upcoming | history.

    Returns list of (Consultation, Patient, User) tuples.
    """
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    base = (
        select(Consultation, Patient, User)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.deleted_at.is_(None),
            Patient.deleted_at.is_(None),
        )
    )

    if filter_type == "today":
        base = base.where(
            Consultation.scheduled_start_at >= today_start,
            Consultation.scheduled_start_at < today_end,
        )
        order = Consultation.scheduled_start_at.asc()
    elif filter_type == "upcoming":
        base = base.where(
            Consultation.scheduled_start_at >= today_end,
            Consultation.status.in_([ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED]),
        )
        order = Consultation.scheduled_start_at.asc()
    else:  # history
        base = base.where(
            Consultation.status.in_([
                ConsultationStatus.COMPLETED,
                ConsultationStatus.CANCELLED,
                ConsultationStatus.NO_SHOW,
            ])
        )
        order = Consultation.scheduled_start_at.desc()

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(base.order_by(order).offset(offset).limit(page_size))
    triples = [(row.Consultation, row.Patient, row.User) for row in rows]
    return triples, total


async def get_doctor_consultation_detail(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    consultation_id: uuid.UUID,
) -> tuple[Consultation, Patient, User] | None:
    """Return (Consultation, Patient, User) for a doctor's consultation; None if not found/not owned."""
    result = await db.execute(
        select(Consultation, Patient, User)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(
            Consultation.id == consultation_id,
            Consultation.doctor_id == doctor_id,
            Consultation.deleted_at.is_(None),
            Patient.deleted_at.is_(None),
        )
    )
    row = result.first()
    if row is None:
        return None
    return row.Consultation, row.Patient, row.User


# ── Doctor notes ───────────────────────────────────────────────────────────────


async def get_notes_for_consultation(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    consultation_id: uuid.UUID,
) -> list[DoctorNote]:
    """Return current (non-superseded) notes for a doctor's consultation.

    Returns an empty list if the consultation doesn't belong to this doctor.
    """
    # Verify ownership first — same pattern as get_doctor_consultation_detail.
    owns = await db.execute(
        select(Consultation.id).where(
            Consultation.id == consultation_id,
            Consultation.doctor_id == doctor_id,
            Consultation.deleted_at.is_(None),
        )
    )
    if owns.scalar_one_or_none() is None:
        return []

    result = await db.execute(
        select(DoctorNote)
        .where(
            DoctorNote.consultation_id == consultation_id,
            DoctorNote.doctor_id == doctor_id,
            DoctorNote.superseded_by_id.is_(None),
        )
        .order_by(DoctorNote.created_at.asc())
    )
    return list(result.scalars().all())


async def append_doctor_note(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    consultation_id: uuid.UUID,
    patient_id: uuid.UUID,
    note_type: NoteType,
    content: str | None = None,
    subjective: str | None = None,
    objective: str | None = None,
    assessment: str | None = None,
    plan: str | None = None,
) -> DoctorNote:
    """Append a versioned note; supersedes the previous current note of the same type.

    Inserts a new DoctorNote row with version = prior_max + 1.  If a prior
    current note of the same type exists, sets its superseded_by_id to the new
    row's id (the spec points superseded_by_id forward, not backward).
    """
    from sqlalchemy import update

    # Compute next version.
    version_result = await db.execute(
        select(func.coalesce(func.max(DoctorNote.version), 0)).where(
            DoctorNote.consultation_id == consultation_id,
            DoctorNote.doctor_id == doctor_id,
            DoctorNote.note_type == note_type,
        )
    )
    next_version: int = version_result.scalar_one() + 1

    new_note = DoctorNote(
        consultation_id=consultation_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        note_type=note_type,
        content=content,
        subjective=subjective,
        objective=objective,
        assessment=assessment,
        plan=plan,
        version=next_version,
    )
    db.add(new_note)
    await db.flush()  # obtain new_note.id before the UPDATE below

    # Point the prior current note of this type at the new one.
    await db.execute(
        update(DoctorNote)
        .where(
            DoctorNote.consultation_id == consultation_id,
            DoctorNote.doctor_id == doctor_id,
            DoctorNote.note_type == note_type,
            DoctorNote.id != new_note.id,
            DoctorNote.superseded_by_id.is_(None),
        )
        .values(superseded_by_id=new_note.id)
    )

    return new_note


# ── Lab orders ─────────────────────────────────────────────────────────────────


async def create_lab_order_for_consultation(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    consultation_id: uuid.UUID,
    patient_id: uuid.UUID,
    tests: list[str],
    lab_name: str | None,
) -> LabOrder:
    """Create a lab order linked to a doctor's consultation."""
    order = LabOrder(
        consultation_id=consultation_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        tests=tests,
        lab_name=lab_name,
        status=LabOrderStatus.ORDERED,
    )
    db.add(order)
    await db.flush()
    return order


# ── Availability / schedule ────────────────────────────────────────────────────


async def list_availability(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Availability]:
    """Return availability slots for the doctor, optionally filtered by date range."""
    q = select(Availability).where(Availability.doctor_id == doctor_id)
    if start is not None:
        q = q.where(Availability.slot_start >= start)
    if end is not None:
        q = q.where(Availability.slot_start < end)
    result = await db.execute(q.order_by(Availability.slot_start.asc()))
    return list(result.scalars().all())


async def create_availability_slots(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    slots: list[tuple[datetime, datetime]],
) -> list[Availability]:
    """Bulk-create availability slots; silently skips duplicates."""
    created: list[Availability] = []
    for slot_start, slot_end in slots:
        # Check for duplicate before insert to avoid constraint error in savepoint context.
        existing = await db.execute(
            select(Availability).where(
                Availability.doctor_id == doctor_id,
                Availability.slot_start == slot_start,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        slot = Availability(
            doctor_id=doctor_id,
            slot_start=slot_start,
            slot_end=slot_end,
            status=AvailabilityStatus.AVAILABLE,
        )
        db.add(slot)
        await db.flush()
        created.append(slot)
    return created


async def get_availability_slot(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    slot_id: uuid.UUID,
) -> Availability | None:
    """Return the slot if it belongs to this doctor; else None."""
    result = await db.execute(
        select(Availability).where(
            Availability.id == slot_id,
            Availability.doctor_id == doctor_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_availability_slot(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    slot_id: uuid.UUID,
) -> bool | None:
    """Delete an available slot owned by this doctor.

    Returns:
        True  — deleted successfully.
        False — slot exists but cannot be deleted (status != available).
        None  — slot not found / not owned by this doctor.
    """
    from sqlalchemy import delete

    slot = await get_availability_slot(db, doctor_id=doctor_id, slot_id=slot_id)
    if slot is None:
        return None
    if slot.status != AvailabilityStatus.AVAILABLE:
        return False
    await db.execute(delete(Availability).where(Availability.id == slot_id))
    return True


async def update_doctor_preferences(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    fields: dict[str, Any],
) -> Doctor | None:
    """Update schedule preferences (duration, buffer time).

    Only keys present in `fields` are updated.
    """
    from sqlalchemy import update

    if not fields:
        result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
        return result.scalar_one_or_none()

    fields["updated_at"] = datetime.now(UTC)
    result = await db.execute(
        update(Doctor)
        .where(Doctor.id == doctor_id)
        .values(**fields)
        .returning(Doctor)
    )
    return result.scalar_one_or_none()


# ── Lab report review ──────────────────────────────────────────────────────────


async def list_patient_lab_reports(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> list[LabReport]:
    """Return all lab reports for a panel patient, newest first.

    Scoping: this doctor must have at least one consultation with the patient.
    Returns empty list if the patient is not on the doctor's panel.
    """
    on_panel = (
        select(Consultation.patient_id)
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.patient_id == patient_id,
            Consultation.deleted_at.is_(None),
        )
        .exists()
    )
    result = await db.execute(
        select(LabReport)
        .where(LabReport.patient_id == patient_id, on_panel)
        .order_by(LabReport.created_at.desc())
    )
    return list(result.scalars().all())


async def get_patient_lab_report(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
    report_id: uuid.UUID,
) -> LabReport | None:
    """Return a single lab report scoped to doctor's panel patient; None if not found."""
    on_panel = (
        select(Consultation.patient_id)
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.patient_id == patient_id,
            Consultation.deleted_at.is_(None),
        )
        .exists()
    )
    result = await db.execute(
        select(LabReport).where(
            LabReport.id == report_id,
            LabReport.patient_id == patient_id,
            on_panel,
        )
    )
    return result.scalar_one_or_none()


async def annotate_lab_report(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    report_id: uuid.UUID,
    patient_id: uuid.UUID,
    commentary: dict[str, str] | None,
    flags: list[str] | None,
) -> LabReport | None:
    """Write doctor commentary and/or patient attention flags to a lab report.

    Sets doctor_reviewed_by_id and marks the report reviewed.
    Returns updated LabReport; None if not found / not on panel.
    """
    from sqlalchemy import update

    on_panel = (
        select(Consultation.patient_id)
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.patient_id == patient_id,
            Consultation.deleted_at.is_(None),
        )
        .exists()
    )
    # Verify the report exists and the patient is on this doctor's panel.
    check = await db.execute(
        select(LabReport).where(
            LabReport.id == report_id,
            LabReport.patient_id == patient_id,
            on_panel,
        )
    )
    if check.scalar_one_or_none() is None:
        return None

    values: dict[str, Any] = {
        "doctor_reviewed_by_id": doctor_id,
        "updated_at": datetime.now(UTC),
    }
    if commentary is not None:
        values["doctor_commentary"] = commentary
    if flags is not None:
        values["patient_attention_flags"] = flags

    result = await db.execute(
        update(LabReport)
        .where(LabReport.id == report_id)
        .values(**values)
        .returning(LabReport)
    )
    return result.scalar_one_or_none()


async def annotate_lab_report_by_doctor(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    report_id: uuid.UUID,
    commentary: dict[str, str] | None,
    flags: list[str] | None,
) -> LabReport | None:
    """Scoped annotation without requiring caller to know patient_id.

    Single scoped query: verifies the report exists AND the owning patient
    is on this doctor's panel. Returns None for both not-found and
    not-on-panel (cross-user 404 pattern).
    """
    from sqlalchemy import update

    on_panel = (
        select(Consultation.patient_id)
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.patient_id == LabReport.patient_id,
            Consultation.deleted_at.is_(None),
        )
        .exists()
    )
    check = await db.execute(
        select(LabReport).where(LabReport.id == report_id, on_panel)
    )
    report = check.scalar_one_or_none()
    if report is None:
        return None

    values: dict[str, Any] = {
        "doctor_reviewed_by_id": doctor_id,
        "updated_at": datetime.now(UTC),
    }
    if commentary is not None:
        values["doctor_commentary"] = commentary
    if flags is not None:
        values["patient_attention_flags"] = flags

    result = await db.execute(
        update(LabReport)
        .where(LabReport.id == report_id)
        .values(**values)
        .returning(LabReport)
    )
    return result.scalar_one_or_none()


# ── Bank details ───────────────────────────────────────────────────────────────


async def save_bank_details_encrypted(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    encrypted_bytes: bytes,
) -> Doctor | None:
    """Save encrypted bank details for the doctor."""
    from sqlalchemy import update

    result = await db.execute(
        update(Doctor)
        .where(Doctor.id == doctor_id)
        .values(
            bank_details_encrypted=encrypted_bytes,
            updated_at=datetime.now(UTC),
        )
        .returning(Doctor)
    )
    return result.scalar_one_or_none()
