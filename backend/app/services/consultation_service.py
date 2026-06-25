from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
from app.repositories import patients as patients_repo
from app.repositories import payments as payments_repo
from app.services import payment_service

logger = structlog.get_logger(__name__)

CANCELLATION_REFUND_WINDOW_HOURS = 24
RESCHEDULE_NOTICE_WINDOW_HOURS = 24


class ConsultationError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


# Canonical consultation lifecycle (staff-rbac-spec.md §5). Only the open/complete
# transitions added in P34 consult this table; the longer-standing transitions in
# confirm_payment/admin_cancel_consultation/cancel_consultation/admin_mark_no_show encode
# equivalent checks ad-hoc and are consistent with it.
_ALLOWED_TRANSITIONS: dict[ConsultationStatus, frozenset[ConsultationStatus]] = {
    ConsultationStatus.REQUESTED: frozenset(
        {ConsultationStatus.SCHEDULED, ConsultationStatus.CANCELLED}
    ),
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


async def request_consultation(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    condition_category: str,
    consultation_type: str,
    requirement_notes: str | None = None,
    preferred_time_window: str | None = None,
    parent_consultation_id: uuid.UUID | None = None,
) -> Consultation:
    """Patient submits a consultation request — no doctor, slot, or payment.

    The request is routed to the patient's assigned coordinator (if any), who
    later assigns a doctor + slot via ``assign_consultation``. A non-null
    ``parent_consultation_id`` marks this as a follow-up to a prior consultation.
    """
    patient = await consultations_repo.get_patient_record(db, user_id=patient_user_id)
    if patient is None:
        raise ConsultationError("patient_profile_not_found")

    is_follow_up = (
        consultation_type == ConsultationType.FOLLOW_UP.value
        and parent_consultation_id is not None
    )

    # Validate the parent reference up front: it must exist, belong to THIS patient,
    # and be a completed consultation. Cross-user / missing parents return the same
    # error (security rule #1: no enumeration via differing responses).
    if parent_consultation_id is not None:
        parent = await consultations_repo.get_consultation_for_patient_by_id(
            db, consultation_id=parent_consultation_id, patient_id=patient.id
        )
        if parent is None:
            raise ConsultationError("parent_consultation_not_found")
        if parent.status != ConsultationStatus.COMPLETED:
            raise ConsultationError("parent_consultation_not_completed")

    # A patient may not hold two active requests for the same condition. Follow-ups
    # to a completed consultation are exempt — they are a legitimate continuation.
    if not is_follow_up:
        has_active = await consultations_repo.has_active_consultation_for_condition(
            db, patient_id=patient.id, condition_category=condition_category
        )
        if has_active:
            raise ConsultationError("active_consultation_exists")

    # Per-consultation load balancing: route this request to the active
    # coordinator currently handling the fewest patients (None if none exist).
    coordinator_id = await patients_repo.route_consultation_to_coordinator(db, patient)

    # The read-check above is a fast path for a clean UX error, but it has a TOCTOU
    # gap: two concurrent requests can both read "no active consultation" and both
    # reach this insert. The partial unique index
    # (uq_active_consultation_per_condition) is the database backstop — the loser of
    # the race trips it and we surface the same clean error. Follow-ups are excluded
    # from the index's predicate via condition/status, so they are unaffected.
    try:
        consultation = await consultations_repo.create_consultation_request(
            db,
            patient_id=patient.id,
            coordinator_id=coordinator_id,
            condition_category=condition_category,
            consultation_type=consultation_type,
            requirement_notes=requirement_notes,
            preferred_time_window=preferred_time_window,
            parent_consultation_id=parent_consultation_id,
        )
    except IntegrityError as exc:
        raise ConsultationError("active_consultation_exists") from exc
    return consultation


async def assign_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    coordinator_id: uuid.UUID,
    slot_id: uuid.UUID,
    coupon_code: str | None = None,
) -> tuple[Consultation, Payment]:
    """Coordinator assigns a doctor + slot to a REQUESTED consultation.

    Scoped to the coordinator's assigned patients. Locks the slot, prices the fee
    server-side, creates the Razorpay order the patient will pay, and moves the
    consultation to SCHEDULED. Returns (consultation, payment).
    The caller commits after this returns.
    """
    from sqlalchemy import select

    from app.models.doctor import Availability
    from app.repositories import coordinator_portal as coord_repo
    from app.services import coupon_service, pricing_service
    from app.services.coupon_service import CouponError

    # Lock the consultation row before checking status so concurrent assignment
    # attempts serialize: only one transaction can see REQUESTED and proceed.
    consultation = await consultations_repo.get_consultation_for_update(
        db, consultation_id=consultation_id
    )
    if consultation is None:
        raise ConsultationError("consultation_not_found")

    if consultation.status != ConsultationStatus.REQUESTED:
        raise ConsultationError("consultation_not_assignable")

    # Resource scope: the request's patient must be assigned to this coordinator.
    assignment = await coord_repo.get_assigned_patient(
        db, coordinator_id=coordinator_id, patient_id=consultation.patient_id
    )
    if assignment is None:
        raise ConsultationError("patient_not_assigned")

    slot_ref = (
        await db.execute(select(Availability).where(Availability.id == slot_id))
    ).scalar_one_or_none()
    if slot_ref is None:
        raise ConsultationError("slot_not_found")

    doctor = await db.get(Doctor, slot_ref.doctor_id)
    if doctor is None or doctor.status != DoctorStatus.ACTIVE:
        raise ConsultationError("doctor_not_available")

    consultation_fee_paise = await pricing_service.get_consultation_fee_paise(
        db,
        condition_category=consultation.condition_category,
        consultation_type=ConsultationType(consultation.consultation_type),
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

    net_amount_paise = max(0, consultation_fee_paise - discount_paise)
    if net_amount_paise == 0:
        raise ConsultationError("fully_discounted_not_supported")

    # Claim the slot before pricing-side effects so a lost race rolls everything back.
    booked = await consultations_repo.lock_and_book_slot(
        db, slot_id=slot_id, consultation_id=consultation.id
    )
    if booked is None:
        raise ConsultationError("slot_not_available")

    patient_user = await consultations_repo.get_patient_user_for_consultation(
        db, patient_id=consultation.patient_id
    )
    if patient_user is None:
        raise ConsultationError("patient_profile_not_found")

    payment = await payment_service.create_order(
        db,
        user_id=patient_user.id,
        amount_paise=net_amount_paise,
        consultation_id=consultation.id,
        notes={"consultation_id": str(consultation.id)},
    )

    # The Razorpay order now exists externally. If the DB update below fails and
    # the transaction rolls back, the order becomes orphaned. Log it so ops can
    # reconcile via the Razorpay dashboard.
    try:
        updated = await consultations_repo.update_consultation(
            db,
            consultation_id=consultation.id,
            doctor_id=slot_ref.doctor_id,
            coordinator_id=coordinator_id,
            scheduled_start_at=slot_ref.slot_start,
            scheduled_end_at=slot_ref.slot_end,
            consultation_fee_paise=consultation_fee_paise,
            coupon_id=coupon_id,
            discount_paise=discount_paise,
            payment_id=payment.id,
            status=ConsultationStatus.SCHEDULED,
        )
        if updated is None:
            raise ConsultationError("consultation_update_failed")
    except Exception:
        logger.error(
            "orphaned_razorpay_order",
            razorpay_order_id=payment.razorpay_order_id,
            consultation_id=str(consultation.id),
            payment_id=str(payment.id),
        )
        raise

    from app.services.notifications import notify_doctor_assigned
    await notify_doctor_assigned(db, consultation_id=updated.id)

    return updated, payment


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
            except payment_service.PaymentError as exc:
                # Razorpay hiccup must not block the cancellation; the refund
                # can be retried from Razorpay's dashboard. The payment row stays
                # PAID (not REFUNDED), preserving a durable record of money owed.
                refund_issued = False
                logger.error(
                    "consultation_refund_failed",
                    consultation_id=str(consultation.id),
                    payment_id=str(payment.id),
                    error_code=exc.code,
                    cancel_origin="admin",
                )

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

    await consultations_repo.release_slot(db, consultation_id=consultation.id)

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

    # A patient may withdraw a not-yet-assigned request, or cancel a scheduled/
    # confirmed appointment (subject to the refund window below).
    if consultation.status not in (
        ConsultationStatus.REQUESTED,
        ConsultationStatus.SCHEDULED,
        ConsultationStatus.CONFIRMED,
    ):
        raise ConsultationError("consultation_not_cancellable")

    now = datetime.now(UTC)
    # A 'requested' consultation has no slot and no payment — nothing to refund.
    if consultation.scheduled_start_at is None:
        eligible_for_refund = False
    else:
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
            except payment_service.PaymentError as exc:
                # Don't block the cancellation; the payment row stays PAID (not
                # REFUNDED), preserving a durable record of money owed so the
                # refund can be retried from Razorpay's dashboard.
                refund_issued = False
                logger.error(
                    "consultation_refund_failed",
                    consultation_id=str(consultation.id),
                    payment_id=str(payment.id),
                    error_code=exc.code,
                    cancel_origin="patient",
                )

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


async def reschedule_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    patient_user_id: uuid.UUID,
    slot_id: uuid.UUID,
) -> Consultation:
    """Move a patient's consultation to a new slot with the same doctor.

    Payment and status carry over — the patient is not pushed through a refund +
    rebook cycle. Constrained to the existing doctor; switching doctors is a
    re-triage concern handled by cancel + rebook. Returns the updated consultation.
    """
    from sqlalchemy import select

    from app.models.doctor import Availability

    consultation = await consultations_repo.get_consultation_for_patient(
        db, consultation_id=consultation_id, patient_user_id=patient_user_id
    )
    if consultation is None:
        raise ConsultationError("consultation_not_found")

    if consultation.status not in (ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED):
        raise ConsultationError("consultation_not_reschedulable")

    if consultation.scheduled_start_at is None:
        raise ConsultationError("consultation_not_reschedulable")

    now = datetime.now(UTC)
    hours_until = (consultation.scheduled_start_at - now).total_seconds() / 3600
    if hours_until <= RESCHEDULE_NOTICE_WINDOW_HOURS:
        raise ConsultationError("reschedule_window_closed")

    # Verify the target slot exists and belongs to the same doctor before touching
    # the current booking.
    slot_result = await db.execute(select(Availability).where(Availability.id == slot_id))
    slot_ref = slot_result.scalar_one_or_none()
    if slot_ref is None:
        raise ConsultationError("slot_not_found")
    if slot_ref.doctor_id != consultation.doctor_id:
        raise ConsultationError("slot_wrong_doctor")
    if slot_ref.slot_start <= datetime.now(UTC):
        raise ConsultationError("slot_in_past")

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
        scheduled_start_at=slot.slot_start,
        scheduled_end_at=slot.slot_end,
        # Drop any provisioned room so a stale 100ms room can't be reused.
        video_room_id=None,
        # Reset recording consent so the patient is re-prompted on the new call
        # (security rule #20: consent is captured per consultation, no blanket recording).
        recording_consent=False,
        # Clear any stale egress id alongside the consent reset.
        recording_egress_id=None,
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

    return updated


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

    # A consultation cannot be completed without at least one doctor note on record.
    has_notes = await consultations_repo.has_doctor_notes(db, consultation_id=consultation.id)
    if not has_notes:
        raise ConsultationError("doctor_notes_required")

    if consultation.actual_start_at is None:
        raise ConsultationError("consultation_not_started")

    # Stop the S3 egress recording, if one is running, before marking complete.
    # A LiveKit hiccup must not block completion — the recording also auto-stops
    # on room empty-timeout — but stopping explicitly honours per-consultation
    # consent boundaries (security rule #20) and curbs runaway egress cost.
    egress_id = consultation.recording_egress_id
    if egress_id is not None:
        from app.integrations import livekit_video

        try:
            await livekit_video.stop_recording(egress_id=egress_id)
        except Exception:
            logger.warning(
                "consultation.recording_stop_failed",
                consultation_id=str(consultation.id),
            )

    updated = await consultations_repo.update_consultation(
        db,
        consultation_id=consultation.id,
        status=ConsultationStatus.COMPLETED,
        actual_end_at=datetime.now(UTC),
        recording_egress_id=None,
    )
    if updated is None:
        raise ConsultationError("consultation_update_failed")

    return updated


