from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UserRole
from app.models.admin import StaffRole


async def list_roles_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[UserRole]:
    """Additional staff roles held by a user beyond their primary users.role."""
    result = await db.execute(
        select(StaffRole.role).where(StaffRole.user_id == user_id)
    )
    return list(result.scalars().all())


async def grant_role(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    role: UserRole,
    granted_by: uuid.UUID | None,
) -> StaffRole:
    entry = StaffRole(user_id=user_id, role=role, granted_by=granted_by)
    db.add(entry)
    await db.flush()
    return entry
