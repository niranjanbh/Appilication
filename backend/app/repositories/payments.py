from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import PaymentStatus
from app.models.payment import Payment


async def create_payment(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    razorpay_order_id: str,
    amount_paise: int,
    currency: str = "INR",
    consultation_id: uuid.UUID | None = None,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        razorpay_order_id=razorpay_order_id,
        amount_paise=amount_paise,
        currency=currency,
        consultation_id=consultation_id,
        status=PaymentStatus.CREATED,
    )
    db.add(payment)
    await db.flush()
    return payment


async def get_payment_for_user(
    db: AsyncSession,
    *,
    payment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Payment | None:
    """Resource-scoped fetch — returns None for payments owned by other users."""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id, Payment.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_by_order_id(
    db: AsyncSession,
    *,
    razorpay_order_id: str,
) -> Payment | None:
    result = await db.execute(
        select(Payment).where(Payment.razorpay_order_id == razorpay_order_id)
    )
    return result.scalar_one_or_none()


async def get_by_razorpay_payment_id(
    db: AsyncSession,
    *,
    razorpay_payment_id: str,
) -> Payment | None:
    result = await db.execute(
        select(Payment).where(Payment.razorpay_payment_id == razorpay_payment_id)
    )
    return result.scalar_one_or_none()


async def update_payment(
    db: AsyncSession,
    *,
    payment_id: uuid.UUID,
    **kwargs: Any,
) -> Payment | None:
    result = await db.execute(
        update(Payment)
        .where(Payment.id == payment_id)
        .values(**kwargs, updated_at=datetime.now(UTC))
        .returning(Payment)
    )
    return result.scalar_one_or_none()


async def list_stale_payments(
    db: AsyncSession,
    *,
    statuses: list[PaymentStatus],
    older_than_minutes: int = 30,
) -> list[Payment]:
    """Return payments in the given statuses that haven't been updated recently."""
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
    result = await db.execute(
        select(Payment)
        .where(Payment.status.in_(statuses), Payment.updated_at < cutoff)
        .order_by(Payment.updated_at.asc())
        .limit(100)
    )
    return list(result.scalars().all())
