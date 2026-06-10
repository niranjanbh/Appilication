"""Pre-consultation report Celery tasks.

Tasks:
  kyrosclinic.comal.generate_pre_consultation_report    — per-consultation, on-demand or scheduled
  kyrosclinic.comal.generate_pre_consult_reports_for_tomorrow — daily cron fan-out
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.worker import celery_app

log = logging.getLogger(__name__)
logger = structlog.get_logger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyrosclinic.comal.generate_pre_consultation_report",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_pre_consultation_report(self: Any, consultation_id: str) -> dict[str, Any]:
    """Generate and upload the pre-consultation PDF for a single consultation.

    Idempotent — running twice with the same consultation_id is safe (upserts the row,
    re-uploads the PDF).  No PHI in logs.
    """
    bound_logger = logger.bind(
        task_name="generate_pre_consultation_report",
        task_id=self.request.id,
        attempt=self.request.retries + 1,
        consultation_id=consultation_id,
    )
    bound_logger.info("task.started")
    try:
        result = asyncio.run(_generate_report_async(consultation_id))
        bound_logger.info("task.completed", status=result.get("status"))
        return result
    except Exception as exc:
        bound_logger.exception("task.failed")
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyrosclinic.comal.generate_pre_consult_reports_for_tomorrow",
    bind=True,
    acks_late=True,
)
def generate_pre_consult_reports_for_tomorrow(self: Any) -> dict[str, Any]:
    """Cron fan-out: find all consultations in the T-24h window, enqueue individual tasks."""
    bound_logger = logger.bind(
        task_name="generate_pre_consult_reports_for_tomorrow",
        task_id=self.request.id,
    )
    bound_logger.info("cron.started")
    result = asyncio.run(_fan_out_tomorrow())
    bound_logger.info("cron.completed", enqueued=result.get("enqueued", 0))
    return result


# ── Async implementations ─────────────────────────────────────────────────────


async def _fan_out_tomorrow() -> dict[str, Any]:
    from app.db.session import AsyncSessionLocal
    from app.repositories import pre_consult_reports as reports_repo

    now = datetime.now(UTC)
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    async with AsyncSessionLocal() as db:
        consultations = await reports_repo.list_consultations_needing_reports(
            db, window_start=window_start, window_end=window_end
        )

    enqueued = 0
    for c in consultations:
        generate_pre_consultation_report.apply_async(
            args=[str(c.id)],
            queue="reports",
        )
        enqueued += 1

    return {"enqueued": enqueued}


async def _generate_report_async(consultation_id: str) -> dict[str, Any]:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.clinic import Consultation, Patient
    from app.models.doctor import Doctor
    from app.models.identity import User
    from app.repositories import pre_consult_reports as reports_repo
    from app.services.pre_consult_report_service import (
        generate_report_for_consultation,
        render_pre_consult_html,
    )

    c_id = uuid.UUID(consultation_id)

    async with AsyncSessionLocal() as db:
        report = await generate_report_for_consultation(db, consultation_id=c_id)
        if report is None:
            return {"status": "skipped", "reason": "not_found_or_wrong_status"}

        # Load names for the PDF
        consult_result = await db.execute(
            select(Consultation).where(Consultation.id == c_id)
        )
        consultation = consult_result.scalar_one_or_none()
        if consultation is None:
            return {"status": "skipped", "reason": "consultation_gone"}

        patient_result = await db.execute(
            select(User)
            .join(Patient, Patient.user_id == User.id)
            .where(Patient.id == consultation.patient_id)
        )
        patient_user = patient_result.scalar_one_or_none()
        patient_name = patient_user.name if patient_user else "—"

        doctor_user_result = await db.execute(
            select(User)
            .join(Doctor, Doctor.user_id == User.id)
            .where(Doctor.id == consultation.doctor_id)
        )
        doctor_user = doctor_user_result.scalar_one_or_none()
        doctor_name = doctor_user.name if doctor_user else "—"

        html = render_pre_consult_html(
            report=report,
            patient_name=patient_name,
            doctor_name=doctor_name,
            scheduled_at=consultation.scheduled_start_at,
        )
        report_id = report.id
        await db.commit()

    # Render PDF outside the DB session (CPU bound)
    pdf_bytes = _render_pdf(html)

    s3_key = f"pre-consult-reports/{consultation_id}/v1.pdf"
    s3_url = _upload_to_s3(pdf_bytes, s3_key)

    async with AsyncSessionLocal() as db:
        await reports_repo.set_pdf_url(db, report_id=report_id, pdf_url=s3_url)
        await db.commit()

    # Notify patient that pre-consultation report is ready (fire-and-forget)
    from app.services.notifications import notify_pre_consult_report_ready
    async with AsyncSessionLocal() as notif_db:
        await notify_pre_consult_report_ready(notif_db, consultation_id=c_id)

    return {"status": "done", "s3_key": s3_key}


def _render_pdf(html: str) -> bytes:
    from weasyprint import HTML  # type: ignore[import-untyped]

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        HTML(string=html).write_pdf(tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _upload_to_s3(pdf_bytes: bytes, s3_key: str) -> str:
    from app.core.config import settings
    from app.integrations.s3 import _s3_client

    client = _s3_client()
    client.upload_fileobj(
        io.BytesIO(pdf_bytes),
        settings.s3_bucket,
        s3_key,
        ExtraArgs={
            "ContentType": "application/pdf",
            "ServerSideEncryption": "aws:kms",
        },
    )
    return f"s3://{settings.s3_bucket}/{s3_key}"
