from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ReminderAction, ReminderType
from app.models.wellness import Reminder, ReminderLog
from app.repositories import reminders as reminders_repo


async def create_reminder(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: ReminderType,
    label: str,
    schedule_cron: str | None,
    schedule_interval_minutes: int | None,
    notification_channels: list[Any],
    extra_metadata: dict[str, Any] | None,
) -> Reminder:
    return await reminders_repo.create_reminder(
        db,
        user_id=user_id,
        type=type,
        label=label,
        schedule_cron=schedule_cron,
        schedule_interval_minutes=schedule_interval_minutes,
        notification_channels=notification_channels,
        extra_metadata=extra_metadata,
    )


async def log_adherence(
    db: AsyncSession,
    *,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    scheduled_at: datetime,
    action: ReminderAction,
    notes: str | None,
) -> ReminderLog:
    return await reminders_repo.log_adherence(
        db,
        reminder_id=reminder_id,
        user_id=user_id,
        scheduled_at=scheduled_at,
        action=action,
        action_at=datetime.now(UTC),
        notes=notes,
    )
