"""Prescription repository.

All patient-scoped queries filter status NOT IN ('draft') at the SQL layer — draft
prescriptions are NEVER visible to patients regardless of any application-layer check.

Doctor-scoped queries are scoped by doctor_id (the dr_doctors.id, not users.id).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import PrescriptionStatus
from app.models.clinic import (
    Patient,
    Prescription,
    PrescriptionItem,
)

# ── Patient visibility set ─────────────────────────────────────────────────────

_PATIENT_VISIBLE = (PrescriptionStatus.SIGNED, PrescriptionStatus.DISPENSED)


# ── Write helpers ──────────────────────────────────────────────────────────────


async def create_draft(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
    diagnosis_note: str | None,
    general_instructions: str | None,
    items: list[dict[str, Any]],
) -> Prescription:
    """Create a new draft prescription with its items."""
    rx = Prescription(
        consultation_id=consultation_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        status=PrescriptionStatus.DRAFT,
        diagnosis_note=diagnosis_note,
        general_instructions=general_instructions,
        version=1,
    )
    db.add(rx)
    await db.flush()  # get rx.id

    for idx, item in enumerate(items):
        from app.db.enums import DrugForm

        db.add(
            PrescriptionItem(
                prescription_id=rx.id,
                drug_generic_name=item["drug_generic_name"],
                drug_form=DrugForm(item["drug_form"]),
                dosage=item["dosage"],
                frequency=item["frequency"],
                duration_days=item.get("duration_days"),
                instructions=item.get("instructions"),
                refill_allowed=bool(item.get("refill_allowed", False)),
                order_index=idx,
            )
        )

    await db.flush()
    return rx


async def get_for_doctor(
    db: AsyncSession,
    *,
    prescription_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> Prescription | None:
    result = await db.execute(
        select(Prescription).where(
            Prescription.id == prescription_id,
            Prescription.doctor_id == doctor_id,
        )
    )
    return result.scalar_one_or_none()


async def list_for_consultation_for_doctor(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> list[Prescription]:
    """All prescriptions this doctor wrote for one consultation, drafts included,
    newest first. Scoped by doctor_id — another doctor's consultation yields []."""
    result = await db.execute(
        select(Prescription)
        .where(
            Prescription.consultation_id == consultation_id,
            Prescription.doctor_id == doctor_id,
        )
        .order_by(Prescription.created_at.desc())
    )
    return list(result.scalars().all())


async def get_for_patient(
    db: AsyncSession,
    *,
    prescription_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> Prescription | None:
    """Patient-scoped fetch — draft prescriptions return None regardless of ownership."""
    result = await db.execute(
        select(Prescription)
        .join(Patient, Patient.id == Prescription.patient_id)
        .where(
            Prescription.id == prescription_id,
            Patient.user_id == patient_user_id,
            Prescription.status.in_(_PATIENT_VISIBLE),
        )
    )
    return result.scalar_one_or_none()


async def list_for_patient(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Prescription], int]:
    """Signed/dispensed prescriptions only, newest first."""
    base = (
        select(Prescription)
        .join(Patient, Patient.id == Prescription.patient_id)
        .where(
            Patient.user_id == patient_user_id,
            Prescription.status.in_(_PATIENT_VISIBLE),
            Prescription.superseded_by_id.is_(None),
        )
        .order_by(Prescription.signed_at.desc().nulls_last(), Prescription.created_at.desc())
    )
    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.scalar(count_q)) or 0

    offset = (page - 1) * page_size
    rows_result = await db.execute(base.offset(offset).limit(page_size))
    return list(rows_result.scalars().all()), total


async def list_items(
    db: AsyncSession,
    *,
    prescription_id: uuid.UUID,
) -> list[PrescriptionItem]:
    result = await db.execute(
        select(PrescriptionItem)
        .where(PrescriptionItem.prescription_id == prescription_id)
        .order_by(PrescriptionItem.order_index)
    )
    return list(result.scalars().all())


async def update_draft(
    db: AsyncSession,
    *,
    prescription_id: uuid.UUID,
    doctor_id: uuid.UUID,
    diagnosis_note: str | None,
    general_instructions: str | None,
    items: list[dict[str, Any]] | None,
) -> Prescription | None:
    """Edit a DRAFT prescription in place. Signed prescriptions are immutable —
    corrections after signing go through the supersede-version flow, never here.

    items=None leaves the medication lines untouched; a list replaces them all.
    Returns None when not owned by this doctor or no longer a draft.
    """
    rx = await get_for_doctor(db, prescription_id=prescription_id, doctor_id=doctor_id)
    if rx is None or rx.status != PrescriptionStatus.DRAFT:
        return None

    rx.diagnosis_note = diagnosis_note
    rx.general_instructions = general_instructions
    rx.updated_at = datetime.now(UTC)

    if items is not None:
        from sqlalchemy import delete

        from app.db.enums import DrugForm

        await db.execute(
            delete(PrescriptionItem).where(
                PrescriptionItem.prescription_id == prescription_id
            )
        )
        for idx, item in enumerate(items):
            db.add(
                PrescriptionItem(
                    prescription_id=rx.id,
                    drug_generic_name=item["drug_generic_name"],
                    drug_form=DrugForm(item["drug_form"]),
                    dosage=item["dosage"],
                    frequency=item["frequency"],
                    duration_days=item.get("duration_days"),
                    instructions=item.get("instructions"),
                    refill_allowed=bool(item.get("refill_allowed", False)),
                    order_index=idx,
                )
            )

    await db.flush()
    return rx


async def sign(
    db: AsyncSession,
    *,
    prescription_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> Prescription | None:
    """Transition draft → signed.  Returns None if not owned by this doctor."""
    rx = await get_for_doctor(db, prescription_id=prescription_id, doctor_id=doctor_id)
    if rx is None:
        return None
    if rx.status != PrescriptionStatus.DRAFT:
        return None
    rx.status = PrescriptionStatus.SIGNED
    rx.signed_at = datetime.now(UTC)
    rx.updated_at = datetime.now(UTC)
    await db.flush()
    return rx


async def set_pdf_url(
    db: AsyncSession,
    *,
    prescription_id: uuid.UUID,
    pdf_url: str,
) -> None:
    await db.execute(
        update(Prescription)
        .where(Prescription.id == prescription_id)
        .values(pdf_url=pdf_url, updated_at=datetime.now(UTC))
    )


async def get_by_id(
    db: AsyncSession,
    *,
    prescription_id: uuid.UUID,
) -> Prescription | None:
    """Unscoped fetch for internal use (Celery tasks)."""
    result = await db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    )
    return result.scalar_one_or_none()
