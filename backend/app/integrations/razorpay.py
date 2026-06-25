"""Razorpay REST API wrapper.

All amounts are in paise (integer). This client never raises on HTTP errors —
it returns the parsed JSON so callers can inspect the error payload.
Callers should check for "error" keys in the returned dict.

When razorpay_key_id is blank (dev/test mode without real credentials), methods
that make outbound calls log a warning and return a synthetic stub response so
the application can be exercised without a live Razorpay account.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_BASE_URL = "https://api.razorpay.com/v1"

# Stub response returned when no Razorpay credentials are configured.
_STUB_ORDER = {
    "id": "order_STUB000000000",
    "entity": "order",
    "amount": 0,
    "currency": "INR",
    "status": "created",
    "receipt": "stub",
    "_stub": True,
}
_STUB_REFUND = {
    "id": "rfnd_STUB000000000",
    "entity": "refund",
    "status": "processed",
    "_stub": True,
}
_STUB_SUBSCRIPTION = {
    "id": "sub_STUB000000000",
    "entity": "subscription",
    "status": "created",
    "_stub": True,
}


def _is_configured() -> bool:
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


def _auth() -> tuple[str, str]:
    return (settings.razorpay_key_id, settings.razorpay_key_secret)


async def create_order(
    *,
    amount_paise: int,
    currency: str = "INR",
    receipt: str,
    notes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a Razorpay order. Returns the order object from Razorpay."""
    if not _is_configured():
        logger.warning("razorpay_not_configured_returning_stub", receipt=receipt)
        stub = {**_STUB_ORDER, "amount": amount_paise, "currency": currency, "receipt": receipt,
                "id": f"order_STUB{uuid.uuid4().hex[:12].upper()}"}
        return stub

    async with httpx.AsyncClient(auth=_auth(), timeout=10.0) as client:
        resp = await client.post(
            f"{_BASE_URL}/orders",
            json={"amount": amount_paise, "currency": currency, "receipt": receipt,
                  "notes": notes or {}},
        )
    return resp.json()  # type: ignore[no-any-return]


async def fetch_payment(razorpay_payment_id: str) -> dict[str, Any]:
    """Fetch a payment record from Razorpay by payment ID."""
    if not _is_configured():
        return {"id": razorpay_payment_id, "status": "captured", "_stub": True}

    async with httpx.AsyncClient(auth=_auth(), timeout=10.0) as client:
        resp = await client.get(f"{_BASE_URL}/payments/{razorpay_payment_id}")
    return resp.json()  # type: ignore[no-any-return]


async def fetch_order_payments(razorpay_order_id: str) -> dict[str, Any]:
    """Return payments associated with an order (for reconciliation)."""
    if not _is_configured():
        return {"entity": "collection", "count": 0, "items": [], "_stub": True}

    async with httpx.AsyncClient(auth=_auth(), timeout=10.0) as client:
        resp = await client.get(f"{_BASE_URL}/orders/{razorpay_order_id}/payments")
    return resp.json()  # type: ignore[no-any-return]


async def initiate_refund(
    *,
    razorpay_payment_id: str,
    amount_paise: int,
    notes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Initiate a refund for a captured payment. Returns Razorpay refund object."""
    if not _is_configured():
        logger.warning("razorpay_not_configured_stub_refund", payment_id=razorpay_payment_id)
        return {**_STUB_REFUND, "payment_id": razorpay_payment_id, "amount": amount_paise}

    async with httpx.AsyncClient(auth=_auth(), timeout=10.0) as client:
        resp = await client.post(
            f"{_BASE_URL}/payments/{razorpay_payment_id}/refund",
            json={"amount": amount_paise, "notes": notes or {}},
        )
    return resp.json()  # type: ignore[no-any-return]


async def create_subscription(
    *,
    plan_id: str,
    total_count: int,
    customer_email: str,
    customer_phone: str,
    notes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a Razorpay subscription for RBI e-mandate / annual billing."""
    if not _is_configured():
        logger.warning("razorpay_not_configured_stub_subscription")
        return {**_STUB_SUBSCRIPTION, "plan_id": plan_id}

    async with httpx.AsyncClient(auth=_auth(), timeout=10.0) as client:
        resp = await client.post(
            f"{_BASE_URL}/subscriptions",
            json={
                "plan_id": plan_id,
                "total_count": total_count,
                "notify_info": {"notify_phone": customer_phone, "notify_email": customer_email},
                "notes": notes or {},
            },
        )
    return resp.json()  # type: ignore[no-any-return]


def verify_payment_signature(
    *,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """Verify the client-side payment signature returned after checkout.

    Razorpay signs "{order_id}|{payment_id}" with the key secret using HMAC-SHA256.
    """
    if not settings.razorpay_key_secret:
        # Dev/test bypass: no key secret configured, so we cannot verify the
        # signature. Production refuses to boot without this secret (see
        # Settings._refuse_unsafe_production_config), so reaching here means dev mode.
        logger.warning(
            "razorpay_key_secret_not_configured_skipping_signature_check",
            razorpay_order_id=razorpay_order_id,
        )
        return True  # dev stub — always pass when unconfigured

    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected = hmac.new(
        settings.razorpay_key_secret.encode(), message, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature)


def verify_webhook_signature(raw_body: bytes, header_signature: str) -> bool:
    """Verify the X-Razorpay-Signature header on an inbound webhook.

    Razorpay signs the raw request body with the webhook secret using HMAC-SHA256.
    Returns False if the webhook secret is not configured.
    """
    if not settings.razorpay_webhook_secret:
        logger.warning("razorpay_webhook_secret_not_configured")
        return False
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header_signature)