async def ensure_video_room(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> str:
    """Return the consultation's video room id, provisioning one on demand if absent.

    The beat task pre-warms rooms ~15 min before start, but that window is only a
    best-effort optimization: a consult created shortly before its start, or a join
    after the start time when beat was down, would otherwise leave the room
    unprovisioned and the call permanently un-joinable (a doctor unable to start a
    paid consultation). Provisioning here, on the join path, closes that gap.

    Idempotent: the LiveKit room name is deterministic per consultation, so a doctor
    and patient joining near-simultaneously converge on the same room id —
    ``set_video_room_if_absent`` keeps the first writer's value.

    Raises on provider failure; the caller maps that to a retryable 503.
    """
    from app.integrations import livekit_video

    consultation = await db.get(Consultation, consultation_id)
    if consultation is not None and consultation.video_room_id is not None:
        return consultation.video_room_id

    room_id = await livekit_video.create_room(
        consultation_id=str(consultation_id),
        max_participants=consultation.video_max_participants if consultation else None,
    )
    effective = await consultations_repo.set_video_room_if_absent(
        db, consultation_id=consultation_id, video_room_id=room_id
    )
    return effective or room_id


def _clamp_max_participants(requested: int | None) -> int:
    """Resolve a requested room size to a safe value in [2, cap], default if unset."""
    if requested is None:
        return settings.video_default_max_participants
    return max(2, min(requested, settings.video_max_participants_cap))


async def create_on_demand_consultation(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    condition_category: str,
    consultation_type: str = ConsultationType.INITIAL.value,
    coordinator_id: uuid.UUID | None = None,
    max_participants: int | None = None,
    duration_minutes: int = 30,
) -> Consultation:
    """Staff-initiated instant consultation between a doctor and a patient.

    Creates a CONFIRMED, zero-fee consultation scheduled for now, provisions the
    video room immediately (sized to ``max_participants``, clamped to the platform
    cap), and notifies both parties. No payment and no availability slot are
    consumed.

    The TPG hard gate still applies downstream: the doctor cannot OPEN the call
    (``open_consultation``) until the patient has a verified identity and an active
    telemedicine consent. On-demand creation does not bypass that clinical gate.

    Raises ``doctor_not_available`` if the doctor isn't ACTIVE, and
    ``active_consultation_exists`` if the patient already has an open consultation
    for this condition (the partial unique index backstop).
    """
    doctor = await db.get(Doctor, doctor_id)
    if doctor is None or doctor.status != DoctorStatus.ACTIVE:
        raise ConsultationError("doctor_not_available")

    cap = _clamp_max_participants(max_participants)
    now = datetime.now(UTC)

    try:
        consultation = await consultations_repo.create_adhoc_consultation(
            db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            coordinator_id=coordinator_id,
            condition_category=condition_category,
            consultation_type=consultation_type,
            scheduled_start_at=now,
            scheduled_end_at=now + timedelta(minutes=duration_minutes),
            video_max_participants=cap,
        )
    except IntegrityError as exc:
        raise ConsultationError("active_consultation_exists") from exc

    # Provision the room now so both parties can join immediately.
    await ensure_video_room(db, consultation_id=consultation.id)

    from app.services.notifications import notify_on_demand_consultation
    await notify_on_demand_consultation(db, consultation_id=consultation.id)

    return consultation
