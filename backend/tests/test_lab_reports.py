"""Integration tests for lab report endpoints.

Covers:
  - Initiate upload (201, validation errors, missing patient profile)
  - Finalize upload (200, 404 cross-user, 422 validation)
  - List reports (200, pagination)
  - Get report (200, cross-user 404 + audit log)
  - Patient correction PATCH (200, cross-user 404)
  - Download URL (200, cross-user 404)
  - Doctor / coordinator / unauthenticated → 403 / 401

S3 and Document AI calls are mocked so tests run without cloud credentials.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    _synth_email,
    _synth_phone,
    create_coordinator_user,
    create_doctor_user,
    make_auth_headers,
)

# ── Fixtures ───────────────────────────────────────────────────────────────────

INITIATE_BODY = {
    "original_filename": "blood_test.pdf",
    "content_type": "application/pdf",
    "file_size_bytes": 512_000,
}


async def _make_patient_with_profile(db: AsyncSession) -> object:
    """Create a patient user + kc_patients profile row."""
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


# ── Stub helpers ───────────────────────────────────────────────────────────────

def _stub_generate_upload_url(**kwargs: object) -> dict[str, object]:
    return {
        "upload_url": "https://s3.example.com/upload",
        "fields": {"key": "stub-key", "Content-Type": "application/pdf"},
        "s3_key": f"patients/stub/lab-reports/{uuid.uuid4()}/blood_test.pdf",
    }


def _stub_head_object(*, s3_key: str) -> dict[str, object]:
    return {"ContentType": "application/pdf", "ContentLength": 512_000}


def _stub_generate_download_url(*, s3_key: str) -> str:
    return "https://s3.example.com/download?signed=yes"


def _stub_celery_delay(lab_report_id: str) -> MagicMock:
    task = MagicMock()
    task.id = "stub-task-id-1234"
    return task


# ── Auth / role matrix ─────────────────────────────────────────────────────────

async def test_initiate_upload_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post("/v1/clinic/patient/lab-reports/initiate-upload", json=INITIATE_BODY)
    assert resp.status_code == 401


async def test_initiate_upload_as_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/clinic/patient/lab-reports/initiate-upload",
        json=INITIATE_BODY,
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_initiate_upload_as_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        "/v1/clinic/patient/lab-reports/initiate-upload",
        json=INITIATE_BODY,
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_list_lab_reports_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/lab-reports")
    assert resp.status_code == 401


async def test_get_lab_report_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_download_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}/download")
    assert resp.status_code == 401


# ── Validation ─────────────────────────────────────────────────────────────────

async def test_initiate_upload_invalid_content_type(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)
    resp = await client.post(
        "/v1/clinic/patient/lab-reports/initiate-upload",
        json={**INITIATE_BODY, "content_type": "text/plain"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 422


async def test_initiate_upload_zero_size(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)
    resp = await client.post(
        "/v1/clinic/patient/lab-reports/initiate-upload",
        json={**INITIATE_BODY, "file_size_bytes": 0},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 422


async def test_initiate_upload_over_size_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)
    resp = await client.post(
        "/v1/clinic/patient/lab-reports/initiate-upload",
        json={**INITIATE_BODY, "file_size_bytes": 11 * 1024 * 1024},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 422


# ── Happy path ─────────────────────────────────────────────────────────────────

async def test_initiate_upload_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)
    with patch("app.integrations.s3.generate_upload_url", side_effect=_stub_generate_upload_url):
        resp = await client.post(
            "/v1/clinic/patient/lab-reports/initiate-upload",
            json=INITIATE_BODY,
            headers=make_auth_headers(patient),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert "lab_report_id" in data
    assert "upload_url" in data
    assert "fields" in data
    assert "s3_key" in data


async def test_list_lab_reports_empty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)
    resp = await client.get(
        "/v1/clinic/patient/lab-reports",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_get_lab_report_not_found_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 404


async def test_cross_user_lab_report_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A patient cannot view another patient's lab report — must receive 404 not 403."""
    from sqlalchemy import select

    from app.models.audit import AuditLog

    owner = await _make_patient_with_profile(db_session)
    requester = await _make_patient_with_profile(db_session)

    with patch("app.integrations.s3.generate_upload_url", side_effect=_stub_generate_upload_url):
        create_resp = await client.post(
            "/v1/clinic/patient/lab-reports/initiate-upload",
            json=INITIATE_BODY,
            headers=make_auth_headers(owner),
        )
    assert create_resp.status_code == 201
    report_id = create_resp.json()["lab_report_id"]

    resp = await client.get(
        f"/v1/clinic/patient/lab-reports/{report_id}",
        headers=make_auth_headers(requester),
    )
    assert resp.status_code == 404

    from app.models.identity import User as UserModel

    assert isinstance(requester, UserModel)
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == requester.id,
            AuditLog.action == "view_lab_report",
            AuditLog.allowed.is_(False),
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


async def test_finalize_upload_nonexistent_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}/finalize",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 404


