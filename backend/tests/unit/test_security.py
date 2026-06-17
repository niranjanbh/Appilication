"""Unit tests for staff auth plane primitives: audience separation and TOTP MFA
helpers (staff-rbac-spec §1)."""

from __future__ import annotations

import re
import uuid

import pyotp
from jose import jwt

from app.core.config import settings
from app.core.security import (
    audience_for_role,
    create_access_token,
    decrypt_mfa_secret,
    encrypt_mfa_secret,
    generate_recovery_codes,
    generate_totp_secret,
    verify_totp_code,
)
from app.db.enums import UserRole


def test_audience_for_role_patient() -> None:
    assert audience_for_role(UserRole.PATIENT) == "patient"


def test_audience_for_role_staff() -> None:
    for role in (UserRole.DOCTOR, UserRole.COORDINATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN):
        assert audience_for_role(role) == "staff"


def _decode(token: str) -> dict[str, object]:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"verify_aud": False},
    )


def test_create_access_token_patient_claims() -> None:
    token = create_access_token(uuid.uuid4(), UserRole.PATIENT, uuid.uuid4())
    payload = _decode(token)
    assert payload["aud"] == "patient"
    assert payload["mfa"] is False
    delta = payload["exp"] - payload["iat"]
    assert delta == settings.jwt_access_token_expire_minutes * 60


def test_create_access_token_staff_claims() -> None:
    token = create_access_token(uuid.uuid4(), UserRole.DOCTOR, uuid.uuid4(), mfa_verified=True)
    payload = _decode(token)
    assert payload["aud"] == "staff"
    assert payload["mfa"] is True
    delta = payload["exp"] - payload["iat"]
    assert delta == settings.jwt_staff_access_token_expire_minutes * 60


def test_encrypt_decrypt_mfa_secret_round_trip() -> None:
    secret = generate_totp_secret()
    encrypted = encrypt_mfa_secret(secret)
    assert encrypted != secret
    assert decrypt_mfa_secret(encrypted) == secret


def test_verify_totp_code_accepts_current_code() -> None:
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).now()
    assert verify_totp_code(secret, code) is True


def test_verify_totp_code_rejects_wrong_code() -> None:
    secret = generate_totp_secret()
    # A fixed wrong code is astronomically unlikely to match the current TOTP.
    assert verify_totp_code(secret, "000000") is False


def test_generate_recovery_codes_count_format_and_uniqueness() -> None:
    codes = generate_recovery_codes(8)
    assert len(codes) == 8
    assert len(set(codes)) == 8
    for code in codes:
        assert re.fullmatch(r"[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{5}-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{5}", code)
