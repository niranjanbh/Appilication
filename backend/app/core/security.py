from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings
from app.db.enums import UserRole

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def generate_otp(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hash_otp(code: str) -> str:
    """HMAC-SHA256 of the OTP code using the deployment otp_secret."""
    return hmac.new(
        settings.otp_secret.encode(), code.encode(), hashlib.sha256
    ).hexdigest()


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_refresh_token(raw_token: str) -> str:
    """SHA-256 hex digest of a raw refresh token."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


@dataclass
class TokenClaims:
    sub: str
    role: UserRole
    jti: str
    session_id: str
    v: int
    aud: str
    mfa: bool


# Staff plane: provisioned accounts, mandatory MFA, short idle-timeout sessions, a
# different token audience from the patient app (staff-rbac-spec §1).
_STAFF_ROLES: frozenset[UserRole] = frozenset(
    {UserRole.DOCTOR, UserRole.COORDINATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN}
)


def audience_for_role(role: UserRole) -> str:
    return "staff" if role in _STAFF_ROLES else "patient"


def create_access_token(
    user_id: uuid.UUID,
    role: UserRole,
    session_id: uuid.UUID,
    *,
    mfa_verified: bool = False,
) -> str:
    now = datetime.now(UTC)
    aud = audience_for_role(role)
    ttl_minutes = (
        settings.jwt_staff_access_token_expire_minutes
        if aud == "staff"
        else settings.jwt_access_token_expire_minutes
    )
    exp = now + timedelta(minutes=ttl_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
        "session_id": str(session_id),
        "v": 1,
        "aud": aud,
        "mfa": mfa_verified,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenClaims:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_or_expired_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    try:
        return TokenClaims(
            sub=payload["sub"],
            role=UserRole(payload["role"]),
            jti=payload["jti"],
            session_id=payload["session_id"],
            v=payload["v"],
            # Tokens minted before audience separation shipped decode as
            # patient-audience/non-MFA, which forces a staff re-login (audience
            # mismatch) rather than erroring here.
            aud=payload.get("aud", "patient"),
            mfa=payload.get("mfa", False),
        )
    except (KeyError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="malformed_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


# ── Staff MFA (TOTP) ─────────────────────────────────────────────────────────────

_RECOVERY_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def _mfa_fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.mfa_encryption_key.encode()).digest())
    return Fernet(key)


def encrypt_mfa_secret(secret: str) -> str:
    return _mfa_fernet().encrypt(secret.encode()).decode()


def decrypt_mfa_secret(token: str) -> str:
    return _mfa_fernet().decrypt(token.encode()).decode()


def totp_provisioning_uri(secret: str, account_name: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=account_name, issuer_name="Kyros Clinic"
    )


def verify_totp_code(secret: str, code: str) -> bool:
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)


def generate_recovery_codes(n: int) -> list[str]:
    """Return ``n`` one-time recovery codes formatted ``XXXXX-XXXXX``."""
    return [
        "-".join(
            "".join(secrets.choice(_RECOVERY_CODE_ALPHABET) for _ in range(5))
            for _ in range(2)
        )
        for _ in range(n)
    ]
