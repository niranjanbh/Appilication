from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import PlatformSetting


async def get(db: AsyncSession, key: str) -> Any | None:
    """Return the JSONB value for a key, or None if the key is absent."""
    result = await db.execute(
        select(PlatformSetting.value).where(PlatformSetting.key == key)
    )
    return result.scalar_one_or_none()


async def get_all(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(PlatformSetting.key, PlatformSetting.value))
    return {row.key: row.value for row in result.all()}


async def upsert(
    db: AsyncSession,
    *,
    key: str,
    value: Any,
    updated_by: uuid.UUID | None,
) -> None:
    stmt = insert(PlatformSetting).values(
        key=key, value=value, updated_by=updated_by
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[PlatformSetting.key],
        set_={"value": value, "updated_by": updated_by},
    )
    await db.execute(stmt)
