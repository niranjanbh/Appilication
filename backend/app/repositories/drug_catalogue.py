"""Drug catalogue repository — lookup and autocomplete search."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import DrugCatalogue


async def lookup_drug(db: AsyncSession, *, name: str) -> DrugCatalogue | None:
    """Case-insensitive exact lookup by INN name."""
    result = await db.execute(
        select(DrugCatalogue).where(
            func.lower(DrugCatalogue.drug_generic_name) == name.lower().strip()
        )
    )
    return result.scalar_one_or_none()


async def search_drugs(
    db: AsyncSession, *, query: str, limit: int = 20
) -> list[DrugCatalogue]:
    """ILIKE autocomplete search. Excludes prohibited drugs and Schedule X/H1
    (no point surfacing drugs the doctor cannot prescribe)."""
    result = await db.execute(
        select(DrugCatalogue)
        .where(
            DrugCatalogue.drug_generic_name.ilike(f"%{query}%"),
            DrugCatalogue.is_prohibited.is_(False),
            DrugCatalogue.drug_schedule.notin_(["X", "H1"]),
        )
        .order_by(DrugCatalogue.drug_generic_name)
        .limit(limit)
    )
    return list(result.scalars().all())
