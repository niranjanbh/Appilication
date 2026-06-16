from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    ConsentType,
    ConsultationStatus,
    ConsultationType,
    DoctorStatus,
    PaymentStatus,
)
from app.models.clinic import Consultation
from app.models.doctor import Doctor
from app.models.payment import Payment
from app.repositories import consent as consent_repo
from app.repositories import consultations as consultations_repo
from app.repositories import payments as payments_repo
from app.services import payment_service

CANCELLATION_REFUND_WINDOW_HOURS = 24


class ConsultationError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


# Canonical consultation lifecycle (staff-rbac-spec.md §5). Only the open/complete
# transitions added in P34 consult this table; the longer-standing transitions in
# confirm_payment/admin_cancel_consultation/cancel_consultation/admin_mark_no_show encode
# equivalent checks ad-hoc and are consistent with it.
_ALLOWED_TRANSITIONS: dict[ConsultationStatus, frozenset[ConsultationStatus]] = {
    ConsultationStatus.SCHEDULED: frozenset(
        {ConsultationStatus.CONFIRMED, ConsultationStatus.CANCELLED, ConsultationStatus.NO_SHOW}
    ),
    ConsultationStatus.CONFIRMED: frozenset(
        {ConsultationStatus.IN_PROGRESS, ConsultationStatus.CANCELLED, ConsultationStatus.NO_SHOW}
    ),
    ConsultationStatus.IN_PROGRESS: frozenset({ConsultationStatus.COMPLETED}),
    ConsultationStatus.COMPLETED: frozenset(),
    ConsultationStatus.CANCELLED: frozenset(),
    ConsultationStatus.NO_SHOW: frozenset(),
}


def _assert_transition(
    current: ConsultationStatus,
    new: ConsultationStatus,
    *,
    error_code: str = "invalid_transition",
) -> None:
    if new not in _ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise ConsultationError(error_code)


async def book_consultation(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    doctor_id: uuid.UUID,
    slot_id: uuid.UUID,
    condition_category: str,
    consultation_type: str,
    notes: dict[str, object] | None = None,
    coupon_code: str | None = None,
) -> tuple[Consultation, Payment]:
    """Lock slot → create consultation → create Razorpay order.

    The fee is resolved server-side from pricing config (never client-supplied).
    Returns (consultation, payment) within the same transaction.
    The caller commits after this returns.
    """
    from app.services import coupon_service, pricing_service
    from app.services.coupon_service import CouponError

    patient = await consultations_repo.get_patient_record(db, user_id=patient_user_id)
    if patient is None:
        raise ConsultationError("patient_profile_not_found")

    doctor = await db.get(Doctor, doctor_id)
    if doctor is None or doctor.status != DoctorStatus.ACTIVE:
        raise ConsultationError("doctor_not_available")

    consultation_fee_paise = await pricing_service.get_consultation_fee_paise(
        db,
        condition_category=condition_category,
        consultation_type=ConsultationType(consultation_type),
    )

    coupon_id: uuid.UUID | None = None
    discount_paise = 0
    if coupon_code is not None:
        try:
            coupon, discount_paise = await coupon_service.validate_and_apply_coupon(
                db, code=coupon_code, fee_paise=consultation_fee_paise
            )
            coupon_id = coupon.id
        except CouponError as exc:
            raise ConsultationError(exc.code) from exc

    net_amount_paise = consultation_fee_paise - discount_paise

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
        coupon_id=coupon_id,
        discount_paise=discount_paise,
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
        amount_paise=net_amount_paise,
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


