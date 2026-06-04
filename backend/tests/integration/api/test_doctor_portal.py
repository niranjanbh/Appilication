"""Integration tests for doctor portal foundation endpoints.

Covers:
  GET/PATCH /v1/doctor/me
  GET       /v1/doctor/patients
  GET       /v1/doctor/patients/{id}
  GET       /v1/doctor/consultations
  GET       /v1/doctor/consultations/{id}

Security:
  - All endpoints require DOCTOR role (patient/coordinator → 403)
  - Patient detail: cross-doctor 404 + audit denial logged
  - Consultation detail: cross-doctor 404 + audit denial logged
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
from tests.conftest import (
    create_coordinator_user,
    create_doctor_user,
    create_patient_user,
    make_auth_headers,
)

# ── Shared helpers ─────────────────────────────────────────────────────────────


async def _kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-DP-{seq:05d}"


async def _make_doctor(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    doc = Doctor(
        user_id=user_id,
        nmc_registration_number=f"NMC-D-{uuid.uuid4().hex[:8].upper()}",
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Test doctor",
        consultation_duration_minutes_default=20,
    )
    db.add(doc)
    await db.flush()
    return doc


async def _make_patient(db: AsyncSession, user_id: uuid.UUID) -> Patient:
    kid = await _kyros_id(db)
    pt = Patient(user_id=user_id, kyros_patient_id=kid, primary_conditions=["thyroid"])
    db.add(pt)
    await db.flush()
    return pt


async def _make_consultation(
    db: AsyncSession,
    *,
    patient: Patient,
    doctor: Doctor,
    hours_offset: int = 2,
    status: ConsultationStatus = ConsultationStatus.CONFIRMED,
) -> Consultation:
    now = datetime.now(UTC)
    slot = Availability(
        doctor_id=doctor.id,
        slot_start=now + timedelta(hours=hours_offset),
        slot_end=now + timedelta(hours=hours_offset, minutes=20),
        status=AvailabilityStatus.BOOKED,
    )
    db.add(slot)
    await db.flush()
    c = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(hours=hours_offset),
        scheduled_end_at=now + timedelta(hours=hours_offset, minutes=20),
        consultation_fee_paise=60000,
        status=status,
    )
    db.add(c)
    await db.flush()
    return c


# ── /v1/doctor/me ─────────────────────────────────────────────────────────────


async def test_get_me_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/me")
    assert resp.status_code == 401


async def test_get_me_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    resp = await client.get("/v1/doctor/me", headers=make_auth_headers(patient_user))
    assert resp.status_code == 403


async def test_get_me_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/doctor/me", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_get_me_returns_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor_user = await create_doctor_user(db_session)
    assert isinstance(doctor_user, UserModel)
    await _make_doctor(db_session, doctor_user.id)

    resp = await client.get("/v1/doctor/me", headers=make_auth_headers(doctor_user))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == doctor_user.name
    assert "nmc_registration_number" in data
    assert "specialty" in data


async def test_patch_me_updates_bio(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor_user = await create_doctor_user(db_session)
    assert isinstance(doctor_user, UserModel)
    await _make_doctor(db_session, doctor_user.id)

    resp = await client.patch(
        "/v1/doctor/me",
        json={"bio_short": "Updated bio"},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["bio_short"] == "Updated bio"


async def test_patch_me_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch("/v1/doctor/me", json={"bio_short": "x"})
    assert resp.status_code == 401


# ── /v1/doctor/patients ────────────────────────────────────────────────────────


async def test_list_patients_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/patients")
    assert resp.status_code == 401


async def test_list_patients_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    resp = await client.get("/v1/doctor/patients", headers=make_auth_headers(patient_user))
    assert resp.status_code == 403


async def test_list_patients_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/doctor/patients", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_list_patients_shows_panel_only(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    other_patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    assert isinstance(other_patient_user, UserModel)

    doctor = await _make_doctor(db_session, doctor_user.id)
    panel_patient = await _make_patient(db_session, patient_user.id)
    # This patient has a consultation with our doctor
    await _make_consultation(db_session, patient=panel_patient, doctor=doctor)
    # other_patient has no consultation with our doctor — not in panel

    resp = await client.get("/v1/doctor/patients", headers=make_auth_headers(doctor_user))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    ids = [item["patient_id"] for item in data["items"]]
    assert str(panel_patient.id) in ids


async def test_get_patient_detail_cross_doctor_returns_404_and_audits(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Doctor A cannot view patients of doctor B."""
    from app.models.identity import User as UserModel

    doctor_a_user = await create_doctor_user(db_session)
    doctor_b_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_a_user, UserModel)
    assert isinstance(doctor_b_user, UserModel)
    assert isinstance(patient_user, UserModel)

    await _make_doctor(db_session, doctor_a_user.id)
    doctor_b = await _make_doctor(db_session, doctor_b_user.id)
    patient_b = await _make_patient(db_session, patient_user.id)
    await _make_consultation(db_session, patient=patient_b, doctor=doctor_b)

    resp = await client.get(
        f"/v1/doctor/patients/{patient_b.id}",
        headers=make_auth_headers(doctor_a_user),
    )
    assert resp.status_code == 404

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == doctor_a_user.id,
            AuditLog.action == "view_panel_patient",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


