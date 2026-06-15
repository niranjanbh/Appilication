"""Integration tests: password reset (request → confirm) across roles."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import OtpResetChannel
from tests.conftest import (
    _synth_email,
    create_coordinator_user,
    create_patient_user,
    create_super_admin_user,
)


async def _request_and_get_otp(client: AsyncClient, identifier: str) -> str:
    resp = await client.post(
        "/v1/auth/password-reset/request", json={"identifier": identifier}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["otp_hint"], "Debug OTP hint missing — is KYROS_DEBUG=true?"
    return data["otp_hint"]


async def test_password_reset_full_flow(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = _synth_email()
    await create_patient_user(db_session, email=email)
    await db_session.flush()

    otp = await _request_and_get_otp(client, email)

    new_password = "BrandNewPass1!"
    resp = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"identifier": email, "otp": otp, "new_password": new_password},
    )
    assert resp.status_code == 200, resp.text

    # New password works.
    ok = await client.post(
        "/v1/auth/login", json={"email_or_phone": email, "password": new_password}
    )
    assert ok.status_code == 200, ok.text

    # Old password no longer works.
    bad = await client.post(
        "/v1/auth/login", json={"email_or_phone": email, "password": "TestPass123!"}
    )
    assert bad.status_code == 401


async def test_password_reset_unknown_identifier_no_enumeration(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/v1/auth/password-reset/request", json={"identifier": _synth_email()}
    )
    # Same 200 success shape as a known account; no OTP issued.
    assert resp.status_code == 200
    assert resp.json()["otp_hint"] is None


async def test_password_reset_wrong_otp_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = _synth_email()
    await create_patient_user(db_session, email=email)
    await db_session.flush()

    await _request_and_get_otp(client, email)
    resp = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"identifier": email, "otp": "000000", "new_password": "Whatever12!"},
    )
    assert resp.status_code == 422


async def test_password_reset_unknown_user_confirm_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"identifier": _synth_email(), "otp": "123456", "new_password": "Whatever12!"},
    )
    assert resp.status_code == 422


async def test_password_reset_revokes_existing_sessions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = _synth_email()
    await create_patient_user(db_session, email=email)
    await db_session.flush()

    # Establish a session.
    login = await client.post(
        "/v1/auth/login", json={"email_or_phone": email, "password": "TestPass123!"}
    )
    assert login.status_code == 200
    old_refresh = login.json()["refresh_token"]

    # Reset the password.
    otp = await _request_and_get_otp(client, email)
    resp = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"identifier": email, "otp": otp, "new_password": "FreshPass1!"},
    )
    assert resp.status_code == 200

    # The pre-reset refresh token is now revoked.
    refresh = await client.post(
        "/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert refresh.status_code == 401


async def test_password_reset_works_for_staff_roles(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Reset is role-agnostic: a coordinator (portal staff) can reset too."""
    email = _synth_email()
    await create_coordinator_user(db_session, email=email)
    await db_session.flush()

    otp = await _request_and_get_otp(client, email)
    resp = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"identifier": email, "otp": otp, "new_password": "CoordFresh1!"},
    )
    assert resp.status_code == 200


async def test_password_reset_respects_per_user_channel(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A per-user reset channel is recorded in the request audit metadata."""
    from app.models.audit import AuditLog
    from app.repositories import users as users_repo

    email = _synth_email()
    user = await create_super_admin_user(db_session, email=email)
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    await users_repo.update_reset_otp_channel(db_session, user.id, OtpResetChannel.EMAIL)
    await db_session.flush()

    await _request_and_get_otp(client, email)

    row = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.actor_user_id == user.id,
                AuditLog.action == "password_reset_request",
                AuditLog.allowed.is_(True),
            )
        )
    ).scalars().first()
    assert row is not None
    assert row.log_metadata is not None
    assert row.log_metadata.get("channel") == "email"
