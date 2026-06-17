"""Integration tests for coupon management and coupon-at-booking (P38)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_admin_user,
    create_super_admin_user,
    make_auth_headers,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _valid_coupon_body(
    *,
    code: str | None = None,
    discount_type: str = "flat",
    discount_value: int = 5000,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> dict:
    return {
        "code": code or f"TEST{uuid.uuid4().hex[:6].upper()}",
        "discount_type": discount_type,
        "discount_value": discount_value,
        "min_order_paise": 0,
        "valid_from": (valid_from or datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        "valid_until": valid_until.isoformat() if valid_until else None,
    }


# ── Tests ──────────────────────────────────────────────────────────────────────


async def test_create_coupon_returns_201(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    body = _valid_coupon_body()
    response = await client.post(
        "/v1/admin/coupons",
        json=body,
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == body["code"]
    assert data["active"] is True
    assert data["redemption_count"] == 0


async def test_list_coupons_returns_created(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    headers = make_auth_headers(super_admin)

    body = _valid_coupon_body()
    await client.post("/v1/admin/coupons", json=body, headers=headers)

    r = await client.get("/v1/admin/coupons", headers=headers)
    assert r.status_code == 200
    codes = [c["code"] for c in r.json()["items"]]
    assert body["code"] in codes


async def test_update_coupon(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    headers = make_auth_headers(super_admin)

    body = _valid_coupon_body()
    create_r = await client.post("/v1/admin/coupons", json=body, headers=headers)
    coupon_id = create_r.json()["id"]

    r = await client.patch(
        f"/v1/admin/coupons/{coupon_id}",
        json={"discount_value": 8000},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["discount_value"] == 8000


async def test_deactivate_coupon(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    headers = make_auth_headers(super_admin)

    body = _valid_coupon_body()
    create_r = await client.post("/v1/admin/coupons", json=body, headers=headers)
    coupon_id = create_r.json()["id"]

    r = await client.delete(f"/v1/admin/coupons/{coupon_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["active"] is False


async def test_deactivate_nonexistent_coupon_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    r = await client.delete(
        f"/v1/admin/coupons/{uuid.uuid4()}",
        headers=make_auth_headers(super_admin),
    )
    assert r.status_code == 404


async def test_create_coupon_requires_pricing_manage(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Read-only admin cannot create coupons."""
    admin = await create_admin_user(db_session)
    r = await client.post(
        "/v1/admin/coupons",
        json=_valid_coupon_body(),
        headers=make_auth_headers(admin),
    )
    assert r.status_code == 403


async def test_create_coupon_invalid_discount_type_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    body = _valid_coupon_body()
    body["discount_type"] = "magic"
    r = await client.post(
        "/v1/admin/coupons", json=body, headers=make_auth_headers(super_admin)
    )
    assert r.status_code == 422


async def test_create_coupon_zero_discount_value_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    body = _valid_coupon_body(discount_value=0)
    r = await client.post(
        "/v1/admin/coupons", json=body, headers=make_auth_headers(super_admin)
    )
    assert r.status_code == 422