async def test_get_patient_detail_returns_demographics_not_lab_values(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Patient detail returns demographics; no lab values (checked by field absence)."""
    from app.models.identity import User as UserModel

    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)

    doctor = await _make_doctor(db_session, doctor_user.id)
    patient = await _make_patient(db_session, patient_user.id)
    await _make_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.get(
        f"/v1/doctor/patients/{patient.id}",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "kyros_patient_id" in data
    assert "primary_conditions" in data
    assert "consultation_counts" in data
    # Lab values are never in this response
    assert "lab_values" not in data
    assert "parsed_json" not in data


# ── /v1/doctor/consultations ──────────────────────────────────────────────────


async def test_list_consultations_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/consultations")
    assert resp.status_code == 401


async def test_list_consultations_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/doctor/consultations", headers=make_auth_headers(patient_user)
    )
    assert resp.status_code == 403


async def test_list_consultations_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        "/v1/doctor/consultations", headers=make_auth_headers(coord)
    )
    assert resp.status_code == 403


async def test_list_consultations_today_filter(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)

    doctor = await _make_doctor(db_session, doctor_user.id)
    patient = await _make_patient(db_session, patient_user.id)
    # Consultation starting in 1 hour = today
    await _make_consultation(db_session, patient=patient, doctor=doctor, hours_offset=1)

    resp = await client.get(
        "/v1/doctor/consultations?filter=today",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 1
    assert all(item["patient_name"] for item in data["items"])


async def test_get_consultation_cross_doctor_returns_404_and_audits(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor_a_user = await create_doctor_user(db_session)
    doctor_b_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_a_user, UserModel)
    assert isinstance(doctor_b_user, UserModel)
    assert isinstance(patient_user, UserModel)

    await _make_doctor(db_session, doctor_a_user.id)
    doctor_b = await _make_doctor(db_session, doctor_b_user.id)
    patient = await _make_patient(db_session, patient_user.id)
    consult_b = await _make_consultation(db_session, patient=patient, doctor=doctor_b)

    resp = await client.get(
        f"/v1/doctor/consultations/{consult_b.id}",
        headers=make_auth_headers(doctor_a_user),
    )
    assert resp.status_code == 404

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == doctor_a_user.id,
            AuditLog.action == "view_consultation",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


async def test_get_consultation_detail_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)

    doctor = await _make_doctor(db_session, doctor_user.id)
    patient = await _make_patient(db_session, patient_user.id)
    consult = await _make_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.get(
        f"/v1/doctor/consultations/{consult.id}",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(consult.id)
    assert data["patient_name"] == patient_user.name  # type: ignore[attr-defined]
    assert data["condition_category"] == "thyroid"
