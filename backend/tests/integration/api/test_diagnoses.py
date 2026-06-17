"""Integration tests for ICD-10 diagnosis capture (P35).

Covers GET /v1/doctor/icd10-codes (catalog search) and
GET/POST/DELETE /v1/doctor/consultations/{id}/diagnoses.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus
from app.models.audit import AuditLog
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.models.identity import User as UserModel
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-DGN-{seq:05d}"


async def _create_doctor_profile(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    nmc = f"NMC-DGN-{uuid.uuid4().hex[:8].upper()}"
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=nmc,
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Diagnosis test doctor",
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
        video_room_id="stub-room-diagnosis",
        actual_start_at=now,
    )
    db.add(consultation)
    await db.flush()
    return consultation


async def test_search_icd10_codes_returns_matches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)

    resp = await client.get(
        "/v1/doctor/icd10-codes",
        params={"q": "polycystic"},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    codes = [c["code"] for c in resp.json()]
    assert "E28.2" in codes


async def test_add_and_list_diagnoses(
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
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        json={
            "icd10_code": "E03.9",
            "icd10_description": "Hypothyroidism, unspecified",
            "is_primary": False,
        },
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    secondary = resp.json()
    assert secondary["icd10_code"] == "E03.9"
    assert secondary["is_primary"] is False

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        json={
            "icd10_code": "E28.2",
            "icd10_description": "Polycystic ovarian syndrome",
            "is_primary": True,
        },
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    primary = resp.json()
    assert primary["icd10_code"] == "E28.2"
    assert primary["is_primary"] is True

    list_resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        headers=make_auth_headers(doctor_user),
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 2
    # Primary diagnosis is ordered first.
    assert items[0]["icd10_code"] == "E28.2"
    assert items[0]["is_primary"] is True
    assert items[1]["icd10_code"] == "E03.9"


async def test_duplicate_diagnosis_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    body = {
        "icd10_code": "E66.9",
        "icd10_description": "Obesity, unspecified",
        "is_primary": False,
    }
    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        json=body,
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        json=body,
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "diagnosis_already_recorded"


async def test_delete_diagnosis_returns_204_and_removes_it(
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
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        json={
            "icd10_code": "L70.9",
            "icd10_description": "Acne, unspecified",
            "is_primary": False,
        },
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201
    diagnosis_id = resp.json()["id"]

    del_resp = await client.delete(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses/{diagnosis_id}",
        headers=make_auth_headers(doctor_user),
    )
    assert del_resp.status_code == 204

    list_resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        headers=make_auth_headers(doctor_user),
    )
    assert list_resp.json() == []


async def test_cross_doctor_diagnoses_access_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_a_user = await create_doctor_user(db_session)
    doctor_b_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_a_user, UserModel)
    assert isinstance(doctor_b_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor_a = await _create_doctor_profile(db_session, doctor_a_user.id)
    await _create_doctor_profile(db_session, doctor_b_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor_a)

    # GET, POST, DELETE from doctor B (not the owner) all 404.
    get_resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        headers=make_auth_headers(doctor_b_user),
    )
    assert get_resp.status_code == 404

    post_resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses",
        json={
            "icd10_code": "E11.9",
            "icd10_description": "Type 2 diabetes mellitus without complications",
            "is_primary": False,
        },
        headers=make_auth_headers(doctor_b_user),
    )
    assert post_resp.status_code == 404

    del_resp = await client.delete(
        f"/v1/doctor/consultations/{consultation.id}/diagnoses/{uuid.uuid4()}",
        headers=make_auth_headers(doctor_b_user),
    )
    assert del_resp.status_code == 404

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == doctor_b_user.id,
            AuditLog.action == "list_diagnoses",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"
