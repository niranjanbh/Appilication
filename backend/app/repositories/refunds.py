from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import RefundStatus
from app.models.payment import Refund


async def create_refund(
    db: AsyncSession,
    *,
    payment_id: uuid.UUID,
    user_id: uuid.UUID,
    amount_paise: int,
    currency: str = "INR",
    status: RefundStatus = RefundStatus.PENDING,
    razorpay_refund_id: str | None = None,
    reason: str | None = None,
) -> Refund:
    refund = Refund(
        payment_id=payment_id,
        user_id=user_id,
        amount_paise=amount_paise,
        currency=currency,
        status=status,
        razorpay_refund_id=razorpay_refund_id,
        reason=reason,
    )
    db.add(refund)
    await db.flush()
    return refund


async def get_refund_for_user(
    db: AsyncSession,
    *,
    refund_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Refund | None:
    """Resource-scoped fetch — returns None for refunds owned by other users."""
    result = await db.execute(
        select(Refund).where(Refund.id == refund_id, Refund.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_refunds_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Refund], int]:
    """Return paginated refunds for a user (newest first) with total count."""
    base = select(Refund).where(Refund.user_id == user_id)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    items_result = await db.execute(
        base.order_by(Refund.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(items_result.scalars().all()), total
