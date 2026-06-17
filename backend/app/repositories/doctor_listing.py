"""Patient-facing doctor discovery repository.

Lists active, verified doctors filtered by condition category.
No PHI exposed — only public doctor profile fields.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DoctorStatus
from app.models.doctor import Doctor
from app.models.identity import User


async def list_available_doctors(
    db: AsyncSession,
    *,
    condition_category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Doctor, User]], int]:
    base = (
        select(Doctor, User)
        .join(User, User.id == Doctor.user_id)
        .where(
            Doctor.deleted_at.is_(None),
            User.deleted_at.is_(None),
            Doctor.status == DoctorStatus.ACTIVE,
            Doctor.verified_at.isnot(None),
        )
    )

    if condition_category:
        base = base.where(
            Doctor.conditions_treated.contains([condition_category])
        )

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(Doctor.created_at.desc()).offset(offset).limit(page_size)
    )
    pairs = [(row.Doctor, row.User) for row in rows]
    return pairs, total


async def get_available_doctor(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
) -> tuple[Doctor, User] | None:
    result = await db.execute(
        select(Doctor, User)
        .join(User, User.id == Doctor.user_id)
        .where(
            Doctor.id == doctor_id,
            Doctor.deleted_at.is_(None),
            User.deleted_at.is_(None),
            Doctor.status == DoctorStatus.ACTIVE,
            Doctor.verified_at.isnot(None),
        )
    )
    row = result.first()
    if row is None:
        return None
    return row.Doctor, row.User
