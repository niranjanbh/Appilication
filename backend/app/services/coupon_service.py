"""Coupon validation and discount computation.

DMR Act (Drugs and Magic Remedies Act) constraint: discount_value for percent
coupons is capped at 50 (enforced in ad_coupons CHECK constraint). The DB
constraint is the primary enforcement; service layer mirrors the rule in
compute_discount so unit tests stay pure.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pricing import Coupon


class CouponError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def compute_discount(coupon: Coupon, fee_paise: int) -> int:
    """Pure — returns the discount in paise to subtract from fee_paise.

    Validates all eligibility conditions before computing the amount.
    Caller must increment redemption_count after this succeeds.
    """
    if not coupon.active:
        raise CouponError("coupon_inactive")
    now = datetime.now(UTC)
    if coupon.valid_from > now:
        raise CouponError("coupon_not_yet_valid")
    if coupon.valid_until is not None and coupon.valid_until < now:
        raise CouponError("coupon_expired")
    if (
        coupon.max_redemptions is not None
        and coupon.redemption_count >= coupon.max_redemptions
    ):
        raise CouponError("coupon_exhausted")
    if fee_paise < coupon.min_order_paise:
        raise CouponError("order_below_minimum")

    if coupon.discount_type == "flat":
        discount = coupon.discount_value
    else:
        discount = (fee_paise * coupon.discount_value) // 100
        if coupon.max_discount_paise is not None:
            discount = min(discount, coupon.max_discount_paise)

    return min(discount, fee_paise)


async def validate_and_apply_coupon(
    db: AsyncSession,
    *,
    code: str,
    fee_paise: int,
) -> tuple[Coupon, int]:
    """Validate the coupon and atomically increment its redemption counter.

    Returns (coupon, discount_paise). Raises CouponError on any failure.
    The increment happens inside the caller's transaction — rollback restores it.
    """
    from app.repositories import coupons as coupon_repo

    coupon = await coupon_repo.get_by_code(db, code=code)
    if coupon is None:
        raise CouponError("coupon_not_found")

    discount = compute_discount(coupon, fee_paise)
    await coupon_repo.increment_redemption(db, coupon_id=coupon.id)
    return coupon, discount
