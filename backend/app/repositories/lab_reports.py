"""Lab report repository.

All patient-scoped functions take `patient_user_id` (the users.id of the authenticated
patient) rather than the internal kc_patients.id.  This enforces the cross-user 404
pattern at the SQL layer — a patient cannot observe another patient's reports by status
code alone.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import LabReportSource, LabReportStatus
from app.models.clinic import LabReport, Patient


async def create(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID,
    original_filename: str,
    content_type: str,
    file_size_bytes: int,
    source: LabReportSource = LabReportSource.PATIENT_UPLOAD,
) -> LabReport:
    report = LabReport(
        patient_id=patient_id,
        uploaded_by_user_id=uploaded_by_user_id,
        original_filename=original_filename,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
        source=source,
        status=LabReportStatus.UPLOAD_PENDING,
    )
    db.add(report)
    await db.flush()
    return report


async def get_for_patient(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> LabReport | None:
    """Resource-scoped fetch — returns None for other patients' reports or missing rows."""
    result = await db.execute(
        select(LabReport)
        .join(Patient, Patient.id == LabReport.patient_id)
        .where(
            LabReport.id == lab_report_id,
            Patient.user_id == patient_user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_by_id(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
) -> LabReport | None:
    """Unscoped fetch for internal use (Celery tasks)."""
    result = await db.execute(select(LabReport).where(LabReport.id == lab_report_id))
    return result.scalar_one_or_none()


async def list_for_patient(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[LabReport], int]:
    base = (
        select(LabReport)
        .join(Patient, Patient.id == LabReport.patient_id)
        .where(Patient.user_id == patient_user_id)
        .order_by(LabReport.created_at.desc())
    )
    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.scalar(count_q)) or 0

    offset = (page - 1) * page_size
    rows_result = await db.execute(base.offset(offset).limit(page_size))
    rows = list(rows_result.scalars().all())
    return rows, total


async def set_file_url(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
    file_url: str,
    status: LabReportStatus,
) -> None:
    await db.execute(
        update(LabReport)
        .where(LabReport.id == lab_report_id)
        .values(file_url=file_url, status=status, updated_at=datetime.now(UTC))
    )


async def set_ocr_result(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
    parsed_json: dict[str, Any],
    ocr_confidence_avg: float,
    low_confidence_fields: list[str],
    status: LabReportStatus,
) -> None:
    await db.execute(
        update(LabReport)
        .where(LabReport.id == lab_report_id)
        .values(
            parsed_json=parsed_json,
            ocr_confidence_avg=ocr_confidence_avg,
            low_confidence_fields=low_confidence_fields,
            status=status,
            updated_at=datetime.now(UTC),
        )
    )


async def set_ocr_failed(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
    reason: str,
) -> None:
    await db.execute(
        update(LabReport)
        .where(LabReport.id == lab_report_id)
        .values(
            status=LabReportStatus.OCR_FAILED,
            processing_failed_reason=reason,
            updated_at=datetime.now(UTC),
        )
    )


async def set_status(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
    status: LabReportStatus,
) -> None:
    await db.execute(
        update(LabReport)
        .where(LabReport.id == lab_report_id)
        .values(status=status, updated_at=datetime.now(UTC))
    )


async def apply_patient_correction(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
    patient_user_id: uuid.UUID,
    parsed_json: dict[str, Any],
) -> LabReport | None:
    """Apply patient-corrected OCR data.  Returns None if the report is not owned by the patient."""
    report = await get_for_patient(db, lab_report_id=lab_report_id, patient_user_id=patient_user_id)
    if report is None:
        return None
    report.parsed_json = parsed_json
    report.patient_corrected = True
    report.status = LabReportStatus.OCR_COMPLETE
    report.updated_at = datetime.now(UTC)
    await db.flush()
    return report


async def get_biomarker_trend_for_patient(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    biomarker_name: str,
    range_days: int | None = None,
) -> list[dict[str, Any]]:
    """Extract historical values for a single biomarker across all processed reports.

    Uses a LATERAL join over parsed_json->'biomarkers' so the extraction happens
    in Postgres rather than Python.  Returns rows ordered oldest-first.

    range_days=None means all history.  Cross-user safety: scoped by patient_user_id.
    """
    date_filter = ""
    params: dict[str, Any] = {
        "patient_user_id": str(patient_user_id),
        "biomarker_name": biomarker_name.strip().lower(),
    }
    if range_days is not None:
        cutoff: date = datetime.now(UTC).date() - timedelta(days=range_days)
        date_filter = "AND COALESCE(r.report_date, r.created_at::date) >= :cutoff"
        params["cutoff"] = cutoff

    sql = text(
        f"""
        SELECT
            r.id                AS report_id,
            r.report_date,
            r.lab_name,
            r.lab_order_id,
            o.consultation_id,
            b->>'value'         AS value,
            b->>'unit'          AS unit,
            b->>'ref_low'       AS ref_low,
            b->>'ref_high'      AS ref_high,
            b->>'flag'          AS flag,
            b->>'name'          AS biomarker_name
        FROM kc_lab_reports r
        JOIN kc_patients p ON p.id = r.patient_id
        LEFT JOIN kc_lab_orders o ON o.id = r.lab_order_id
        CROSS JOIN LATERAL jsonb_array_elements(r.parsed_json->'biomarkers') AS b
        WHERE p.user_id = :patient_user_id
          AND r.status IN ('ocr_complete', 'patient_review_needed')
          AND r.parsed_json IS NOT NULL
          AND lower(b->>'name') = :biomarker_name
          {date_filter}
        ORDER BY COALESCE(r.report_date, r.created_at::date) ASC, r.created_at ASC
        """
    )

    result = await db.execute(sql, params)
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def list_pending_ocr(
    db: AsyncSession,
    *,
    stale_minutes: int = 15,
) -> list[LabReport]:
    """Return reports stuck in ocr_pending for longer than stale_minutes (for reconciliation)."""
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(minutes=stale_minutes)
    result = await db.execute(
        select(LabReport).where(
            LabReport.status == LabReportStatus.OCR_PENDING,
            LabReport.created_at < cutoff,
        )
    )
    return list(result.scalars().all())
