from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.db.enums import ConsentType, UserGender, UserRole


class UserMeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str | None = None
    phone: str | None = None
    phone_verified: bool
    email_verified: bool
    role: UserRole
    date_of_birth: date | None = None
    gender: UserGender | None = None
    city: str | None = None
    state: str | None = None
    language_preference: str | None = None
    timezone: str
    last_login_at: datetime | None = None
    created_at: datetime


class ConsentRequest(BaseModel):
    consent_type: ConsentType
    version: str
    granted: bool
    consent_text: str


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    consent_type: ConsentType
    version: str
    granted: bool
    granted_at: datetime
    revoked_at: datetime | None = None
    ip_address: str | None = None

    @field_validator("ip_address", mode="before")
    @classmethod
    def _coerce_ip(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v)


class ConsentListResponse(BaseModel):
    consents: list[ConsentRead]


class ConsentWithdrawRequest(BaseModel):
    consent_type: ConsentType


class DataExportResponse(BaseModel):
    message: str
    request_id: uuid.UUID


class ErasureResponse(BaseModel):
    message: str
    request_id: uuid.UUID


class SessionRead(BaseModel):
    session_id: uuid.UUID
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    is_current: bool


class SessionListResponse(BaseModel):
    items: list[SessionRead]


class SessionRevokeResponse(BaseModel):
    revoked: int
