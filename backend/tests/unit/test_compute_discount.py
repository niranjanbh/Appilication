"""Unit tests for coupon_service.compute_discount — pure function, no DB."""

from __future__ import annotations

import types
from datetime import UTC, datetime, timedelta

import pytest

from app.services.coupon_service import CouponError, compute_discount


def _coupon(**kwargs: object) -> object:
    defaults = {
        "active": True,
        "valid_from": datetime.now(UTC) - timedelta(hours=1),
        "valid_until": None,
        "max_redemptions": None,
        "redemption_count": 0,
        "min_order_paise": 0,
        "discount_type": "flat",
        "discount_value": 5000,
        "max_discount_paise": None,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def test_flat_discount_applied() -> None:
    coupon = _coupon(discount_type="flat", discount_value=5000)
    assert compute_discount(coupon, 70000) == 5000  # type: ignore[arg-type]


def test_percent_discount_applied() -> None:
    coupon = _coupon(discount_type="percent", discount_value=10)
    assert compute_discount(coupon, 70000) == 7000  # type: ignore[arg-type]


def test_percent_discount_capped_by_max() -> None:
    coupon = _coupon(discount_type="percent", discount_value=20, max_discount_paise=5000)
    # 20% of 70000 = 14000, capped at 5000
    assert compute_discount(coupon, 70000) == 5000  # type: ignore[arg-type]


def test_discount_never_exceeds_fee() -> None:
    coupon = _coupon(discount_type="flat", discount_value=100000)
    assert compute_discount(coupon, 70000) == 70000  # type: ignore[arg-type]


def test_inactive_coupon_raises() -> None:
    coupon = _coupon(active=False)
    with pytest.raises(CouponError) as exc_info:
        compute_discount(coupon, 70000)  # type: ignore[arg-type]
    assert exc_info.value.code == "coupon_inactive"


def test_expired_coupon_raises() -> None:
    coupon = _coupon(valid_until=datetime.now(UTC) - timedelta(hours=1))
    with pytest.raises(CouponError) as exc_info:
        compute_discount(coupon, 70000)  # type: ignore[arg-type]
    assert exc_info.value.code == "coupon_expired"


def test_exhausted_coupon_raises() -> None:
    coupon = _coupon(max_redemptions=5, redemption_count=5)
    with pytest.raises(CouponError) as exc_info:
        compute_discount(coupon, 70000)  # type: ignore[arg-type]
    assert exc_info.value.code == "coupon_exhausted"


def test_order_below_minimum_raises() -> None:
    coupon = _coupon(min_order_paise=80000)
    with pytest.raises(CouponError) as exc_info:
        compute_discount(coupon, 70000)  # type: ignore[arg-type]
    assert exc_info.value.code == "order_below_minimum"
