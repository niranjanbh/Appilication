"""Pure schedule evaluation for reminder dispatch — no DB, no I/O.

A reminder carries either a 5-field cron expression (``schedule_cron``, evaluated
in IST — the user-facing timezone) or a fixed interval in minutes
(``schedule_interval_minutes``, anchored at the reminder's ``created_at``).

``due_occurrence`` answers: did this reminder have a scheduled firing inside the
half-open window ``(now - window, now]``? It returns that occurrence's UTC
timestamp (used as the dispatch idempotency slot), or ``None``.

The dispatcher (Celery beat, every 5 minutes) passes ``window`` equal to its tick
interval, so each scheduled minute lands in exactly one window — fired at most a
few minutes late, exactly once. Cron parsing is deliberately tolerant: an
unparseable expression never matches (and never raises).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def _field_matches(field: str, value: int, lo_default: int, hi_default: int) -> bool:
    """Match one cron field (``*``, ``5``, ``8,14,20``, ``1-5``, ``*/15``, ``0-30/10``)."""
    for part in field.split(","):
        part = part.strip()
        if not part:
            return False
        step = 1
        rng = part
        if "/" in part:
            rng, step_s = part.split("/", 1)
            try:
                step = int(step_s)
            except ValueError:
                return False
            if step <= 0:
                return False
        try:
            if rng == "*":
                lo, hi = lo_default, hi_default
            elif "-" in rng:
                lo_s, hi_s = rng.split("-", 1)
                lo, hi = int(lo_s), int(hi_s)
            else:
                lo = hi = int(rng)
        except ValueError:
            return False
        if lo <= value <= hi and (value - lo) % step == 0:
            return True
    return False


def cron_matches(cron: str, dt_ist: datetime) -> bool:
    """True if the 5-field cron fires at ``dt_ist`` (minute granularity, IST).

    Day-of-week uses cron convention: 0 and 7 are both Sunday. An expression that
    is not exactly five fields, or has an unparseable field, never matches.
    """
    parts = cron.split()
    if len(parts) != 5:
        return False
    minute_f, hour_f, dom_f, month_f, dow_f = parts

    # isoweekday(): Mon=1..Sun=7  ->  cron dow: Sun=0..Sat=6 (7 also Sunday).
    cron_dow = dt_ist.isoweekday() % 7  # Mon=1..Sat=6, Sun=0
    dow_ok = _field_matches(dow_f, cron_dow, 0, 6)
    if cron_dow == 0:  # Sunday may also be written as 7
        dow_ok = dow_ok or _field_matches(dow_f, 7, 0, 7)

    return (
        _field_matches(minute_f, dt_ist.minute, 0, 59)
        and _field_matches(hour_f, dt_ist.hour, 0, 23)
        and _field_matches(dom_f, dt_ist.day, 1, 31)
        and _field_matches(month_f, dt_ist.month, 1, 12)
        and dow_ok
    )


def cron_matches_date(cron: str, target_date: date) -> bool:
    """True if the 5-field cron has any firing on ``target_date`` (IST).

    Only the date-level fields are evaluated (day-of-month, month, day-of-week);
    minute and hour are ignored. Used by adherence summaries to decide whether a
    reminder was scheduled on a given calendar day without needing a specific time.
    An expression that is not exactly five fields, or has an unparseable date
    field, never matches.
    """
    parts = cron.split()
    if len(parts) != 5:
        return False
    _minute_f, _hour_f, dom_f, month_f, dow_f = parts

    # Use noon IST as a representative instant — avoids DST edge cases and ensures
    # hour/minute fields (which we're ignoring) don't accidentally affect the dom
    # check if someone were to pass this to cron_matches.
    dt_ist = datetime(target_date.year, target_date.month, target_date.day, 12, 0, tzinfo=IST)

    cron_dow = dt_ist.isoweekday() % 7
    dow_ok = _field_matches(dow_f, cron_dow, 0, 6)
    if cron_dow == 0:
        dow_ok = dow_ok or _field_matches(dow_f, 7, 0, 7)

    return (
        _field_matches(dom_f, dt_ist.day, 1, 31)
        and _field_matches(month_f, dt_ist.month, 1, 12)
        and dow_ok
    )


def due_occurrence(
    *,
    schedule_cron: str | None,
    schedule_interval_minutes: int | None,
    created_at: datetime,
    now: datetime,
    window: timedelta,
) -> datetime | None:
    """Return the scheduled occurrence (UTC) in ``(now - window, now]``, or None.

    ``schedule_cron`` takes precedence over ``schedule_interval_minutes``. A
    reminder with neither schedule is never due (it has no defined firing time).
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    window_start = now - window

    if schedule_cron:
        # Walk each minute in the window, newest first, and return the first
        # cron-matching minute. The window is a few minutes wide, so this is cheap.
        minute = now.replace(second=0, microsecond=0)
        while minute > window_start:
            if cron_matches(schedule_cron, minute.astimezone(IST)):
                return minute
            minute -= timedelta(minutes=1)
        return None

    if schedule_interval_minutes and schedule_interval_minutes > 0:
        anchor = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
        if now < anchor:
            return None
        interval = timedelta(minutes=schedule_interval_minutes)
        elapsed_intervals = int((now - anchor) / interval)
        occurrence = anchor + elapsed_intervals * interval
        if window_start < occurrence <= now:
            return occurrence
        return None

    return None
