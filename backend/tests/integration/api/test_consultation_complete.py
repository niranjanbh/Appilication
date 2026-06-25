"""Integration tests for POST /v1/doctor/consultations/{id}/complete.

Covers the IN_PROGRESS -> COMPLETED transition added in P34: success stamps
actual_end_at; attempting to complete a consult that was never opened
(CONFIRMED) is rejected with consultation_not_in_progress.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-CMP-{seq:05d}"


async def _create_doctor_profile(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    nmc = f"NMC-CMP-{uuid.uuid4().hex[:8].upper()}"
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=nmc,
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Completion test doctor",
        consultation_duration_minutes_default=20,
    )
    db.add(doctor)
    await db.flush()
    return doctor


async def _create_patient_profile(db: AsyncSession, user_id: uuid.UUID) -> Patient:
    kid = await _next_kyros_id(db)
    patient = Patient(
        user_id=user_id,
        kyros_patient_id=kid,
        primary_conditions=["thyroid"],
    )
    db.add(patient)
    await db.flush()
    return patient


async def _create_consultation(
    db: AsyncSession,
    *,
    patient: Patient,
    doctor: Doctor,
    status: ConsultationStatus,
    actual_start_at: datetime | None = None,
) -> Consultation:
    now = datetime.now(UTC)
    slot = Availability(
        doctor_id=doctor.id,
        slot_start=now + timedelta(hours=2),
        slot_end=now + timedelta(hours=2, minutes=20),
        status=AvailabilityStatus.BOOKED,
    )
    db.add(slot)
    await db.flush()

    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(hours=2),
        scheduled_end_at=now + timedelta(hours=2, minutes=20),
        consultation_fee_paise=60000,
        status=status,
        video_room_id="stub-room-complete",
        actual_start_at=actual_start_at,
    )
    db.add(consultation)
    await db.flush()
    return consultation


async def test_complete_consultation_in_progress_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.db.enums import NoteType
    from app.models.clinic import DoctorNote
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    consultation = await _create_consultation(
        db_session,
        patient=patient,
        doctor=doctor,
        status=ConsultationStatus.IN_PROGRESS,
        actual_start_at=datetime.now(UTC),
    )
    # Completion requires at least one doctor note on record.
    db_session.add(
        DoctorNote(
            consultation_id=consultation.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
            note_type=NoteType.CLINICAL,
            content="Reviewed; plan documented.",
        )
    )
    await db_session.flush()

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/complete",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(consultation.id)
    assert data["status"] == "completed"
    assert data["actual_end_at"] is not None

    await db_session.refresh(consultation)
    assert consultation.status == ConsultationStatus.COMPLETED
    assert consultation.actual_end_at is not None


async def test_complete_consultation_confirmed_returns_409_not_in_progress(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A consult that was never opened (still CONFIRMED) cannot be completed."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, status=ConsultationStatus.CONFIRMED
    )

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/complete",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "consultation_not_in_progress"

    await db_session.refresh(consultation)
    assert consultation.status == ConsultationStatus.CONFIRMED


async def test_complete_consultation_stops_active_recording(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Completing a consult with a live egress stops the recording and clears the id.

    Security rule #20: a consented recording must be stoppable on demand, not left
    to LiveKit's empty-timeout. Persisting the egress id is what makes that possible.
    """
    import app.integrations.livekit_video as livekit_video
    from app.db.enums import NoteType
    from app.models.clinic import DoctorNote
    from app.models.identity import User as UserModel

    captured: dict[str, str] = {}

    async def _fake_stop(*, egress_id: str) -> None:
        captured["egress_id"] = egress_id

    monkeypatch.setattr(livekit_video, "stop_recording", _fake_stop)

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    consultation = await _create_consultation(
        db_session,
        patient=patient,
        doctor=doctor,
        status=ConsultationStatus.IN_PROGRESS,
        actual_start_at=datetime.now(UTC),
    )
    # An in-flight recording, plus the doctor note completion requires.
    consultation.recording_egress_id = "EG_test_egress_123"
    db_session.add(
        DoctorNote(
            consultation_id=consultation.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
            note_type=NoteType.CLINICAL,
            content="Reviewed; plan documented.",
        )
    )
    await db_session.flush()

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/complete",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text

    # stop_recording was called with the persisted egress id, and it was cleared.
    assert captured.get("egress_id") == "EG_test_egress_123"
    await db_session.refresh(consultation)
    assert consultation.status == ConsultationStatus.COMPLETED
    assert consultation.recording_egress_id is None


async def test_complete_consultation_cross_doctor_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Doctor B cannot complete doctor A's consultation."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_a_user = await create_doctor_user(db_session)
    doctor_b_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_a_user, UserModel)
    assert isinstance(doctor_b_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor_a = await _create_doctor_profile(db_session, doctor_a_user.id)
    await _create_doctor_profile(db_session, doctor_b_user.id)
    consultation = await _create_consultation(
        db_session,
        patient=patient,
        doctor=doctor_a,
        status=ConsultationStatus.IN_PROGRESS,
        actual_start_at=datetime.now(UTC),
    )

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/complete",
        headers=make_auth_headers(doctor_b_user),
    )
    assert resp.status_code == 404
