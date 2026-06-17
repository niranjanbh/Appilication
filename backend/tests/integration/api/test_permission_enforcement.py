"""Integration tests for require_permission enforcement + role-context stamping.

Covers the two reference endpoints migrated to the permission layer in P31:
  - POST /v1/doctor/consultations/{id}/prescription (prescription:create)
  - POST /v1/admin/content/{id}/approve            (content:publish)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from tests.conftest import (
    create_coordinator_user,
    create_doctor_user,
    create_patient_user,
    create_super_admin_user,
    make_auth_headers,
)

_ITEM: dict[str, Any] = {
    "drug_generic_name": "Levothyroxine",
    "drug_form": "tablet",
    "dosage": "50mcg",
    "frequency": "once daily",
    "duration_days": 90,
    "instructions": "Empty stomach",
}


async def _doctor_with_profile(db: AsyncSession) -> tuple[Any, Any]:
    from app.db.enums import DoctorStatus
    from app.models.doctor import Doctor

    user = await create_doctor_user(db)
    doctor = Doctor(
        user_id=user.id,  # type: ignore[attr-defined]
        nmc_registration_number=f"NMC{uuid.uuid4().hex[:8].upper()}",
        specialty=["Endocrinology"],
        status=DoctorStatus.ACTIVE,
    )
    db.add(doctor)
    await db.flush()
    return user, doctor


async def _patient_row(db: AsyncSession) -> Any:
    from app.models.clinic import Patient

    user = await create_patient_user(db)
    patient = Patient(
        user_id=user.id,  # type: ignore[attr-defined]
        kyros_patient_id=f"KP{uuid.uuid4().hex[:6].upper()}",
        primary_conditions=[],
    )
    db.add(patient)
    await db.flush()
    return patient


async def _consultation(db: AsyncSession, doctor_id: uuid.UUID, patient_id: uuid.UUID) -> Any:
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


async def _audit_row(db: AsyncSession, *, action: str, actor_user_id: uuid.UUID, allowed: bool) -> AuditLog | None:
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.action == action,
            AuditLog.actor_user_id == actor_user_id,
            AuditLog.allowed.is_(allowed),
        )
    )
    return result.scalars().first()


# ── Denial paths (no heavy setup — require_permission short-circuits) ────────────


async def test_coordinator_denied_prescription_create_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescription",
        json={"items": [_ITEM]},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_unauthenticated_prescription_create_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescription",
        json={"items": [_ITEM]},
    )
    assert resp.status_code == 401


# ── Denial-side audit (PHIAuditMiddleware, P33) ───────────────────────────────────


async def test_coordinator_denied_prescription_create_writes_denial_audit_row(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """require_permission's 403 is now audit-logged by PHIAuditMiddleware, with
    the permission that was checked and the path-derived resource.
    """
    from app.db.enums import ActorRole

    coord = await create_coordinator_user(db_session)
    consult_id = uuid.uuid4()
    resp = await client.post(
        f"/v1/doctor/consultations/{consult_id}/prescription",
        json={"items": [_ITEM]},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403

    row = await _audit_row(
        db_session,
        action=f"POST /v1/doctor/consultations/{consult_id}/prescription",
        actor_user_id=coord.id,  # type: ignore[attr-defined]
        allowed=False,
    )
    assert row is not None
    assert row.actor_role == ActorRole.COORDINATOR
    assert row.reason == "forbidden"
    assert row.permission == "prescription:create"
    assert row.resource_type == "consultation"
    assert row.resource_id == consult_id


async def test_patient_denied_doctor_only_endpoint_writes_denial_audit_row(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """enforce_role's 403 (no permission/role_context involved) is also
    audit-logged, on a non-parameterized route (resource_type/resource_id None).
    """
    from app.db.enums import ActorRole

    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/doctor/patients", headers=make_auth_headers(patient))
    assert resp.status_code == 403

    row = await _audit_row(
        db_session,
        action="GET /v1/doctor/patients",
        actor_user_id=patient.id,  # type: ignore[attr-defined]
        allowed=False,
    )
    assert row is not None
    assert row.actor_role == ActorRole.PATIENT
    assert row.reason == "forbidden"
    assert row.permission is None
    assert row.resource_type is None
    assert row.resource_id is None


# ── Allowed path + role-context stamping ─────────────────────────────────────────


async def test_doctor_create_prescription_stamps_role_context(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, doctor = await _doctor_with_profile(db_session)
    patient = await _patient_row(db_session)
    consult = await _consultation(db_session, doctor.id, patient.id)

    resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",
        json={"items": [_ITEM]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text

    row = await _audit_row(
        db_session, action="create_prescription", actor_user_id=doctor_user.id, allowed=True
    )
    assert row is not None
    assert row.role_context == "doctor"
    assert row.permission == "prescription:create"


async def test_multirole_doctor_admin_stamps_doctor_for_clinical_action(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A doctor who also holds super_admin still writes a prescription *as the RMP*."""
    from app.db.enums import UserRole
    from app.repositories import staff_roles as staff_roles_repo

    doctor_user, doctor = await _doctor_with_profile(db_session)
    # Grant an additional super_admin staff role to the same user.
    await staff_roles_repo.grant_role(
        db_session, user_id=doctor_user.id, role=UserRole.SUPER_ADMIN, granted_by=None
    )
    await db_session.flush()

    patient = await _patient_row(db_session)
    consult = await _consultation(db_session, doctor.id, patient.id)

    resp = await client.post(
        f"/v1/doctor/consultations/{consult.id}/prescription",
        json={"items": [_ITEM]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text

    row = await _audit_row(
        db_session, action="create_prescription", actor_user_id=doctor_user.id, allowed=True
    )
    assert row is not None
    # Clinical precedence: stamped doctor, not super_admin.
    assert row.role_context == "doctor"
    assert row.permission == "prescription:create"


async def test_super_admin_with_doctor_role_can_approve_content(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A super_admin who also holds a DOCTOR staff role can approve content via the
    doctor review endpoint. The audit row stamps 'doctor' as the role_context
    (clinical precedence) and 'content:approve' as the permission.
    """
    from app.db.enums import ContentStatus, DoctorStatus, UserRole
    from app.models.doctor import Doctor
    from app.repositories import education as edu_repo
    from app.repositories import staff_roles as staff_roles_repo

    admin = await create_super_admin_user(db_session)
    # Grant the super_admin a DOCTOR staff role so they have CONTENT_APPROVE permission.
    await staff_roles_repo.grant_role(
        db_session, user_id=admin.id, role=UserRole.DOCTOR, granted_by=None  # type: ignore[attr-defined]
    )
    # The doctor review endpoint needs a dr_doctors row for the approver.
    db_session.add(
        Doctor(
            user_id=admin.id,  # type: ignore[attr-defined]
            nmc_registration_number=f"NMC{uuid.uuid4().hex[:8].upper()}",
            specialty=["Endocrinology"],
            status=DoctorStatus.ACTIVE,
        )
    )
    # Content must be in PENDING_REVIEW state to be approvable.
    content = await edu_repo.create_content(
        db_session,
        title="Thyroid basics",
        slug=f"thyroid-{uuid.uuid4().hex[:6]}",
        content_type="article",
        condition_categories=["thyroid"],
        content_url=None,
        body_md="# Thyroid",
    )
    content.status = ContentStatus.PENDING_REVIEW  # type: ignore[attr-defined]
    await db_session.flush()

    resp = await client.post(
        f"/v1/doctor/content/{content.id}/review",
        headers=make_auth_headers(admin),
        json={"action": "approved"},
    )
    assert resp.status_code == 200, resp.text

    row = await _audit_row(
        db_session, action="doctor_review_content", actor_user_id=admin.id, allowed=True  # type: ignore[attr-defined]
    )
    assert row is not None
    # Doctor takes precedence over super_admin for CONTENT_APPROVE (clinical precedence).
    assert row.role_context == "doctor"
    assert row.permission == "content:approve"
