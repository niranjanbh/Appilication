from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

# Preferred OTP delivery channel. None → automatic (WhatsApp → email → SMS).
# The other channels remain as fallback if the preferred one fails to deliver.
OtpChannel = Literal["whatsapp", "email", "sms"]


def _validate_e164(phone: str) -> str:
    if not _E164_RE.match(phone):
        raise ValueError("phone must be E.164 format, e.g. +919876543210")
    return phone


class SignupRequest(BaseModel):
    name: str
    phone: str
    email: str
    password: str
    channel: OtpChannel | None = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        return _validate_e164(v)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class SignupResponse(BaseModel):
    message: str
    phone: str
    otp_hint: str | None = None
    otp_required: bool = True
    access_token: str | None = None
    token_type: str = "bearer"
    refresh_token: str | None = None
    expires_in: int | None = None


class SendOtpRequest(BaseModel):
    phone: str
    channel: OtpChannel | None = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        return _validate_e164(v)


class SendOtpResponse(BaseModel):
    message: str


class VerifyOtpRequest(BaseModel):
    phone: str
    otp: str

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        return _validate_e164(v)


class LoginRequest(BaseModel):
    email_or_phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_in: int


class MfaChallengeResponse(BaseModel):
    """Returned from /login in place of TokenResponse when staff MFA is enabled."""

    mfa_required: bool = True
    challenge_token: str
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    # Email or E.164 phone. Works for every role.
    identifier: str


class PasswordResetRequestResponse(BaseModel):
    # Deliberately generic — never reveals whether the identifier exists.
    message: str
    otp_hint: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    identifier: str
    otp: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class PasswordResetConfirmResponse(BaseModel):
    message: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class AuthConfigResponse(BaseModel):
    google_oauth_enabled: bool
    signup_otp_enabled: bool


class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MfaConfirmRequest(BaseModel):
    code: str


class MfaConfirmResponse(BaseModel):
    recovery_codes: list[str]


class MfaDisableRequest(BaseModel):
    password: str


class MfaVerifyRequest(BaseModel):
    challenge_token: str
    code: str
