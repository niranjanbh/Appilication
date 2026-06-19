"""Integration tests for care plans — doctor create/activate, patient read, RBAC, cross-user scoping."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ConsultationStatus, DoctorStatus
from app.models.audit import AuditLog
from app.models.clinic import Consultation, Patient
from app.models.doctor import Doctor
from app.models.identity import User as UserModel
from tests.conftest import (
    create_coordinator_user,
    create_doctor_user,
    create_patient_user,
    make_auth_headers,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_next_kid_counter = 0


async def _next_kyros_id(db: AsyncSession) -> str:
    global _next_kid_counter
    _next_kid_counter += 1
    return f"KYR-CP-{_next_kid_counter:06d}"


async def _doctor_profile(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=f"NMC-CP-{uuid.uuid4().hex[:8].upper()}",
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Test doctor",
        consultation_duration_minutes_default=20,
    )
    db.add(doctor)
    await db.flush()
    return doctor


async def _patient_profile(db: AsyncSession, user_id: uuid.UUID) -> Patient:
    kid = await _next_kyros_id(db)
    patient = Patient(user_id=user_id, kyros_patient_id=kid, primary_conditions=["thyroid"])
    db.add(patient)
    await db.flush()
    return patient


async def _consultation(
    db: AsyncSession, doctor: Doctor, patient: Patient
) -> Consultation:
    now = datetime.now(UTC)
    consult = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        scheduled_start_at=now,
        scheduled_end_at=now,
        status=ConsultationStatus.COMPLETED,
    )
    db.add(consult)
    await db.flush()
    return consult


_SAMPLE_ITEMS = [
    {"category": "medication", "title": "Levothyroxine 50mcg", "frequency": "Once daily", "duration": "12 weeks"},
    {"category": "diet", "title": "Increase iodine-rich foods", "description": "Seafood, eggs, dairy"},
    {"category": "exercise", "title": "Brisk walking 30 min", "frequency": "5x/week", "priority": "high"},
]


# ── Doctor: create draft ─────────────────────────────────────────────────────


async def test_create_care_plan_draft(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={
            "title": "Thyroid Management Plan",
            "condition_category": "thyroid",
            "goals": "Normalize TSH within 3 months",
            "items": _SAMPLE_ITEMS,
        },
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "draft"
    assert data["title"] == "Thyroid Management Plan"
    assert len(data["items"]) == 3
    assert data["items"][0]["category"] == "medication"
    assert data["items"][2]["priority"] == "high"


async def test_create_care_plan_requires_items(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Empty Plan", "items": []},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 422


# ── Doctor: list for consultation ─────────────────────────────────────────────


async def test_list_care_plans_for_consultation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Plan A", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )
    await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Plan B", "items": [_SAMPLE_ITEMS[0]]},
        headers=make_auth_headers(doctor_user),
    )

    resp = await client.get(
        f"/v1/doctor/consultations/{consult.id}/care-plans",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── Doctor: update draft ──────────────────────────────────────────────────────


async def test_update_care_plan_draft(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Draft Plan", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )
    plan_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/v1/doctor/care-plans/{plan_id}",
        json={
            "title": "Updated Plan",
            "goals": "New goals",
            "items": [{"category": "lifestyle", "title": "Sleep 8 hours"}],
        },
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Plan"
    assert data["goals"] == "New goals"
    assert len(data["items"]) == 1
    assert data["items"][0]["category"] == "lifestyle"


# ── Doctor: activate ──────────────────────────────────────────────────────────


async def test_activate_care_plan(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Activate Me", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )
    plan_id = create_resp.json()["id"]

    resp = await client.post(
        f"/v1/doctor/care-plans/{plan_id}/activate",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["activated_at"] is not None
    assert data["valid_from"] is not None


# ── Doctor: complete ──────────────────────────────────────────────────────────


async def test_complete_care_plan(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Complete Me", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )
    plan_id = create_resp.json()["id"]

    await client.post(
        f"/v1/doctor/care-plans/{plan_id}/activate",
        headers=make_auth_headers(doctor_user),
    )

    resp = await client.post(
        f"/v1/doctor/care-plans/{plan_id}/complete",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None


async def test_update_active_plan_returns_error(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Lock Me", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )
    plan_id = create_resp.json()["id"]

    await client.post(
        f"/v1/doctor/care-plans/{plan_id}/activate",
        headers=make_auth_headers(doctor_user),
    )

    resp = await client.patch(
        f"/v1/doctor/care-plans/{plan_id}",
        json={"title": "Should Fail"},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 404


# ── Patient: draft not visible ────────────────────────────────────────────────


async def test_draft_not_in_patient_list(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Hidden Draft", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )

    resp = await client.get(
        "/v1/clinic/patient/care-plans",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_draft_detail_returns_404_for_patient(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Hidden Draft", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )
    plan_id = create_resp.json()["id"]

    resp = await client.get(
        f"/v1/clinic/patient/care-plans/{plan_id}",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 404


# ── Patient: active visible ───────────────────────────────────────────────────


async def test_active_plan_visible_to_patient(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel) and isinstance(patient_user, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor, patient)

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Visible Plan", "condition_category": "thyroid", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )
    plan_id = create_resp.json()["id"]
    await client.post(
        f"/v1/doctor/care-plans/{plan_id}/activate",
        headers=make_auth_headers(doctor_user),
    )

    list_resp = await client.get(
        "/v1/clinic/patient/care-plans",
        headers=make_auth_headers(patient_user),
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Visible Plan"
    assert data["items"][0]["status"] == "active"
    assert "doctor_id" not in data["items"][0]

    detail_resp = await client.get(
        f"/v1/clinic/patient/care-plans/{plan_id}",
        headers=make_auth_headers(patient_user),
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["title"] == "Visible Plan"
    assert len(detail["items"]) == 3


# ── Cross-user 404 ───────────────────────────────────────────────────────────


async def test_cross_user_care_plan_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_a, UserModel) and isinstance(patient_b, UserModel)

    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient_profile_a = await _patient_profile(db_session, patient_a.id)
    await _patient_profile(db_session, patient_b.id)
    consult = await _consultation(db_session, doctor, patient_profile_a)

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Patient A Plan", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_user),
    )
    plan_id = create_resp.json()["id"]
    await client.post(
        f"/v1/doctor/care-plans/{plan_id}/activate",
        headers=make_auth_headers(doctor_user),
    )

    resp = await client.get(
        f"/v1/clinic/patient/care-plans/{plan_id}",
        headers=make_auth_headers(patient_b),
    )
    assert resp.status_code == 404

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_b.id,
            AuditLog.action == "view_care_plan",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found_or_draft"


# ── Doctor scoping ────────────────────────────────────────────────────────────


async def test_doctor_b_cannot_see_doctor_a_plans(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_a_user = await create_doctor_user(db_session)
    doctor_b_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_a_user, UserModel)
    assert isinstance(doctor_b_user, UserModel)
    assert isinstance(patient_user, UserModel)

    doctor_a = await _doctor_profile(db_session, doctor_a_user.id)
    await _doctor_profile(db_session, doctor_b_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consult = await _consultation(db_session, doctor_a, patient)

    await client.post(
        f"/v1/doctor/consultations/{consult.id}/care-plan",
        json={"title": "Doctor A Plan", "items": _SAMPLE_ITEMS},
        headers=make_auth_headers(doctor_a_user),
    )

    resp = await client.get(
        f"/v1/doctor/consultations/{consult.id}/care-plans",
        headers=make_auth_headers(doctor_b_user),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ── RBAC: no auth ────────────────────────────────────────────────────────────


async def test_doctor_create_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/care-plan",
        json={"title": "X", "items": [{"category": "medication", "title": "Y"}]},
    )
    assert resp.status_code == 401


async def test_doctor_list_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/consultations/{uuid.uuid4()}/care-plans")
    assert resp.status_code == 401


async def test_doctor_activate_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/doctor/care-plans/{uuid.uuid4()}/activate")
    assert resp.status_code == 401


async def test_patient_list_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/care-plans")
    assert resp.status_code == 401


async def test_patient_detail_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/care-plans/{uuid.uuid4()}")
    assert resp.status_code == 401


# ── RBAC: patient on doctor endpoints ─────────────────────────────────────────


async def test_patient_cannot_create_care_plan(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/care-plan",
        json={"title": "X", "items": [{"category": "medication", "title": "Y"}]},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_patient_cannot_activate_care_plan(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/care-plans/{uuid.uuid4()}/activate",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


# ── RBAC: coordinator on care plan endpoints ──────────────────────────────────


async def test_coordinator_cannot_list_care_plans(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/care-plans",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_coordinator_cannot_view_patient_care_plans(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/care-plans",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


# ── Unknown UUID returns 404 ─────────────────────────────────────────────────


async def test_patient_unknown_care_plan_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/care-plans/{uuid.uuid4()}",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 404
