from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
