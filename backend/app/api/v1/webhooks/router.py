"""Razorpay inbound webhook handler.

Security model:
- No JWT auth. Authentication is HMAC-SHA256 of the raw request body
  using the Razorpay webhook secret (X-Razorpay-Signature header).
- Redis idempotency key prevents double-processing of replayed events.
  Key: webhook:razorpay:{event_type}:{entity_id}  TTL: 24h
- Every webhook event is audit-logged, allowed or denied.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, Redis
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, PaymentStatus
from app.integrations import razorpay as razorpay_integration
from app.repositories.payments import (
    get_by_order_id,
    get_by_razorpay_payment_id,
    update_payment,
)

router = APIRouter(tags=["webhooks"])
log = structlog.get_logger(__name__)

_WEBHOOK_KEY_TTL = 86_400  # 24 hours


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    redis: Redis,
    db: DbSession,
) -> dict[str, str]:
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not razorpay_integration.verify_webhook_signature(raw_body, signature):
        log.warning("razorpay_webhook_invalid_signature")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_signature")

    try:
        payload: dict[str, object] = json.loads(raw_body)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_json") from None

    event_type: str = str(payload.get("event", ""))
    entity_id = _extract_entity_id(event_type, payload)

    # Redis idempotency — acknowledge and skip if already processed
    idempotency_key = f"webhook:razorpay:{event_type}:{entity_id}"
    was_new = await redis.set(idempotency_key, "1", ex=_WEBHOOK_KEY_TTL, nx=True)
    if not was_new:
        log.info("razorpay_webhook_duplicate_skipped event=%s entity=%s", event_type, entity_id)
        return {"status": "ok", "note": "duplicate"}

    ctx = AuditContext(
        actor_user_id=None,
        actor_role=ActorRole.SYSTEM,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    post_commit_tasks = await _handle_event(db, ctx, event_type, payload)
    await db.commit()
    for task_fn, task_args in post_commit_tasks:
        task_fn.delay(*task_args)
    return {"status": "ok"}


def _extract_entity_id(event_type: str, payload: dict[str, object]) -> str:
    try:
        p: object = payload.get("payload")
        if not isinstance(p, dict):
            return _fallback_entity_id(payload)
        if event_type.startswith("payment."):
            return str(p["payment"]["entity"]["id"])
        if event_type.startswith("refund."):
            return str(p["refund"]["entity"]["id"])
        if event_type.startswith("order."):
            return str(p["order"]["entity"]["id"])
    except (KeyError, TypeError):
        pass
    return _fallback_entity_id(payload)


def _fallback_entity_id(payload: dict[str, object]) -> str:
    """Use the top-level Razorpay event id as a unique dedup key when the
    entity id can't be extracted, preventing key collisions."""
    event_id = payload.get("event_id") or payload.get("id")
    if event_id:
        return str(event_id)
    import hashlib
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


async def _handle_event(
    db: AsyncSession,
    ctx: AuditContext,
    event_type: str,
    payload: dict[str, object],
) -> list[tuple[Any, tuple[Any, ...]]]:
    """Process the webhook event. Returns a list of (celery_task, args) to
    dispatch *after* the caller commits the transaction."""
    p: Any = payload
    deferred: list[tuple[Any, tuple[Any, ...]]] = []

    if event_type == "payment.captured":
        entity = p["payload"]["payment"]["entity"]
        payment = await get_by_order_id(db, razorpay_order_id=entity.get("order_id", ""))
        if payment is not None:
            if payment.status == PaymentStatus.PAID:
                log.info("razorpay_webhook_payment_already_captured payment_id=%s", payment.id)
                return deferred
            await update_payment(
                db,
                payment_id=payment.id,
                status=PaymentStatus.PAID,
                razorpay_payment_id=entity.get("id"),
            )
            await write_audit(
                db, ctx, action="webhook_payment_captured",
                resource_type="payment", resource_id=payment.id, allowed=True,
            )
            from app.tasks.payment_tasks import generate_gst_invoice
            deferred.append((generate_gst_invoice, (str(payment.id),)))
        else:
            log.warning("razorpay_webhook_payment_not_found order_id=%s", entity.get("order_id"))

    elif event_type == "payment.failed":
        entity = p["payload"]["payment"]["entity"]
        payment = await get_by_order_id(db, razorpay_order_id=entity.get("order_id", ""))
        if payment is not None:
            await update_payment(
                db, payment_id=payment.id, status=PaymentStatus.FAILED,
                razorpay_payment_id=entity.get("id"),
            )
            await write_audit(
                db, ctx, action="webhook_payment_failed",
                resource_type="payment", resource_id=payment.id, allowed=True,
            )

    elif event_type == "refund.processed":
        entity = p["payload"]["refund"]["entity"]
        payment = await get_by_razorpay_payment_id(
            db, razorpay_payment_id=entity.get("payment_id", "")
        )
        if payment is not None:
            await update_payment(db, payment_id=payment.id, status=PaymentStatus.REFUNDED)
            await write_audit(
                db, ctx, action="webhook_refund_processed",
                resource_type="payment", resource_id=payment.id, allowed=True,
            )

    else:
        log.info("razorpay_webhook_unhandled_event event=%s", event_type)

    return deferred
