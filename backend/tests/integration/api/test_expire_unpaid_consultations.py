"""Tests for the unpaid-scheduled expiry path (slot-leak fix).

A SCHEDULED consultation only leaves that state by being paid+confirmed,
cancelled, or rescheduled. One still SCHEDULED after its start time passed was
never paid (assign flow) or never intake-confirmed (coordinator book flow), and
must be cancelled with its Availability slot released — otherwise the slot stays
BOOKED forever, leaking doctor capacity.

Covers the repository selector `get_expired_unpaid_consultations` and the
cancel -> release_slot sequence the beat task performs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.repositories import consultations as consultations_repo
from tests.conftest import create_doctor_user, create_patient_user


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-EXP-{seq:05d}"


async def _create_doctor_profile(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=f"NMC-EXP-{uuid.uuid4().hex[:8].upper()}",
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Expiry test doctor",
        consultation_duration_minutes_default=20,
    )
    db.add(doctor)
    await db.flush()
    return doctor


async def _create_patient_profile(db: AsyncSession, user_id: uuid.UUID) -> Patient:
    patient = Patient(
        user_id=user_id,
        kyros_patient_id=await _next_kyros_id(db),
        primary_conditions=["thyroid"],
    )
    db.add(patient)
    await db.flush()
    return patient


async def _create_scheduled_consult(
    db: AsyncSession,
    *,
    patient: Patient,
    doctor: Doctor,
    start_at: datetime,
    status: ConsultationStatus = ConsultationStatus.SCHEDULED,
) -> tuple[Consultation, Availability]:
    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=start_at,
        scheduled_end_at=start_at + timedelta(minutes=20),
        consultation_fee_paise=60000,
        status=status,
    )
    db.add(consultation)
    await db.flush()

    slot = Availability(
        doctor_id=doctor.id,
        slot_start=start_at,
        slot_end=start_at + timedelta(minutes=20),
        status=AvailabilityStatus.BOOKED,
        consultation_id=consultation.id,
    )
    db.add(slot)
    await db.flush()
    return consultation, slot


async def test_selector_picks_past_scheduled_only(db_session: AsyncSession) -> None:
    """Past SCHEDULED is selected; future SCHEDULED, CONFIRMED, and COMPLETED are not."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)

    now = datetime.now(UTC)
    past = now - timedelta(hours=2)
    future = now + timedelta(hours=2)

    expired, _ = await _create_scheduled_consult(
        db_session, patient=patient, doctor=doctor, start_at=past
    )
    # Future scheduled — still has a chance to be paid; must be left alone.
    await _create_scheduled_consult(
        db_session, patient=patient, doctor=doctor, start_at=future,
        status=ConsultationStatus.SCHEDULED,
    )
    # Past CONFIRMED — owned by the no-show task, not this one.
    await _create_scheduled_consult(
        db_session, patient=patient, doctor=doctor, start_at=past - timedelta(hours=1),
        status=ConsultationStatus.CONFIRMED,
    )

    rows = await consultations_repo.get_expired_unpaid_consultations(
        db_session, grace_minutes=30
    )
    ids = {c.id for c in rows}
    assert expired.id in ids
    assert all(c.status == ConsultationStatus.SCHEDULED for c in rows)
    # Exactly the one past-scheduled consult for this doctor.
    assert sum(1 for c in rows if c.doctor_id == doctor.id) == 1


async def test_grace_window_excludes_just_past(db_session: AsyncSession) -> None:
    """A consult only just past its start (inside the grace window) is not expired yet."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)

    just_past = datetime.now(UTC) - timedelta(minutes=5)
    consult, _ = await _create_scheduled_consult(
        db_session, patient=patient, doctor=doctor, start_at=just_past
    )

    rows = await consultations_repo.get_expired_unpaid_consultations(
        db_session, grace_minutes=30
    )
    assert consult.id not in {c.id for c in rows}


async def test_cancel_releases_slot(db_session: AsyncSession) -> None:
    """The task's cancel -> release sequence frees the BOOKED slot back to AVAILABLE."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)

    past = datetime.now(UTC) - timedelta(hours=2)
    consult, slot = await _create_scheduled_consult(
        db_session, patient=patient, doctor=doctor, start_at=past
    )

    updated = await consultations_repo.update_consultation(
        db_session,
        consultation_id=consult.id,
        status=ConsultationStatus.CANCELLED,
        cancellation_reason="Auto-cancelled — payment not completed before the scheduled time.",
    )
    assert updated is not None
    await consultations_repo.release_slot(db_session, consultation_id=consult.id)
    await db_session.flush()

    await db_session.refresh(consult)
    await db_session.refresh(slot)
    assert consult.status == ConsultationStatus.CANCELLED
    assert slot.status == AvailabilityStatus.AVAILABLE
    assert slot.consultation_id is None
