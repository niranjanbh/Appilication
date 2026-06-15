"""Coordinator-portal repository — all queries scoped to coordinator's assigned patients.

Security invariant: every function that returns patient or consultation data first
resolves the coordinator's assigned_patient_ids and filters to that set.
Returning None means "not found OR not assigned" — callers raise 404.

CoordinatorConsultationView and CoordinatorPatientView Pydantic schemas (defined in
the view layer) enforce the clinical-content strip at serialisation time, but the
repository also avoids selecting clinical fields where possible.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus
from app.models.admin import Coordinator, Followup, PatientInteraction
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.models.identity import User
from app.models.public import BookingInquiry, Lead

# Lead/inquiry pipeline statuses. "new" is set by the public form; the rest
# are coordinator transitions. "converted" = the person became a patient.
LEAD_STATUSES = ("new", "contacted", "qualified", "converted", "closed")

# ── Coordinator profile ────────────────────────────────────────────────────────


async def get_coordinator_by_user_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> Coordinator | None:
    result = await db.execute(
        select(Coordinator).where(
            Coordinator.user_id == user_id,
            Coordinator.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _get_assigned_ids(db: AsyncSession, coordinator_id: uuid.UUID) -> list[uuid.UUID]:
    """Return the list of patient UUIDs assigned to this coordinator."""
    result = await db.execute(
        select(Coordinator.assigned_patient_ids).where(Coordinator.id == coordinator_id)
    )
    raw = result.scalar_one_or_none()
    if not raw:
        return []
    return [uuid.UUID(str(pid)) for pid in raw]


# ── Patient access (assigned only) ─────────────────────────────────────────────


async def list_assigned_patients(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    search: str | None = None,
) -> list[tuple[Patient, User]]:
    """Return (Patient, User) pairs for all patients assigned to this coordinator."""
    assigned = await _get_assigned_ids(db, coordinator_id)
    if not assigned:
        return []

    base = (
        select(Patient, User)
        .join(User, User.id == Patient.user_id)
        .where(
            Patient.id.in_(assigned),
            Patient.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
    )
    if search:
        term = f"%{search.lower()}%"
        from sqlalchemy import or_
        base = base.where(
            or_(
                func.lower(User.name).like(term),
                User.phone.like(term),
            )
        )
    result = await db.execute(base.order_by(User.name))
    return [(row.Patient, row.User) for row in result]


async def get_assigned_patient(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> tuple[Patient, User] | None:
    """Return (Patient, User) if the patient is assigned to this coordinator; else None."""
    assigned = await _get_assigned_ids(db, coordinator_id)
    if patient_id not in assigned:
        return None

    result = await db.execute(
        select(Patient, User)
        .join(User, User.id == Patient.user_id)
        .where(
            Patient.id == patient_id,
            Patient.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
    )
    row = result.first()
    if row is None:
        return None
    return row.Patient, row.User


# ── Consultation access (scheduling data only) ─────────────────────────────────


async def list_today_consultations(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
) -> list[tuple[Consultation, User, User | None]]:
    """Return (Consultation, patient_user, doctor_user) triples for today.

    Only returns scheduling-level data — clinical fields are stripped by
    CoordinatorConsultationView at the view layer.
    """
    assigned = await _get_assigned_ids(db, coordinator_id)
    if not assigned:
        return []

    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    result = await db.execute(
        select(Consultation, Patient, User)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(
            Consultation.patient_id.in_(assigned),
            Consultation.scheduled_start_at >= day_start,
            Consultation.scheduled_start_at < day_end,
            Consultation.deleted_at.is_(None),
        )
        .order_by(Consultation.scheduled_start_at)
    )
    triples = []
    for row in result:
        dr_result = await db.execute(
            select(User).join(Doctor, Doctor.user_id == User.id)
            .where(Doctor.id == row.Consultation.doctor_id)
        )
        doctor_user = dr_result.scalar_one_or_none()
        triples.append((row.Consultation, row.User, doctor_user))
    return triples


async def list_intake_queue(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
) -> list[tuple[Consultation, User]]:
    """Return pending/scheduled consultations awaiting coordinator triage.

    Returns (Consultation, patient_user). Clinical fields not included.
    """
    assigned = await _get_assigned_ids(db, coordinator_id)
    if not assigned:
        return []

    result = await db.execute(
        select(Consultation, Patient, User)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(
            Consultation.patient_id.in_(assigned),
            Consultation.status == ConsultationStatus.SCHEDULED,
            Consultation.coordinator_id == coordinator_id,
            Consultation.deleted_at.is_(None),
        )
        .order_by(Consultation.scheduled_start_at)
    )
    return [(row.Consultation, row.User) for row in result]


async def list_patient_consultations_restricted(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> list[tuple[Consultation, User | None]]:
    """List consultation history for an assigned patient.

    Returns (Consultation, doctor_user). Coordinator sees dates/status/doctor only.
    """
    assigned = await _get_assigned_ids(db, coordinator_id)
    if patient_id not in assigned:
        return []

    result = await db.execute(
        select(Consultation)
        .where(
            Consultation.patient_id == patient_id,
            Consultation.deleted_at.is_(None),
        )
        .order_by(Consultation.scheduled_start_at.desc())
        .limit(50)
    )
    consultations = list(result.scalars().all())

    pairs = []
    for consultation in consultations:
        dr_result = await db.execute(
            select(User).join(Doctor, Doctor.user_id == User.id)
            .where(Doctor.id == consultation.doctor_id)
        )
        doctor_user = dr_result.scalar_one_or_none()
        pairs.append((consultation, doctor_user))
    return pairs


# ── Scheduling ─────────────────────────────────────────────────────────────────


async def list_available_slots(
    db: AsyncSession,
    *,
    date_from: datetime,
    date_to: datetime,
) -> list[tuple[Availability, Doctor, User]]:
    """Return available slots across all doctors in the given window."""
    result = await db.execute(
        select(Availability, Doctor, User)
        .join(Doctor, Doctor.id == Availability.doctor_id)
        .join(User, User.id == Doctor.user_id)
        .where(
            Availability.status == AvailabilityStatus.AVAILABLE,
            Availability.slot_start >= date_from,
            Availability.slot_start < date_to,
            Doctor.deleted_at.is_(None),
        )
        .order_by(Availability.slot_start)
    )
    return [(row.Availability, row.Doctor, row.User) for row in result]


async def book_consultation_for_patient(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    patient_id: uuid.UUID,
    slot_id: uuid.UUID,
    condition_category: str,
    consultation_fee_paise: int,
) -> Consultation | None:
    """Book a consultation on behalf of an assigned patient.

    Locks the slot (SELECT FOR UPDATE SKIP LOCKED) and creates the consultation.
    Returns None if the slot is no longer available.
    Raises ValueError if the patient is not assigned to this coordinator.
    """
    from sqlalchemy import update

    assigned = await _get_assigned_ids(db, coordinator_id)
    if patient_id not in assigned:
        return None

    # Lock the slot
    slot_result = await db.execute(
        select(Availability)
        .where(
            Availability.id == slot_id,
            Availability.status == AvailabilityStatus.AVAILABLE,
        )
        .with_for_update(skip_locked=True)
    )
    slot = slot_result.scalar_one_or_none()
    if slot is None:
        return None

    doctor = await db.get(Doctor, slot.doctor_id)
    if doctor is None or doctor.status != DoctorStatus.ACTIVE:
        return None

    consultation = Consultation(
        patient_id=patient_id,
        doctor_id=slot.doctor_id,
        coordinator_id=coordinator_id,
        condition_category=condition_category,
        consultation_type="initial",
        scheduled_start_at=slot.slot_start,
        scheduled_end_at=slot.slot_end,
        consultation_fee_paise=consultation_fee_paise,
        status=ConsultationStatus.SCHEDULED,
    )
    db.add(consultation)
    await db.flush()

    # Mark slot as booked
    await db.execute(
        update(Availability)
        .where(Availability.id == slot_id)
        .values(
            status=AvailabilityStatus.BOOKED,
            consultation_id=consultation.id,
            updated_at=datetime.now(UTC),
        )
    )
    return consultation


async def cancel_consultation_for_coordinator(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    consultation_id: uuid.UUID,
    reason: str,
) -> Consultation | None:
    """Cancel a consultation only if it belongs to an assigned patient."""
    from sqlalchemy import update

    assigned = await _get_assigned_ids(db, coordinator_id)

    result = await db.execute(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.patient_id.in_(assigned),
            Consultation.deleted_at.is_(None),
        )
    )
    consultation = result.scalar_one_or_none()
    if consultation is None:
        return None

    updated = await db.execute(
        update(Consultation)
        .where(Consultation.id == consultation_id)
        .values(
            status=ConsultationStatus.CANCELLED,
            cancellation_reason=reason[:500],
            updated_at=datetime.now(UTC),
        )
        .returning(Consultation)
    )
    # Release the slot
    await db.execute(
        update(Availability)
        .where(Availability.consultation_id == consultation_id)
        .values(
            status=AvailabilityStatus.AVAILABLE,
            consultation_id=None,
            updated_at=datetime.now(UTC),
        )
    )
    return updated.scalar_one_or_none()


async def list_upcoming_consultations(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
) -> list[tuple[Consultation, User, User | None]]:
    """Future scheduled/confirmed consultations for assigned patients.

    Returns (Consultation, patient_user, doctor_user) — scheduling data only.
    """
    assigned = await _get_assigned_ids(db, coordinator_id)
    if not assigned:
        return []

    result = await db.execute(
        select(Consultation, Patient, User)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(
            Consultation.patient_id.in_(assigned),
            Consultation.status.in_(
                (ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED)
            ),
            Consultation.scheduled_start_at >= datetime.now(UTC),
            Consultation.deleted_at.is_(None),
        )
        .order_by(Consultation.scheduled_start_at)
    )
    triples = []
    for row in result:
        dr_result = await db.execute(
            select(User).join(Doctor, Doctor.user_id == User.id)
            .where(Doctor.id == row.Consultation.doctor_id)
        )
        triples.append((row.Consultation, row.User, dr_result.scalar_one_or_none()))
    return triples


async def reschedule_consultation_for_coordinator(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    consultation_id: uuid.UUID,
    slot_id: uuid.UUID,
) -> Consultation | None:
    """Move a consultation to a new slot (possibly a different doctor).

    Payment and status are preserved — unlike cancel+rebook, no refund cycle.
    Returns None when the consultation isn't an assigned patient's, isn't
    reschedulable, or the new slot is taken (caller's transaction rolls back).
    """
    from sqlalchemy import update

    assigned = await _get_assigned_ids(db, coordinator_id)
    if not assigned:
        return None

    consultation = await db.scalar(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.patient_id.in_(assigned),
            Consultation.status.in_(
                (ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED)
            ),
            Consultation.deleted_at.is_(None),
        )
    )
    if consultation is None:
        return None

    # Free the old slot first so the rollback path leaves it booked.
    await db.execute(
        update(Availability)
        .where(Availability.consultation_id == consultation_id)
        .values(
            status=AvailabilityStatus.AVAILABLE,
            consultation_id=None,
            updated_at=datetime.now(UTC),
        )
    )

    slot = await db.scalar(
        select(Availability)
        .where(
            Availability.id == slot_id,
            Availability.status == AvailabilityStatus.AVAILABLE,
        )
        .with_for_update(skip_locked=True)
    )
    if slot is None:
        return None

    await db.execute(
        update(Availability)
        .where(Availability.id == slot_id)
        .values(
            status=AvailabilityStatus.BOOKED,
            consultation_id=consultation_id,
            updated_at=datetime.now(UTC),
        )
    )
    updated = await db.execute(
        update(Consultation)
        .where(Consultation.id == consultation_id)
        .values(
            doctor_id=slot.doctor_id,
            scheduled_start_at=slot.slot_start,
            scheduled_end_at=slot.slot_end,
            updated_at=datetime.now(UTC),
        )
        .returning(Consultation)
    )
    return updated.scalar_one_or_none()


# ── Follow-ups ──────────────────────────────────────────────────────────────────


async def create_followup(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    patient_id: uuid.UUID,
    note: str,
    due_at: datetime,
) -> Followup | None:
    """Create a follow-up for an assigned patient. None = patient not assigned."""
    assigned = await _get_assigned_ids(db, coordinator_id)
    if patient_id not in assigned:
        return None

    followup = Followup(
        coordinator_id=coordinator_id,
        patient_id=patient_id,
        note=note[:500],
        due_at=due_at,
    )
    db.add(followup)
    await db.flush()
    return followup


async def list_followups(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    status: str = "pending",
    limit: int = 200,
) -> list[tuple[Followup, User]]:
    """Return (Followup, patient_user) for this coordinator, due-date order."""
    result = await db.execute(
        select(Followup, User)
        .join(Patient, Patient.id == Followup.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(
            Followup.coordinator_id == coordinator_id,
            Followup.status == status,
        )
        .order_by(Followup.due_at)
        .limit(limit)
    )
    return [(row.Followup, row.User) for row in result]


async def complete_followup(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    followup_id: uuid.UUID,
) -> Followup | None:
    """Mark a follow-up done. None = not found or not this coordinator's."""
    from sqlalchemy import update

    result = await db.execute(
        update(Followup)
        .where(
            Followup.id == followup_id,
            Followup.coordinator_id == coordinator_id,
            Followup.status == "pending",
        )
        .values(
            status="done",
            completed_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        .returning(Followup)
    )
    return result.scalar_one_or_none()


async def count_pending_followups(db: AsyncSession, coordinator_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Followup)
        .where(
            Followup.coordinator_id == coordinator_id,
            Followup.status == "pending",
        )
    )
    return result.scalar_one()


# ── Patient interactions ────────────────────────────────────────────────────────


async def create_interaction(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    patient_id: uuid.UUID,
    channel: str,
    summary: str,
) -> PatientInteraction | None:
    """Log a contact with an assigned patient. None = patient not assigned."""
    assigned = await _get_assigned_ids(db, coordinator_id)
    if patient_id not in assigned:
        return None

    interaction = PatientInteraction(
        coordinator_id=coordinator_id,
        patient_id=patient_id,
        channel=channel[:20],
        summary=summary[:1000],
    )
    db.add(interaction)
    await db.flush()
    return interaction


async def list_interactions_for_patient(
    db: AsyncSession,
    *,
    coordinator_id: uuid.UUID,
    patient_id: uuid.UUID,
    limit: int = 50,
) -> list[tuple[PatientInteraction, str | None]]:
    """Return (interaction, coordinator_name) newest first, assigned patients only.

    All coordinators' interactions with the patient are shown (handovers need
    the full operational history), but access requires current assignment.
    """
    assigned = await _get_assigned_ids(db, coordinator_id)
    if patient_id not in assigned:
        return []

    result = await db.execute(
        select(PatientInteraction, User.name)
        .join(Coordinator, Coordinator.id == PatientInteraction.coordinator_id)
        .join(User, User.id == Coordinator.user_id)
        .where(PatientInteraction.patient_id == patient_id)
        .order_by(PatientInteraction.created_at.desc())
        .limit(limit)
    )
    return [(row.PatientInteraction, row.name) for row in result]


# ── Dashboard stats ─────────────────────────────────────────────────────────────


async def count_assigned_patients(db: AsyncSession, coordinator_id: uuid.UUID) -> int:
    assigned = await _get_assigned_ids(db, coordinator_id)
    return len(assigned)


async def count_pending_intake(db: AsyncSession, coordinator_id: uuid.UUID) -> int:
    assigned = await _get_assigned_ids(db, coordinator_id)
    if not assigned:
        return 0
    result = await db.execute(
        select(func.count())
        .select_from(Consultation)
        .where(
            Consultation.patient_id.in_(assigned),
            Consultation.status == ConsultationStatus.SCHEDULED,
            Consultation.coordinator_id == coordinator_id,
            Consultation.deleted_at.is_(None),
        )
    )
    return result.scalar_one()


# ── Website inquiries & help queries (shared queue) ────────────────────────────
# Pre-account submissions have no patient assignment, so every coordinator sees
# the full queue. The first coordinator to reach out marks the item contacted.


async def list_booking_inquiries(
    db: AsyncSession,
    *,
    only_new: bool = False,
    limit: int = 200,
) -> list[tuple[BookingInquiry, str | None]]:
    """Return (inquiry, contacted_by_name) newest first."""
    stmt = (
        select(BookingInquiry, User.name)
        .outerjoin(User, User.id == BookingInquiry.contacted_by_user_id)
        .where(BookingInquiry.deleted_at.is_(None))
        .order_by(BookingInquiry.created_at.desc())
        .limit(limit)
    )
    if only_new:
        stmt = stmt.where(BookingInquiry.contacted_at.is_(None))
    result = await db.execute(stmt)
    return [(row.BookingInquiry, row.name) for row in result]


async def mark_inquiry_contacted(
    db: AsyncSession,
    *,
    inquiry_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Claim an inquiry as contacted. First coordinator wins; returns False when
    the inquiry doesn't exist or someone already contacted it."""
    from sqlalchemy import update

    result = await db.execute(
        update(BookingInquiry)
        .where(
            BookingInquiry.id == inquiry_id,
            BookingInquiry.contacted_at.is_(None),
            BookingInquiry.deleted_at.is_(None),
        )
        .values(
            status="contacted",
            contacted_by_user_id=user_id,
            contacted_at=datetime.now(UTC),
        )
        .returning(BookingInquiry.id)
    )
    return result.scalar_one_or_none() is not None


async def create_manual_inquiry(
    db: AsyncSession,
    *,
    created_by_user_id: uuid.UUID,
    name: str,
    phone: str,
    gender: str | None,
    condition_category: str,
    note: str | None,
) -> BookingInquiry:
    """Coordinator-entered lead (walk-in call, referral). Counts as contacted —
    the coordinator is already on the phone with them."""
    inquiry = BookingInquiry(
        name=name[:255],
        gender=gender,
        phone=phone[:20],
        condition_category=condition_category,
        intake_responses={"coordinator_note": note} if note else {},
        skipped_intake=True,
        status="contacted",
        contacted_by_user_id=created_by_user_id,
        contacted_at=datetime.now(UTC),
    )
    db.add(inquiry)
    await db.flush()
    return inquiry


async def set_inquiry_status(
    db: AsyncSession,
    *,
    inquiry_id: uuid.UUID,
    user_id: uuid.UUID,
    new_status: str,
) -> bool:
    """Move an inquiry along the pipeline. Invalid status or missing row = False."""
    from sqlalchemy import update

    if new_status not in LEAD_STATUSES:
        return False

    values: dict[str, object] = {"status": new_status}
    # First transition out of "new" stamps who reached out.
    if new_status != "new":
        inquiry = await db.scalar(
            select(BookingInquiry).where(
                BookingInquiry.id == inquiry_id, BookingInquiry.deleted_at.is_(None)
            )
        )
        if inquiry is None:
            return False
        if inquiry.contacted_at is None:
            values["contacted_by_user_id"] = user_id
            values["contacted_at"] = datetime.now(UTC)

    result = await db.execute(
        update(BookingInquiry)
        .where(BookingInquiry.id == inquiry_id, BookingInquiry.deleted_at.is_(None))
        .values(**values)
        .returning(BookingInquiry.id)
    )
    return result.scalar_one_or_none() is not None


async def set_lead_status(
    db: AsyncSession,
    *,
    lead_id: uuid.UUID,
    user_id: uuid.UUID,
    new_status: str,
) -> bool:
    """Move a help query along the pipeline. Invalid status or missing row = False."""
    from sqlalchemy import update

    if new_status not in LEAD_STATUSES:
        return False

    values: dict[str, object] = {"status": new_status}
    if new_status != "new":
        lead = await db.scalar(
            select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None))
        )
        if lead is None:
            return False
        if lead.contacted_at is None:
            values["contacted_by_user_id"] = user_id
            values["contacted_at"] = datetime.now(UTC)

    result = await db.execute(
        update(Lead)
        .where(Lead.id == lead_id, Lead.deleted_at.is_(None))
        .values(**values)
        .returning(Lead.id)
    )
    return result.scalar_one_or_none() is not None


async def list_leads(
    db: AsyncSession,
    *,
    only_new: bool = False,
    limit: int = 200,
) -> list[tuple[Lead, str | None]]:
    """Return (lead, contacted_by_name) newest first."""
    stmt = (
        select(Lead, User.name)
        .outerjoin(User, User.id == Lead.contacted_by_user_id)
        .where(Lead.deleted_at.is_(None))
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    if only_new:
        stmt = stmt.where(Lead.contacted_at.is_(None))
    result = await db.execute(stmt)
    return [(row.Lead, row.name) for row in result]


async def mark_lead_contacted(
    db: AsyncSession,
    *,
    lead_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Claim a help query as contacted. First coordinator wins."""
    from sqlalchemy import update

    result = await db.execute(
        update(Lead)
        .where(
            Lead.id == lead_id,
            Lead.contacted_at.is_(None),
            Lead.deleted_at.is_(None),
        )
        .values(
            status="contacted",
            contacted_by_user_id=user_id,
            contacted_at=datetime.now(UTC),
        )
        .returning(Lead.id)
    )
    return result.scalar_one_or_none() is not None
