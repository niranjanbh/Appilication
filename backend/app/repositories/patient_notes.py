from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import PatientNote


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


async def list_notes_for_patient(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PatientNote], int]:
    stmt = (
        select(PatientNote)
        .where(
            PatientNote.patient_user_id == patient_user_id,
            PatientNote.deleted_at.is_(None),
        )
        .order_by(PatientNote.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    notes = list(result.scalars().all())

    count_stmt = (
        select(PatientNote)
        .where(
            PatientNote.patient_user_id == patient_user_id,
            PatientNote.deleted_at.is_(None),
        )
    )
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())
    return notes, total


async def get_note_for_patient(
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


async def update_note(
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    patient_user_id: uuid.UUID,
    body: str,
) -> PatientNote | None:
    note = await get_note_for_patient(db, note_id=note_id, patient_user_id=patient_user_id)
    if note is None:
        return None
    note.body = body
    note.updated_at = datetime.now(UTC)
    await db.flush()
    return note


async def soft_delete_note(
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> bool:
    note = await get_note_for_patient(db, note_id=note_id, patient_user_id=patient_user_id)
    if note is None:
        return False
    note.deleted_at = datetime.now(UTC)
    note.updated_at = datetime.now(UTC)
    await db.flush()
    return True


async def list_notes_for_doctor(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    doctor_id: uuid.UUID,
    limit: int = 50,
) -> list[PatientNote] | None:
    """Return notes only if this doctor has at least one consultation with the patient."""
    from app.models.clinic import Consultation
    from app.models.clinic import Patient as PatientModel

    # Resolve patient record from user ID
    patient_result = await db.execute(
        select(PatientModel).where(PatientModel.user_id == patient_user_id)
    )
    patient = patient_result.scalar_one_or_none()
    if patient is None:
        return None

    # Verify doctor-patient relationship via any consultation
    consult_result = await db.execute(
        select(Consultation).where(
            Consultation.patient_id == patient.id,
            Consultation.doctor_id == doctor_id,
            Consultation.deleted_at.is_(None),
        ).limit(1)
    )
    if consult_result.scalar_one_or_none() is None:
        return None

    stmt = (
        select(PatientNote)
        .where(
            PatientNote.patient_user_id == patient_user_id,
            PatientNote.deleted_at.is_(None),
        )
        .order_by(PatientNote.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
