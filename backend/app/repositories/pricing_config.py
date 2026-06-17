from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ConsultationType
from app.models.pricing import PricingConfig


async def get_fee(
    db: AsyncSession,
    *,
    condition_category: str,
    consultation_type: ConsultationType,
) -> int | None:
    result = await db.execute(
        select(PricingConfig.fee_paise).where(
            PricingConfig.condition_category == condition_category,
            PricingConfig.consultation_type == consultation_type,
        )
    )
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[PricingConfig]:
    result = await db.execute(
        select(PricingConfig).order_by(
            PricingConfig.condition_category, PricingConfig.consultation_type
        )
    )
    return list(result.scalars().all())


async def upsert(
    db: AsyncSession,
    *,
    condition_category: str,
    consultation_type: ConsultationType,
    fee_paise: int,
    admin_id: uuid.UUID,
) -> PricingConfig:
    stmt = (
        insert(PricingConfig)
        .values(
            condition_category=condition_category,
            consultation_type=consultation_type,
            fee_paise=fee_paise,
            created_by_admin_id=admin_id,
        )
        .on_conflict_do_update(
            index_elements=["condition_category", "consultation_type"],
            set_={
                "fee_paise": fee_paise,
                "created_by_admin_id": admin_id,
                "updated_at": datetime.now(UTC),
            },
        )
        .returning(PricingConfig)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.scalar_one()
