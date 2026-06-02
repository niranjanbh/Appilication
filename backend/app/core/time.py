from __future__ import annotations

from datetime import datetime, timezone

IST = timezone.utc  # stored UTC, displayed IST at the presentation layer


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def utc_from_timestamp(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)
