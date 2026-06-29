"""Unit tests for reminder schedule evaluation (pure — no DB).

Covers cron matching (IST), interval anchoring, the half-open dispatch window,
and tolerance of malformed cron. These back the schedule-aware get_due_reminders.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.schedule import cron_matches, due_occurrence

IST = ZoneInfo("Asia/Kolkata")
WINDOW = timedelta(minutes=5)


def _ist(y: int, mo: int, d: int, h: int, mi: int) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=IST)


# ── cron_matches ──────────────────────────────────────────────────────────────


def test_cron_daily_time_matches_in_ist() -> None:
    assert cron_matches("0 8 * * *", _ist(2026, 6, 27, 8, 0)) is True
    assert cron_matches("0 8 * * *", _ist(2026, 6, 27, 9, 0)) is False
    assert cron_matches("0 8 * * *", _ist(2026, 6, 27, 8, 1)) is False


def test_cron_multiple_hours() -> None:
    cron = "0 8,14,20 * * *"
    assert cron_matches(cron, _ist(2026, 6, 27, 14, 0)) is True
    assert cron_matches(cron, _ist(2026, 6, 27, 20, 0)) is True
    assert cron_matches(cron, _ist(2026, 6, 27, 15, 0)) is False


def test_cron_step_minutes() -> None:
    cron = "*/15 * * * *"
    assert cron_matches(cron, _ist(2026, 6, 27, 10, 0)) is True
    assert cron_matches(cron, _ist(2026, 6, 27, 10, 15)) is True
    assert cron_matches(cron, _ist(2026, 6, 27, 10, 7)) is False


def test_cron_sunday_accepts_0_and_7() -> None:
    # 2026-06-28 is a Sunday.
    sunday = _ist(2026, 6, 28, 8, 0)
    assert cron_matches("0 8 * * 0", sunday) is True
    assert cron_matches("0 8 * * 7", sunday) is True
    # ...and a Monday should not match a Sunday-only schedule.
    monday = _ist(2026, 6, 29, 8, 0)
    assert cron_matches("0 8 * * 0", monday) is False


def test_cron_weekday_range() -> None:
    cron = "0 8 * * 1-5"  # Mon–Fri
    assert cron_matches(cron, _ist(2026, 6, 29, 8, 0)) is True   # Monday
    assert cron_matches(cron, _ist(2026, 6, 27, 8, 0)) is False  # Saturday


def test_cron_malformed_never_matches() -> None:
    assert cron_matches("not a cron", _ist(2026, 6, 27, 8, 0)) is False
    assert cron_matches("0 8 * *", _ist(2026, 6, 27, 8, 0)) is False  # 4 fields
    assert cron_matches("0 25 * * *", _ist(2026, 6, 27, 8, 0)) is False


# ── due_occurrence: cron ──────────────────────────────────────────────────────


def test_due_cron_returns_occurrence_in_window() -> None:
    # 08:00 IST cron, evaluated at 08:02 IST -> due, occurrence is 08:00 IST in UTC.
    now = _ist(2026, 6, 27, 8, 2).astimezone(UTC)
    occ = due_occurrence(
        schedule_cron="0 8 * * *",
        schedule_interval_minutes=None,
        created_at=_ist(2026, 1, 1, 0, 0).astimezone(UTC),
        now=now,
        window=WINDOW,
    )
    assert occ == _ist(2026, 6, 27, 8, 0).astimezone(UTC)


def test_due_cron_not_due_outside_window() -> None:
    now = _ist(2026, 6, 27, 9, 0).astimezone(UTC)
    occ = due_occurrence(
        schedule_cron="0 8 * * *",
        schedule_interval_minutes=None,
        created_at=_ist(2026, 1, 1, 0, 0).astimezone(UTC),
        now=now,
        window=WINDOW,
    )
    assert occ is None


def test_due_cron_catches_offbeat_minute_within_window() -> None:
    # An 08:07 IST dose is caught by the beat run a few minutes later (08:10 IST).
    now = _ist(2026, 6, 27, 8, 10).astimezone(UTC)
    occ = due_occurrence(
        schedule_cron="7 8 * * *",
        schedule_interval_minutes=None,
        created_at=_ist(2026, 1, 1, 0, 0).astimezone(UTC),
        now=now,
        window=WINDOW,
    )
    assert occ == _ist(2026, 6, 27, 8, 7).astimezone(UTC)


# ── due_occurrence: interval ──────────────────────────────────────────────────


def test_due_interval_returns_recent_occurrence() -> None:
    anchor = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    now = anchor + timedelta(hours=3, minutes=2)  # 2 min past the 3rd hourly tick
    occ = due_occurrence(
        schedule_cron=None,
        schedule_interval_minutes=60,
        created_at=anchor,
        now=now,
        window=WINDOW,
    )
    assert occ == anchor + timedelta(hours=3)


def test_due_interval_not_due_between_ticks() -> None:
    anchor = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    now = anchor + timedelta(hours=3, minutes=30)  # well past the tick, outside window
    occ = due_occurrence(
        schedule_cron=None,
        schedule_interval_minutes=60,
        created_at=anchor,
        now=now,
        window=WINDOW,
    )
    assert occ is None


def test_due_interval_before_anchor() -> None:
    anchor = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)
    now = anchor - timedelta(minutes=1)
    occ = due_occurrence(
        schedule_cron=None,
        schedule_interval_minutes=60,
        created_at=anchor,
        now=now,
        window=WINDOW,
    )
    assert occ is None


# ── due_occurrence: precedence / empty ────────────────────────────────────────


def test_cron_takes_precedence_over_interval() -> None:
    # At 08:30 IST the cron's 08:00 occurrence is outside the 5-min window. An
    # every-minute interval would be due, but cron takes precedence -> None.
    now = _ist(2026, 6, 27, 8, 30).astimezone(UTC)
    occ = due_occurrence(
        schedule_cron="0 8 * * *",
        schedule_interval_minutes=1,
        created_at=_ist(2026, 6, 27, 0, 0).astimezone(UTC),
        now=now,
        window=WINDOW,
    )
    assert occ is None


def test_no_schedule_is_never_due() -> None:
    now = datetime(2026, 6, 27, 8, 0, tzinfo=UTC)
    occ = due_occurrence(
        schedule_cron=None,
        schedule_interval_minutes=None,
        created_at=now - timedelta(days=1),
        now=now,
        window=WINDOW,
    )
    assert occ is None
