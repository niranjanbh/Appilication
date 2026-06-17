"""ICD-10 diagnosis capture — doctor-scoped repository.

Every function takes `doctor_id` (the dr_doctors.id UUID) as a mandatory scope
parameter. `kc_icd10_codes` is a curated reference catalog used for search/
autocomplete only — `kc_diagnoses.icd10_code`/`icd10_description` are
denormalized onto the row and are not validated against the catalog.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Diagnosis, Icd10Code


async def search_icd10_codes(
    db: AsyncSession,
    *,
    query: str,
    limit: int = 20,
) -> list[Icd10Code]:
    """Search the curated ICD-10 catalog by code or description (case-insensitive)."""
    pattern = f"%{query}%"
    result = await db.execute(
        select(Icd10Code)
        .where(or_(Icd10Code.code.ilike(pattern), Icd10Code.description.ilike(pattern)))
        .order_by(Icd10Code.code)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_diagnoses_for_consultation(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    consultation_id: uuid.UUID,
) -> list[Diagnosis]:
    """Return diagnoses for a doctor's consultation, primary first."""
    result = await db.execute(
        select(Diagnosis)
        .where(
            Diagnosis.consultation_id == consultation_id,
            Diagnosis.doctor_id == doctor_id,
        )
        .order_by(Diagnosis.is_primary.desc(), Diagnosis.created_at.asc())
    )
    return list(result.scalars().all())


async def add_diagnosis(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    consultation_id: uuid.UUID,
    patient_id: uuid.UUID,
    icd10_code: str,
    icd10_description: str,
    is_primary: bool,
) -> Diagnosis:
    """Insert a new diagnosis row. Caller has already verified consult ownership."""
    diagnosis = Diagnosis(
        consultation_id=consultation_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        icd10_code=icd10_code,
        icd10_description=icd10_description,
        is_primary=is_primary,
    )
    db.add(diagnosis)
    await db.flush()
    return diagnosis


async def delete_diagnosis(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID,
    consultation_id: uuid.UUID,
    diagnosis_id: uuid.UUID,
) -> bool:
    """Delete a diagnosis. Returns whether a row was deleted (False = not found/not owned)."""
    result = await db.execute(
        delete(Diagnosis).where(
            Diagnosis.id == diagnosis_id,
            Diagnosis.consultation_id == consultation_id,
            Diagnosis.doctor_id == doctor_id,
        )
    )
    return bool(result.rowcount > 0)  # type: ignore[attr-defined]
