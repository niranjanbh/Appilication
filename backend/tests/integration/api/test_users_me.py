"""Integration tests: /v1/users/me, /v1/users/me/data-export, /v1/users/me/delete.

Covers:
- RBAC: patient 200, doctor/coordinator 403, no-auth 401
- cross_user_404 helper: writes denial audit and raises 404 on None resource
- Consent capture: version hash persisted as SHA-256
- Data export: DSR created, async task generates ZIP and marks COMPLETED
- Erasure: DSR created, async task soft-deletes user and marks COMPLETED
"""

from __future__ import annotations

import hashlib
import json
import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext
from app.core.rbac import cross_user_404
from app.db.enums import ActorRole, ConsentType, DataSubjectRequestStatus
from app.models.audit import AuditLog
from app.models.consent import DataSubjectRequest
from app.models.identity import User
from tests.conftest import (
    create_coordinator_user,
    create_doctor_user,
    create_patient_user,
    make_auth_headers,
)

# ── GET /v1/users/me ─────────────────────────────────────────────────────────


async def test_get_me_as_patient_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    assert isinstance(user, User)
    resp = await client.get("/v1/users/me", headers=make_auth_headers(user))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(user.id)
    assert data["role"] == "patient"
    assert "password_hash" not in data


async def test_get_me_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me")
    assert resp.status_code == 401


async def test_get_me_as_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    assert isinstance(doctor, User)
    resp = await client.get("/v1/users/me", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_get_me_as_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    assert isinstance(coord, User)
    resp = await client.get("/v1/users/me", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_get_me_writes_allowed_audit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    assert isinstance(user, User)
    await client.get("/v1/users/me", headers=make_auth_headers(user))

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == user.id,
            AuditLog.action == "view_own_profile",
            AuditLog.allowed.is_(True),
        )
    )
    assert audit is not None


# ── cross_user_404 helper ─────────────────────────────────────────────────────


async def test_cross_user_404_raises_404_for_none_resource(
    db_session: AsyncSession,
) -> None:
    # We need a user in DB for a valid actor_user_id in the audit log.
    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole.PATIENT,
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_id="test-req-id",
    )
    resource_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await cross_user_404(
            db_session,
            None,
            ctx,
            action="view_consultation",
            resource_type="consultation",
            resource_id=resource_id,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not found"


async def test_cross_user_404_writes_denial_audit(
    db_session: AsyncSession,
) -> None:
    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole.PATIENT,
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_id="test-req-id",
    )
    resource_id = uuid.uuid4()

    with pytest.raises(HTTPException):
        await cross_user_404(
            db_session,
            None,
            ctx,
            action="view_consultation",
            resource_type="consultation",
            resource_id=resource_id,
        )

    # cross_user_404 commits its own audit row before raising.
    # Use a fresh select on the same connection to verify.
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == user.id,
            AuditLog.action == "view_consultation",
            AuditLog.allowed.is_(False),
            AuditLog.reason == "not_own_or_not_found",
        )
    )
    assert audit is not None


async def test_cross_user_404_returns_resource_when_not_none(
    db_session: AsyncSession,
) -> None:
    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole.PATIENT,
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_id="test-req-id",
    )
    sentinel = object()
    result = await cross_user_404(
        db_session,
        sentinel,
        ctx,
        action="view_consultation",
        resource_type="consultation",
        resource_id=uuid.uuid4(),
    )
    assert result is sentinel


# ── Consent capture ───────────────────────────────────────────────────────────


async def test_capture_consent_stores_sha256_hash(db_session: AsyncSession) -> None:
    from app.services import consent as consent_service

    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    consent_text = "I agree to the Kyros Terms of Service version 2.0."
    record = await consent_service.capture_consent(
        db_session,
        user_id=user.id,
        consent_type=ConsentType.TERMS,
        version="v2.0",
        granted=True,
        ip_address="127.0.0.1",
        consent_text=consent_text,
    )

    expected_hash = hashlib.sha256(consent_text.encode()).hexdigest()
    assert record.consent_text_hash == expected_hash
    assert record.version == "v2.0"
    assert record.granted is True


async def test_revoke_consent_sets_revoked_at(db_session: AsyncSession) -> None:
    from app.services import consent as consent_service

    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    await consent_service.capture_consent(
        db_session,
        user_id=user.id,
        consent_type=ConsentType.MARKETING,
        version="v1.0",
        granted=True,
        ip_address="127.0.0.1",
        consent_text="Marketing consent text.",
    )

    revoked = await consent_service.revoke_consent(
        db_session,
        user_id=user.id,
        consent_type=ConsentType.MARKETING,
    )
    # Reload from DB to see updated revoked_at
    await db_session.refresh(revoked)
    assert revoked.revoked_at is not None


# ── POST /v1/users/me/data-export ─────────────────────────────────────────────


