from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import DbSession
from app.api.v1.clinic.schemas import (
    AvailableSlotRead,
    ConsultationCancelRequest,
    ConsultationCancelResponse,
    ConsultationConfirmPaymentRequest,
    ConsultationJoinResponse,
    ConsultationRequestCreate,
    ConsultationRequestResponse,
    ConsultationRescheduleRequest,
    ConsultationRescheduleResponse,
    PatientConsultationListResponse,
    PatientConsultationRead,
    RazorpayOrderInfo,
    RecordingConsentResponse,
)
from app.core.audit import AuditContext, write_audit
from app.core.rbac import cross_user_404, get_patient_user
from app.db.enums import ActorRole, ConsultationStatus  # ConsultationStatus used for query filter
from app.repositories import consultations as consultations_repo
from app.services import consultation_service

router = APIRouter(tags=["consultations"])


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


async def _attach_doctor_display(
    db: DbSession, reads: list[PatientConsultationRead]
) -> None:
    """Populate doctor_name/doctor_specialty on patient consultation reads so the
    patient sees which doctor the coordinator assigned."""
    doctor_ids = {r.doctor_id for r in reads if r.doctor_id is not None}
    if not doctor_ids:
        return
    display = await consultations_repo.get_doctor_display_map(db, doctor_ids)
    for r in reads:
        if r.doctor_id is not None and r.doctor_id in display:
            r.doctor_name, r.doctor_specialty = display[r.doctor_id]


