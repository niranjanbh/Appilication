from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schedule import cron_matches_date
from app.db.enums import ReminderAction, ReminderType
from app.models.wellness import Reminder, ReminderLog

IST = ZoneInfo("Asia/Kolkata")


def _reminder_scheduled_on_date(reminder: Reminder, target_date: date_type) -> bool:
    """True if this reminder has a scheduled occurrence on target_date (IST)."""
    created_ist = reminder.created_at.astimezone(IST).date()
    if created_ist > target_date:
        return False
    if reminder.schedule_interval_minutes and reminder.schedule_interval_minutes > 0:
        return True
    if reminder.schedule_cron:
        return cron_matches_date(reminder.schedule_cron, target_date)
    return False


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


async def get_daily_adherence_summary(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_date: date_type,
) -> tuple[int, int]:
    """Return (scheduled_reminders, completed_count) for a given IST date.

    ``total`` counts only reminders scheduled on ``target_date`` (a Monday-only
    cron does not count on Wednesday; a reminder created after the date does not
    count). ``completed`` is clamped to ``total`` so progress never exceeds 100%.
    """
    day_start_ist = datetime(target_date.year, target_date.month, target_date.day, tzinfo=IST)
    day_start = day_start_ist.astimezone(UTC)
    day_end = day_start + timedelta(days=1)

    reminders_result = await db.execute(
        select(Reminder).where(
            Reminder.user_id == user_id,
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
    )
    reminders = list(reminders_result.scalars().all())
    total = sum(1 for r in reminders if _reminder_scheduled_on_date(r, target_date))

    completed_result = await db.execute(
        select(func.count(func.distinct(ReminderLog.reminder_id)))
        .join(Reminder, ReminderLog.reminder_id == Reminder.id)
        .where(
            ReminderLog.user_id == user_id,
            ReminderLog.action == ReminderAction.TAKEN,
            ReminderLog.scheduled_at >= day_start,
            ReminderLog.scheduled_at < day_end,
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
    )
    completed = completed_result.scalar() or 0

    return total, min(completed, total)


async def get_adherence_streak(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    max_lookback_days: int = 90,
) -> int:
    """Count consecutive IST days ending at today (or yesterday) with at least one 'taken' log."""
    since = datetime.now(IST) - timedelta(days=max_lookback_days)

    result = await db.execute(
        select(
            func.date(func.timezone("Asia/Kolkata", ReminderLog.scheduled_at)).label("d")
        )
        .join(Reminder, ReminderLog.reminder_id == Reminder.id)
        .where(
            ReminderLog.user_id == user_id,
            ReminderLog.action == ReminderAction.TAKEN,
            ReminderLog.scheduled_at >= since.astimezone(UTC),
            Reminder.deleted_at.is_(None),
        )
        .group_by(text("d"))
        .order_by(text("d DESC"))
    )
    log_dates: set[date_type] = set()
    for row in result.all():
        d = row[0]
        if isinstance(d, datetime):
            d = d.date()
        log_dates.add(d)

    if not log_dates:
        return 0

    today = datetime.now(IST).date()
    check = today if today in log_dates else today - timedelta(days=1)
    if check not in log_dates:
        return 0

    streak = 0
    while check in log_dates and streak < max_lookback_days:
        streak += 1
        check -= timedelta(days=1)

    return streak


async def get_week_adherence(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    week_start: date_type,
) -> list[tuple[date_type, int]]:
    """Return (ist_date, completed_count) pairs for 7 days starting from week_start."""
    start_ist = datetime(week_start.year, week_start.month, week_start.day, tzinfo=IST)
    start_utc = start_ist.astimezone(UTC)
    end_utc = start_utc + timedelta(days=7)

    result = await db.execute(
        select(
            func.date(func.timezone("Asia/Kolkata", ReminderLog.scheduled_at)).label("d"),
            func.count(func.distinct(ReminderLog.reminder_id)).label("cnt"),
        )
        .join(Reminder, ReminderLog.reminder_id == Reminder.id)
        .where(
            ReminderLog.user_id == user_id,
            ReminderLog.action == ReminderAction.TAKEN,
            ReminderLog.scheduled_at >= start_utc,
            ReminderLog.scheduled_at < end_utc,
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
        .group_by(text("d"))
    )
    rows = []
    for row in result.all():
        d = row.d
        if isinstance(d, datetime):
            d = d.date()
        rows.append((d, row.cnt))
    return rows


async def get_due_reminders(
    db: AsyncSession,
    *,
    active_only: bool = True,
    now: datetime | None = None,
    window_minutes: int = 5,
) -> list[tuple[Reminder, datetime]]:
    """Return reminders with a scheduled occurrence in the dispatch window.

    Schedule-aware: each candidate is evaluated against its ``schedule_cron``
    (IST) or ``schedule_interval_minutes`` (anchored at ``created_at``). Only
    reminders genuinely due in ``(now - window_minutes, now]`` are returned, each
    paired with its occurrence timestamp (UTC) — the dispatch idempotency slot.

    ``window_minutes`` should match the beat tick (every 5 minutes) so each
    scheduled minute lands in exactly one window. ``now`` is injectable for tests.
    """
    from app.core.schedule import due_occurrence

    eval_now = now or datetime.now(UTC)
    window = timedelta(minutes=window_minutes)

    stmt = select(Reminder).where(Reminder.deleted_at.is_(None))
    if active_only:
        stmt = stmt.where(Reminder.active.is_(True))
    result = await db.execute(stmt)

    due: list[tuple[Reminder, datetime]] = []
    for reminder in result.scalars().all():
        occurrence = due_occurrence(
            schedule_cron=reminder.schedule_cron,
            schedule_interval_minutes=reminder.schedule_interval_minutes,
            created_at=reminder.created_at,
            now=eval_now,
            window=window,
        )
        if occurrence is not None:
            due.append((reminder, occurrence))
    return due
