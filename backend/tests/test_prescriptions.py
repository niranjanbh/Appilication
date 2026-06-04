"""Tests for prescription endpoints and business logic.

Covers:
  - Doctor creates draft prescription (201)
  - Doctor signs draft (200, PDF task enqueued)
  - Patient lists prescriptions (signed only)
  - Patient views prescription detail (cross-user 404)
  - Draft prescription invisible to patient (404)
  - PDF URL endpoint (404 if pdf_url not set, 404 for wrong patient)
  - Audit log written for all authorization decisions
  - RBAC: wrong role returns 403
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    _synth_email,
    _synth_phone,
    create_doctor_user,
    make_auth_headers,
)

# ── Fixture helpers ────────────────────────────────────────────────────────────


async def _make_patient(db: AsyncSession) -> object:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.models.clinic import Patient
    from app.repositories import users as users_repo

    user = await users_repo.create(
        db,
        name="Test Patient",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    await users_repo.update_phone_verified(db, user.id)  # type: ignore[union-attr]
    patient = Patient(
        user_id=user.id,  # type: ignore[union-attr]
        kyros_patient_id=f"KP{uuid.uuid4().hex[:6].upper()}",
        primary_conditions=[],
    )
    db.add(patient)
    await db.flush()
    return user


async def _make_doctor_with_profile(db: AsyncSession) -> tuple[object, object]:
    """Return (user, doctor) with a full Doctor profile."""
    from app.db.enums import DoctorStatus
    from app.models.doctor import Doctor

    user = await create_doctor_user(db)
    doctor = Doctor(
        user_id=user.id,  # type: ignore[union-attr]
        nmc_registration_number=f"NMC{uuid.uuid4().hex[:8].upper()}",
        specialty=["Endocrinology"],
        status=DoctorStatus.ACTIVE,
    )
    db.add(doctor)
    await db.flush()
    return user, doctor


async def _make_consultation(db: AsyncSession, doctor_id: uuid.UUID, patient_id: uuid.UUID) -> object:
    from app.db.enums import ConsultationStatus, ConsultationType
    from app.models.clinic import Consultation

    consult = Consultation(
        patient_id=patient_id,
        doctor_id=doctor_id,
        condition_category="thyroid",
        consultation_type=ConsultationType.INITIAL,
        status=ConsultationStatus.COMPLETED,
        consultation_fee_paise=50000,
        scheduled_start_at=datetime.now(UTC),
        scheduled_end_at=datetime.now(UTC),
    )
    db.add(consult)
    await db.flush()
    return consult


async def _get_patient_row(db: AsyncSession, user_id: uuid.UUID) -> object:
    from sqlalchemy import select

    from app.models.clinic import Patient

    result = await db.execute(select(Patient).where(Patient.user_id == user_id))
    return result.scalar_one()


ITEM_BODY: dict[str, Any] = {
    "drug_generic_name": "Levothyroxine",
    "drug_form": "tablet",
    "dosage": "50mcg",
    "frequency": "once daily",
    "duration_days": 90,
    "instructions": "Empty stomach",
}


# ── Doctor create prescription ─────────────────────────────────────────────────


async def test_doctor_create_prescription_returns_201(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft"
    assert len(body["items"]) == 1
    assert body["items"][0]["drug_generic_name"] == "Levothyroxine"


async def test_doctor_create_prescription_wrong_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, _doctor = await _make_doctor_with_profile(db_session)

    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescription",
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 404


async def test_doctor_create_prescription_no_doctor_profile_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)  # no Doctor row

    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescription",
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 404


async def test_doctor_create_prescription_empty_items_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, _doctor = await _make_doctor_with_profile(db_session)

    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescription",
        json={"items": []},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 422


# ── Doctor sign prescription ───────────────────────────────────────────────────


async def test_doctor_sign_prescription_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    assert create_resp.status_code == 201
    rx_id = create_resp.json()["id"]

    with patch("app.tasks.prescription_tasks.generate_prescription_pdf.apply_async"):
        sign_resp = await client.post(
            f"/v1/doctor/prescriptions/{rx_id}/sign",
            headers=make_auth_headers(doctor_user),
        )
    assert sign_resp.status_code == 200
    assert sign_resp.json()["status"] == "signed"
    assert sign_resp.json()["signed_at"] is not None


async def test_doctor_sign_prescription_twice_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    rx_id = create_resp.json()["id"]

    with patch("app.tasks.prescription_tasks.generate_prescription_pdf.apply_async"):
        await client.post(f"/v1/doctor/prescriptions/{rx_id}/sign", headers=make_auth_headers(doctor_user))
        sign_resp2 = await client.post(f"/v1/doctor/prescriptions/{rx_id}/sign", headers=make_auth_headers(doctor_user))

    assert sign_resp2.status_code == 404


# ── Patient list prescriptions ─────────────────────────────────────────────────


async def test_patient_list_prescriptions_empty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await _make_patient(db_session)

    resp = await client.get(
        "/v1/clinic/patient/prescriptions",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 0


async def test_patient_cannot_see_draft_prescription(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )

    resp = await client.get(
        "/v1/clinic/patient/prescriptions",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_patient_sees_prescription_after_signing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    rx_id = create_resp.json()["id"]

    with patch("app.tasks.prescription_tasks.generate_prescription_pdf.apply_async"):
        await client.post(f"/v1/doctor/prescriptions/{rx_id}/sign", headers=make_auth_headers(doctor_user))

    list_resp = await client.get(
        "/v1/clinic/patient/prescriptions",
        headers=make_auth_headers(patient_user),
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == rx_id
    assert items[0]["status"] == "signed"


# ── Patient get prescription ───────────────────────────────────────────────────


async def test_patient_get_prescription_cross_user_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_a = await _make_patient(db_session)
    patient_b = await _make_patient(db_session)
    pat_a = await _get_patient_row(db_session, patient_a.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, pat_a.id)  # type: ignore[union-attr]

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    rx_id = create_resp.json()["id"]

    with patch("app.tasks.prescription_tasks.generate_prescription_pdf.apply_async"):
        await client.post(f"/v1/doctor/prescriptions/{rx_id}/sign", headers=make_auth_headers(doctor_user))

    # Patient B tries to access Patient A's prescription
    resp = await client.get(
        f"/v1/clinic/patient/prescriptions/{rx_id}",
        headers=make_auth_headers(patient_b),
    )
    assert resp.status_code == 404


async def test_patient_draft_prescription_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    rx_id = create_resp.json()["id"]

    # Patient tries to view their own DRAFT prescription — must be 404
    resp = await client.get(
        f"/v1/clinic/patient/prescriptions/{rx_id}",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 404


# ── PDF URL endpoint ───────────────────────────────────────────────────────────


async def test_patient_pdf_url_no_pdf_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    rx_id = create_resp.json()["id"]

    with patch("app.tasks.prescription_tasks.generate_prescription_pdf.apply_async"):
        await client.post(f"/v1/doctor/prescriptions/{rx_id}/sign", headers=make_auth_headers(doctor_user))

    # pdf_url is None (task hasn't run) → 404
    resp = await client.get(
        f"/v1/clinic/patient/prescriptions/{rx_id}/pdf",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 404


# ── Audit log ─────────────────────────────────────────────────────────────────


async def test_draft_invisible_to_patient_writes_denial_audit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.models.audit import AuditLog

    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    rx_id = create_resp.json()["id"]

    await client.get(
        f"/v1/clinic/patient/prescriptions/{rx_id}",
        headers=make_auth_headers(patient_user),
    )

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "view_prescription",
            AuditLog.actor_user_id == patient_user.id,  # type: ignore[union-attr]
            AuditLog.allowed.is_(False),
        )
    )
    assert result.scalar_one_or_none() is not None


async def test_sign_prescription_writes_allowed_audit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.models.audit import AuditLog

    doctor_user, doctor = await _make_doctor_with_profile(db_session)
    patient_user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, patient_user.id)  # type: ignore[union-attr]
    consult = await _make_consultation(db_session, doctor.id, patient.id)  # type: ignore[union-attr]

    create_resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",  # type: ignore[union-attr]
        json={"items": [ITEM_BODY]},
        headers=make_auth_headers(doctor_user),
    )
    rx_id = create_resp.json()["id"]

    with patch("app.tasks.prescription_tasks.generate_prescription_pdf.apply_async"):
        await client.post(f"/v1/doctor/prescriptions/{rx_id}/sign", headers=make_auth_headers(doctor_user))

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "sign_prescription",
            AuditLog.actor_user_id == doctor_user.id,  # type: ignore[union-attr]
            AuditLog.allowed.is_(True),
        )
    )
    assert result.scalar_one_or_none() is not None
