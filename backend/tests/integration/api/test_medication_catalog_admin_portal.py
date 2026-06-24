"""Integration tests for the admin-portal medication-catalog views (/admin/medication-catalog).

Uses session-cookie auth (Redis). Skips gracefully when Redis is unavailable,
matching tests/integration/api/test_admin_session_revoke.py.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_admin_user, create_super_admin_user


def _admin_session_cookie(user_id: uuid.UUID) -> tuple[str, str]:
    """Create an admin-portal session in Redis and return (session_id, csrf_token)."""
    from fastapi.responses import Response as FResponse

    from app.adminui.deps import create_admin_session

    resp = FResponse()
    create_admin_session(resp, user_id)
    session_id = ""
    csrf_token = ""
    for header_val in resp.raw_headers:
        decoded = header_val[1].decode() if isinstance(header_val[1], bytes) else header_val[1]
        if "kyros_admin_session=" in decoded:
            for part in decoded.split(";"):
                if "kyros_admin_session=" in part:
                    session_id = part.split("=", 1)[1].strip()
        if "kyros_admin_csrf=" in decoded:
            for part in decoded.split(";"):
                if "kyros_admin_csrf=" in part:
                    csrf_token = part.split("=", 1)[1].strip()
    return session_id, csrf_token


async def test_catalog_page_requires_login(client: AsyncClient) -> None:
    resp = await client.get("/admin/medication-catalog", follow_redirects=False)
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers.get("location", "")


async def test_catalog_create_and_list(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.repositories import medication_catalog as catalog_repo

    super_admin = await create_super_admin_user(db_session)
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return  # Redis unavailable — skip
    if not cookie:
        return
    cookies = {"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}

    resp = await client.post(
        "/admin/medication-catalog",
        data={"_csrf": csrf, "name": "Thyronorm 50mcg", "generic_name": "Levothyroxine",
              "form": "tablet", "strength": "50 mcg"},
        cookies=cookies,
        follow_redirects=False,
    )
    assert resp.status_code == 302, resp.text
    assert "success=created" in resp.headers.get("location", "")

    entry = await catalog_repo.get_by_name(db_session, name="Thyronorm 50mcg")
    assert entry is not None
    assert entry.form is not None and entry.form.value == "tablet"

    page = await client.get("/admin/medication-catalog", cookies=cookies)
    assert page.status_code == 200
    assert "Thyronorm 50mcg" in page.text


async def test_catalog_image_upload(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.repositories import medication_catalog as catalog_repo

    super_admin = await create_super_admin_user(db_session)
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not cookie:
        return
    cookies = {"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}

    entry = await catalog_repo.create(
        db_session, name="Ecosprin 75", generic_name=None, form=None, strength=None,
        created_by_user_id=super_admin.id,
    )
    await db_session.commit()

    with patch("app.integrations.s3.put_bytes") as put_bytes:
        resp = await client.post(
            f"/admin/medication-catalog/{entry.id}/image",
            data={"_csrf": csrf},
            files={"image": ("pill.png", b"\x89PNG\r\n\x1a\nfake", "image/png")},
            cookies=cookies,
            follow_redirects=False,
        )
    assert resp.status_code == 302, resp.text
    assert "success=image_uploaded" in resp.headers.get("location", "")
    put_bytes.assert_called_once()

    refreshed = await catalog_repo.get(db_session, catalog_id=entry.id)
    assert refreshed is not None and refreshed.image_s3_key is not None


async def test_catalog_image_rejects_pdf(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.repositories import medication_catalog as catalog_repo

    super_admin = await create_super_admin_user(db_session)
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not cookie:
        return
    cookies = {"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}
    entry = await catalog_repo.create(
        db_session, name="Pan-D", generic_name=None, form=None, strength=None,
        created_by_user_id=super_admin.id,
    )
    await db_session.commit()

    resp = await client.post(
        f"/admin/medication-catalog/{entry.id}/image",
        data={"_csrf": csrf},
        files={"image": ("x.pdf", b"%PDF-1.4", "application/pdf")},
        cookies=cookies,
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "error=bad_image_type" in resp.headers.get("location", "")


async def test_read_only_admin_cannot_create(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    try:
        cookie, csrf = _admin_session_cookie(admin.id)
    except Exception:
        return
    if not cookie:
        return
    resp = await client.post(
        "/admin/medication-catalog",
        data={"_csrf": csrf, "name": "Metformin", "form": "tablet"},
        cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 403


async def test_read_only_admin_can_view_list(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    try:
        cookie, csrf = _admin_session_cookie(admin.id)
    except Exception:
        return
    if not cookie:
        return
    resp = await client.get(
        "/admin/medication-catalog",
        cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf},
    )
    assert resp.status_code == 200
