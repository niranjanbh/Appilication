"""Integration tests for SOAP-structured clinical notes (P35).

Covers POST/GET /v1/doctor/consultations/{id}/notes: SOAP-only notes (no free-text
content), the existing content-only flow (regression), and the "at least one field"
validation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.models.identity import User as UserModel
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-SOAP-{seq:05d}"


async def _create_doctor_profile(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    nmc = f"NMC-SOAP-{uuid.uuid4().hex[:8].upper()}"
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=nmc,
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="SOAP test doctor",
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
    db: AsyncSession, *, patient: Patient, doctor: Doctor
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
        status=ConsultationStatus.IN_PROGRESS,
        video_room_id="stub-room-soap",
        actual_start_at=now,
    )
    db.add(consultation)
    await db.flush()
    return consultation


async def test_add_soap_only_note_returns_201_and_is_listed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/notes",
        json={
            "subjective": "Fatigue for 3 weeks, no weight change.",
            "objective": "BP 120/80, pulse 72. TSH pending.",
            "assessment": "Suspected hypothyroidism.",
            "plan": "Order TSH, FT4; review in 2 weeks.",
        },
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["content"] is None
    assert data["subjective"] == "Fatigue for 3 weeks, no weight change."
    assert data["objective"] == "BP 120/80, pulse 72. TSH pending."
    assert data["assessment"] == "Suspected hypothyroidism."
    assert data["plan"] == "Order TSH, FT4; review in 2 weeks."
    assert data["note_type"] == "clinical"
    assert data["version"] == 1

    list_resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/notes",
        headers=make_auth_headers(doctor_user),
    )
    assert list_resp.status_code == 200
    notes = list_resp.json()
    assert len(notes) == 1
    assert notes[0]["subjective"] == "Fatigue for 3 weeks, no weight change."
    assert notes[0]["content"] is None


async def test_add_content_only_note_still_works(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/notes",
        json={"content": "Free-text note, no SOAP structure."},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["content"] == "Free-text note, no SOAP structure."
    assert data["subjective"] is None
    assert data["objective"] is None
    assert data["assessment"] is None
    assert data["plan"] is None


async def test_add_note_with_no_fields_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/notes",
        json={},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 422
