"""Prescription Celery tasks.

Task:  kyros.clinical.generate_prescription_pdf  (routes to 'reports' queue)
Idempotency: re-uploads if pdf_url is already set (safe duplicate).
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from typing import Any

import structlog

from app.worker import celery_app

log = logging.getLogger(__name__)
logger = structlog.get_logger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.clinical.generate_prescription_pdf",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_prescription_pdf(self: Any, prescription_id: str) -> dict[str, Any]:
    """Generate a WeasyPrint PDF for a signed prescription and upload to S3.

    Idempotent — running twice with the same prescription_id is safe.
    No PHI is logged — only prescription_id and task metadata.
    """
    bound_logger = logger.bind(
        task_name="generate_prescription_pdf",
        task_id=self.request.id,
        attempt=self.request.retries + 1,
        prescription_id=prescription_id,
    )
    bound_logger.info("task.started")
    try:
        result = asyncio.run(_generate_pdf_async(prescription_id))
        bound_logger.info("task.completed", s3_key=result.get("s3_key"))
        return result
    except Exception as exc:
        bound_logger.exception("task.failed")
        raise self.retry(exc=exc) from exc


async def _generate_pdf_async(prescription_id: str) -> dict[str, Any]:
    from app.db.session import AsyncSessionLocal
    from app.repositories import prescriptions as prescriptions_repo

    rx_id = uuid.UUID(prescription_id)

    async with AsyncSessionLocal() as db:
        rx = await prescriptions_repo.get_by_id(db, prescription_id=rx_id)
        if rx is None:
            logger.warning("prescription.not_found", prescription_id=prescription_id)
            return {"status": "not_found"}

        items = await prescriptions_repo.list_items(db, prescription_id=rx_id)

        # Load doctor info
        from sqlalchemy import select

        from app.models.doctor import Doctor
        from app.models.identity import User

        doctor_result = await db.execute(select(Doctor).where(Doctor.id == rx.doctor_id))
        doctor = doctor_result.scalar_one_or_none()

        patient_user_result = await db.execute(
            select(User)
            .join(__import__('app.models.clinic', fromlist=['Patient']).Patient, __import__('app.models.clinic', fromlist=['Patient']).Patient.user_id == User.id)
            .where(__import__('app.models.clinic', fromlist=['Patient']).Patient.id == rx.patient_id)
        )
        patient_user = patient_user_result.scalar_one_or_none()

        doctor_name = ""
        nmc_number = ""
        specialty: list[str] = []
        if doctor:
            # Load user for name
            user_result = await db.execute(select(User).where(User.id == doctor.user_id))
            doctor_user = user_result.scalar_one_or_none()
            doctor_name = doctor_user.name if doctor_user else "—"
            nmc_number = doctor.nmc_registration_number
            specialty = list(doctor.specialty) if doctor.specialty else []

        patient_name = patient_user.name if patient_user else "—"

        from app.services.prescription_service import render_prescription_html
        html = render_prescription_html(
            prescription=rx,
            items=items,
            doctor_name=doctor_name,
            nmc_registration_number=nmc_number,
            specialty=specialty,
            patient_name=patient_name,
        )

    # Generate PDF via WeasyPrint
    pdf_bytes = _render_pdf(html)

    # Upload to S3 (sync boto3 — runs outside the async event loop context)
    s3_key = f"prescriptions/{prescription_id}/v1.pdf"
    s3_url = _upload_to_s3(pdf_bytes, s3_key)

    # Persist pdf_url
    async with AsyncSessionLocal() as db:
        await prescriptions_repo.set_pdf_url(db, prescription_id=rx_id, pdf_url=s3_url)
        await db.commit()

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
    import io

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
