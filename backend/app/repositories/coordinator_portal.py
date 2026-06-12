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

from app.db.enums import AvailabilityStatus, ConsultationStatus
from app.models.admin import Coordinator
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.models.identity import User
from app.models.public import BookingInquiry, Lead

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
    consultation_fee_paise: int = 50000,
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
