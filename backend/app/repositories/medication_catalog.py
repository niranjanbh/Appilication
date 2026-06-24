"""Repository for the admin-curated medication catalog (kc_medication_catalog)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DrugForm
from app.models.clinic import MedicationCatalog


async def create(
    db: AsyncSession,
    *,
    name: str,
    generic_name: str | None,
    form: DrugForm | None,
    strength: str | None,
    created_by_user_id: uuid.UUID | None,
) -> MedicationCatalog:
    entry = MedicationCatalog(
        name=name,
        generic_name=generic_name,
        form=form,
        strength=strength,
        created_by_user_id=created_by_user_id,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get(db: AsyncSession, *, catalog_id: uuid.UUID) -> MedicationCatalog | None:
    result = await db.execute(
        select(MedicationCatalog).where(
            MedicationCatalog.id == catalog_id,
            MedicationCatalog.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_by_name(db: AsyncSession, *, name: str) -> MedicationCatalog | None:
    result = await db.execute(
        select(MedicationCatalog).where(
            func.lower(MedicationCatalog.name) == name.lower(),
            MedicationCatalog.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def search(
    db: AsyncSession,
    *,
    query: str | None,
    limit: int = 20,
    active_only: bool = True,
) -> list[MedicationCatalog]:
    stmt = select(MedicationCatalog).where(MedicationCatalog.deleted_at.is_(None))
    if active_only:
        stmt = stmt.where(MedicationCatalog.active.is_(True))
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(MedicationCatalog.name.ilike(like))
    stmt = stmt.order_by(MedicationCatalog.name.asc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_paginated(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    include_inactive: bool = True,
) -> tuple[list[MedicationCatalog], int]:
    base = select(MedicationCatalog).where(MedicationCatalog.deleted_at.is_(None))
    if not include_inactive:
        base = base.where(MedicationCatalog.active.is_(True))

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(MedicationCatalog.name.asc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def update_fields(
    db: AsyncSession,
    *,
    catalog_id: uuid.UUID,
    **kwargs: Any,
) -> MedicationCatalog | None:
    entry = await get(db, catalog_id=catalog_id)
    if entry is None:
        return None
    for key, value in kwargs.items():
        setattr(entry, key, value)
    entry.updated_at = datetime.now(UTC)
    await db.flush()
    return entry


async def set_image(
    db: AsyncSession,
    *,
    catalog_id: uuid.UUID,
    image_s3_key: str,
    image_content_type: str,
) -> MedicationCatalog | None:
    return await update_fields(
        db,
        catalog_id=catalog_id,
        image_s3_key=image_s3_key,
        image_content_type=image_content_type,
    )


async def soft_delete(db: AsyncSession, *, catalog_id: uuid.UUID) -> bool:
    result = await db.execute(
        update(MedicationCatalog)
        .where(
            MedicationCatalog.id == catalog_id,
            MedicationCatalog.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(UTC), active=False, updated_at=datetime.now(UTC))
    )
    return bool(result.rowcount > 0)  # type: ignore[attr-defined]
