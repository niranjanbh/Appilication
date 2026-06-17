from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Diagnosis
from app.repositories import diagnoses as diagnoses_repo


class DiagnosisError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


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
    """Record a diagnosis, rejecting a duplicate ICD-10 code on the same consultation."""
    existing = await diagnoses_repo.list_diagnoses_for_consultation(
        db, doctor_id=doctor_id, consultation_id=consultation_id
    )
    if any(d.icd10_code == icd10_code for d in existing):
        raise DiagnosisError("diagnosis_already_recorded")

    return await diagnoses_repo.add_diagnosis(
        db,
        doctor_id=doctor_id,
        consultation_id=consultation_id,
        patient_id=patient_id,
        icd10_code=icd10_code,
        icd10_description=icd10_description,
        is_primary=is_primary,
    )
