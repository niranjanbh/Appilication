"""Integration tests for refund tracking — list, detail, cross-user scoping, RBAC."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import PaymentStatus, RefundStatus
from app.models.audit import AuditLog
from app.models.identity import User as UserModel
from app.models.payment import Payment, Refund
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


async def _make_paid_payment(db: AsyncSession, user_id: uuid.UUID) -> Payment:
    payment = Payment(
        user_id=user_id,
        razorpay_order_id=f"order_RF{uuid.uuid4().hex[:10].upper()}",
        razorpay_payment_id=f"pay_RF{uuid.uuid4().hex[:10].upper()}",
        amount_paise=60000,
        status=PaymentStatus.PAID,
    )
    db.add(payment)
    await db.flush()
    return payment


async def _make_refund(
    db: AsyncSession, payment: Payment, *, amount_paise: int = 60000
) -> Refund:
    refund = Refund(
        payment_id=payment.id,
        user_id=payment.user_id,
        razorpay_refund_id=f"rfnd_{uuid.uuid4().hex[:10].upper()}",
        amount_paise=amount_paise,
        status=RefundStatus.PROCESSED,
    )
    db.add(refund)
    await db.flush()
    return refund


# ── List ────────────────────────────────────────────────────────────────────────


async def test_list_refunds_empty_for_new_patient(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/payments/refunds", headers=make_auth_headers(patient))
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_refunds_returns_own_refunds(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    payment = await _make_paid_payment(db_session, patient.id)
    refund = await _make_refund(db_session, payment)

    resp = await client.get("/v1/payments/refunds", headers=make_auth_headers(patient))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(refund.id)
    assert data["items"][0]["amount_paise"] == 60000
    assert data["items"][0]["status"] == "processed"


async def test_list_refunds_excludes_other_patients(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    assert isinstance(patient_a, UserModel)
    payment_a = await _make_paid_payment(db_session, patient_a.id)
    await _make_refund(db_session, payment_a)

    resp = await client.get("/v1/payments/refunds", headers=make_auth_headers(patient_b))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── initiate_refund records a refund row ─────────────────────────────────────────


async def test_initiate_refund_records_refund_row(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.services import payment_service

    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    payment = await _make_paid_payment(db_session, patient.id)

    with patch(
        "app.integrations.razorpay.initiate_refund",
        new_callable=AsyncMock,
        return_value={"id": "rfnd_STUB123", "status": "processed"},
    ):
        await payment_service.initiate_refund(
            db_session, payment_id=payment.id, user_id=patient.id, reason="cancelled"
        )
    await db_session.flush()

    rows = (
        await db_session.execute(select(Refund).where(Refund.payment_id == payment.id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].razorpay_refund_id == "rfnd_STUB123"
    assert rows[0].status == RefundStatus.PROCESSED
    assert rows[0].amount_paise == 60000
    assert rows[0].reason == "cancelled"


# ── Detail + cross-user 404 ──────────────────────────────────────────────────────


async def test_get_own_refund_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    payment = await _make_paid_payment(db_session, patient.id)
    refund = await _make_refund(db_session, payment)

    resp = await client.get(
        f"/v1/payments/refunds/{refund.id}", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(refund.id)


async def test_get_other_patients_refund_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    assert isinstance(patient_a, UserModel)
    assert isinstance(patient_b, UserModel)
    payment = await _make_paid_payment(db_session, patient_a.id)
    refund = await _make_refund(db_session, payment)

    resp = await client.get(
        f"/v1/payments/refunds/{refund.id}", headers=make_auth_headers(patient_b)
    )
    assert resp.status_code == 404

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_b.id,
            AuditLog.action == "view_refund",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


async def test_get_unknown_refund_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/payments/refunds/{uuid.uuid4()}", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 404


# ── RBAC ──────────────────────────────────────────────────────────────────────────


async def test_list_refunds_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/payments/refunds")
    assert resp.status_code == 401


async def test_list_refunds_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/payments/refunds", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_get_refund_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/payments/refunds/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_get_refund_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/payments/refunds/{uuid.uuid4()}", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403
