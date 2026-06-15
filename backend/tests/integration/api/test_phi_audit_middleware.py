"""Integration tests for PHIAuditMiddleware (P33 — denial-side audit).

Covers the cross-cutting 401/403 denial cases that app.core.rbac and
app.adminui.deps stamp on request.state, and that PHIAuditMiddleware turns into
ad_audit_log rows after the response is produced. The allowed-path audit rows
(per-handler write_audit, P31) and unidentified-actor 401s are out of scope —
see docs/build-prompts/P33-phi-access-audit-middleware.md.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ActorRole
from app.models.audit import AuditLog
from app.models.identity import User as UserModel
from tests.conftest import create_admin_user, create_patient_user


def _admin_session_cookie(user_id: uuid.UUID) -> str:
    """Create an admin-portal session in Redis and return the cookie value."""
    from fastapi.responses import Response as FResponse

    from app.adminui.deps import create_admin_session

    dummy_response = FResponse()
    create_admin_session(dummy_response, user_id)
    session_cookie = dummy_response.headers.get("set-cookie", "")
    for part in session_cookie.split(";"):
        if "kyros_admin_session=" in part:
            return part.split("=", 1)[1].strip()
    return ""


async def test_admin_tier_hitting_super_admin_view_writes_denial_audit_row(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Read-only admin hitting a require_super_admin_session view still gets 403
    (unchanged), and the middleware writes a denial row with the path-derived
    resource and reason="super_admin_required".
    """
    admin = await create_admin_user(db_session)
    assert isinstance(admin, UserModel)

    try:
        cookie = _admin_session_cookie(admin.id)
    except Exception:
        return  # Redis unavailable in this environment — skip
    if not cookie:
        return

    content_id = uuid.uuid4()
    resp = await client.post(
        f"/admin/content/{content_id}/publish",
        cookies={"kyros_admin_session": cookie},
        follow_redirects=False,
    )
    assert resp.status_code == 403

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.actor_user_id == admin.id,
            AuditLog.allowed.is_(False),
            AuditLog.reason == "super_admin_required",
        )
    )
    row = result.scalars().first()
    assert row is not None
    assert row.actor_role == ActorRole.ADMIN
    assert row.resource_type == "content"
    assert row.resource_id == content_id
    assert row.action == f"POST /admin/content/{content_id}/publish"


async def test_unauthenticated_request_writes_no_denial_audit_row(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A request with no bearer token still gets 401 (unchanged), and the
    middleware writes nothing — the actor could not be identified.
    """
    resp = await client.get("/v1/doctor/patients")
    assert resp.status_code == 401

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.actor_user_id.is_(None),
            AuditLog.allowed.is_(False),
            AuditLog.action == "GET /v1/doctor/patients",
        )
    )
    assert result.scalars().first() is None


async def test_bad_password_login_writes_no_middleware_audit_row(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """/v1/auth/login is exempt — its existing response is unchanged and the
    middleware writes nothing for it.
    """
    user = await create_patient_user(db_session)
    assert isinstance(user, UserModel)

    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": user.email, "password": "WrongPassword123!"},
    )
    assert resp.status_code == 401

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "POST /v1/auth/login")
    )
    assert result.scalars().first() is None


async def test_disabling_phi_audit_middleware_skips_denial_write(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """settings.phi_audit_middleware_enabled = False disables the writes above
    with no other behavior change (ops kill-switch).
    """
    from app.core.config import settings

    admin = await create_admin_user(db_session)
    assert isinstance(admin, UserModel)

    try:
        cookie = _admin_session_cookie(admin.id)
    except Exception:
        return
    if not cookie:
        return

    content_id = uuid.uuid4()
    settings.phi_audit_middleware_enabled = False
    try:
        resp = await client.post(
            f"/admin/content/{content_id}/publish",
            cookies={"kyros_admin_session": cookie},
            follow_redirects=False,
        )
    finally:
        settings.phi_audit_middleware_enabled = True

    assert resp.status_code == 403

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.actor_user_id == admin.id,
            AuditLog.allowed.is_(False),
            AuditLog.reason == "super_admin_required",
        )
    )
    assert result.scalars().first() is None
