from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ConsultationStatus, PaymentStatus
from app.models.clinic import Consultation
from app.models.payment import Payment
from app.repositories import consultations as consultations_repo
from app.repositories import payments as payments_repo
from app.services import payment_service

CANCELLATION_REFUND_WINDOW_HOURS = 24


class ConsultationError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


async def book_consultation(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    doctor_id: uuid.UUID,
    slot_id: uuid.UUID,
    condition_category: str,
    consultation_type: str,
    consultation_fee_paise: int,
    notes: dict[str, object] | None = None,
) -> tuple[Consultation, Payment]:
    """Lock slot → create consultation → create Razorpay order.

    Returns (consultation, payment) within the same transaction.
    The caller commits after this returns.
    """
    patient = await consultations_repo.get_patient_record(db, user_id=patient_user_id)
    if patient is None:
        raise ConsultationError("patient_profile_not_found")

    # Fetch slot metadata before locking (to get scheduled times)
    from sqlalchemy import select

    from app.models.doctor import Availability

    slot_result = await db.execute(
        select(Availability).where(Availability.id == slot_id)
    )
    slot_ref = slot_result.scalar_one_or_none()
    if slot_ref is None:
        raise ConsultationError("slot_not_found")

    consultation = await consultations_repo.create_consultation(
        db,
        patient_id=patient.id,
        doctor_id=doctor_id,
        condition_category=condition_category,
        consultation_type=consultation_type,
        scheduled_start_at=slot_ref.slot_start,
        scheduled_end_at=slot_ref.slot_end,
        consultation_fee_paise=consultation_fee_paise,
    )

    # Lock and claim the slot — must happen after consultation row exists
    # so the slot can reference it.
    booked = await consultations_repo.lock_and_book_slot(
        db, slot_id=slot_id, consultation_id=consultation.id
    )
    if booked is None:
        raise ConsultationError("slot_not_available")

    payment = await payment_service.create_order(
        db,
        user_id=patient_user_id,
        amount_paise=consultation_fee_paise,
        consultation_id=consultation.id,
        notes=notes or {"consultation_id": str(consultation.id)},
    )

    # Link payment back to consultation
    await consultations_repo.update_consultation(
        db, consultation_id=consultation.id, payment_id=payment.id
    )
    consultation.payment_id = payment.id

    return consultation, payment


async def confirm_payment(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    patient_user_id: uuid.UUID,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    razorpay_signature: str,
) -> Consultation:
    """Verify Razorpay signature → mark payment paid → confirm consultation."""
    consultation = await consultations_repo.get_consultation_for_patient(
        db, consultation_id=consultation_id, patient_user_id=patient_user_id
    )
    if consultation is None:
        raise ConsultationError("consultation_not_found")

    if consultation.status == ConsultationStatus.CONFIRMED:
        return consultation  # idempotent

    if consultation.status not in (ConsultationStatus.SCHEDULED,):
        raise ConsultationError("consultation_not_confirmable")

    if consultation.payment_id is None:
        raise ConsultationError("payment_not_linked")

    payment = await payments_repo.get_payment_for_user(
        db,
        payment_id=consultation.payment_id,
        user_id=patient_user_id,
    )
    if payment is None:
        raise ConsultationError("payment_not_found")

    if payment.status != PaymentStatus.PAID:
        try:
            payment = await payment_service.verify_and_capture(
                db,
                payment_id=payment.id,
                user_id=patient_user_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
                razorpay_signature=razorpay_signature,
            )
        except payment_service.PaymentError as exc:
            raise ConsultationError(f"payment_verification_failed:{exc.code}") from exc

    updated = await consultations_repo.update_consultation(
        db,
        consultation_id=consultation.id,
        status=ConsultationStatus.CONFIRMED,
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

    # Dispatch appointment confirmation notifications (fire-and-forget Celery tasks)
    from app.services.notifications import notify_appointment_confirmed
    await notify_appointment_confirmed(db, consultation_id=consultation.id)

    return updated


async def cancel_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    patient_user_id: uuid.UUID,
    reason: str = "",
) -> tuple[Consultation, bool]:
    """Cancel a consultation and apply the refund policy.

    Returns (consultation, refund_issued).
    Refund is issued when the cancellation is >CANCELLATION_REFUND_WINDOW_HOURS before start.
    """
    consultation = await consultations_repo.get_consultation_for_patient(
        db, consultation_id=consultation_id, patient_user_id=patient_user_id
    )
    if consultation is None:
        raise ConsultationError("consultation_not_found")

    if consultation.status not in (ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED):
        raise ConsultationError("consultation_not_cancellable")

    now = datetime.now(UTC)
    hours_until = (consultation.scheduled_start_at - now).total_seconds() / 3600
    eligible_for_refund = hours_until > CANCELLATION_REFUND_WINDOW_HOURS

    refund_issued = False
    if eligible_for_refund and consultation.payment_id is not None:
        payment = await payments_repo.get_payment_for_user(
            db,
            payment_id=consultation.payment_id,
            user_id=patient_user_id,
        )
        if payment is not None and payment.status == PaymentStatus.PAID:
            try:
                await payment_service.initiate_refund(
                    db,
                    payment_id=payment.id,
                    user_id=patient_user_id,
                )
                refund_issued = True
            except payment_service.PaymentError:
                # Log but don't block the cancellation
                refund_issued = False

    # Release availability slot back to open
    await consultations_repo.release_slot(db, consultation_id=consultation.id)

    updated = await consultations_repo.update_consultation(
        db,
        consultation_id=consultation.id,
        status=ConsultationStatus.CANCELLED,
        cancellation_reason=reason or None,
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

    return updated, refund_issued
