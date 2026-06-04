from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import PaymentStatus
from app.integrations import razorpay as razorpay_integration
from app.models.payment import Payment
from app.repositories import payments as payments_repo


class PaymentError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


async def create_order(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    amount_paise: int,
    currency: str = "INR",
    consultation_id: uuid.UUID | None = None,
    notes: dict[str, object] | None = None,
) -> Payment:
    """Create a Razorpay order and persist a kc_payments row in created status."""
    receipt = f"kyros-{uuid.uuid4().hex[:16]}"
    order = await razorpay_integration.create_order(
        amount_paise=amount_paise,
        currency=currency,
        receipt=receipt,
        notes=notes,
    )
    if "error" in order:
        raise PaymentError("razorpay_order_failed", str(order.get("error")))

    razorpay_order_id: str = order["id"]
    return await payments_repo.create_payment(
        db,
        user_id=user_id,
        razorpay_order_id=razorpay_order_id,
        amount_paise=amount_paise,
        currency=currency,
        consultation_id=consultation_id,
    )


async def verify_and_capture(
    db: AsyncSession,
    *,
    payment_id: uuid.UUID,
    user_id: uuid.UUID,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    razorpay_signature: str,
) -> Payment:
    """Verify the client-side payment signature and mark payment as paid."""
    payment = await payments_repo.get_payment_for_user(
        db, payment_id=payment_id, user_id=user_id
    )
    if payment is None:
        raise PaymentError("payment_not_found")

    if payment.status == PaymentStatus.PAID:
        return payment  # idempotent — already captured

    if not razorpay_integration.verify_payment_signature(
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
    ):
        raise PaymentError("invalid_signature")

    updated = await payments_repo.update_payment(
        db,
        payment_id=payment_id,
        status=PaymentStatus.PAID,
        razorpay_payment_id=razorpay_payment_id,
    )
    if updated is None:
        raise PaymentError("payment_update_failed")
    return updated


async def initiate_refund(
    db: AsyncSession,
    *,
    payment_id: uuid.UUID,
    user_id: uuid.UUID,
    amount_paise: int | None = None,
) -> Payment:
    """Initiate a Razorpay refund for a paid payment."""
    payment = await payments_repo.get_payment_for_user(
        db, payment_id=payment_id, user_id=user_id
    )
    if payment is None:
        raise PaymentError("payment_not_found")
    if payment.status not in (PaymentStatus.PAID,):
        raise PaymentError("payment_not_refundable")
    if payment.razorpay_payment_id is None:
        raise PaymentError("razorpay_payment_id_missing")

    refund_amount = amount_paise if amount_paise is not None else payment.amount_paise
    result = await razorpay_integration.initiate_refund(
        razorpay_payment_id=payment.razorpay_payment_id,
        amount_paise=refund_amount,
    )
    if "error" in result:
        raise PaymentError("razorpay_refund_failed", str(result.get("error")))

    new_status = (
        PaymentStatus.PARTIAL_REFUNDED
        if refund_amount < payment.amount_paise
        else PaymentStatus.REFUNDED
    )
    updated = await payments_repo.update_payment(
        db, payment_id=payment_id, status=new_status
    )
    if updated is None:
        raise PaymentError("payment_update_failed")
    return updated
