from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ReminderAction, ReminderType
from app.models.wellness import Reminder, ReminderLog


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
    reminder = Reminder(
        user_id=user_id,
        type=type,
        label=label,
        schedule_cron=schedule_cron,
        schedule_interval_minutes=schedule_interval_minutes,
        notification_channels=notification_channels,
        extra_metadata=extra_metadata,
    )
    db.add(reminder)
    await db.flush()
    return reminder


async def get_reminder_for_user(
    db: AsyncSession,
    *,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Reminder | None:
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == user_id,
            Reminder.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_reminders_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    include_inactive: bool = False,
) -> list[Reminder]:
    stmt = select(Reminder).where(
        Reminder.user_id == user_id,
        Reminder.deleted_at.is_(None),
    )
    if not include_inactive:
        stmt = stmt.where(Reminder.active.is_(True))
    stmt = stmt.order_by(Reminder.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_reminder(
    db: AsyncSession,
    *,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    **kwargs: Any,
) -> Reminder | None:
    reminder = await get_reminder_for_user(db, reminder_id=reminder_id, user_id=user_id)
    if reminder is None:
        return None
    for key, value in kwargs.items():
        if value is not None or key == "active":
            setattr(reminder, key, value)
    reminder.updated_at = datetime.now(UTC)
    await db.flush()
    return reminder


async def soft_delete_reminder(
    db: AsyncSession,
    *,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        update(Reminder)
        .where(
            Reminder.id == reminder_id,
            Reminder.user_id == user_id,
            Reminder.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(UTC), active=False, updated_at=datetime.now(UTC))
    )
    return bool(result.rowcount > 0)  # type: ignore[attr-defined]


async def log_adherence(
    db: AsyncSession,
    *,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    scheduled_at: datetime,
    action: ReminderAction,
    action_at: datetime,
    notes: str | None,
) -> ReminderLog:
    log = ReminderLog(
        reminder_id=reminder_id,
        user_id=user_id,
        scheduled_at=scheduled_at,
        action=action,
        action_at=action_at,
        notes=notes,
    )
    db.add(log)
    await db.flush()
    return log


async def get_adherence_rate(
    db: AsyncSession,
    *,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    days: int = 30,
) -> float:
    """Return fraction of taken/(taken+skipped+missed) logs in the last `days` days."""
    from datetime import timedelta

    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(ReminderLog.action, func.count().label("cnt"))
        .where(
            ReminderLog.reminder_id == reminder_id,
            ReminderLog.user_id == user_id,
            ReminderLog.scheduled_at >= since,
        )
        .group_by(ReminderLog.action)
    )
    rows = result.all()
    counts: dict[str, int] = {row.action: row.cnt for row in rows}
    taken = counts.get(ReminderAction.TAKEN, 0)
    total = sum(
        counts.get(a, 0)
        for a in (ReminderAction.TAKEN, ReminderAction.SKIPPED, ReminderAction.MISSED)
    )
    return round(taken / total, 2) if total > 0 else 0.0


async def get_due_reminders(
    db: AsyncSession,
    *,
    active_only: bool = True,
) -> list[Reminder]:
    """Return all active reminders for notification dispatch."""
    stmt = select(Reminder).where(Reminder.deleted_at.is_(None))
    if active_only:
        stmt = stmt.where(Reminder.active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())
