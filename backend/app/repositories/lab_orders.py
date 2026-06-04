"""Lab order repository — doctor-issued lab test orders."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import LabOrder


async def get_by_id(
    db: AsyncSession,
    *,
    lab_order_id: uuid.UUID,
) -> LabOrder | None:
    result = await db.execute(select(LabOrder).where(LabOrder.id == lab_order_id))
    return result.scalar_one_or_none()


async def list_for_patient(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
) -> list[LabOrder]:
    result = await db.execute(
        select(LabOrder)
        .where(LabOrder.patient_id == patient_id)
        .order_by(LabOrder.created_at.desc())
    )
    return list(result.scalars().all())


async def list_for_doctor(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
) -> list[LabOrder]:
    result = await db.execute(
        select(LabOrder)
        .where(LabOrder.doctor_id == doctor_id)
        .order_by(LabOrder.created_at.desc())
    )
    return list(result.scalars().all())
