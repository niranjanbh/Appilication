"""Integration tests: staff MFA enrollment, login challenge, recovery codes,
and JWT audience separation (staff-rbac-spec §1)."""

from __future__ import annotations

import pyotp
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.db.enums import UserRole
from tests.conftest import create_doctor_user, make_auth_headers

_DOCTOR_PASSWORD = "TestPass123!"


async def _verified_doctor(db: AsyncSession) -> object:
    from app.models.identity import User as UserModel
    from app.repositories import users as users_repo

    doctor = await create_doctor_user(db)
    assert isinstance(doctor, UserModel)
    await users_repo.update_phone_verified(db, doctor.id)
    return doctor


async def _enroll_mfa(client: AsyncClient, doctor: object) -> tuple[str, list[str]]:
    """Enroll + confirm TOTP MFA for `doctor`. Returns (totp_secret, recovery_codes)."""
    resp = await client.post("/v1/auth/mfa/setup", headers=make_auth_headers(doctor))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    secret = body["secret"]
    assert body["provisioning_uri"].startswith("otpauth://totp/")

    code = pyotp.TOTP(secret).now()
    resp = await client.post(
        "/v1/auth/mfa/confirm", json={"code": code}, headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 200, resp.text
    recovery_codes = resp.json()["recovery_codes"]
    assert len(recovery_codes) == settings.mfa_recovery_codes_count
    return secret, recovery_codes


# ── Login challenge ──────────────────────────────────────────────────────────


async def test_login_with_mfa_enabled_returns_challenge(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)
    await _enroll_mfa(client, doctor)

    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mfa_required"] is True
    assert "challenge_token" in body
    assert "access_token" not in body


# ── /mfa/verify with TOTP ────────────────────────────────────────────────────


async def test_mfa_verify_with_totp_returns_staff_audience_tokens(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)
    secret, _recovery_codes = await _enroll_mfa(client, doctor)

    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    challenge_token = resp.json()["challenge_token"]

    code = pyotp.TOTP(secret).now()
    resp = await client.post(
        "/v1/auth/mfa/verify", json={"challenge_token": challenge_token, "code": code}
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["expires_in"] == settings.jwt_staff_access_token_expire_minutes * 60

    payload = jwt.decode(
        tokens["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert payload["aud"] == "staff"
    assert payload["mfa"] is True


async def test_mfa_verify_wrong_code_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)
    await _enroll_mfa(client, doctor)

    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    challenge_token = resp.json()["challenge_token"]

    resp = await client.post(
        "/v1/auth/mfa/verify", json={"challenge_token": challenge_token, "code": "000000"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "mfa_invalid_code"


# ── Recovery codes ───────────────────────────────────────────────────────────


async def test_mfa_verify_with_recovery_code_is_single_use(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)
    _secret, recovery_codes = await _enroll_mfa(client, doctor)
    recovery_code = recovery_codes[0]

    # First use succeeds.
    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    challenge_token = resp.json()["challenge_token"]
    resp = await client.post(
        "/v1/auth/mfa/verify",
        json={"challenge_token": challenge_token, "code": recovery_code},
    )
    assert resp.status_code == 200, resp.text

    # Second use of the same code fails.
    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    challenge_token = resp.json()["challenge_token"]
    resp = await client.post(
        "/v1/auth/mfa/verify",
        json={"challenge_token": challenge_token, "code": recovery_code},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "mfa_invalid_code"


# ── /mfa/disable ──────────────────────────────────────────────────────────────


async def test_mfa_disable_wrong_password_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)
    secret, _recovery_codes = await _enroll_mfa(client, doctor)

    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    challenge_token = resp.json()["challenge_token"]
    code = pyotp.TOTP(secret).now()
    resp = await client.post(
        "/v1/auth/mfa/verify", json={"challenge_token": challenge_token, "code": code}
    )
    mfa_verified_token = resp.json()["access_token"]

    resp = await client.post(
        "/v1/auth/mfa/disable",
        json={"password": "WrongPassword1!"},
        headers={"Authorization": f"Bearer {mfa_verified_token}"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid_credentials"


async def test_mfa_disable_requires_mfa_verified_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A non-MFA-verified access token cannot disable MFA, even with the right password."""
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)
    await _enroll_mfa(client, doctor)

    resp = await client.post(
        "/v1/auth/mfa/disable",
        json={"password": _DOCTOR_PASSWORD},
        headers=make_auth_headers(doctor),  # mfa_verified=False by default
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "mfa_required"


async def test_mfa_disable_correct_password_returns_204(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)
    secret, _recovery_codes = await _enroll_mfa(client, doctor)

    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    challenge_token = resp.json()["challenge_token"]
    code = pyotp.TOTP(secret).now()
    resp = await client.post(
        "/v1/auth/mfa/verify", json={"challenge_token": challenge_token, "code": code}
    )
    mfa_verified_token = resp.json()["access_token"]

    resp = await client.post(
        "/v1/auth/mfa/disable",
        json={"password": _DOCTOR_PASSWORD},
        headers={"Authorization": f"Bearer {mfa_verified_token}"},
    )
    assert resp.status_code == 204

    # MFA is gone — login now returns tokens directly, no challenge.
    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


# ── Re-enrollment ─────────────────────────────────────────────────────────────


async def test_mfa_reenrollment_without_mfa_verified_session_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)
    await _enroll_mfa(client, doctor)

    # A regular (non-mfa-verified) token cannot re-enroll an already-enabled account.
    resp = await client.post("/v1/auth/mfa/setup", headers=make_auth_headers(doctor))
    assert resp.status_code == 401
    assert resp.json()["detail"] == "mfa_required"


# ── Audience separation ──────────────────────────────────────────────────────


async def test_audience_mismatch_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)

    # Forge a token with aud="patient" for a staff user's id.
    forged = create_access_token(doctor.id, UserRole.PATIENT, doctor.id)

    resp = await client.post(
        "/v1/auth/mfa/setup", headers={"Authorization": f"Bearer {forged}"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "audience_mismatch"


async def test_staff_login_without_mfa_uses_staff_access_token_ttl(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A staff account with no MFA enrolled still gets the short staff TTL and aud."""
    from app.models.identity import User as UserModel

    doctor = await _verified_doctor(db_session)
    assert isinstance(doctor, UserModel)

    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": doctor.email, "password": _DOCTOR_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["expires_in"] == settings.jwt_staff_access_token_expire_minutes * 60

    payload = jwt.decode(
        tokens["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert payload["aud"] == "staff"
    assert payload["mfa"] is False
