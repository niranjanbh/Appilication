from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus
from app.models.clinic import Consultation, PreConsultationReport
from app.models.doctor import Availability, Doctor
from app.models.identity import User


async def get_consultation_for_patient(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> Consultation | None:
    """Resource-scoped fetch — returns None for other patients' consultations or missing rows."""
    from app.models.clinic import Patient

    result = await db.execute(
        select(Consultation)
        .join(Patient, Patient.id == Consultation.patient_id)
        .where(
            Consultation.id == consultation_id,
            Patient.user_id == patient_user_id,
            Consultation.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_doctor_display_map(
    db: AsyncSession, doctor_ids: set[uuid.UUID]
) -> dict[uuid.UUID, tuple[str, list[Any]]]:
    """Map doctor_id -> (name, specialty) so patient-facing responses can show
    the assigned doctor. None ids are ignored; empty input returns {}."""
    ids = {d for d in doctor_ids if d is not None}
    if not ids:
        return {}
    result = await db.execute(
        select(Doctor.id, User.name, Doctor.specialty)
        .join(User, User.id == Doctor.user_id)
        .where(Doctor.id.in_(ids))
    )
    return {row.id: (row.name, list(row.specialty or [])) for row in result}


async def list_consultations_for_patient(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    status: ConsultationStatus | None = None,
    upcoming: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Consultation], int]:
    """Return paginated consultations for a patient with total count."""
    from sqlalchemy import func

    from app.models.clinic import Patient

    base = (
        select(Consultation)
        .join(Patient, Patient.id == Consultation.patient_id)
        .where(Patient.user_id == patient_user_id, Consultation.deleted_at.is_(None))
    )

    if status is not None:
        base = base.where(Consultation.status == status)

    now = datetime.now(UTC)
    if upcoming is True:
        base = base.where(
            Consultation.status.in_([ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED]),
            Consultation.scheduled_start_at >= now,
        )
    elif upcoming is False:
        base = base.where(
            Consultation.status.in_(
                [ConsultationStatus.COMPLETED, ConsultationStatus.CANCELLED, ConsultationStatus.NO_SHOW]
            )
        )

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    items_result = await db.execute(
        base.order_by(Consultation.scheduled_start_at.desc()).offset(offset).limit(page_size)
    )
    return list(items_result.scalars().all()), total


async def get_available_slots(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> list[Availability]:
    result = await db.execute(
        select(Availability).where(
            Availability.doctor_id == doctor_id,
            Availability.status == AvailabilityStatus.AVAILABLE,
            Availability.slot_start >= date_from,
            Availability.slot_start < date_to,
        ).order_by(Availability.slot_start)
    )
    return list(result.scalars().all())


async def get_patient_record(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> Any | None:
    """Return the kc_patients row for a user, or None if not found."""
    from app.models.clinic import Patient

    result = await db.execute(
        select(Patient).where(Patient.user_id == user_id, Patient.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def lock_and_book_slot(
    db: AsyncSession,
    *,
    slot_id: uuid.UUID,
    consultation_id: uuid.UUID,
) -> Availability | None:
    """SELECT FOR UPDATE SKIP LOCKED — atomically claims the slot.

    Returns the locked Availability if still available, None if already taken.
    """
    result = await db.execute(
        select(Availability)
        .where(
            Availability.id == slot_id,
            Availability.status == AvailabilityStatus.AVAILABLE,
        )
        .with_for_update(skip_locked=True)
    )
    slot = result.scalar_one_or_none()
    if slot is None:
        return None

    slot.status = AvailabilityStatus.BOOKED
    slot.consultation_id = consultation_id
    await db.flush()
    return slot


async def release_slot(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> None:
    """Return a slot to available status when a consultation is cancelled."""
    await db.execute(
        update(Availability)
        .where(Availability.consultation_id == consultation_id)
        .values(
            status=AvailabilityStatus.AVAILABLE,
            consultation_id=None,
            updated_at=datetime.now(UTC),
        )
    )


async def create_consultation(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    condition_category: str,
    consultation_type: str,
    scheduled_start_at: datetime,
    scheduled_end_at: datetime,
    consultation_fee_paise: int,
    coordinator_id: uuid.UUID | None = None,
    coupon_id: uuid.UUID | None = None,
    discount_paise: int = 0,
) -> Consultation:
    consultation = Consultation(
        patient_id=patient_id,
        doctor_id=doctor_id,
        coordinator_id=coordinator_id,
        condition_category=condition_category,
        consultation_type=consultation_type,
        scheduled_start_at=scheduled_start_at,
        scheduled_end_at=scheduled_end_at,
        consultation_fee_paise=consultation_fee_paise,
        coupon_id=coupon_id,
        discount_paise=discount_paise,
        status=ConsultationStatus.SCHEDULED,
    )
    db.add(consultation)
    await db.flush()
    return consultation


async def create_consultation_request(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    condition_category: str,
    consultation_type: str,
    coordinator_id: uuid.UUID | None = None,
    requirement_notes: str | None = None,
    preferred_time_window: str | None = None,
) -> Consultation:
    """Create a patient-submitted consultation request (status='requested').

    No doctor, slot, fee, or payment yet — a coordinator assigns those later.
    """
    consultation = Consultation(
        patient_id=patient_id,
        doctor_id=None,
        coordinator_id=coordinator_id,
        condition_category=condition_category,
        consultation_type=consultation_type,
        scheduled_start_at=None,
        scheduled_end_at=None,
        consultation_fee_paise=None,
        requirement_notes=requirement_notes,
        preferred_time_window=preferred_time_window,
        status=ConsultationStatus.REQUESTED,
    )
    db.add(consultation)
    await db.flush()
    return consultation


async def update_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    **fields: Any,
) -> Consultation | None:
    result = await db.execute(
        update(Consultation)
        .where(Consultation.id == consultation_id)
        .values(**fields, updated_at=datetime.now(UTC))
        .returning(Consultation)
    )
    return result.scalar_one_or_none()


async def get_consultation_for_doctor(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> Consultation | None:
    """Resource-scoped fetch for a doctor — returns None for other doctors' consultations."""
    result = await db.execute(
        select(Consultation)
        .join(Doctor, Doctor.id == Consultation.doctor_id)
        .where(
            Consultation.id == consultation_id,
            Doctor.id == doctor_id,
            Consultation.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_doctor_record(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> Doctor | None:
    """Return the dr_doctors row for a user, or None if not found."""
    result = await db.execute(
        select(Doctor).where(Doctor.user_id == user_id, Doctor.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_patient_user_for_consultation(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
) -> User | None:
    """Return the users row for the patient on a consultation (joins kc_patients -> users)."""
    from app.models.clinic import Patient

    result = await db.execute(
        select(User)
        .join(Patient, Patient.user_id == User.id)
        .where(Patient.id == patient_id)
    )
    return result.scalar_one_or_none()


async def get_unprovisioned_consultations_in_window(
    db: AsyncSession,
    *,
    window_minutes: int = 15,
) -> list[Consultation]:
    """Return consultations starting within *window_minutes* that have no video_room_id yet."""
    now = datetime.now(UTC)
    window_end = now + timedelta(minutes=window_minutes)
    result = await db.execute(
        select(Consultation).where(
            Consultation.status.in_([ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED]),
            Consultation.scheduled_start_at >= now,
            Consultation.scheduled_start_at <= window_end,
            Consultation.video_room_id.is_(None),
            Consultation.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def update_consultation_video_room(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    video_room_id: str,
) -> None:
    """Atomically set video_room_id on a consultation row."""
    await db.execute(
        update(Consultation)
        .where(Consultation.id == consultation_id)
        .values(video_room_id=video_room_id, updated_at=datetime.now(UTC))
    )


async def get_pre_consult_report_for_patient(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> PreConsultationReport | None:
    from app.models.clinic import Patient

    result = await db.execute(
        select(PreConsultationReport)
        .join(Patient, Patient.id == PreConsultationReport.patient_id)
        .join(Consultation, Consultation.id == PreConsultationReport.consultation_id)
        .where(
            PreConsultationReport.consultation_id == consultation_id,
            Patient.user_id == patient_user_id,
            Patient.deleted_at.is_(None),
            Consultation.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def has_prior_completed_consultation(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    exclude_consultation_id: uuid.UUID,
) -> bool:
    """Return True if the patient has at least one COMPLETED consultation other than
    the current one. Used to gate refill_allowed on prescriptions."""
    result = await db.execute(
        select(
            exists().where(
                Consultation.patient_id == patient_id,
                Consultation.status == ConsultationStatus.COMPLETED,
                Consultation.id != exclude_consultation_id,
                Consultation.deleted_at.is_(None),
            )
        )
    )
    return bool(result.scalar())
