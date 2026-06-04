"""Integration tests for payment creation, verification, and cross-user scoping."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers

_STUB_ORDER_ID = "order_TESTSTUB00001"
_STUB_PAYMENT_ID = "pay_TESTSTUB00001"


def _make_razorpay_signature(order_id: str, payment_id: str, key_secret: str) -> str:
    message = f"{order_id}|{payment_id}".encode()
    return hmac.new(key_secret.encode(), message, hashlib.sha256).hexdigest()


# ── Order creation ─────────────────────────────────────────────────────────────


async def test_create_order_patient_returns_201(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    headers = make_auth_headers(patient)

    with patch(
        "app.integrations.razorpay.create_order",
        new_callable=AsyncMock,
        return_value={"id": _STUB_ORDER_ID, "amount": 60000, "currency": "INR"},
    ):
        resp = await client.post(
            "/v1/payments/order",
            json={"amount_paise": 60000},
            headers=headers,
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["razorpay_order_id"] == _STUB_ORDER_ID
    assert data["amount_paise"] == 60000
    assert data["status"] == "created"


async def test_create_order_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/payments/order", json={"amount_paise": 60000})
    assert resp.status_code == 401


async def test_create_order_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/payments/order",
        json={"amount_paise": 60000},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


# ── Payment verification ───────────────────────────────────────────────────────


async def test_verify_payment_valid_signature_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.core.config import settings
    from app.db.enums import PaymentStatus
    from app.models.payment import Payment

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient, UserModel)

    # Insert a payment row directly
    payment = Payment(
        user_id=patient.id,
        razorpay_order_id=_STUB_ORDER_ID,
        amount_paise=60000,
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    await db_session.flush()

    sig = _make_razorpay_signature(
        _STUB_ORDER_ID, _STUB_PAYMENT_ID, settings.razorpay_key_secret
    )

    resp = await client.post(
        "/v1/payments/verify",
        json={
            "payment_id": str(payment.id),
            "razorpay_order_id": _STUB_ORDER_ID,
            "razorpay_payment_id": _STUB_PAYMENT_ID,
            "razorpay_signature": sig,
        },
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"


async def test_verify_payment_bad_signature_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.db.enums import PaymentStatus
    from app.models.payment import Payment

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient, UserModel)

    order_id = f"order_BADSIG{uuid.uuid4().hex[:6].upper()}"
    payment = Payment(
        user_id=patient.id,
        razorpay_order_id=order_id,
        amount_paise=50000,
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    await db_session.flush()

    resp = await client.post(
        "/v1/payments/verify",
        json={
            "payment_id": str(payment.id),
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_FAKE",
            "razorpay_signature": "definitely_wrong_signature",
        },
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_signature"


# ── GET payment (cross-user 404) ───────────────────────────────────────────────


async def test_get_own_payment_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.db.enums import PaymentStatus
    from app.models.payment import Payment

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient, UserModel)

    order_id = f"order_GET{uuid.uuid4().hex[:8].upper()}"
    payment = Payment(
        user_id=patient.id,
        razorpay_order_id=order_id,
        amount_paise=30000,
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    await db_session.flush()

    resp = await client.get(
        f"/v1/payments/{payment.id}",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    assert resp.json()["razorpay_order_id"] == order_id


async def test_get_other_patients_payment_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.db.enums import PaymentStatus
    from app.models.payment import Payment

    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient_a, UserModel)
    assert isinstance(patient_b, UserModel)

    order_id = f"order_XUSER{uuid.uuid4().hex[:6].upper()}"
    payment = Payment(
        user_id=patient_a.id,
        razorpay_order_id=order_id,
        amount_paise=40000,
        status=PaymentStatus.CREATED,
    )
    db_session.add(payment)
    await db_session.flush()

    resp = await client.get(
        f"/v1/payments/{payment.id}",
        headers=make_auth_headers(patient_b),
    )
    assert resp.status_code == 404
