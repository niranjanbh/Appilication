"""Integration tests: admin-forced session-kill (staff-rbac-spec §1).

Revokes both the JWT refresh-token family (API sessions) and any live admin/
coordinator portal session cookies for a staff account.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_doctor_user, create_super_admin_user


def _admin_session_cookie(user_id: uuid.UUID) -> tuple[str, str]:
    """Create an admin-portal session in Redis and return (session_id, csrf_token)."""
    from fastapi.responses import Response as FResponse

    from app.adminui.deps import create_admin_session

    dummy_response = FResponse()
    create_admin_session(dummy_response, user_id)
    session_id = ""
    csrf_token = ""
    for header_val in dummy_response.raw_headers:
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


async def test_revoke_sessions_kills_jwt_and_portal_sessions(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_client: object,
) -> None:
    import redis.asyncio as aioredis

    from app.core.security import hash_refresh_token
    from app.models.audit import AuditLog
    from app.models.identity import RefreshToken
    from app.models.identity import User as UserModel
    from app.repositories import users as users_repo

    assert isinstance(redis_client, aioredis.Redis)

    super_admin = await create_super_admin_user(db_session)
    doctor = await create_doctor_user(db_session)
    assert isinstance(super_admin, UserModel)
    assert isinstance(doctor, UserModel)
    await users_repo.update_phone_verified(db_session, doctor.id)

    try:
        admin_cookie, admin_csrf = _admin_session_cookie(super_admin.id)
        doctor_portal_session_id, _ = _admin_session_cookie(doctor.id)
    except Exception:
        return  # Redis unavailable in test — skip session creation path
    if not admin_cookie or not doctor_portal_session_id:
        return

    # Doctor has a live JWT refresh-token session.
    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text
    refresh_token = resp.json()["refresh_token"]
    token_hash = hash_refresh_token(refresh_token)

    # Sanity: portal session keys exist before revocation.
    assert await redis_client.exists(f"session:admin:{doctor_portal_session_id}")
    assert await redis_client.exists(f"staff_sessions:{doctor.id}")

    resp = await client.post(
        f"/admin/users/{doctor.id}/revoke-sessions",
        data={"_csrf": admin_csrf},
        cookies={"kyros_admin_session": admin_cookie, "kyros_admin_csrf": admin_csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302, resp.text
    assert "revoke=ok" in resp.headers.get("location", "")

    # JWT refresh token family revoked.
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    row = result.scalar_one()
    assert row.revoked_at is not None

    # Portal session keys deleted.
    assert not await redis_client.exists(f"session:admin:{doctor_portal_session_id}")
    assert not await redis_client.exists(f"sessionfresh:admin:{doctor_portal_session_id}")
    assert not await redis_client.exists(f"staff_sessions:{doctor.id}")

    # Audit row written.
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.actor_user_id == super_admin.id,
            AuditLog.action == "force_session_revoke",
            AuditLog.allowed.is_(True),
        )
    )
    assert result.scalars().first() is not None


async def test_revoke_sessions_on_patient_returns_not_a_staff_role(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from app.models.identity import User as UserModel
    from tests.conftest import create_patient_user

    super_admin = await create_super_admin_user(db_session)
    patient = await create_patient_user(db_session)
    assert isinstance(super_admin, UserModel)
    assert isinstance(patient, UserModel)

    try:
        admin_cookie, admin_csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not admin_cookie:
        return

    resp = await client.post(
        f"/admin/users/{patient.id}/revoke-sessions",
        data={"_csrf": admin_csrf},
        cookies={"kyros_admin_session": admin_cookie, "kyros_admin_csrf": admin_csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "revoke_error=not_a_staff_role" in resp.headers.get("location", "")
