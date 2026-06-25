from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pricing import Coupon


async def get_by_code(db: AsyncSession, *, code: str) -> Coupon | None:
    result = await db.execute(select(Coupon).where(Coupon.code == code))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, *, coupon_id: uuid.UUID) -> Coupon | None:
    return await db.get(Coupon, coupon_id)


async def list_coupons(
    db: AsyncSession,
    *,
    active_only: bool = False,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[Coupon], int]:
    base = select(Coupon)
    if active_only:
        base = base.where(Coupon.active.is_(True))

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(Coupon.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_coupon(
    db: AsyncSession,
    *,
    code: str,
    description: str | None,
    discount_type: str,
    discount_value: int,
    max_discount_paise: int | None,
    min_order_paise: int,
    max_redemptions: int | None,
    valid_from: datetime,
    valid_until: datetime | None,
    admin_id: uuid.UUID,
) -> Coupon:
    coupon = Coupon(
        code=code,
        description=description,
        discount_type=discount_type,
        discount_value=discount_value,
        max_discount_paise=max_discount_paise,
        min_order_paise=min_order_paise,
        max_redemptions=max_redemptions,
        valid_from=valid_from,
        valid_until=valid_until,
        created_by_admin_id=admin_id,
    )
    db.add(coupon)
    await db.flush()
    return coupon


async def update_coupon(
    db: AsyncSession,
    *,
    coupon_id: uuid.UUID,
    **fields: object,
) -> Coupon | None:
    fields["updated_at"] = datetime.now(UTC)
    result = await db.execute(
        update(Coupon)
        .where(Coupon.id == coupon_id)
        .values(**fields)
        .returning(Coupon)
    )
    return result.scalar_one_or_none()


async def deactivate_coupon(
    db: AsyncSession, *, coupon_id: uuid.UUID
) -> Coupon | None:
    result = await db.execute(
        update(Coupon)
        .where(Coupon.id == coupon_id)
        .values(active=False, updated_at=datetime.now(UTC))
        .returning(Coupon)
    )
    return result.scalar_one_or_none()


async def activate_coupon(
    db: AsyncSession, *, coupon_id: uuid.UUID
) -> Coupon | None:
    result = await db.execute(
        update(Coupon)
        .where(Coupon.id == coupon_id)
        .values(active=True, updated_at=datetime.now(UTC))
        .returning(Coupon)
    )
    return result.scalar_one_or_none()


async def delete_coupon(db: AsyncSession, *, coupon_id: uuid.UUID) -> bool:
    """Hard-delete a coupon (ad_coupons has no soft-delete column).

    Redemptions are recorded on the order, not via an FK back to the coupon, so
    deleting a code does not orphan payment history.
    """
    from sqlalchemy import delete as sa_delete

    result = await db.execute(sa_delete(Coupon).where(Coupon.id == coupon_id))
    return bool(result.rowcount > 0)  # type: ignore[attr-defined]


async def increment_redemption(db: AsyncSession, *, coupon_id: uuid.UUID) -> None:
    await db.execute(
        update(Coupon)
        .where(Coupon.id == coupon_id)
        .values(
            redemption_count=Coupon.redemption_count + 1,
            updated_at=datetime.now(UTC),
        )
    )
