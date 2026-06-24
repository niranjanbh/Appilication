"""OCR Celery tasks — lab report parsing via Google Document AI.

Task name:  kyrosclinic.comal.parse_lab_report  (routes to the 'ocr' queue)
Idempotency: exits early if parsed_json is already populated.
Retries:    up to 5 times with exponential backoff (max 10 min between retries).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date as date_type
from typing import Any

import structlog

from app.worker import celery_app

log = logging.getLogger(__name__)
logger = structlog.get_logger(__name__)


class DocumentAITransientError(Exception):
    """Raised for retryable Document AI errors (network, quota, 5xx)."""


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyrosclinic.comal.parse_lab_report",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, DocumentAITransientError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True,
)
def parse_lab_report(self: Any, lab_report_id: str) -> dict[str, Any]:
    """Parse a lab report PDF/image via Google Document AI.

    Idempotent: if the report already has parsed_json, returns immediately.
    No PHI is logged — only the lab_report_id and task metadata.
    """
    bound_logger = logger.bind(
        task_name="parse_lab_report",
        task_id=self.request.id,
        attempt=self.request.retries + 1,
        lab_report_id=lab_report_id,
    )
    bound_logger.info("task.started")
    try:
        result = asyncio.run(_parse_lab_report_async(lab_report_id))
        bound_logger.info("task.completed", skipped=result.get("skipped", False))
        return result
    except Exception as exc:
        bound_logger.exception("task.failed", error_type=type(exc).__name__)
        raise


async def _parse_lab_report_async(lab_report_id: str) -> dict[str, Any]:
    import uuid

    from app.db.enums import LabReportStatus
    from app.db.session import AsyncSessionLocal
    from app.integrations import document_ai, s3
    from app.repositories import lab_reports as lab_reports_repo

    report_uuid = uuid.UUID(lab_report_id)

    async with AsyncSessionLocal() as db:
        report = await lab_reports_repo.get_by_id(db, lab_report_id=report_uuid)

        if report is None:
            logger.warning("ocr_task.report_not_found", lab_report_id=lab_report_id)
            return {"skipped": True, "reason": "report_not_found"}

        if report.parsed_json is not None:
            return {"skipped": True, "reason": "already_parsed"}

        if report.status == LabReportStatus.OCR_PROCESSING:
            return {"skipped": True, "reason": "already_processing"}

        if report.file_url is None:
            await lab_reports_repo.set_ocr_failed(
                db, lab_report_id=report_uuid, reason="no_file_url"
            )
            await db.commit()
            return {"skipped": True, "reason": "no_file_url"}

        try:
            await lab_reports_repo.set_status(
                db, lab_report_id=report_uuid, status=LabReportStatus.OCR_PROCESSING
            )
            await db.commit()

            file_bytes = s3.download_bytes(s3_key=report.file_url)
            mime_type = report.content_type or "application/pdf"

            parsed = document_ai.parse_healthcare_document(file_bytes, mime_type=mime_type)

        except Exception as exc:
            async with AsyncSessionLocal() as err_db:
                await lab_reports_repo.set_ocr_failed(
                    err_db,
                    lab_report_id=report_uuid,
                    reason=type(exc).__name__,
                )
                await err_db.commit()
            raise _maybe_transient(exc) from exc

    low_confidence_fields: list[str] = parsed.pop("_low_confidence_fields", [])
    overall_confidence: float = float(parsed.get("overall_confidence", 0.0))

    final_status = (
        LabReportStatus.PATIENT_REVIEW_NEEDED
        if any(
            b.get("needs_patient_correction", False)
            for b in parsed.get("biomarkers", [])
        )
        else LabReportStatus.OCR_COMPLETE
    )

    lab_name = parsed.get("lab_name")
    report_date_str = parsed.get("report_date")
    report_date: date_type | None = None
    if report_date_str:
        try:
            report_date = date_type.fromisoformat(report_date_str)
        except (ValueError, TypeError):
            report_date = None

    async with AsyncSessionLocal() as save_db:
        await lab_reports_repo.set_ocr_result(
            save_db,
            lab_report_id=report_uuid,
            parsed_json=parsed,
            ocr_confidence_avg=overall_confidence,
            low_confidence_fields=low_confidence_fields,
            status=final_status,
            lab_name=lab_name,
            report_date=report_date,
        )
        await save_db.commit()

    # Notify patient that lab results are ready (fire-and-forget Celery tasks)
    from app.services.notifications import notify_lab_result_ready
    async with AsyncSessionLocal() as notif_db:
        await notify_lab_result_ready(notif_db, lab_report_id=report_uuid)

    return {
        "ok": True,
        "lab_report_id": lab_report_id,
        "status": final_status,
        "overall_confidence": overall_confidence,
        "low_confidence_count": len(low_confidence_fields),
    }


def _maybe_transient(exc: Exception) -> Exception:
    """Wrap known transient errors so Celery retries; pass others through."""
    import google.api_core.exceptions as gcp_exc

    transient = (
        gcp_exc.ServiceUnavailable,
        gcp_exc.DeadlineExceeded,
        gcp_exc.InternalServerError,
        gcp_exc.ResourceExhausted,
    )
    if isinstance(exc, transient):
        return DocumentAITransientError(str(exc))
    return exc


@celery_app.task(name="kyrosclinic.comal.reconcile_pending_lab_ocr")  # type: ignore[untyped-decorator]
def reconcile_pending_lab_ocr() -> dict[str, Any]:
    """Beat task (every 30 min): re-dispatch OCR for reports stuck in ocr_pending."""
    return asyncio.run(_reconcile_async())


async def _reconcile_async() -> dict[str, Any]:
    from app.db.session import AsyncSessionLocal
    from app.repositories import lab_reports as lab_reports_repo

    async with AsyncSessionLocal() as db:
        stale = await lab_reports_repo.list_pending_ocr(db, stale_minutes=15)

    dispatched = 0
    for report in stale:
        parse_lab_report.delay(str(report.id))
        dispatched += 1

    logger.info("reconcile_pending_lab_ocr.done", dispatched=dispatched)
    return {"dispatched": dispatched}
