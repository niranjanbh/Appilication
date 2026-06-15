"""Integration tests: signup → verify-otp → login → refresh flow."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _synth_email, _synth_phone

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_debug_otp(redis_client: object, phone: str) -> str:
    import redis.asyncio as aioredis

    assert isinstance(redis_client, aioredis.Redis)
    otp: str | None = await redis_client.get(f"otp:phone:{phone}:debug")
    assert otp is not None, "Debug OTP not found in Redis — is KYROS_DEBUG=true?"
    return otp


async def _assert_audit(db: AsyncSession, *, actor_user_id: object, action: str, allowed: bool) -> None:
    from app.models.audit import AuditLog

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.actor_user_id == actor_user_id,
            AuditLog.action == action,
            AuditLog.allowed == allowed,
        )
    )
    row = result.scalars().first()
    assert row is not None, f"Audit log missing: action={action!r} allowed={allowed}"


# ── Full happy-path flow ───────────────────────────────────────────────────────


async def test_signup_verify_login_refresh(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_client: object,
) -> None:
    phone = _synth_phone()
    email = _synth_email()
    password = "SecurePass99!"

    # 1. Signup
    resp = await client.post(
        "/v1/auth/signup",
        json={"name": "Test User", "phone": phone, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["phone"] == phone
    assert "otp_hint" in data  # debug mode returns OTP hint

    # 2. Verify OTP
    otp = await _get_debug_otp(redis_client, phone)
    resp = await client.post(
        "/v1/auth/verify-otp", json={"phone": phone, "otp": otp}
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    # 3. Login (fully verified account)
    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    login_tokens = resp.json()
    assert login_tokens["access_token"]

    # 4. Refresh
    resp = await client.post(
        "/v1/auth/refresh", json={"refresh_token": login_tokens["refresh_token"]}
    )
    assert resp.status_code == 200, resp.text
    refreshed = resp.json()
    assert refreshed["access_token"] != login_tokens["access_token"]
    assert refreshed["refresh_token"] != login_tokens["refresh_token"]

    # 5. Stale refresh token must be rejected (reuse detection)
    resp = await client.post(
        "/v1/auth/refresh", json={"refresh_token": login_tokens["refresh_token"]}
    )
    assert resp.status_code == 401, resp.text

    # 6. Audit log assertions
    from app.repositories import users as users_repo

    user = await users_repo.get_by_email(db_session, email)
    assert user is not None
    await _assert_audit(db_session, actor_user_id=user.id, action="signup", allowed=True)
    await _assert_audit(db_session, actor_user_id=user.id, action="phone_verified", allowed=True)
    await _assert_audit(db_session, actor_user_id=user.id, action="login", allowed=True)


# ── Duplicate registration ─────────────────────────────────────────────────────


async def test_signup_duplicate_email_returns_409(client: AsyncClient) -> None:
    email = _synth_email()
    payload = {"name": "A", "phone": _synth_phone(), "email": email, "password": "Pass1234!"}
    resp = await client.post("/v1/auth/signup", json=payload)
    assert resp.status_code == 201

    payload2 = {**payload, "phone": _synth_phone()}
    resp2 = await client.post("/v1/auth/signup", json=payload2)
    assert resp2.status_code == 409


async def test_signup_unverified_phone_allows_reregistration(client: AsyncClient) -> None:
    """Abandoned registration (OTP never verified) can be retried with the same phone."""
    phone = _synth_phone()
    payload = {"name": "B", "phone": phone, "email": _synth_email(), "password": "Pass1234!"}
    resp = await client.post("/v1/auth/signup", json=payload)
    assert resp.status_code == 201

    payload2 = {**payload, "email": _synth_email()}
    resp2 = await client.post("/v1/auth/signup", json=payload2)
    assert resp2.status_code == 201


async def test_signup_verified_phone_returns_409(
    client: AsyncClient, redis_client: object
) -> None:
    """Once phone is verified, a second signup with the same phone must be rejected."""
    phone = _synth_phone()
    email = _synth_email()
    payload = {"name": "B2", "phone": phone, "email": email, "password": "Pass1234!"}
    resp = await client.post("/v1/auth/signup", json=payload)
    assert resp.status_code == 201

    otp = await _get_debug_otp(redis_client, phone)
    await client.post("/v1/auth/verify-otp", json={"phone": phone, "otp": otp})

    payload2 = {**payload, "email": _synth_email()}
    resp2 = await client.post("/v1/auth/signup", json=payload2)
    assert resp2.status_code == 409


# ── OTP edge cases ─────────────────────────────────────────────────────────────


async def test_verify_otp_wrong_code_returns_422(
    client: AsyncClient,
    redis_client: object,
) -> None:
    phone = _synth_phone()
    await client.post(
        "/v1/auth/signup",
        json={"name": "C", "phone": phone, "email": _synth_email(), "password": "Pass1234!"},
    )
    resp = await client.post(
        "/v1/auth/verify-otp", json={"phone": phone, "otp": "000000"}
    )
    assert resp.status_code == 422


# ── Login edge cases ───────────────────────────────────────────────────────────


async def test_login_wrong_password_returns_401(
    client: AsyncClient,
    redis_client: object,
) -> None:
    phone = _synth_phone()
    email = _synth_email()
    await client.post(
        "/v1/auth/signup",
        json={"name": "D", "phone": phone, "email": email, "password": "RightPass1!"},
    )
    otp = await _get_debug_otp(redis_client, phone)
    await client.post("/v1/auth/verify-otp", json={"phone": phone, "otp": otp})

    resp = await client.post(
        "/v1/auth/login", json={"email_or_phone": email, "password": "WrongPass1!"}
    )
    assert resp.status_code == 401


async def test_login_unverified_phone_returns_403(
    client: AsyncClient,
) -> None:
    email = _synth_email()
    await client.post(
        "/v1/auth/signup",
        json={"name": "E", "phone": _synth_phone(), "email": email, "password": "Pass1234!"},
    )
    # Do NOT call verify-otp — account still unverified
    resp = await client.post(
        "/v1/auth/login", json={"email_or_phone": email, "password": "Pass1234!"}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "phone_not_verified"


# ── JWT claims ─────────────────────────────────────────────────────────────────


async def test_access_token_contains_user_id_and_role(
    client: AsyncClient,
    redis_client: object,
) -> None:
    from jose import jwt

    from app.core.config import settings as cfg

    phone = _synth_phone()
    email = _synth_email()
    await client.post(
        "/v1/auth/signup",
        json={"name": "F", "phone": phone, "email": email, "password": "Pass5678!"},
    )
    otp = await _get_debug_otp(redis_client, phone)
    resp = await client.post("/v1/auth/verify-otp", json={"phone": phone, "otp": otp})
    access_token = resp.json()["access_token"]

    payload = jwt.decode(access_token, cfg.jwt_secret, algorithms=[cfg.jwt_algorithm])
    assert "sub" in payload
    assert payload["role"] == "patient"
    assert payload["v"] == 1
    assert payload["aud"] == "patient"
    assert payload["mfa"] is False
    # Validate sub is a valid UUID
    uuid.UUID(payload["sub"])


# ── Staff idle-timeout (staff-rbac-spec §1) ─────────────────────────────────────


async def test_staff_refresh_after_idle_timeout_revokes_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.core.config import settings as cfg
    from app.core.security import hash_refresh_token
    from app.models.identity import RefreshToken
    from app.models.identity import User as UserModel
    from app.repositories import users as users_repo
    from tests.conftest import create_doctor_user

    doctor = await create_doctor_user(db_session)
    assert isinstance(doctor, UserModel)
    await users_repo.update_phone_verified(db_session, doctor.id)

    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text
    refresh_token = resp.json()["refresh_token"]

    token_hash = hash_refresh_token(refresh_token)
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    row = result.scalar_one()
    row.updated_at = datetime.now(UTC) - timedelta(
        minutes=cfg.jwt_staff_idle_timeout_minutes + 5
    )
    await db_session.flush()

    resp = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401, resp.text
    assert resp.json()["detail"] == "session_idle_timeout"

    await db_session.refresh(row)
    assert row.revoked_at is not None
    await _assert_audit(db_session, actor_user_id=doctor.id, action="token_refresh", allowed=False)