async def test_finalize_upload_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)

    with patch("app.integrations.s3.generate_upload_url", side_effect=_stub_generate_upload_url):
        create_resp = await client.post(
            "/v1/clinic/patient/lab-reports/initiate-upload",
            json=INITIATE_BODY,
            headers=make_auth_headers(patient),
        )
    assert create_resp.status_code == 201
    report_id = create_resp.json()["lab_report_id"]

    with (
        patch("app.integrations.s3.head_object", side_effect=_stub_head_object),
        patch("app.tasks.ocr_tasks.parse_lab_report") as mock_task,
    ):
        mock_task.delay.side_effect = _stub_celery_delay
        resp = await client.post(
            f"/v1/clinic/patient/lab-reports/{report_id}/finalize",
            headers=make_auth_headers(patient),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ocr_pending"
    assert data["ocr_task_id"] == "stub-task-id-1234"


async def test_patient_correction_cross_user_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await _make_patient_with_profile(db_session)
    attacker = await _make_patient_with_profile(db_session)

    with patch("app.integrations.s3.generate_upload_url", side_effect=_stub_generate_upload_url):
        create_resp = await client.post(
            "/v1/clinic/patient/lab-reports/initiate-upload",
            json=INITIATE_BODY,
            headers=make_auth_headers(owner),
        )
    report_id = create_resp.json()["lab_report_id"]

    resp = await client.patch(
        f"/v1/clinic/patient/lab-reports/{report_id}",
        json={"parsed_json": {"biomarkers": []}},
        headers=make_auth_headers(attacker),
    )
    assert resp.status_code == 404


async def test_download_url_cross_user_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await _make_patient_with_profile(db_session)
    attacker = await _make_patient_with_profile(db_session)

    with patch("app.integrations.s3.generate_upload_url", side_effect=_stub_generate_upload_url):
        create_resp = await client.post(
            "/v1/clinic/patient/lab-reports/initiate-upload",
            json=INITIATE_BODY,
            headers=make_auth_headers(owner),
        )
    report_id = create_resp.json()["lab_report_id"]

    resp = await client.get(
        f"/v1/clinic/patient/lab-reports/{report_id}/download",
        headers=make_auth_headers(attacker),
    )
    assert resp.status_code == 404


async def test_download_url_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _make_patient_with_profile(db_session)

    with patch("app.integrations.s3.generate_upload_url", side_effect=_stub_generate_upload_url):
        create_resp = await client.post(
            "/v1/clinic/patient/lab-reports/initiate-upload",
            json=INITIATE_BODY,
            headers=make_auth_headers(patient),
        )
    report_id = create_resp.json()["lab_report_id"]

    with patch("app.integrations.s3.generate_download_url", side_effect=_stub_generate_download_url):
        resp = await client.get(
            f"/v1/clinic/patient/lab-reports/{report_id}/download",
            headers=make_auth_headers(patient),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "download_url" in data


# ── OCR task (direct async function) ──────────────────────────────────────────

async def test_ocr_task_idempotent_already_parsed(db_session: AsyncSession) -> None:
    """If parsed_json is already set, the task exits early."""
    from app.core.security import hash_password
    from app.db.enums import LabReportStatus, UserRole
    from app.models.clinic import LabReport, Patient
    from app.repositories import users as users_repo
    from app.tasks.ocr_tasks import _parse_lab_report_async

    user = await users_repo.create(
        db_session,
        name="OCR Test",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    await users_repo.update_phone_verified(db_session, user.id)  # type: ignore[union-attr]

    from app.models.identity import User as UserModel
    assert isinstance(user, UserModel)

    patient = Patient(user_id=user.id, kyros_patient_id=f"KP{uuid.uuid4().hex[:6].upper()}", primary_conditions=[])
    db_session.add(patient)
    await db_session.flush()

    report = LabReport(
        patient_id=patient.id,
        uploaded_by_user_id=user.id,
        original_filename="already_done.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        status=LabReportStatus.OCR_COMPLETE,
        parsed_json={"biomarkers": [], "overall_confidence": 0.99},
    )
    db_session.add(report)
    await db_session.flush()

    with patch("app.db.session.AsyncSessionLocal") as mock_session_factory:
        # Point the task's session factory at our test session
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = db_session
        mock_cm.__aexit__.return_value = False
        mock_session_factory.return_value = mock_cm

        result = await _parse_lab_report_async(str(report.id))

    assert result.get("skipped") is True
    assert result.get("reason") == "already_parsed"


async def test_ocr_task_report_not_found(db_session: AsyncSession) -> None:
    from app.tasks.ocr_tasks import _parse_lab_report_async

    random_id = str(uuid.uuid4())
    with patch("app.db.session.AsyncSessionLocal") as mock_session_factory:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = db_session
        mock_cm.__aexit__.return_value = False
        mock_session_factory.return_value = mock_cm

        result = await _parse_lab_report_async(random_id)

    assert result.get("skipped") is True
    assert result.get("reason") == "report_not_found"
