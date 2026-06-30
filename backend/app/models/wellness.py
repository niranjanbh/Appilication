from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import (
    HealthDatapointSource,
    HealthDatapointType,
    HealthSyncSource,
    HealthSyncStatus,
    ReminderAction,
    ReminderType,
    enum_values,
)
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Reminder(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "wn_reminders"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ReminderType] = mapped_column(
        SAEnum(ReminderType, name="reminder_type", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    schedule_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    # When the reminder stops producing occurrences (e.g. a finite medication
    # course). NULL = open-ended. Queries ignore occurrences after this instant.
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notification_channels: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    # Provenance: where the reminder came from, the source row's id, and who
    # created it. Explicit columns (not buried in metadata) so editing/regeneration
    # rules can key on origin. Stored as strings (see ReminderSourceType/…GeneratedBy).
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'manual'")
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    generated_by: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'patient'")
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )


class ReminderLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wn_reminder_logs"

    reminder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wn_reminders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[ReminderAction] = mapped_column(
        SAEnum(ReminderAction, name="reminder_action", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    action_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class HealthSyncSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wn_health_sync_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[HealthSyncSource] = mapped_column(
        SAEnum(HealthSyncSource, name="health_sync_source", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    consent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_consent_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[HealthSyncStatus] = mapped_column(
        SAEnum(HealthSyncStatus, name="health_sync_status", create_type=False, values_callable=enum_values),
        nullable=False,
    )


class SymptomCheckIn(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wn_symptom_checkins"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mood: Mapped[int] = mapped_column(Integer, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HealthDatapoint(Base):
    """Monthly-partitioned health datapoint. PK includes measured_at for Postgres partitioning."""

    __tablename__ = "wn_health_datapoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[HealthDatapointSource] = mapped_column(
        SAEnum(
            HealthDatapointSource,
            name="health_datapoint_source",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wn_health_sync_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[HealthDatapointType] = mapped_column(
        SAEnum(
            HealthDatapointType,
            name="health_datapoint_type",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
