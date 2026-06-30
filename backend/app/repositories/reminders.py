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
    if reminder.ends_at is not None and reminder.ends_at.astimezone(IST).date() < target_date:
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
    ends_at: datetime | None = None,
    source_type: str = "manual",
    source_id: uuid.UUID | None = None,
    generated_by: str = "patient",
) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        type=type,
        label=label,
        schedule_cron=schedule_cron,
        schedule_interval_minutes=schedule_interval_minutes,
        notification_channels=notification_channels,
        extra_metadata=extra_metadata,
        ends_at=ends_at,
        source_type=source_type,
        source_id=source_id,
        generated_by=generated_by,
    )
    db.add(reminder)
    await db.flush()
    return reminder


async def deactivate_ended_reminders(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    """Deactivate active reminders whose finite course (``ends_at``) has passed.

    Idempotent — only flips rows still active. The row is kept (active=False) so
    its adherence history survives; it simply stops appearing as active and stops
    firing. Returns the count deactivated.
    """
    cutoff = now or datetime.now(UTC)
    result = await db.execute(
        update(Reminder)
        .where(
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
            Reminder.ends_at.is_not(None),
            Reminder.ends_at < cutoff,
        )
        .values(active=False, updated_at=datetime.now(UTC))
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


async def deactivate_reminders_for_source(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
) -> int:
    """Deactivate active reminders that originated from a given source row.

    Used when regenerating reminders for a (re-signed / superseded) prescription
    so the previous version's reminders stop firing. Returns the count affected.
    Rows are kept (active=False) to preserve adherence history and provenance.
    """
    result = await db.execute(
        update(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.source_type == source_type,
            Reminder.source_id == source_id,
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
        .values(active=False, updated_at=datetime.now(UTC))
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


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
    """Record an adherence action for a reminder's scheduled slot, idempotently.

    A reminder occurrence is identified by ``(reminder_id, scheduled_at)``. Logging
    the same slot again — a double-tap, a retry, or a changed decision
    (skipped → taken) — updates the existing row in place rather than inserting a
    duplicate. Duplicates would otherwise skew ``get_adherence_rate``, which counts
    every log row.
    """
    existing = await db.execute(
        select(ReminderLog)
        .where(
            ReminderLog.reminder_id == reminder_id,
            ReminderLog.user_id == user_id,
            ReminderLog.scheduled_at == scheduled_at,
        )
        .order_by(ReminderLog.created_at.asc())
    )
    rows = list(existing.scalars().all())
    if rows:
        # Keep the earliest row and self-heal any legacy duplicates for this slot
        # (created before logging was idempotent) so they stop skewing
        # get_adherence_rate, which counts every row.
        log = rows[0]
        log.action = action
        log.action_at = action_at
        log.notes = notes
        for dup in rows[1:]:
            await db.delete(dup)
    else:
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


async def get_day_status_reminder_ids(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_date: date_type,
) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    """Return ``(resolved_ids, completed_ids)`` for reminders on a given IST date.

    ``resolved`` = an explicit ``taken`` or ``skipped`` log exists in the IST day
    window (the patient has dealt with that occurrence); ``snoozed`` is not
    resolved (deferred, will re-notify). ``completed`` is the subset with a
    ``taken`` log. The mobile UI uses ``resolved`` to suppress overdue urgency and
    ``completed`` to mark a reminder as done (vs merely skipped).
    """
    day_start_ist = datetime(target_date.year, target_date.month, target_date.day, tzinfo=IST)
    day_start = day_start_ist.astimezone(UTC)
    day_end = day_start + timedelta(days=1)

    result = await db.execute(
        select(ReminderLog.reminder_id, ReminderLog.action)
        .join(Reminder, ReminderLog.reminder_id == Reminder.id)
        .where(
            ReminderLog.user_id == user_id,
            ReminderLog.action.in_((ReminderAction.TAKEN, ReminderAction.SKIPPED)),
            ReminderLog.scheduled_at >= day_start,
            ReminderLog.scheduled_at < day_end,
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
        .distinct()
    )
    resolved: list[uuid.UUID] = []
    completed: list[uuid.UUID] = []
    seen_resolved: set[uuid.UUID] = set()
    for reminder_id, action in result.all():
        if reminder_id not in seen_resolved:
            seen_resolved.add(reminder_id)
            resolved.append(reminder_id)
        if action == ReminderAction.TAKEN:
            completed.append(reminder_id)
    return resolved, completed


STREAK_THRESHOLD = 0.80


async def _adherence_day_inputs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    lookback_days: int,
) -> tuple[dict[date_type, int], list[Reminder]]:
    """Shared inputs for streak math: completed-taken-per-IST-day plus the
    patient's active reminders (used for each day's scheduled denominator)."""
    since = datetime.now(IST) - timedelta(days=lookback_days)
    result = await db.execute(
        select(
            func.date(func.timezone("Asia/Kolkata", ReminderLog.scheduled_at)).label("d"),
            func.count(func.distinct(ReminderLog.reminder_id)).label("c"),
        )
        .join(Reminder, ReminderLog.reminder_id == Reminder.id)
        .where(
            ReminderLog.user_id == user_id,
            ReminderLog.action == ReminderAction.TAKEN,
            ReminderLog.scheduled_at >= since.astimezone(UTC),
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
        .group_by(text("d"))
    )
    completed_by_day: dict[date_type, int] = {}
    for row in result.all():
        d = row.d
        if isinstance(d, datetime):
            d = d.date()
        completed_by_day[d] = row.c

    reminders_result = await db.execute(
        select(Reminder).where(
            Reminder.user_id == user_id,
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
    )
    return completed_by_day, list(reminders_result.scalars().all())


async def get_adherence_streak(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    max_lookback_days: int = 90,
    threshold: float = STREAK_THRESHOLD,
) -> int:
    """Count consecutive IST days where the patient completed ``threshold`` (80%
    by default) of that day's scheduled reminders.

    A day's denominator is the reminders actually scheduled on it (a Monday-only
    cron does not count toward Tuesday; a reminder is not counted before it was
    created). Days with **no** scheduled reminders are neutral — they neither
    extend nor break the streak (e.g. a weekend with weekday-only reminders).
    Today is only required to qualify if it already meets the threshold; an
    in-progress today does not break a prior streak.

    Only active, non-deleted reminders count, matching the daily summary.
    """
    completed_by_day, reminders = await _adherence_day_inputs(
        db, user_id=user_id, lookback_days=max_lookback_days
    )

    def scheduled_count(d: date_type) -> int:
        return sum(1 for r in reminders if _reminder_scheduled_on_date(r, d))

    def meets_threshold(d: date_type) -> bool:
        scheduled = scheduled_count(d)
        if scheduled == 0:
            return False
        done = min(completed_by_day.get(d, 0), scheduled)
        return done / scheduled >= threshold

    today = datetime.now(IST).date()
    # Start at today only if it already qualifies; otherwise yesterday, so an
    # unfinished today does not reset the streak.
    check = today if meets_threshold(today) else today - timedelta(days=1)

    streak = 0
    for _ in range(max_lookback_days):
        scheduled = scheduled_count(check)
        if scheduled == 0:
            # Neutral day — skip without breaking.
            check -= timedelta(days=1)
            continue
        done = min(completed_by_day.get(check, 0), scheduled)
        if done / scheduled >= threshold:
            streak += 1
            check -= timedelta(days=1)
        else:
            break

    return streak


async def get_longest_streak(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    max_lookback_days: int = 90,
    threshold: float = STREAK_THRESHOLD,
) -> int:
    """Longest run of qualifying days within the lookback window.

    Same day semantics as ``get_adherence_streak``: neutral (nothing scheduled)
    days bridge a run without extending it; an in-progress today that hasn't yet
    met the threshold is treated as neutral so it never truncates the maximum.
    """
    completed_by_day, reminders = await _adherence_day_inputs(
        db, user_id=user_id, lookback_days=max_lookback_days
    )

    def scheduled_count(d: date_type) -> int:
        return sum(1 for r in reminders if _reminder_scheduled_on_date(r, d))

    today = datetime.now(IST).date()
    longest = 0
    current = 0
    for offset in range(max_lookback_days, -1, -1):  # oldest → today
        day = today - timedelta(days=offset)
        scheduled = scheduled_count(day)
        if scheduled == 0:
            continue  # neutral — bridges a run
        done = min(completed_by_day.get(day, 0), scheduled)
        if done / scheduled >= threshold:
            current += 1
            longest = max(longest, current)
        elif day == today:
            continue  # in-progress today does not break the run
        else:
            current = 0
    return longest


async def get_overall_adherence_rate(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    days: int = 30,
) -> float:
    """Fraction taken/(taken+skipped+missed) across all the patient's active
    reminders over the last ``days`` days. Snoozes are excluded (deferred, not a
    miss), matching the per-reminder rate."""
    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(ReminderLog.action, func.count().label("cnt"))
        .join(Reminder, ReminderLog.reminder_id == Reminder.id)
        .where(
            ReminderLog.user_id == user_id,
            ReminderLog.scheduled_at >= since,
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
        .group_by(ReminderLog.action)
    )
    counts: dict[str, int] = {row.action: row.cnt for row in result.all()}
    taken = counts.get(ReminderAction.TAKEN, 0)
    total = sum(
        counts.get(a, 0)
        for a in (ReminderAction.TAKEN, ReminderAction.SKIPPED, ReminderAction.MISSED)
    )
    return round(taken / total, 2) if total > 0 else 0.0


async def get_last_missed_at(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> datetime | None:
    """Most recent occurrence the patient did not take (skipped or missed),
    across active reminders. None if there is none."""
    result = await db.execute(
        select(func.max(ReminderLog.scheduled_at))
        .join(Reminder, ReminderLog.reminder_id == Reminder.id)
        .where(
            ReminderLog.user_id == user_id,
            ReminderLog.action.in_((ReminderAction.SKIPPED, ReminderAction.MISSED)),
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def count_active_reminders_by_source(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_type: str,
) -> int:
    """Count of the patient's active reminders from a given provenance source."""
    result = await db.execute(
        select(func.count())
        .select_from(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.source_type == source_type,
            Reminder.active.is_(True),
            Reminder.deleted_at.is_(None),
        )
    )
    return int(result.scalar() or 0)


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
        # A finite course that has ended produces no further occurrences.
        if reminder.ends_at is not None and eval_now > reminder.ends_at:
            continue
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
