"""Patient notes repository.

All queries filter deleted_at IS NULL at the SQL layer (soft-delete).
Patient-scoped queries filter by patient_user_id — cross-user access returns None.
Doctor-scoped queries are read-only; they receive the patient_user_id resolved
from the Patient record after panel-membership is verified by the caller.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import PatientNote


async def list_for_patient(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PatientNote], int]:
    base = (
        select(PatientNote)
        .where(
            PatientNote.patient_user_id == patient_user_id,
            PatientNote.deleted_at.is_(None),
        )
    )
    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = total_result.scalar_one()

    rows = await db.execute(
        base.order_by(PatientNote.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.scalars().all()), total


async def get_for_patient(
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> PatientNote | None:
    result = await db.execute(
        select(PatientNote).where(
            PatientNote.id == note_id,
            PatientNote.patient_user_id == patient_user_id,
            PatientNote.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_note(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    body: str,
) -> PatientNote:
    note = PatientNote(patient_user_id=patient_user_id, body=body)
    db.add(note)
    await db.flush()
    return note


async def update_for_patient(
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    patient_user_id: uuid.UUID,
    body: str,
) -> PatientNote | None:
    """Update a note owned by this patient. Returns None if not found/not own."""
    note = await get_for_patient(db, note_id=note_id, patient_user_id=patient_user_id)
    if note is None:
        return None
    note.body = body
    note.updated_at = datetime.now(UTC)
    await db.flush()
    return note


async def soft_delete_for_patient(
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> bool:
    """Soft-delete a note owned by this patient. Returns False if not found/not own."""
    note = await get_for_patient(db, note_id=note_id, patient_user_id=patient_user_id)
    if note is None:
        return False
    note.deleted_at = datetime.now(UTC)
    await db.flush()
    return True


async def list_for_doctor(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PatientNote], int]:
    """Read-only view of a patient's notes for a doctor.

    Caller is responsible for verifying panel membership before invoking.
    """
    base = (
        select(PatientNote)
        .where(
            PatientNote.patient_user_id == patient_user_id,
            PatientNote.deleted_at.is_(None),
        )
    )
    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = total_result.scalar_one()

    rows = await db.execute(
        base.order_by(PatientNote.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.scalars().all()), total
