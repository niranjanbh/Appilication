from __future__ import annotations

from datetime import UTC, datetime

IST = UTC  # stored UTC, displayed IST at the presentation layer


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


def utc_from_timestamp(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)
