"""Lab report service — orchestrates upload lifecycle and OCR dispatch."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import LabReportSource, LabReportStatus
from app.integrations import s3
from app.repositories import lab_reports as lab_reports_repo

logger = structlog.get_logger(__name__)

# Allowed content types must match S3 integration allowlist
_ALLOWED_CONTENT_TYPES = s3.ALLOWED_CONTENT_TYPES
_MAX_SIZE_BYTES = s3.MAX_FILE_SIZE_BYTES


class LabReportValidationError(Exception):
    pass


async def initiate_upload(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    patient_id: uuid.UUID,
    original_filename: str,
    content_type: str,
    file_size_bytes: int,
) -> dict[str, Any]:
    """Create a lab report row and return an S3 presigned upload URL.

    Returns:
        {lab_report_id, upload_url, fields, s3_key, content_type}
    """
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise LabReportValidationError(
            f"content_type must be one of: {', '.join(sorted(_ALLOWED_CONTENT_TYPES))}"
        )
    if file_size_bytes <= 0 or file_size_bytes > _MAX_SIZE_BYTES:
        raise LabReportValidationError(
            f"file_size_bytes must be between 1 and {_MAX_SIZE_BYTES}"
        )

    report = await lab_reports_repo.create(
        db,
        patient_id=patient_id,
        uploaded_by_user_id=patient_user_id,
        original_filename=original_filename,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
        source=LabReportSource.PATIENT_UPLOAD,
    )

    presigned = s3.generate_upload_url(
        patient_uuid=patient_user_id,
        lab_report_uuid=report.id,
        filename=original_filename,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
    )

    await lab_reports_repo.set_file_url(
        db,
        lab_report_id=report.id,
        file_url=presigned["s3_key"],
        status=LabReportStatus.UPLOAD_PENDING,
    )

    logger.info("lab_report.upload_initiated", lab_report_id=str(report.id))
    return {
        "lab_report_id": report.id,
        "upload_url": presigned["upload_url"],
        "fields": presigned["fields"],
        "s3_key": presigned["s3_key"],
        "content_type": content_type,
    }


async def finalize_upload(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> dict[str, Any]:
    """Confirm upload, verify S3 object exists, dispatch OCR task.

    Returns:
        {lab_report_id, status, ocr_task_id}
    """
    report = await lab_reports_repo.get_for_patient(
        db,
        lab_report_id=lab_report_id,
        patient_user_id=patient_user_id,
    )
    if report is None:
        return {"not_found": True}

    if report.status != LabReportStatus.UPLOAD_PENDING:
        return {"lab_report_id": report.id, "status": report.status, "ocr_task_id": None}

    if report.file_url is None:
        raise LabReportValidationError("Report has no file_url — cannot finalize.")

    import asyncio

    meta = await asyncio.to_thread(s3.head_object, s3_key=report.file_url)
    if meta is None:
        raise LabReportValidationError(
            "Upload not found in S3. Please complete the upload before calling finalize."
        )

    content_type_in_s3 = meta.get("ContentType", "")
    if content_type_in_s3 and content_type_in_s3 not in _ALLOWED_CONTENT_TYPES:
        raise LabReportValidationError(
            f"Unexpected content type in S3: {content_type_in_s3}"
        )

    await lab_reports_repo.set_status(
        db, lab_report_id=report.id, status=LabReportStatus.OCR_PENDING
    )

    from app.tasks.ocr_tasks import parse_lab_report

    task = parse_lab_report.delay(str(report.id))
    logger.info("lab_report.finalized", lab_report_id=str(report.id), task_id=task.id)

    return {
        "lab_report_id": report.id,
        "status": LabReportStatus.OCR_PENDING,
        "ocr_task_id": task.id,
    }


async def get_download_url(
    db: AsyncSession,
    *,
    lab_report_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> str | None:
    """Return a 10-minute presigned GET URL or None if not authorized."""
    report = await lab_reports_repo.get_for_patient(
        db,
        lab_report_id=lab_report_id,
        patient_user_id=patient_user_id,
    )
    if report is None or report.file_url is None:
        return None
    return s3.generate_download_url(s3_key=report.file_url)
