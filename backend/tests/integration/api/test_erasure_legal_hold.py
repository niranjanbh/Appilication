"""Integration tests for the DPDP erasure-with-legal-hold workflow (P39).

Tests:
  - POST /v1/users/me/delete → 202 + DSR request_id
  - Erasure task: PII anonymized, erased_at set, name changed
  - Erasure task: consultations get legal_hold_until ≈ now + 7yr
  - Erasure task: prescriptions get legal_hold_until
  - Idempotency: running task twice does not error
  - Postgres trigger: DELETE on held consultation raises
  - DSR status updated to COMPLETED
  - Admin DSR list + status-patch endpoints
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus
from app.models.clinic import Consultation, Patient, Prescription
from app.models.consent import DataSubjectRequest
from app.models.doctor import Availability, Doctor
from app.models.identity import User as UserModel
from app.tasks.data_subject_request import _process_erasure_async
from tests.conftest import (
    create_doctor_with_profile,
    create_patient_user,
    create_super_admin_user,
    make_auth_headers,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


async def _doctor_profile(db: AsyncSession, doctor_user: object) -> Doctor:
    """Return the dr_doctors row for a user created by create_doctor_with_profile."""
    from sqlalchemy import select as sa_select

    from app.models.identity import User as UserModel

    assert isinstance(doctor_user, UserModel)
    result = await db.execute(sa_select(Doctor).where(Doctor.user_id == doctor_user.id))
    return result.scalar_one()


async def _next_kyros_id(db: AsyncSession) -> str:
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-ERS-{seq:05d}"


async def _create_patient_profile(db: AsyncSession, user_id: uuid.UUID) -> Patient:

    kyros_id = await _next_kyros_id(db)
    patient = Patient(user_id=user_id, kyros_patient_id=kyros_id)
    db.add(patient)
    await db.flush()
    return patient


async def _create_minimal_consultation(
    db: AsyncSession, patient: Patient, doctor: Doctor
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
        status=ConsultationStatus.COMPLETED,
    )
    db.add(consultation)
    await db.flush()
    return consultation


async def _create_dsr(db: AsyncSession, user_id: uuid.UUID) -> DataSubjectRequest:
    from app.db.enums import DataSubjectRequestStatus, DataSubjectRequestType

    dsr = DataSubjectRequest(
        user_id=user_id,
        request_type=DataSubjectRequestType.ERASURE,
        status=DataSubjectRequestStatus.RECEIVED,
        received_at=datetime.now(UTC),
    )
    db.add(dsr)
    await db.flush()
    return dsr


# ── Tests ──────────────────────────────────────────────────────────────────────


async def test_request_erasure_returns_202(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    resp = await client.post(
        "/v1/users/me/delete", headers=make_auth_headers(patient_user)
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "request_id" in data


async def test_erasure_task_anonymizes_pii(db_session: AsyncSession) -> None:
    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    dsr = await _create_dsr(db_session, patient_user.id)

    await _process_erasure_async(patient_user.id, dsr.id, db=db_session)

    await db_session.refresh(patient_user)
    assert patient_user.erased_at is not None
    assert patient_user.name == "Deleted User"
    assert str(patient_user.id) in (patient_user.email or "")
    assert patient_user.phone is None
    assert patient_user.password_hash is None


async def test_erasure_task_sets_legal_hold_on_consultations(
    db_session: AsyncSession,
) -> None:
    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    doctor = await _doctor_profile(db_session, await create_doctor_with_profile(db_session))
    assert isinstance(doctor, Doctor)

    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_minimal_consultation(db_session, patient, doctor)
    dsr = await _create_dsr(db_session, patient_user.id)

    await _process_erasure_async(patient_user.id, dsr.id, db=db_session)

    await db_session.refresh(consultation)
    assert consultation.legal_hold_until is not None
    assert consultation.legal_hold_reason == "nmc_7yr_retention"
    # Should be ~7 years from now
    years_held = (consultation.legal_hold_until - datetime.now(UTC)).days // 365
    assert years_held >= 6


async def test_erasure_task_sets_legal_hold_on_prescriptions(
    db_session: AsyncSession,
) -> None:
    from app.db.enums import PrescriptionStatus

    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    doctor = await _doctor_profile(db_session, await create_doctor_with_profile(db_session))
    assert isinstance(doctor, Doctor)

    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_minimal_consultation(db_session, patient, doctor)

    # Create a prescription for this consultation
    rx = Prescription(
        consultation_id=consultation.id,
        doctor_id=doctor.id,
        patient_id=patient.id,
        status=PrescriptionStatus.SIGNED,
        version=1,
    )
    db_session.add(rx)
    await db_session.flush()

    dsr = await _create_dsr(db_session, patient_user.id)
    await _process_erasure_async(patient_user.id, dsr.id, db=db_session)

    await db_session.refresh(rx)
    assert rx.legal_hold_until is not None
    assert rx.legal_hold_reason == "nmc_7yr_retention"


async def test_erasure_task_is_idempotent(db_session: AsyncSession) -> None:
    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    dsr = await _create_dsr(db_session, patient_user.id)

    # Run twice — should not raise
    await _process_erasure_async(patient_user.id, dsr.id, db=db_session)
    await _process_erasure_async(patient_user.id, dsr.id, db=db_session)

    await db_session.refresh(patient_user)
    assert patient_user.erased_at is not None


async def test_dsr_status_completed_after_erasure(db_session: AsyncSession) -> None:
    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    dsr = await _create_dsr(db_session, patient_user.id)

    await _process_erasure_async(patient_user.id, dsr.id, db=db_session)

    await db_session.refresh(dsr)
    assert dsr.status.value == "completed"
    assert dsr.completed_at is not None
    assert "anonymized" in (dsr.notes or "")


async def test_postgres_trigger_blocks_delete_on_held_consultation(
    db_session: AsyncSession,
) -> None:
    """The Postgres trigger prevents hard DELETE when legal_hold_until is active."""
    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    doctor = await _doctor_profile(db_session, await create_doctor_with_profile(db_session))
    assert isinstance(doctor, Doctor)

    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_minimal_consultation(db_session, patient, doctor)
    dsr = await _create_dsr(db_session, patient_user.id)
    await _process_erasure_async(patient_user.id, dsr.id, db=db_session)

    # Verify the hold was applied
    await db_session.refresh(consultation)
    assert consultation.legal_hold_until is not None

    # Attempt a raw hard DELETE — the Postgres trigger should raise
    with pytest.raises((DBAPIError, Exception)):
        await db_session.execute(
            text("DELETE FROM kc_consultations WHERE id = :id"),
            {"id": str(consultation.id)},
        )
        await db_session.flush()


async def test_admin_list_dsr_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get("/v1/admin/dsr", headers=make_auth_headers(admin))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


async def test_admin_patch_dsr_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    dsr = await _create_dsr(db_session, patient_user.id)
    admin = await create_super_admin_user(db_session)

    resp = await client.patch(
        f"/v1/admin/dsr/{dsr.id}/status",
        json={"new_status": "in_progress"},
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


async def test_admin_patch_dsr_invalid_transition_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    dsr = await _create_dsr(db_session, patient_user.id)
    admin = await create_super_admin_user(db_session)

    # received → completed is not a valid transition
    resp = await client.patch(
        f"/v1/admin/dsr/{dsr.id}/status",
        json={"new_status": "completed"},
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 409
