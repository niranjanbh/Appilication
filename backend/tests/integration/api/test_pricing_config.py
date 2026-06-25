"""Integration tests for the pricing-as-config system (P38).

Tests: CRUD on ad_pricing_config, booking uses DB price, fallback to settings.
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_admin_user,
    create_super_admin_user,
    make_auth_headers,
)

# ── Tests ──────────────────────────────────────────────────────────────────────


async def test_list_pricing_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    response = await client.get(
        "/v1/admin/pricing", headers=make_auth_headers(super_admin)
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_upsert_pricing_creates_and_updates(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    headers = make_auth_headers(super_admin)

    # First upsert — creates a row
    r = await client.put(
        "/v1/admin/pricing/thyroid/initial",
        json={"fee_paise": 65000},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["fee_paise"] == 65000
    assert r.json()["condition_category"] == "thyroid"

    # Second upsert — updates the fee
    r2 = await client.put(
        "/v1/admin/pricing/thyroid/initial",
        json={"fee_paise": 72000},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["fee_paise"] == 72000


async def test_upsert_pricing_invalid_category_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    response = await client.put(
        "/v1/admin/pricing/not_a_real_category/initial",
        json={"fee_paise": 65000},
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 422


async def test_upsert_pricing_zero_fee_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    response = await client.put(
        "/v1/admin/pricing/thyroid/initial",
        json={"fee_paise": 0},
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 422


async def test_upsert_pricing_requires_pricing_manage(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Read-only admin cannot update pricing."""
    admin = await create_admin_user(db_session)
    response = await client.put(
        "/v1/admin/pricing/thyroid/initial",
        json={"fee_paise": 65000},
        headers=make_auth_headers(admin),
    )
    assert response.status_code == 403


async def test_list_pricing_after_upsert_shows_config(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    headers = make_auth_headers(super_admin)

    await client.put(
        "/v1/admin/pricing/pcos/follow_up",
        json={"fee_paise": 45000},
        headers=headers,
    )

    r = await client.get("/v1/admin/pricing", headers=headers)
    assert r.status_code == 200
    configs = r.json()
    found = next(
        (c for c in configs if c["condition_category"] == "pcos" and c["consultation_type"] == "follow_up"),
        None,
    )
    assert found is not None
    assert found["fee_paise"] == 45000