@router.get("/consultations/slots", response_model=list[AvailableSlotRead])
async def list_available_slots(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    doctor_id: uuid.UUID = Query(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
) -> list[AvailableSlotRead]:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    if date_to <= date_from:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_to must be after date_from")
    if (date_to - date_from) > timedelta(days=31):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date range must not exceed 31 days")

    has_consultation = await consultations_repo.patient_has_consultation_with_doctor(
        db, patient_user_id=user.id, doctor_id=doctor_id
    )
    if not has_consultation:
        await write_audit(
            db, ctx, action="list_available_slots", resource_type="availability",
            allowed=False, reason="no_consultation_with_doctor",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")

    slots = await consultations_repo.get_available_slots(
        db, doctor_id=doctor_id, date_from=date_from, date_to=date_to
    )
    await write_audit(db, ctx, action="list_available_slots", resource_type="availability", allowed=True)
    return [AvailableSlotRead.model_validate(s) for s in slots]


@router.get("/consultations", response_model=PatientConsultationListResponse)
async def list_consultations(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    upcoming: bool | None = Query(default=None),
    status_filter: ConsultationStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PatientConsultationListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    items, total = await consultations_repo.list_consultations_for_patient(
        db,
        patient_user_id=user.id,
        status=status_filter,
        upcoming=upcoming,
        page=page,
        page_size=page_size,
    )
    await write_audit(db, ctx, action="list_consultations", resource_type="consultation", allowed=True)

    pages = max(1, -(-total // page_size))
    reads = [PatientConsultationRead.model_validate(c) for c in items]
    await _attach_doctor_display(db, reads)
    return PatientConsultationListResponse(
        items=reads,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/consultations/{consultation_id}", response_model=PatientConsultationRead)
async def get_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PatientConsultationRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    consultation = await consultations_repo.get_consultation_for_patient(
        db, consultation_id=consultation_id, patient_user_id=user.id
    )
    consultation = await cross_user_404(
        db,
        consultation,
        ctx,
        action="view_consultation",
        resource_type="consultation",
        resource_id=consultation_id,
    )
    await write_audit(
        db, ctx, action="view_consultation",
        resource_type="consultation", resource_id=consultation_id, allowed=True
    )

    read = PatientConsultationRead.model_validate(consultation)
    await _attach_doctor_display(db, [read])
    # Surface the Razorpay order so the app can collect payment once a coordinator
    # has assigned the doctor + slot (status='scheduled', payment not yet captured).
    if (
        consultation.status == ConsultationStatus.SCHEDULED
        and consultation.payment_id is not None
    ):
        from app.db.enums import PaymentStatus
        from app.models.payment import Payment

        payment = await db.get(Payment, consultation.payment_id)
        if payment is not None and payment.status != PaymentStatus.PAID:
            read.payment = RazorpayOrderInfo(
                payment_id=payment.id,
                razorpay_order_id=payment.razorpay_order_id,
                amount_paise=payment.amount_paise,
                currency=payment.currency,
            )
    return read


@router.post("/consultations", response_model=ConsultationRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_consultation(
    body: ConsultationRequestCreate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ConsultationRequestResponse:
    """Submit a consultation request.

    Patients do not choose a doctor or a slot — a care coordinator assigns the
    right specialist based on the stated requirement. No payment is taken here;
    the patient pays to confirm once a doctor + time have been assigned.
    """
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        consultation = await consultation_service.request_consultation(
            db,
            patient_user_id=user.id,
            condition_category=body.condition_category,
            consultation_type=body.consultation_type.value,
            requirement_notes=body.requirement_notes,
            preferred_time_window=body.preferred_time_window,
            parent_consultation_id=body.parent_consultation_id,
        )
    except consultation_service.ConsultationError as exc:
        await write_audit(
            db, ctx, action="request_consultation",
            resource_type="consultation", allowed=False, reason=exc.code
        )
        await db.commit()
        code = exc.code
        if code == "patient_profile_not_found":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=code) from exc
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=code) from exc

    await write_audit(
        db, ctx, action="request_consultation",
        resource_type="consultation", resource_id=consultation.id, allowed=True
    )

    return ConsultationRequestResponse(
        consultation_id=consultation.id,
        status=consultation.status,
        condition_category=consultation.condition_category,
        consultation_type=consultation.consultation_type,
        requirement_notes=consultation.requirement_notes,
        preferred_time_window=consultation.preferred_time_window,
        created_at=consultation.created_at,
    )


@router.post("/consultations/{consultation_id}/confirm-payment", response_model=PatientConsultationRead)
async def confirm_payment(
    consultation_id: uuid.UUID,
    body: ConsultationConfirmPaymentRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PatientConsultationRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        consultation = await consultation_service.confirm_payment(
            db,
            consultation_id=consultation_id,
            patient_user_id=user.id,
            razorpay_payment_id=body.razorpay_payment_id,
            razorpay_order_id=body.razorpay_order_id,
            razorpay_signature=body.razorpay_signature,
        )
    except consultation_service.ConsultationError as exc:
        await write_audit(
            db, ctx, action="confirm_payment",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason=exc.code
        )
        await db.commit()
        code = exc.code
        if code == "consultation_not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found") from exc
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=code) from exc

    await write_audit(
        db, ctx, action="confirm_payment",
        resource_type="consultation", resource_id=consultation.id, allowed=True
    )
    read = PatientConsultationRead.model_validate(consultation)
    await _attach_doctor_display(db, [read])
    return read


@router.post("/consultations/{consultation_id}/cancel", response_model=ConsultationCancelResponse)
async def cancel_consultation(
    consultation_id: uuid.UUID,
    body: ConsultationCancelRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ConsultationCancelResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        consultation, refund_issued = await consultation_service.cancel_consultation(
            db,
            consultation_id=consultation_id,
            patient_user_id=user.id,
            reason=body.reason,
        )
    except consultation_service.ConsultationError as exc:
        await write_audit(
            db, ctx, action="cancel_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason=exc.code
        )
        await db.commit()
        code = exc.code
        if code == "consultation_not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found") from exc
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=code) from exc

    await write_audit(
        db, ctx, action="cancel_consultation",
        resource_type="consultation", resource_id=consultation.id, allowed=True
    )
    return ConsultationCancelResponse(
        consultation_id=consultation.id,
        status=consultation.status,
        refund_issued=refund_issued,
    )


@router.post(
    "/consultations/{consultation_id}/reschedule",
    response_model=ConsultationRescheduleResponse,
)
async def reschedule_consultation(
    consultation_id: uuid.UUID,
    body: ConsultationRescheduleRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ConsultationRescheduleResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        consultation = await consultation_service.reschedule_consultation(
            db,
            consultation_id=consultation_id,
            patient_user_id=user.id,
            slot_id=body.slot_id,
        )
    except consultation_service.ConsultationError as exc:
        # The service may have released the old slot before failing — undo that
        # first, then record the denial so the audit row survives the rollback.
        await db.rollback()
        await write_audit(
            db, ctx, action="reschedule_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason=exc.code,
        )
        await db.commit()
        if exc.code == "consultation_not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found") from exc
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.code) from exc

    await write_audit(
        db, ctx, action="reschedule_consultation",
        resource_type="consultation", resource_id=consultation.id, allowed=True,
    )
    return ConsultationRescheduleResponse(
        consultation_id=consultation.id,
        status=consultation.status,
        scheduled_start_at=consultation.scheduled_start_at,
        scheduled_end_at=consultation.scheduled_end_at,
    )


@router.get("/consultations/{consultation_id}/join", response_model=ConsultationJoinResponse)
async def patient_join_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ConsultationJoinResponse:
    from app.integrations import livekit_video
    from app.models.identity import User as UserModel
    from app.services import consultation_service

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    consultation = await consultations_repo.get_consultation_for_patient(
        db, consultation_id=consultation_id, patient_user_id=user.id
    )
    if consultation is None:
        await write_audit(
            db, ctx, action="join_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    # Gate on status first: a patient may join the waiting room once confirmed
    # (shortly before the doctor opens) or while in progress. Joining a
    # requested/scheduled/completed/cancelled/no-show consultation is rejected,
    # including re-joining after the call has ended (video_room_id is not cleared).
    # Checking before provisioning avoids creating a room for a non-joinable consult.
    if consultation.status not in (
        ConsultationStatus.CONFIRMED,
        ConsultationStatus.IN_PROGRESS,
    ):
        await write_audit(
            db, ctx, action="join_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="consultation_not_joinable",
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="consultation_not_joinable",
        )

    # TPG pre-flight (same hard gate the doctor's open_consultation enforces):
    # the consult cannot legally proceed unless the patient's identity is verified
    # and an active telemedicine consent is on file. Checking here too means the
    # patient gets an actionable reason instead of silently sitting in a room the
    # doctor can never open. Checked before provisioning so a blocked join never
    # spins up a room.
    from app.db.enums import ConsentType
    from app.repositories import consent as consent_repo

    if not user.phone_verified:
        await write_audit(
            db, ctx, action="join_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="identity_not_verified",
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="identity_not_verified"
        )

    telemedicine_consent = await consent_repo.get_active_consent(
        db, user_id=user.id, consent_type=ConsentType.TELEMEDICINE
    )
    if telemedicine_consent is None:
        await write_audit(
            db, ctx, action="join_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="telemedicine_consent_missing",
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="telemedicine_consent_missing"
        )

    room_id = consultation.video_room_id
    if room_id is None:
        # Provision on demand so a not-yet-provisioned room doesn't dead-end the
        # patient with a 503 (mirrors the doctor join path). Only a genuine
        # provider failure still yields a retryable 503.
        try:
            room_id = await consultation_service.ensure_video_room(
                db, consultation_id=consultation.id
            )
        except Exception as exc:
            await write_audit(
                db, ctx, action="join_consultation",
                resource_type="consultation", resource_id=consultation_id,
                allowed=False, reason="room_provisioning_failed",
            )
            await db.commit()
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="video_room_not_ready",
            ) from exc

    token = livekit_video.generate_patient_token(
        room_id=room_id,
        user_id=str(user.id),
    )
    await write_audit(
        db, ctx, action="join_consultation",
        resource_type="consultation", resource_id=consultation_id, allowed=True
    )
    return ConsultationJoinResponse(room_id=room_id, token=token)


@router.post(
    "/consultations/{consultation_id}/recording-consent",
    response_model=RecordingConsentResponse,
    status_code=status.HTTP_200_OK,
)
async def capture_recording_consent(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> RecordingConsentResponse:
    import hashlib

    from app.db.enums import ConsentType
    from app.models.consent import ConsentRecord
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    consultation = await consultations_repo.get_consultation_for_patient(
        db, consultation_id=consultation_id, patient_user_id=user.id
    )
    if consultation is None:
        await write_audit(
            db, ctx, action="capture_recording_consent",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    recording_consent_text = (
        "I consent to this telemedicine consultation being recorded. "
        "The recording will be stored securely and used only for my care."
    )
    consent_text_hash = hashlib.sha256(recording_consent_text.encode()).hexdigest()

    if not consultation.recording_consent:
        from datetime import UTC
        from datetime import datetime as dt
        consultation.recording_consent = True
        db.add(
            ConsentRecord(
                user_id=user.id,
                consent_type=ConsentType.RECORDING,
                version="1.0",
                granted=True,
                granted_at=dt.now(UTC),
                ip_address=request.client.host if request.client else None,
                consent_text_hash=consent_text_hash,
            )
        )

    await write_audit(
        db, ctx, action="capture_recording_consent",
        resource_type="consultation", resource_id=consultation_id, allowed=True
    )
    return RecordingConsentResponse(
        consultation_id=consultation.id,
        recording_consent=consultation.recording_consent,
    )
