from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.worker import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="kyros.payment.generate_gst_invoice")  # type: ignore[untyped-decorator]
def generate_gst_invoice(payment_id: str) -> dict[str, Any]:
    """Generate a GST-compliant invoice number for a successful payment.

    In production this would render a WeasyPrint PDF, upload to S3,
    and store the signed URL. For Phase 1, writes a sequential invoice
    number and a placeholder URL.
    """
    return asyncio.run(_generate_gst_invoice_async(payment_id))


async def _generate_gst_invoice_async(payment_id: str) -> dict[str, Any]:
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import text

    from app.db.session import AsyncSessionLocal
    from app.repositories.payments import update_payment

    pid = uuid.UUID(payment_id)
    async with AsyncSessionLocal() as db:
        seq_num = await db.scalar(text("SELECT nextval('gst_invoice_seq')"))
        year = datetime.now(UTC).year
        invoice_number = f"INV-{year}-{seq_num:06d}"
        # In production: generate PDF → S3 → signed URL
        invoice_url = f"https://invoices.dev.kyros.local/{invoice_number}.pdf"

        await update_payment(
            db,
            payment_id=pid,
            gst_invoice_number=invoice_number,
            gst_invoice_url=invoice_url,
        )
        await db.commit()

    log.info("gst_invoice_generated payment_id=%s invoice=%s", payment_id, invoice_number)
    return {"payment_id": payment_id, "invoice_number": invoice_number}


@celery_app.task(name="kyros.payment.reconcile_pending")  # type: ignore[untyped-decorator]
def reconcile_pending_payments() -> dict[str, Any]:
    """Reconcile payments stuck in created/attempted status.

    Runs every 2 hours via Celery beat. Calls Razorpay's order payments API
    to detect captures that arrived without a webhook.
    """
    return asyncio.run(_reconcile_pending_async())


async def _reconcile_pending_async() -> dict[str, Any]:
    from app.db.enums import PaymentStatus
    from app.db.session import AsyncSessionLocal
    from app.integrations import razorpay as rzp
    from app.repositories.payments import list_stale_payments, update_payment

    reconciled = 0
    async with AsyncSessionLocal() as db:
        stale = await list_stale_payments(
            db,
            statuses=[PaymentStatus.CREATED, PaymentStatus.ATTEMPTED],
            older_than_minutes=30,
        )
        for payment in stale:
            order_data = await rzp.fetch_order_payments(payment.razorpay_order_id)
            items: list[dict[str, Any]] = order_data.get("items", [])
            for item in items:
                if item.get("status") == "captured":
                    await update_payment(
                        db,
                        payment_id=payment.id,
                        status=PaymentStatus.PAID,
                        razorpay_payment_id=item.get("id"),
                    )
                    # Enqueue invoice generation
                    generate_gst_invoice.delay(str(payment.id))
                    reconciled += 1
                    break

        await db.commit()

    log.info("payment_reconciliation_complete reconciled=%d", reconciled)
    return {"reconciled": reconciled}
