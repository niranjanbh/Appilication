"""Coordinator no-show action (coordinator_portal.mark_no_show_for_coordinator).

A coordinator may mark a past consultation for one of their assigned patients as
a NO_SHOW: the slot is released and no refund is issued. Scoping, status, and the
"must have started" guard mirror the super-admin path but stay coordinator-scoped.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    AvailabilityStatus,
    ConsultationStatus,
    CoordinatorStatus,
    DoctorStatus,
)
from app.models.admin import Coordinator
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.repositories import coordinator_portal as coord_repo
from tests.conftest import (
    create_coordinator_user,
    create_doctor_user,
    create_patient_user,
)


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-NSH-{seq:05d}"


async def _patient(db: AsyncSession, user_id: uuid.UUID) -> Patient:
    p = Patient(
        user_id=user_id,
        kyros_patient_id=await _next_kyros_id(db),
        primary_conditions=["thyroid"],
    )
    db.add(p)
    await db.flush()
    return p


async def _doctor(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    d = Doctor(
        user_id=user_id,
        nmc_registration_number=f"NMC-NSH-{uuid.uuid4().hex[:8].upper()}",
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="No-show test doctor",
        consultation_duration_minutes_default=20,
    )
    db.add(d)
    await db.flush()
    return d


async def _consult(
    db: AsyncSession,
    *,
    patient: Patient,
    doctor: Doctor,
    coordinator_id: uuid.UUID,
    start_at: datetime,
    status: ConsultationStatus = ConsultationStatus.CONFIRMED,
) -> tuple[Consultation, Availability]:
    c = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        coordinator_id=coordinator_id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=start_at,
        scheduled_end_at=start_at + timedelta(minutes=20),
        consultation_fee_paise=60000,
        status=status,
    )
    db.add(c)
    await db.flush()
    slot = Availability(
        doctor_id=doctor.id,
        slot_start=start_at,
        slot_end=start_at + timedelta(minutes=20),
        status=AvailabilityStatus.BOOKED,
        consultation_id=c.id,
    )
    db.add(slot)
    await db.flush()
    return c, slot


async def _coordinator(db: AsyncSession, patient_ids: list[str]) -> Coordinator:
    user = await create_coordinator_user(db)
    coord = Coordinator(
        user_id=user.id,
        status=CoordinatorStatus.ACTIVE,
        assigned_patient_ids=patient_ids,
    )
    db.add(coord)
    await db.flush()
    return coord


async def test_no_show_marks_and_releases_slot(db_session: AsyncSession) -> None:
    patient = await _patient(db_session, (await create_patient_user(db_session)).id)
    doctor = await _doctor(db_session, (await create_doctor_user(db_session)).id)
    coord = await _coordinator(db_session, [str(patient.id)])

    past = datetime.now(UTC) - timedelta(hours=1)
    consult, slot = await _consult(
        db_session, patient=patient, doctor=doctor, coordinator_id=coord.id, start_at=past
    )

    result = await coord_repo.mark_no_show_for_coordinator(
        db_session, coordinator_id=coord.id, consultation_id=consult.id
    )
    assert result is not None
    await db_session.refresh(consult)
    await db_session.refresh(slot)
    assert consult.status == ConsultationStatus.NO_SHOW
    assert slot.status == AvailabilityStatus.AVAILABLE
    assert slot.consultation_id is None


async def test_no_show_future_consult_rejected(db_session: AsyncSession) -> None:
    """A consultation that hasn't started yet cannot be no-showed."""
    patient = await _patient(db_session, (await create_patient_user(db_session)).id)
    doctor = await _doctor(db_session, (await create_doctor_user(db_session)).id)
    coord = await _coordinator(db_session, [str(patient.id)])

    future = datetime.now(UTC) + timedelta(hours=2)
    consult, _ = await _consult(
        db_session, patient=patient, doctor=doctor, coordinator_id=coord.id, start_at=future
    )

    result = await coord_repo.mark_no_show_for_coordinator(
        db_session, coordinator_id=coord.id, consultation_id=consult.id
    )
    assert result is None
    await db_session.refresh(consult)
    assert consult.status == ConsultationStatus.CONFIRMED


async def test_no_show_unassigned_patient_rejected(db_session: AsyncSession) -> None:
    """A coordinator cannot no-show a consultation for a patient they aren't assigned."""
    patient = await _patient(db_session, (await create_patient_user(db_session)).id)
    doctor = await _doctor(db_session, (await create_doctor_user(db_session)).id)
    # Coordinator assigned to NOBODY.
    coord = await _coordinator(db_session, [])

    past = datetime.now(UTC) - timedelta(hours=1)
    consult, _ = await _consult(
        db_session, patient=patient, doctor=doctor, coordinator_id=coord.id, start_at=past
    )

    result = await coord_repo.mark_no_show_for_coordinator(
        db_session, coordinator_id=coord.id, consultation_id=consult.id
    )
    assert result is None
    await db_session.refresh(consult)
    assert consult.status == ConsultationStatus.CONFIRMED