async def test_data_export_returns_202_and_creates_dsr(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    with patch("app.tasks.data_subject_request.process_data_export.delay"):
        resp = await client.post(
            "/v1/users/me/data-export", headers=make_auth_headers(user)
        )

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "request_id" in data

    dsr = await db_session.scalar(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == uuid.UUID(data["request_id"]),
            DataSubjectRequest.user_id == user.id,
        )
    )
    assert dsr is not None
    assert dsr.request_type.value == "access"
    assert dsr.status == DataSubjectRequestStatus.RECEIVED


async def test_data_export_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/users/me/data-export")
    assert resp.status_code == 401


async def test_data_export_async_generates_zip_and_marks_completed(
    db_session: AsyncSession,
) -> None:
    from datetime import UTC, datetime

    from app.db.enums import DataSubjectRequestType
    from app.repositories import consent as consent_repo
    from app.tasks.data_subject_request import _process_data_export_async

    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    dsr = await consent_repo.create_data_subject_request(
        db_session,
        user_id=user.id,
        request_type=DataSubjectRequestType.ACCESS,
        received_at=datetime.now(UTC),
    )

    # The export uploads the ZIP to S3 (SSE-KMS); patch that boundary so the
    # test stays offline and capture the uploaded bytes.
    with patch("app.integrations.s3.put_bytes") as mock_put:
        await _process_data_export_async(user.id, dsr.id, db=db_session)

    mock_put.assert_called_once()
    assert mock_put.call_args.kwargs["s3_key"] == f"exports/{user.id}/{dsr.id}.zip"
    assert len(mock_put.call_args.kwargs["data"]) > 0

    updated_dsr = await db_session.scalar(
        select(DataSubjectRequest).where(DataSubjectRequest.id == dsr.id)
    )
    assert updated_dsr is not None
    assert updated_dsr.status == DataSubjectRequestStatus.COMPLETED
    assert updated_dsr.completed_at is not None
    assert updated_dsr.notes is not None
    notes = json.loads(updated_dsr.notes)
    assert notes["zip_size_bytes"] > 0
    assert notes["export_s3_key"] == f"exports/{user.id}/{dsr.id}.zip"
    assert "profile.json" in notes["categories"]


# ── POST /v1/users/me/delete ──────────────────────────────────────────────────


async def test_erasure_returns_202_and_creates_dsr(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    with patch("app.tasks.data_subject_request.process_erasure.delay"):
        resp = await client.post("/v1/users/me/delete", headers=make_auth_headers(user))

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "request_id" in data

    dsr = await db_session.scalar(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == uuid.UUID(data["request_id"]),
            DataSubjectRequest.user_id == user.id,
        )
    )
    assert dsr is not None
    assert dsr.request_type.value == "erasure"


async def test_erasure_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/users/me/delete")
    assert resp.status_code == 401


async def test_erasure_async_soft_deletes_user_and_marks_completed(
    db_session: AsyncSession,
) -> None:
    from datetime import UTC, datetime

    from app.db.enums import DataSubjectRequestType
    from app.repositories import consent as consent_repo
    from app.tasks.data_subject_request import _process_erasure_async

    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    dsr = await consent_repo.create_data_subject_request(
        db_session,
        user_id=user.id,
        request_type=DataSubjectRequestType.ERASURE,
        received_at=datetime.now(UTC),
    )

    await _process_erasure_async(user.id, dsr.id, db=db_session)

    # User should be soft-deleted
    await db_session.refresh(user)
    assert user.deleted_at is not None

    # DSR should be completed
    updated_dsr = await db_session.scalar(
        select(DataSubjectRequest).where(DataSubjectRequest.id == dsr.id)
    )
    assert updated_dsr is not None
    assert updated_dsr.status == DataSubjectRequestStatus.COMPLETED
    assert updated_dsr.completed_at is not None


async def test_erasure_async_revokes_all_refresh_tokens(
    db_session: AsyncSession,
) -> None:
    from datetime import UTC, datetime

    from app.db.enums import DataSubjectRequestType
    from app.models.identity import RefreshToken
    from app.repositories import consent as consent_repo
    from app.tasks.data_subject_request import _process_erasure_async

    user = await create_patient_user(db_session)
    assert isinstance(user, User)

    # Create a refresh token for the user
    rt = RefreshToken(
        user_id=user.id,
        session_id=uuid.uuid4(),
        token_hash="dummy_hash_for_test",
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    db_session.add(rt)
    await db_session.flush()

    dsr = await consent_repo.create_data_subject_request(
        db_session,
        user_id=user.id,
        request_type=DataSubjectRequestType.ERASURE,
        received_at=datetime.now(UTC),
    )

    await _process_erasure_async(user.id, dsr.id, db=db_session)

    await db_session.refresh(rt)
    assert rt.revoked_at is not None
