from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Patient


async def get_patient_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> Patient | None:
    """Return the Patient profile row for a given user. Returns None if not found."""
    result = await db.execute(
        select(Patient).where(Patient.user_id == user_id, Patient.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def update_abha_number(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    abha_number: str,
) -> Patient:
    """Persist an ABHA number to the patient record. Flushes but does not commit."""
    await db.execute(
        update(Patient).where(Patient.id == patient_id).values(abha_number=abha_number)
    )
    await db.flush()
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one()
    return patient
