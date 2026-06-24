"""Integration tests: mandatory mobile-number capture for the signed-in patient.

Google sign-in carries no phone, so a patient may be authenticated with
``phone = NULL``. These endpoints attach (and, when signup OTP is enabled,
verify) a number on the current account.
"""

from __future__ import annotations

import redis.asyncio as aioredis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UserRole
from tests.conftest import (
    _synth_email,
    _synth_phone,
    create_patient_user,
    make_auth_headers,
)


async def _google_style_patient(db: AsyncSession) -> object:
    """A patient with no phone yet — as created by Google sign-in."""
    from app.repositories import users as users_repo

    return await users_repo.create(
        db,
        name="Phone Less",
        role=UserRole.PATIENT,
        phone=None,
        email=_synth_email(),
        password_hash=None,
    )


async def _set_signup_otp(db: AsyncSession, *, enabled: bool) -> None:
    from app.repositories import platform_settings as settings_repo
    from app.services import platform_settings_service

    await settings_repo.upsert(
        db,
        key=platform_settings_service.SIGNUP_OTP_ENABLED,
        value=enabled,
        updated_by=None,
    )
    await db.flush()


async def _get_debug_otp(redis_client: object, phone: str) -> str:
    assert isinstance(redis_client, aioredis.Redis)
    otp: str | None = await redis_client.get(f"otp:phone:{phone}:debug")
    assert otp is not None, "Debug OTP not found in Redis — is KYROS_DEBUG=true?"
    return otp


async def test_phone_capture_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/me/phone/request", json={"phone": "+919000000111"})
    assert resp.status_code == 401


async def test_phone_capture_with_otp_enabled_verifies_via_code(
    client: AsyncClient, db_session: AsyncSession, redis_client: object
) -> None:
    # Default behaviour: signup OTP on → number must be confirmed via OTP.
    patient = await _google_style_patient(db_session)
    await db_session.flush()
    headers = make_auth_headers(patient)
    phone = _synth_phone()

    resp = await client.post(
        "/v1/auth/me/phone/request", json={"phone": phone}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["otp_required"] is True
    assert body["phone"] == phone

    # Not attached until confirmed.
    from app.repositories import users as users_repo

    fresh = await users_repo.get_by_id(db_session, patient.id)  # type: ignore[union-attr]
    assert fresh is not None and fresh.phone is None

    otp = await _get_debug_otp(redis_client, phone)
    resp = await client.post(
        "/v1/auth/me/phone/confirm", json={"phone": phone, "otp": otp}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    await db_session.refresh(fresh)
    assert fresh.phone == phone
    assert fresh.phone_verified is True


async def test_phone_capture_with_otp_disabled_saves_immediately(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _set_signup_otp(db_session, enabled=False)
    patient = await _google_style_patient(db_session)
    await db_session.flush()
    phone = _synth_phone()

    resp = await client.post(
        "/v1/auth/me/phone/request",
        json={"phone": phone},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["otp_required"] is False

    from app.repositories import users as users_repo

    fresh = await users_repo.get_by_id(db_session, patient.id)  # type: ignore[union-attr]
    assert fresh is not None
    assert fresh.phone == phone
    assert fresh.phone_verified is True


async def test_phone_capture_rejects_number_owned_by_another_verified_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    taken = _synth_phone()
    await create_patient_user(db_session, phone=taken, phone_verified=True)
    patient = await _google_style_patient(db_session)
    await db_session.flush()

    resp = await client.post(
        "/v1/auth/me/phone/request",
        json={"phone": taken},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "phone_already_registered"


async def test_phone_capture_invalid_format_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _google_style_patient(db_session)
    await db_session.flush()
    resp = await client.post(
        "/v1/auth/me/phone/request",
        json={"phone": "98765"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 422
