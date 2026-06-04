from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
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


def create_access_token(
    user_id: uuid.UUID, role: UserRole, session_id: uuid.UUID
) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
        "session_id": str(session_id),
        "v": 1,
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
        )
    except (KeyError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="malformed_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
