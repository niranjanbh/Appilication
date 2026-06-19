from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.enums import (
    ConsentType,
    DataSubjectRequestStatus,
    UserGender,
    UserRole,
)


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


class DataExportSummary(BaseModel):
    id: uuid.UUID
    status: DataSubjectRequestStatus
    requested_at: datetime
    completed_at: datetime | None = None


class DataExportListResponse(BaseModel):
    items: list[DataExportSummary]


class DataExportStatusRead(DataExportSummary):
    # Present only when the export is COMPLETED. Short-lived presigned GET URL.
    download_url: str | None = None
    download_expires_in_seconds: int | None = None


class ErasureResponse(BaseModel):
    message: str
    request_id: uuid.UUID


class EmergencyContactWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    relationship: str = Field(min_length=1, max_length=60)
    phone: str = Field(min_length=4, max_length=20)
    email: str | None = Field(default=None, max_length=255)


class EmergencyContactRead(BaseModel):
    name: str | None = None
    relationship: str | None = None
    phone: str | None = None
    email: str | None = None


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


class ActivityItem(BaseModel):
    action: str
    description: str
    resource_type: str | None = None
    allowed: bool
    ip_address: str | None = None
    timestamp: datetime


class ActivityListResponse(BaseModel):
    items: list[ActivityItem]
    total: int
    page: int
    page_size: int
    pages: int
