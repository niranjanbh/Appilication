"""Server-authoritative consultation pricing.

The fee is NEVER accepted from the client — it is resolved here from the DB-backed
pricing config table (ad_pricing_config), with a fallback to settings for any
combination not yet configured. Admin manages per-vertical pricing via PRICING_MANAGE.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.enums import ConsultationType


async def get_consultation_fee_paise(
    db: AsyncSession,
    *,
    condition_category: str,
    consultation_type: ConsultationType,
) -> int:
    """Return the authoritative consultation fee in paise.

    Looks up ad_pricing_config first; falls back to settings if no row exists
    for this (condition_category, consultation_type) pair.
    """
    from app.repositories import pricing_config as pricing_config_repo

    fee = await pricing_config_repo.get_fee(
        db,
        condition_category=condition_category,
        consultation_type=consultation_type,
    )
    if fee is not None:
        return fee
    if consultation_type == ConsultationType.FOLLOW_UP:
        return settings.consultation_fee_followup_paise
    return settings.consultation_fee_initial_paise
