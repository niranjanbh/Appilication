"""TPG pre-flight gate on the patient video-join endpoint.

GET /v1/clinic/patient/consultations/{id}/join must refuse with an actionable
409 when the patient is not consult-ready — identity not verified, or no active
telemedicine consent — instead of letting the patient into a room the doctor can
never open (open_consultation enforces the same gate). Mirrors the doctor-side gate.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    AvailabilityStatus,
    ConsentType,
    ConsultationStatus,
    DoctorStatus,
)
from app.models.clinic import Consultation, Patient
from app.models.consent import ConsentRecord
from app.models.doctor import Availability, Doctor
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-TPG-{seq:05d}"


async def _setup_confirmed_consult(
    db: AsyncSession, patient_user_id: uuid.UUID, doctor_user_id: uuid.UUID
) -> Consultation:
    doctor = Doctor(
        user_id=doctor_user_id,
        nmc_registration_number=f"NMC-TPG-{uuid.uuid4().hex[:8].upper()}",
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="TPG test doctor",
        consultation_duration_minutes_default=20,
    )
    db.add(doctor)
    await db.flush()

    patient = Patient(
        user_id=patient_user_id,
        kyros_patient_id=await _next_kyros_id(db),
        primary_conditions=["thyroid"],
    )
    db.add(patient)
    await db.flush()

    now = datetime.now(UTC)
    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(minutes=5),
        scheduled_end_at=now + timedelta(minutes=25),
        consultation_fee_paise=60000,
        status=ConsultationStatus.CONFIRMED,
        video_room_id="stub-room-tpg",
    )
    db.add(consultation)
    db.add(
        Availability(
            doctor_id=doctor.id,
            slot_start=now + timedelta(minutes=5),
            slot_end=now + timedelta(minutes=25),
            status=AvailabilityStatus.BOOKED,
        )
    )
    await db.flush()
    return consultation


async def test_join_without_telemedicine_consent_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Phone verified but no telemedicine consent → blocked with the consent reason."""
    patient_user = await create_patient_user(db_session)  # phone_verified=True
    doctor_user = await create_doctor_user(db_session)
    consultation = await _setup_confirmed_consult(
        db_session, patient_user.id, doctor_user.id
    )

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}/join",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == "telemedicine_consent_missing"


async def test_join_unverified_phone_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Unverified identity is rejected before the consent check."""
    patient_user = await create_patient_user(db_session, phone_verified=False)
    doctor_user = await create_doctor_user(db_session)
    consultation = await _setup_confirmed_consult(
        db_session, patient_user.id, doctor_user.id
    )

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}/join",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == "identity_not_verified"


async def test_join_with_consent_passes_tpg_gate(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    """With identity verified + active telemedicine consent, the gate is cleared
    (the request proceeds past the gate; a 200 with a room token is returned)."""
    import app.integrations.livekit_video as livekit_video

    monkeypatch.setattr(
        livekit_video, "generate_patient_token",
        lambda *, room_id, user_id: "stub-token",
    )

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    consultation = await _setup_confirmed_consult(
        db_session, patient_user.id, doctor_user.id
    )
    db_session.add(
        ConsentRecord(
            user_id=patient_user.id,
            consent_type=ConsentType.TELEMEDICINE,
            version="1.0",
            granted=True,
            granted_at=datetime.now(UTC),
            consent_text_hash="0" * 64,
        )
    )
    await db_session.flush()

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}/join",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["room_id"] == "stub-room-tpg"
    assert body["token"]
