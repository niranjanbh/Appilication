"""Integration tests for patient data-export status endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DataSubjectRequestStatus, DataSubjectRequestType
from app.models.audit import AuditLog
from app.models.identity import User as UserModel
from app.repositories import consent as consent_repo
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


async def _make_export(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: DataSubjectRequestStatus = DataSubjectRequestStatus.RECEIVED,
    request_type: DataSubjectRequestType = DataSubjectRequestType.ACCESS,
) -> uuid.UUID:
    dsr = await consent_repo.create_data_subject_request(
        db, user_id=user_id, request_type=request_type, received_at=datetime.now(UTC)
    )
    if status != DataSubjectRequestStatus.RECEIVED:
        await consent_repo.update_data_subject_request_status(
            db,
            request_id=dsr.id,
            status=status,
            completed_at=datetime.now(UTC) if status == DataSubjectRequestStatus.COMPLETED else None,
        )
    return dsr.id


# ── List ────────────────────────────────────────────────────────────────────────


async def test_list_data_exports_empty_for_new_patient(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/users/me/data-exports", headers=make_auth_headers(patient))
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_list_data_exports_returns_own_access_requests(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    export_id = await _make_export(db_session, patient.id)
    # An erasure request must not show up on the export surface.
    await _make_export(db_session, patient.id, request_type=DataSubjectRequestType.ERASURE)

    resp = await client.get("/v1/users/me/data-exports", headers=make_auth_headers(patient))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [i["id"] for i in items] == [str(export_id)]
    assert items[0]["status"] == "received"


# ── Detail / download URL ─────────────────────────────────────────────────────────


async def test_get_data_export_pending_has_no_url(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    export_id = await _make_export(db_session, patient.id)

    resp = await client.get(
        f"/v1/users/me/data-exports/{export_id}", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "received"
    assert data["download_url"] is None
    assert data["completed_at"] is None


async def test_get_data_export_completed_returns_download_url(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    export_id = await _make_export(
        db_session, patient.id, status=DataSubjectRequestStatus.COMPLETED
    )

    with patch(
        "app.integrations.s3.generate_download_url",
        return_value="https://s3.example/exports/file.zip?sig=abc",
    ):
        resp = await client.get(
            f"/v1/users/me/data-exports/{export_id}", headers=make_auth_headers(patient)
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["download_url"] == "https://s3.example/exports/file.zip?sig=abc"
    assert data["download_expires_in_seconds"] == 600
    assert data["completed_at"] is not None


async def test_get_other_patients_export_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    assert isinstance(patient_a, UserModel)
    assert isinstance(patient_b, UserModel)
    export_id = await _make_export(db_session, patient_a.id)

    resp = await client.get(
        f"/v1/users/me/data-exports/{export_id}", headers=make_auth_headers(patient_b)
    )
    assert resp.status_code == 404

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_b.id,
            AuditLog.action == "view_data_export",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


async def test_get_erasure_request_via_export_endpoint_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    erasure_id = await _make_export(
        db_session, patient.id, request_type=DataSubjectRequestType.ERASURE
    )

    resp = await client.get(
        f"/v1/users/me/data-exports/{erasure_id}", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 404


async def test_get_unknown_export_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/users/me/data-exports/{uuid.uuid4()}", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 404


# ── RBAC ──────────────────────────────────────────────────────────────────────────


async def test_list_data_exports_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me/data-exports")
    assert resp.status_code == 401


async def test_list_data_exports_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/users/me/data-exports", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_get_data_export_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/users/me/data-exports/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_get_data_export_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/users/me/data-exports/{uuid.uuid4()}", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403
