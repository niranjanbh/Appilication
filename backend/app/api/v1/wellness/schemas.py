from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.enums import (
    HealthDatapointType,
    HealthSyncSource,
    HealthSyncStatus,
    ReminderAction,
    ReminderType,
)


class ReminderCreate(BaseModel):
    type: ReminderType
    label: str = Field(..., min_length=1, max_length=255)
    schedule_cron: str | None = Field(None, max_length=100)
    schedule_interval_minutes: int | None = Field(None, ge=1, le=1440)
    notification_channels: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class ReminderUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=255)
    schedule_cron: str | None = None
    schedule_interval_minutes: int | None = Field(None, ge=1, le=1440)
    active: bool | None = None
    notification_channels: list[str] | None = None
    metadata: dict[str, Any] | None = None


class ReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ReminderType
    label: str
    schedule_cron: str | None
    schedule_interval_minutes: int | None
    active: bool
    notification_channels: list[Any]
    # ORM attribute is `extra_metadata` (to avoid clash with Base.metadata);
    # we expose it to clients as `metadata`.
    metadata: dict[str, Any] | None = Field(None, validation_alias="extra_metadata")
    created_at: datetime
    updated_at: datetime
    adherence_rate: float = 0.0


class ReminderListResponse(BaseModel):
    reminders: list[ReminderRead]
    total: int


class ReminderImageInitiateRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str
    file_size_bytes: int = Field(..., ge=1)


class ReminderImageInitiateResponse(BaseModel):
    reminder_id: uuid.UUID
    upload_url: str
    fields: dict[str, str]
    s3_key: str
    content_type: str


class ReminderImageUrlResponse(BaseModel):
    url: str


class DailySummaryResponse(BaseModel):
    date: str
    total: int
    completed: int
    streak: int


class WeekDaySummary(BaseModel):
    date: str
    total: int
    completed: int


class WeekSummaryResponse(BaseModel):
    days: list[WeekDaySummary]


class AdherenceLogRequest(BaseModel):
    scheduled_at: datetime
    action: ReminderAction
    notes: str | None = Field(None, max_length=500)


class AdherenceLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reminder_id: uuid.UUID
    scheduled_at: datetime
    action: ReminderAction
    action_at: datetime
    notes: str | None
    created_at: datetime


# ── Health sync ────────────────────────────────────────────────────────────────


class HealthDatapointItem(BaseModel):
    type: HealthDatapointType
    source_record_id: str = Field(..., min_length=1, max_length=255)
    measured_at: datetime
    value: dict[str, Any]


class HealthSyncRequest(BaseModel):
    source: HealthSyncSource
    data_range_start: datetime
    data_range_end: datetime
    datapoints: list[HealthDatapointItem] = Field(default_factory=list, max_length=500)


class HealthSyncResponse(BaseModel):
    session_id: uuid.UUID
    inserted_count: int
    skipped_count: int
    status: HealthSyncStatus


# ── Manual vitals ────────────────────────────────────────────────────────────────


class VitalsLogRequest(BaseModel):
    measured_at: datetime
    weight_kg: float | None = Field(None, gt=0, le=500)
    blood_pressure_systolic: int | None = Field(None, ge=40, le=300)
    blood_pressure_diastolic: int | None = Field(None, ge=20, le=250)
    blood_glucose_mg_dl: float | None = Field(None, gt=0, le=2000)

    @model_validator(mode="after")
    def _validate(self) -> VitalsLogRequest:
        provided = (
            self.weight_kg,
            self.blood_pressure_systolic,
            self.blood_pressure_diastolic,
            self.blood_glucose_mg_dl,
        )
        if all(v is None for v in provided):
            raise ValueError("at least one vital must be provided")
        if (self.blood_pressure_systolic is None) != (self.blood_pressure_diastolic is None):
            raise ValueError("blood pressure requires both systolic and diastolic")
        return self


class VitalsLogResponse(BaseModel):
    logged_count: int


class VitalReadItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: HealthDatapointType
    value: dict[str, Any]
    measured_at: datetime


class VitalsListResponse(BaseModel):
    items: list[VitalReadItem]
