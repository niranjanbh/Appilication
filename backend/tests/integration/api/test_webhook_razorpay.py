"""Integration tests for the Razorpay webhook endpoint."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_patient_user


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _payment_captured_payload(order_id: str, payment_id: str) -> bytes:
    return json.dumps({
        "entity": "event",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "status": "captured",
                    "amount": 60000,
                    "currency": "INR",
                }
            }
        },
    }).encode()


def _payment_failed_payload(order_id: str, payment_id: str) -> bytes:
    return json.dumps({
        "entity": "event",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "status": "failed",
                }
            }
        },
    }).encode()


# ── Signature verification ─────────────────────────────────────────────────────


async def test_webhook_invalid_signature_returns_400(client: AsyncClient) -> None:
    body = b'{"event":"payment.captured"}'
    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": "bad_signature",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_signature"


async def test_webhook_no_signature_returns_400(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=b'{"event":"payment.captured"}',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


# ── payment.captured ──────────────────────────────────────────────────────────


async def test_webhook_payment_captured_updates_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.core.config import settings
    from app.db.enums import PaymentStatus
    from app.models.payment import Payment

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient, UserModel)

    order_id = f"order_WHK{uuid.uuid4().hex[:8].upper()}"
    payment_id = f"pay_WHK{uuid.uuid4().hex[:8].upper()}"

    payment = Payment(
        user_id=patient.id,
        razorpay_order_id=order_id,
        amount_paise=60000,
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    await db_session.flush()

    body = _payment_captured_payload(order_id, payment_id)
    sig = _sign(body, settings.razorpay_webhook_secret)

    with patch("app.tasks.payment_tasks.generate_gst_invoice.delay"):
        resp = await client.post(
            "/v1/webhooks/razorpay",
            content=body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
        )
    assert resp.status_code == 200

    result = await db_session.execute(
        select(Payment).where(Payment.razorpay_order_id == order_id)
    )
    updated = result.scalar_one_or_none()
    assert updated is not None
    assert updated.status == PaymentStatus.PAID
    assert updated.razorpay_payment_id == payment_id


# ── payment.failed ────────────────────────────────────────────────────────────


async def test_webhook_payment_failed_updates_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.core.config import settings
    from app.db.enums import PaymentStatus
    from app.models.payment import Payment

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient, UserModel)

    order_id = f"order_FAIL{uuid.uuid4().hex[:8].upper()}"
    payment_id = f"pay_FAIL{uuid.uuid4().hex[:8].upper()}"

    payment = Payment(
        user_id=patient.id,
        razorpay_order_id=order_id,
        amount_paise=50000,
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    await db_session.flush()

    body = _payment_failed_payload(order_id, payment_id)
    sig = _sign(body, settings.razorpay_webhook_secret)

    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        select(Payment).where(Payment.razorpay_order_id == order_id)
    )
    updated = result.scalar_one_or_none()
    assert updated is not None
    assert updated.status == PaymentStatus.FAILED


# ── Idempotency ───────────────────────────────────────────────────────────────


async def test_webhook_duplicate_event_is_noop(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Replaying the same event a second time must not change payment state."""
    from sqlalchemy import select

    from app.core.config import settings
    from app.db.enums import PaymentStatus
    from app.models.payment import Payment

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient, UserModel)

    order_id = f"order_IDEM{uuid.uuid4().hex[:8].upper()}"
    payment_id = f"pay_IDEM{uuid.uuid4().hex[:8].upper()}"

    payment = Payment(
        user_id=patient.id,
        razorpay_order_id=order_id,
        amount_paise=70000,
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    await db_session.flush()

    body = _payment_captured_payload(order_id, payment_id)
    sig = _sign(body, settings.razorpay_webhook_secret)
    headers = {"Content-Type": "application/json", "X-Razorpay-Signature": sig}

    with patch("app.tasks.payment_tasks.generate_gst_invoice.delay"):
        # First call — processes and sets Redis idempotency key
        resp1 = await client.post("/v1/webhooks/razorpay", content=body, headers=headers)
        assert resp1.status_code == 200
        assert resp1.json().get("note") != "duplicate"

        # Second call with the same body — idempotent skip
        resp2 = await client.post("/v1/webhooks/razorpay", content=body, headers=headers)
        assert resp2.status_code == 200
        assert resp2.json().get("note") == "duplicate"

    # Verify DB was only updated once (status is paid, not double-updated to something else)
    result = await db_session.execute(
        select(Payment).where(Payment.razorpay_order_id == order_id)
    )
    updated = result.scalar_one_or_none()
    assert updated is not None
    assert updated.status == PaymentStatus.PAID


# ── Unknown order ID ──────────────────────────────────────────────────────────


async def test_webhook_unknown_order_returns_200(client: AsyncClient) -> None:
    """Webhooks for orders we don't know about are acknowledged without error."""
    from app.core.config import settings

    body = _payment_captured_payload("order_UNKNOWN99999", "pay_UNKNOWN99999")
    sig = _sign(body, settings.razorpay_webhook_secret)

    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
    )
    assert resp.status_code == 200