async def admin_cancel_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    reason: str,
) -> tuple[Consultation, bool]:
    """Operational cancellation by a super admin (doctor no-show, emergencies).

    Unlike the patient flow there is no refund window: if the consultation was
    paid, the patient is always refunded in full. Returns (consultation,
    refund_issued).
    """
    from app.models.payment import Payment

    consultation = await db.get(Consultation, consultation_id)
    if consultation is None or consultation.deleted_at is not None:
        raise ConsultationError("consultation_not_found")

    if consultation.status not in (ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED):
        raise ConsultationError("consultation_not_cancellable")

    refund_issued = False
    if consultation.payment_id is not None:
        payment = await db.get(Payment, consultation.payment_id)
        if payment is not None and payment.status == PaymentStatus.PAID:
            try:
                await payment_service.initiate_refund(
                    db,
                    payment_id=payment.id,
                    user_id=payment.user_id,
                )
                refund_issued = True
            except payment_service.PaymentError:
                # Razorpay hiccup must not block the cancellation; the refund
                # can be retried from Razorpay's dashboard.
                refund_issued = False

    await consultations_repo.release_slot(db, consultation_id=consultation.id)

    updated = await consultations_repo.update_consultation(
        db,
        consultation_id=consultation.id,
        status=ConsultationStatus.CANCELLED,
        cancellation_reason=f"[ADMIN] {reason[:480]}",
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

    return updated, refund_issued


async def admin_reassign_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    slot_id: uuid.UUID,
) -> Consultation:
    """Move a consultation to a new slot — possibly a different doctor.

    For doctor unavailability: payment and status carry over, so the patient
    is not pushed through a refund + rebook cycle.
    """
    consultation = await db.get(Consultation, consultation_id)
    if consultation is None or consultation.deleted_at is not None:
        raise ConsultationError("consultation_not_found")

    if consultation.status not in (ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED):
        raise ConsultationError("consultation_not_reassignable")

    # Free the old slot first: if claiming the new one fails we raise, and the
    # transaction rollback restores the old booking.
    await consultations_repo.release_slot(db, consultation_id=consultation_id)

    slot = await consultations_repo.lock_and_book_slot(
        db, slot_id=slot_id, consultation_id=consultation_id
    )
    if slot is None:
        raise ConsultationError("slot_not_available")

    updated = await consultations_repo.update_consultation(
        db,
        consultation_id=consultation_id,
        doctor_id=slot.doctor_id,
        scheduled_start_at=slot.slot_start,
        scheduled_end_at=slot.slot_end,
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

    return updated


async def admin_mark_no_show(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> Consultation:
    """Mark a past consultation as a patient no-show. No refund — the slot was
    held and the doctor was present. Refund-worthy cases (doctor no-show) go
    through admin_cancel_consultation instead.
    """
    consultation = await db.get(Consultation, consultation_id)
    if consultation is None or consultation.deleted_at is not None:
        raise ConsultationError("consultation_not_found")

    if consultation.status not in (ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED):
        raise ConsultationError("consultation_not_markable")

    if consultation.scheduled_start_at > datetime.now(UTC):
        raise ConsultationError("consultation_not_started_yet")

    updated = await consultations_repo.update_consultation(
        db,
        consultation_id=consultation_id,
        status=ConsultationStatus.NO_SHOW,
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

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


async def open_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> Consultation:
    """TPG hard gate: doctor "opens" a consult (CONFIRMED -> IN_PROGRESS).

    Verifies the patient's identity-verification status and an active TELEMEDICINE
    consent before transitioning, per the Telemedicine Practice Guidelines 2020
    (the RMP bears this obligation). Idempotent if the consult is already IN_PROGRESS
    (doctor reconnect).
    """
    consultation = await consultations_repo.get_consultation_for_doctor(
        db, consultation_id=consultation_id, doctor_id=doctor_id
    )
    if consultation is None:
        raise ConsultationError("consultation_not_found")

    if consultation.status == ConsultationStatus.IN_PROGRESS:
        return consultation

    _assert_transition(
        consultation.status,
        ConsultationStatus.IN_PROGRESS,
        error_code="consultation_not_open_eligible",
    )

    patient_user = await consultations_repo.get_patient_user_for_consultation(
        db, patient_id=consultation.patient_id
    )
    if patient_user is None or not patient_user.phone_verified:
        raise ConsultationError("identity_not_verified")

    consent = await consent_repo.get_active_consent(
        db, user_id=patient_user.id, consent_type=ConsentType.TELEMEDICINE
    )
    if consent is None:
        raise ConsultationError("telemedicine_consent_missing")

    updated = await consultations_repo.update_consultation(
        db,
        consultation_id=consultation.id,
        status=ConsultationStatus.IN_PROGRESS,
        actual_start_at=datetime.now(UTC),
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

    return updated


async def complete_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> Consultation:
    """IN_PROGRESS -> COMPLETED, stamping actual_end_at."""
    consultation = await consultations_repo.get_consultation_for_doctor(
        db, consultation_id=consultation_id, doctor_id=doctor_id
    )
    if consultation is None:
        raise ConsultationError("consultation_not_found")

    _assert_transition(
        consultation.status,
        ConsultationStatus.COMPLETED,
        error_code="consultation_not_in_progress",
    )

    updated = await consultations_repo.update_consultation(
        db,
        consultation_id=consultation.id,
        status=ConsultationStatus.COMPLETED,
        actual_end_at=datetime.now(UTC),
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

    return updated
