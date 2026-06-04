"""Repository for kc_pre_consultation_reports.

All patient-scoped and doctor-scoped functions enforce resource ownership at the SQL
layer — returning None for rows that don't exist OR belong to another user/doctor,
so routers can translate None → 404 uniformly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Consultation, Patient, PreConsultationReport


async def create_or_update(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    patient_id: uuid.UUID,
    generated_at: datetime,
    lab_summary: dict[str, Any] | None,
    adherence_summary: dict[str, Any] | None,
    wearable_summary: dict[str, Any] | None,
    patient_flags: dict[str, Any] | None,
    intake_responses: dict[str, Any] | None,
) -> PreConsultationReport:
    """Upsert on consultation_id — idempotent, safe to re-run."""
    result = await db.execute(
        select(PreConsultationReport).where(
            PreConsultationReport.consultation_id == consultation_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        existing.generated_at = generated_at
        existing.lab_summary = lab_summary
        existing.adherence_summary = adherence_summary
        existing.wearable_summary = wearable_summary
        existing.patient_flags = patient_flags
        existing.intake_responses = intake_responses
        existing.updated_at = datetime.now(UTC)
        await db.flush()
        return existing

    report = PreConsultationReport(
        consultation_id=consultation_id,
        patient_id=patient_id,
        generated_at=generated_at,
        lab_summary=lab_summary,
        adherence_summary=adherence_summary,
        wearable_summary=wearable_summary,
        patient_flags=patient_flags,
        intake_responses=intake_responses,
    )
    db.add(report)
    await db.flush()
    return report


async def get_for_patient(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> PreConsultationReport | None:
    """Cross-user safe: returns None if the consultation isn't owned by this patient."""
    result = await db.execute(
        select(PreConsultationReport)
        .join(Patient, Patient.id == PreConsultationReport.patient_id)
        .where(
            PreConsultationReport.consultation_id == consultation_id,
            Patient.user_id == patient_user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_for_doctor(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> PreConsultationReport | None:
    """Cross-doctor safe: returns None if the consultation isn't owned by this doctor."""
    result = await db.execute(
        select(PreConsultationReport)
        .join(
            Consultation,
            Consultation.id == PreConsultationReport.consultation_id,
        )
        .where(
            PreConsultationReport.consultation_id == consultation_id,
            Consultation.doctor_id == doctor_id,
            Consultation.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_by_consultation_id(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> PreConsultationReport | None:
    """Unscoped — for internal Celery task use only."""
    result = await db.execute(
        select(PreConsultationReport).where(
            PreConsultationReport.consultation_id == consultation_id
        )
    )
    return result.scalar_one_or_none()


async def update_doctor_notes(
    db: AsyncSession,
    *,
    report_id: uuid.UUID,
    notes: str,
) -> PreConsultationReport | None:
    result = await db.execute(
        update(PreConsultationReport)
        .where(PreConsultationReport.id == report_id)
        .values(
            doctor_notes_pre_consult=notes,
            doctor_reviewed_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        .returning(PreConsultationReport)
    )
    return result.scalar_one_or_none()


async def set_pdf_url(
    db: AsyncSession,
    *,
    report_id: uuid.UUID,
    pdf_url: str,
) -> None:
    await db.execute(
        update(PreConsultationReport)
        .where(PreConsultationReport.id == report_id)
        .values(pdf_url=pdf_url, updated_at=datetime.now(UTC))
    )


async def list_consultations_needing_reports(
    db: AsyncSession,
    *,
    window_start: datetime,
    window_end: datetime,
) -> list[Consultation]:
    """Return consultations in the given time window that have no pre-consult report yet."""
    from app.db.enums import ConsultationStatus

    result = await db.execute(
        select(Consultation)
        .outerjoin(
            PreConsultationReport,
            PreConsultationReport.consultation_id == Consultation.id,
        )
        .where(
            Consultation.scheduled_start_at >= window_start,
            Consultation.scheduled_start_at < window_end,
            Consultation.status.in_(
                [ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED]
            ),
            Consultation.deleted_at.is_(None),
            PreConsultationReport.id.is_(None),
        )
    )
    return list(result.scalars().all())
