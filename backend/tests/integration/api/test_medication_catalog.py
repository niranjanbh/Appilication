"""Integration tests for medication catalog + reminder image endpoints.

S3 calls are mocked so tests run without cloud credentials.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_admin_user,
    create_doctor_user,
    create_patient_user,
    create_super_admin_user,
    make_auth_headers,
)

# ── S3 stubs ────────────────────────────────────────────────────────────────────


def _stub_image_upload(*, s3_key: str, content_type: str) -> dict[str, object]:
    return {"upload_url": "https://s3.example.com/upload", "fields": {"key": s3_key}, "s3_key": s3_key}


def _stub_head(*, s3_key: str) -> dict[str, object]:
    return {"ContentLength": 2048, "ContentType": "image/jpeg"}


def _stub_download(*, s3_key: str) -> str:
    return "https://s3.example.com/view?signed=yes"


def _stub_delete(*, s3_key: str) -> None:
    return None


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def super_admin_headers(db_session: AsyncSession) -> dict[str, str]:
    return make_auth_headers(await create_super_admin_user(db_session))


@pytest.fixture
async def admin_headers(db_session: AsyncSession) -> dict[str, str]:
    return make_auth_headers(await create_admin_user(db_session))


@pytest.fixture
async def doctor_headers(db_session: AsyncSession) -> dict[str, str]:
    return make_auth_headers(await create_doctor_user(db_session))


@pytest.fixture
async def patient(db_session: AsyncSession) -> object:
    return await create_patient_user(db_session)


@pytest.fixture
async def patient_headers(patient: object) -> dict[str, str]:
    return make_auth_headers(patient)


async def _create_entry(
    client: AsyncClient, headers: dict[str, str], *, name: str = "Thyronorm 50mcg"
) -> dict:
    resp = await client.post(
        "/v1/admin/medication-catalog",
        headers=headers,
        json={"name": name, "generic_name": "Levothyroxine", "form": "tablet", "strength": "50 mcg"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_reminder(client: AsyncClient, headers: dict[str, str]) -> dict:
    resp = await client.post(
        "/v1/wellness/reminders",
        headers=headers,
        json={"type": "medication", "label": "Thyroid", "schedule_cron": "0 8 * * *",
              "notification_channels": ["push"]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Admin catalog CRUD + RBAC ───────────────────────────────────────────────────


async def test_create_requires_super_admin(
    client: AsyncClient, doctor_headers: dict[str, str], patient_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    body = {"name": "Metformin", "form": "tablet"}
    assert (await client.post("/v1/admin/medication-catalog", json=body)).status_code == 401
    for h in (doctor_headers, patient_headers, admin_headers):  # admin tier is read-only
        resp = await client.post("/v1/admin/medication-catalog", headers=h, json=body)
        assert resp.status_code == 403


async def test_create_and_get(client: AsyncClient, super_admin_headers: dict[str, str]) -> None:
    entry = await _create_entry(client, super_admin_headers)
    assert entry["name"] == "Thyronorm 50mcg"
    assert entry["form"] == "tablet"
    assert entry["has_image"] is False

    got = await client.get(f"/v1/admin/medication-catalog/{entry['id']}", headers=super_admin_headers)
    assert got.status_code == 200
    assert got.json()["id"] == entry["id"]


async def test_create_duplicate_name_returns_400(
    client: AsyncClient, super_admin_headers: dict[str, str]
) -> None:
    await _create_entry(client, super_admin_headers, name="Aspirin")
    resp = await client.post(
        "/v1/admin/medication-catalog", headers=super_admin_headers,
        json={"name": "aspirin", "form": "tablet"},
    )
    assert resp.status_code == 400


async def test_invalid_form_returns_422(
    client: AsyncClient, super_admin_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/admin/medication-catalog", headers=super_admin_headers,
        json={"name": "X", "form": "powder"},
    )
    assert resp.status_code == 422


async def test_admin_tier_can_read_list(
    client: AsyncClient, super_admin_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    await _create_entry(client, super_admin_headers, name="Vitamin D3")
    resp = await client.get("/v1/admin/medication-catalog", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


async def test_update_and_soft_delete(
    client: AsyncClient, super_admin_headers: dict[str, str]
) -> None:
    entry = await _create_entry(client, super_admin_headers, name="Losartan")
    upd = await client.patch(
        f"/v1/admin/medication-catalog/{entry['id']}", headers=super_admin_headers,
        json={"strength": "25 mg", "active": False},
    )
    assert upd.status_code == 200
    assert upd.json()["strength"] == "25 mg"
    assert upd.json()["active"] is False

    dele = await client.delete(
        f"/v1/admin/medication-catalog/{entry['id']}", headers=super_admin_headers
    )
    assert dele.status_code == 204
    # Now 404 on fetch.
    assert (await client.get(
        f"/v1/admin/medication-catalog/{entry['id']}", headers=super_admin_headers
    )).status_code == 404


async def test_get_missing_returns_404(
    client: AsyncClient, super_admin_headers: dict[str, str]
) -> None:
    resp = await client.get(
        f"/v1/admin/medication-catalog/{uuid.uuid4()}", headers=super_admin_headers
    )
    assert resp.status_code == 404


# ── Catalog image upload (S3 mocked) ────────────────────────────────────────────


async def test_catalog_image_upload_flow(
    client: AsyncClient, super_admin_headers: dict[str, str]
) -> None:
    entry = await _create_entry(client, super_admin_headers, name="Ecosprin")
    with patch("app.integrations.s3.generate_image_upload_url", side_effect=_stub_image_upload):
        init = await client.post(
            f"/v1/admin/medication-catalog/{entry['id']}/image-initiate",
            headers=super_admin_headers,
            json={"filename": "pill.jpg", "content_type": "image/jpeg", "file_size_bytes": 2048},
        )
    assert init.status_code == 200, init.text
    assert "upload_url" in init.json()

    with patch("app.integrations.s3.head_object", side_effect=_stub_head):
        fin = await client.post(
            f"/v1/admin/medication-catalog/{entry['id']}/image-finalize",
            headers=super_admin_headers,
        )
    assert fin.status_code == 200
    assert fin.json()["image_uploaded"] is True

    # has_image now true
    got = await client.get(
        f"/v1/admin/medication-catalog/{entry['id']}", headers=super_admin_headers
    )
    assert got.json()["has_image"] is True

    with patch("app.integrations.s3.generate_download_url", side_effect=_stub_download):
        url = await client.get(
            f"/v1/admin/medication-catalog/{entry['id']}/image-url", headers=super_admin_headers
        )
    assert url.status_code == 200
    assert url.json()["url"].startswith("https://")


async def test_catalog_image_rejects_pdf(
    client: AsyncClient, super_admin_headers: dict[str, str]
) -> None:
    entry = await _create_entry(client, super_admin_headers, name="Pan-D")
    resp = await client.post(
        f"/v1/admin/medication-catalog/{entry['id']}/image-initiate",
        headers=super_admin_headers,
        json={"filename": "x.pdf", "content_type": "application/pdf", "file_size_bytes": 100},
    )
    assert resp.status_code == 422


# ── Doctor search ────────────────────────────────────────────────────────────────


async def test_doctor_search(
    client: AsyncClient, super_admin_headers: dict[str, str], doctor_headers: dict[str, str]
) -> None:
    await _create_entry(client, super_admin_headers, name="Cetirizine")
    resp = await client.get(
        "/v1/doctor/medication-catalog?search=cetir", headers=doctor_headers
    )
    assert resp.status_code == 200
    names = [i["name"] for i in resp.json()["items"]]
    assert "Cetirizine" in names


async def test_doctor_search_patient_forbidden(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.get("/v1/doctor/medication-catalog", headers=patient_headers)
    assert resp.status_code == 403


# ── Reminder image (patient) ────────────────────────────────────────────────────


async def test_reminder_image_flow(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    reminder = await _create_reminder(client, patient_headers)
    rid = reminder["id"]

    # No image yet → 404
    assert (await client.get(
        f"/v1/wellness/reminders/{rid}/image-url", headers=patient_headers
    )).status_code == 404

    with patch("app.integrations.s3.generate_image_upload_url", side_effect=_stub_image_upload):
        init = await client.post(
            f"/v1/wellness/reminders/{rid}/image-initiate", headers=patient_headers,
            json={"filename": "mypill.png", "content_type": "image/png", "file_size_bytes": 1024},
        )
    assert init.status_code == 200, init.text

    with patch("app.integrations.s3.head_object", side_effect=_stub_head):
        fin = await client.post(
            f"/v1/wellness/reminders/{rid}/image-finalize", headers=patient_headers
        )
    assert fin.status_code == 200

    with patch("app.integrations.s3.generate_download_url", side_effect=_stub_download):
        url = await client.get(
            f"/v1/wellness/reminders/{rid}/image-url", headers=patient_headers
        )
    assert url.status_code == 200

    # Delete image → S3 object removed, subsequent url 404
    with patch("app.integrations.s3.delete_object", side_effect=_stub_delete) as del_mock:
        assert (await client.delete(
            f"/v1/wellness/reminders/{rid}/image", headers=patient_headers
        )).status_code == 204
    del_mock.assert_called_once()
    assert (await client.get(
        f"/v1/wellness/reminders/{rid}/image-url", headers=patient_headers
    )).status_code == 404


async def test_deleting_reminder_cleans_up_custom_image(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    """Soft-deleting a reminder with a custom photo deletes the S3 object so it
    is not orphaned."""
    reminder = await _create_reminder(client, patient_headers)
    rid = reminder["id"]

    with patch("app.integrations.s3.generate_image_upload_url", side_effect=_stub_image_upload):
        await client.post(
            f"/v1/wellness/reminders/{rid}/image-initiate", headers=patient_headers,
            json={"filename": "mypill.png", "content_type": "image/png", "file_size_bytes": 1024},
        )
    with patch("app.integrations.s3.head_object", side_effect=_stub_head):
        await client.post(f"/v1/wellness/reminders/{rid}/image-finalize", headers=patient_headers)

    with patch("app.integrations.s3.delete_object", side_effect=_stub_delete) as del_mock:
        resp = await client.delete(f"/v1/wellness/reminders/{rid}", headers=patient_headers)
    assert resp.status_code == 204
    del_mock.assert_called_once()


async def test_deleting_reminder_without_image_skips_s3(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    """A reminder with no custom photo deletes cleanly without touching S3."""
    reminder = await _create_reminder(client, patient_headers)
    with patch("app.integrations.s3.delete_object", side_effect=_stub_delete) as del_mock:
        resp = await client.delete(
            f"/v1/wellness/reminders/{reminder['id']}", headers=patient_headers
        )
    assert resp.status_code == 204
    del_mock.assert_not_called()


async def test_reminder_image_cross_patient_404(
    client: AsyncClient, patient_headers: dict[str, str], db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.models.audit import AuditLog

    reminder = await _create_reminder(client, patient_headers)
    other = await create_patient_user(db_session)
    other_headers = make_auth_headers(other)
    resp = await client.post(
        f"/v1/wellness/reminders/{reminder['id']}/image-initiate", headers=other_headers,
        json={"filename": "x.png", "content_type": "image/png", "file_size_bytes": 1024},
    )
    assert resp.status_code == 404

    # The denial is audit-logged with the cross-user reason.
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == other.id,
            AuditLog.action == "upload_reminder_image",
            AuditLog.allowed.is_(False),
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


async def test_reminder_image_doctor_forbidden(
    client: AsyncClient, patient_headers: dict[str, str], doctor_headers: dict[str, str]
) -> None:
    reminder = await _create_reminder(client, patient_headers)
    resp = await client.post(
        f"/v1/wellness/reminders/{reminder['id']}/image-initiate", headers=doctor_headers,
        json={"filename": "x.png", "content_type": "image/png", "file_size_bytes": 1024},
    )
    assert resp.status_code == 403


async def test_reminder_image_no_auth_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/wellness/reminders/{uuid.uuid4()}/image-url")
    assert resp.status_code == 401
