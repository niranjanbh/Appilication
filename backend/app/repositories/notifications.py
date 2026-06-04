"""Repository for wn_notifications — patient notification inbox.

All list/get functions are scoped to user_id — cross-user access returns None.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification


async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    template_name: str,
    title: str,
    body: str,
    channels: list[str],
    data: dict[str, Any] | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        template_name=template_name,
        title=title,
        body=body,
        channels=channels,
        data=data or {},
    )
    db.add(notif)
    await db.flush()
    return notif


async def list_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
) -> tuple[list[Notification], int]:
    """Return (items, total_count) for a user's inbox, newest-first."""
    base = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        base = base.where(Notification.read_at.is_(None))

    total_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = total_result.scalar_one()

    rows_result = await db.execute(
        base.order_by(Notification.sent_at.desc()).limit(limit).offset(offset)
    )
    items = list(rows_result.scalars().all())
    return items, total


async def get_for_user(
    db: AsyncSession,
    *,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def mark_read(
    db: AsyncSession,
    *,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    notif = await get_for_user(db, notification_id=notification_id, user_id=user_id)
    if notif is None:
        return None
    if notif.read_at is None:
        notif.read_at = datetime.now(tz=UTC)
        await db.flush()
    return notif


async def mark_all_read(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    now = datetime.now(tz=UTC)
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=now)
        .returning(Notification.id)
    )
    rows = result.fetchall()
    return len(rows)


async def count_unread(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(func.count()).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    )
    return result.scalar_one()
