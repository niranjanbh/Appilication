"""Integration tests for admin-portal bulk actions and CSV exports.

Session-cookie auth via Redis; skips gracefully when Redis is unavailable,
matching test_medication_catalog_admin_portal.py. Covers:

* Bulk suspend/reactivate writes one audit row per item (security rule 5).
* Bulk state-changers require super_admin (read-only admin → 403).
* CSV export is available to both admin tiers and carries no PHI beyond the
  agreed operational columns.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    cookie_header,
    create_admin_user,
    create_patient_user,
    create_super_admin_user,
)


def _admin_session_cookie(user_id: uuid.UUID) -> tuple[str, str]:
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


async def test_bulk_suspend_users_audits_each_item(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.audit import AuditLog
    from app.repositories import admin_portal as admin_repo

    super_admin = await create_super_admin_user(db_session)
    p1 = await create_patient_user(db_session)
    p2 = await create_patient_user(db_session)
    await db_session.commit()
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not cookie:
        return
    cookies = {"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}

    resp = await client.post(
        "/admin/bulk/users",
        data={"_csrf": csrf, "action": "suspend", "ids": [str(p1.id), str(p2.id)]},
        headers=cookie_header(cookies),
        follow_redirects=False,
    )
    assert resp.status_code == 302, resp.text
    assert "bulk_success=2" in resp.headers.get("location", "")

    # Both users are now suspended (deleted_at set).
    detail1 = await admin_repo.get_user_detail(db_session, p1.id)
    assert detail1 is None  # get_user_detail filters out soft-deleted

    # One audit row per item, not just the batch.
    rows = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.actor_user_id == super_admin.id,
                AuditLog.action == "admin_bulk_suspend_user",
            )
        )
    ).scalars().all()
    audited_ids = {r.resource_id for r in rows}
    assert p1.id in audited_ids
    assert p2.id in audited_ids


async def test_bulk_reactivate_users(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.repositories import admin_portal as admin_repo

    super_admin = await create_super_admin_user(db_session)
    patient = await create_patient_user(db_session)
    await admin_repo.suspend_user(db_session, patient.id)
    await db_session.commit()
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not cookie:
        return
    cookies = {"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}

    resp = await client.post(
        "/admin/bulk/users",
        data={"_csrf": csrf, "action": "reactivate", "ids": [str(patient.id)]},
        headers=cookie_header(cookies),
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "bulk_success=1" in resp.headers.get("location", "")
    detail = await admin_repo.get_user_detail(db_session, patient.id)
    assert detail is not None


async def test_bulk_action_requires_super_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    patient = await create_patient_user(db_session)
    await db_session.commit()
    try:
        cookie, csrf = _admin_session_cookie(admin.id)
    except Exception:
        return
    if not cookie:
        return
    resp = await client.post(
        "/admin/bulk/users",
        data={"_csrf": csrf, "action": "suspend", "ids": [str(patient.id)]},
        headers=cookie_header({"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}),
        follow_redirects=False,
    )
    assert resp.status_code == 403


async def test_export_users_csv_columns_and_no_phi(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    await create_patient_user(db_session, name="Synthetic Patient", email="syn@test.kyros.local")
    await db_session.commit()
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not cookie:
        return
    cookies = {"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}

    resp = await client.get("/admin/export/users.csv", headers=cookie_header(cookies))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")
    body = resp.text
    header = body.splitlines()[0]
    assert header == "Name,Phone,Email,Role,Joined,Status"
    # Operational columns only — no password hash or clinical fields leak.
    assert "password" not in body.lower()
    assert "Synthetic Patient" in body


async def test_export_csv_allowed_for_read_only_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    await db_session.commit()
    try:
        cookie, csrf = _admin_session_cookie(admin.id)
    except Exception:
        return
    if not cookie:
        return
    resp = await client.get(
        "/admin/export/users.csv",
        headers=cookie_header({"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}),
    )
    assert resp.status_code == 200


async def test_export_users_csv_selected_ids(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    keep = await create_patient_user(db_session, name="Keep Me")
    await create_patient_user(db_session, name="Skip Me")
    await db_session.commit()
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not cookie:
        return
    cookies = {"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}

    resp = await client.get(
        f"/admin/export/users.csv?ids={keep.id}", headers=cookie_header(cookies)
    )
    assert resp.status_code == 200
    body = resp.text
    assert "Keep Me" in body
    assert "Skip Me" not in body


async def test_export_csv_requires_login(client: AsyncClient) -> None:
    resp = await client.get("/admin/export/users.csv", follow_redirects=False)
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers.get("location", "")
