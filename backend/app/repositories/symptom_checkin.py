from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wellness import SymptomCheckIn

IST = ZoneInfo("Asia/Kolkata")


async def get_today_checkin(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> SymptomCheckIn | None:
    today_ist: date = datetime.now(IST).date()
    start = datetime(today_ist.year, today_ist.month, today_ist.day, tzinfo=IST)
    end = datetime(today_ist.year, today_ist.month, today_ist.day, 23, 59, 59, 999999, tzinfo=IST)
    result = await db.execute(
        select(SymptomCheckIn)
        .where(
            SymptomCheckIn.user_id == user_id,
            SymptomCheckIn.checked_in_at >= start,
            SymptomCheckIn.checked_in_at <= end,
        )
        .order_by(SymptomCheckIn.checked_in_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_checkin(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    mood: int,
    energy: int,
    note: str | None,
) -> SymptomCheckIn:
    now = datetime.now(UTC)
    entry = SymptomCheckIn(
        user_id=user_id,
        mood=mood,
        energy=energy,
        note=note,
        checked_in_at=now,
    )
    db.add(entry)
    await db.flush()
    return entry
