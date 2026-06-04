from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def _validate_e164(phone: str) -> str:
    if not _E164_RE.match(phone):
        raise ValueError("phone must be E.164 format, e.g. +919876543210")
    return phone


class SignupRequest(BaseModel):
    name: str
    phone: str
    email: str
    password: str

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


class SendOtpRequest(BaseModel):
    phone: str

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


class RefreshRequest(BaseModel):
    refresh_token: str
