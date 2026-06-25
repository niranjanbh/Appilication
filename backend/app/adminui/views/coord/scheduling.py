"""Coordinator scheduling views — book and cancel on behalf of assigned patients."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_coord_session
from app.adminui.schemas import coordinator as coord_schemas
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, PaymentStatus
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo
from app.repositories import coordinator_portal as coord_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")
logger = structlog.get_logger(__name__)

_CONDITIONS = [
    "thyroid", "weight", "pcos", "skin_hair",
    "mens_intimate", "hormones_trt", "longevity",
]


def _ctx(request: Request, coord: object) -> AuditContext:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)
    return AuditContext(
        actor_user_id=coord.id,
        actor_role=ActorRole.COORDINATOR,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/scheduling", response_class=HTMLResponse)
async def scheduling_view(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    days_ahead: int = 7,
) -> HTMLResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        return templates.TemplateResponse(
            request, "coord/scheduling.html",
            {"coord": coord, "slots": [], "patients": [], "doctors": [],
             "conditions": _CONDITIONS, "error": "No coordinator profile."},
        )

    now = datetime.now(UTC)
    date_to = now + timedelta(days=max(1, min(days_ahead, 30)))
    slots = await coord_repo.list_available_slots(db, date_from=now, date_to=date_to)
    patients = await coord_repo.list_assigned_patients(db, coordinator_id=coordinator.id)
    upcoming = await coord_repo.list_upcoming_consultations(
        db, coordinator_id=coordinator.id
    )
    requests = await coord_repo.list_requested_consultations(
        db, coordinator_id=coordinator.id
    )
    doctors = await admin_repo.list_active_doctors(db)

    return templates.TemplateResponse(
        request,
        "coord/scheduling.html",
        {
            "coord": coord,
            "coordinator": coordinator,
            # Slots carry doctor scheduling data only — no patient clinical content.
            "slots": slots,
            "patients": coord_schemas.patient_pairs(patients),
            "doctors": doctors,
            "upcoming": coord_schemas.consultation_user_user_triples(upcoming),
            "requests": coord_schemas.consultation_user_pairs(requests),
            "conditions": _CONDITIONS,
            "days_ahead": days_ahead,
            "error": None,
        },
    )


@router.post("/scheduling/book")
async def book_consultation(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    patient_id: uuid.UUID = Form(...),
    slot_id: uuid.UUID = Form(...),
    condition_category: str = Form(...),
) -> RedirectResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    if condition_category not in _CONDITIONS:
        return RedirectResponse(
            url="/coord/scheduling?error=invalid_condition",
            status_code=status.HTTP_302_FOUND,
        )

    from app.db.enums import ConsultationType
    from app.services import pricing_service

    consultation_fee_paise = await pricing_service.get_consultation_fee_paise(
        db,
        condition_category=condition_category,
        consultation_type=ConsultationType.INITIAL,
    )
    consultation = await coord_repo.book_consultation_for_patient(
        db,
        coordinator_id=coordinator.id,
        patient_id=patient_id,
        slot_id=slot_id,
        condition_category=condition_category,
        consultation_fee_paise=consultation_fee_paise,
    )

    allowed = consultation is not None
    await write_audit(
        db, ctx, action="coord_book_consultation", resource_type="consultation",
        resource_id=consultation.id if consultation else None,
        allowed=allowed,
        reason=None if allowed else "slot_unavailable_or_patient_not_assigned",
    )

    if not allowed:
        return RedirectResponse(
            url="/coord/scheduling?error=slot_unavailable",
            status_code=status.HTTP_302_FOUND,
        )

    # Notify patient (best-effort — a notification failure must not fail the booking).
    assert consultation is not None  # guaranteed by the `allowed` guard above
    await _notify_patient_booked(db, consultation_id=consultation.id)

    return RedirectResponse(url="/coord/scheduling?success=booked", status_code=status.HTTP_302_FOUND)


@router.post("/scheduling/on-demand")
async def create_on_demand_consultation(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    patient_id: uuid.UUID = Form(...),
    doctor_id: uuid.UUID = Form(...),
    condition_category: str = Form(...),
    max_participants: int = Form(6),
) -> RedirectResponse:
    """Start an instant video consultation between an assigned patient and a doctor.

    Scoped to the coordinator's assigned patients: an unassigned patient yields the
    same redirect as 'not found' (no enumeration). Free and CONFIRMED on creation;
    the room is provisioned immediately and both parties are notified to join.
    """
    from app.models.identity import User as UserModel
    from app.services import consultation_service

    assert isinstance(coord, UserModel)
    ctx = _ctx(request, coord)

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    if condition_category not in _CONDITIONS:
        return RedirectResponse(
            url="/coord/scheduling?error=invalid_condition",
            status_code=status.HTTP_302_FOUND,
        )

    # Resource scope: the patient must be assigned to this coordinator. A miss is
    # audited as a denial and redirected identically to a real 'not assigned'.
    assignment = await coord_repo.get_assigned_patient(
        db, coordinator_id=coordinator.id, patient_id=patient_id
    )
    if assignment is None:
        await write_audit(
            db, ctx, action="coord_create_on_demand_consultation",
            resource_type="consultation", resource_id=None,
            allowed=False, reason="patient_not_assigned",
        )
        await db.commit()
        return RedirectResponse(
            url="/coord/scheduling?error=patient_not_assigned",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        consultation = await consultation_service.create_on_demand_consultation(
            db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            condition_category=condition_category,
            coordinator_id=coordinator.id,
            max_participants=max_participants,
        )
    except consultation_service.ConsultationError as exc:
        await write_audit(
            db, ctx, action="coord_create_on_demand_consultation",
            resource_type="consultation", resource_id=None,
            allowed=False, reason=exc.code,
        )
        await db.commit()
        return RedirectResponse(
            url=f"/coord/scheduling?error={exc.code}",
            status_code=status.HTTP_302_FOUND,
        )

    await write_audit(
        db, ctx, action="coord_create_on_demand_consultation",
        resource_type="consultation", resource_id=consultation.id, allowed=True,
    )
    return RedirectResponse(
        url="/coord/scheduling?success=on_demand_started",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/scheduling/{consultation_id}/join-room", response_class=HTMLResponse)
async def join_room(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
) -> Response:
    """Join the video room of an assigned patient's consultation as a support seat.

    Scoped to the coordinator's assigned patients (a miss is audited and 404s, no
    enumeration). The room is provisioned if needed, then a visible-identity staff
    token is minted — the coordinator's presence is never covert.
    """
    from app.core.config import settings
    from app.db.enums import ConsultationStatus
    from app.integrations import livekit_video
    from app.models.clinic import Consultation
    from app.models.identity import User as UserModel
    from app.services import consultation_service

    assert isinstance(coord, UserModel)
    ctx = _ctx(request, coord)

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    consultation = await db.get(Consultation, consultation_id)
    assignment = None
    if consultation is not None and consultation.deleted_at is None:
        assignment = await coord_repo.get_assigned_patient(
            db, coordinator_id=coordinator.id, patient_id=consultation.patient_id
        )
    if consultation is None or assignment is None:
        await write_audit(
            db, ctx, action="coord_join_consultation_room",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="not_assigned_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    if consultation.status not in (
        ConsultationStatus.CONFIRMED,
        ConsultationStatus.IN_PROGRESS,
    ):
        return RedirectResponse(
            url="/coord/scheduling?error=not_joinable",
            status_code=status.HTTP_302_FOUND,
        )

    room_id = await consultation_service.ensure_video_room(
        db, consultation_id=consultation.id
    )
    token = livekit_video.generate_staff_token(
        room_id=room_id, user_id=str(coord.id), role="coordinator"
    )
    await write_audit(
        db, ctx, action="coord_join_consultation_room",
        resource_type="consultation", resource_id=consultation.id, allowed=True,
    )
    return templates.TemplateResponse(
        request,
        "coord/video_room.html",
        {
            "coord": coord,
            "room_id": room_id,
            "token": token,
            "ws_url": settings.livekit_host,
            "role": "coordinator",
            "back_url": "/coord/scheduling",
        },
    )


@router.post("/scheduling/{consultation_id}/assign")
async def assign_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    slot_id: uuid.UUID = Form(...),
) -> RedirectResponse:
    """Assign a doctor + slot to a patient's consultation request.

    The doctor is determined by the chosen slot. Prices the fee, creates the
    Razorpay order the patient pays, and moves the request to 'scheduled'.
    """
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    from app.services import consultation_service

    try:
        consultation, _payment = await consultation_service.assign_consultation(
            db,
            consultation_id=consultation_id,
            coordinator_id=coordinator.id,
            slot_id=slot_id,
        )
    except consultation_service.ConsultationError as exc:
        # Roll back any partial slot/payment work, then record the denial
        # (audit rows must survive the rollback).
        await db.rollback()
        await write_audit(
            db, ctx, action="coord_assign_consultation", resource_type="consultation",
            resource_id=consultation_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        return RedirectResponse(
            url=f"/coord/scheduling?error={exc.code}",
            status_code=status.HTTP_302_FOUND,
        )

    await write_audit(
        db, ctx, action="coord_assign_consultation", resource_type="consultation",
        resource_id=consultation.id, allowed=True,
        log_metadata={"slot_id": str(slot_id)},
    )
    return RedirectResponse(
        url="/coord/scheduling?success=assigned", status_code=status.HTTP_302_FOUND
    )


@router.post("/scheduling/{consultation_id}/cancel")
async def cancel_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    reason: str = Form(default="Cancelled by coordinator"),
) -> RedirectResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    cancelled = await coord_repo.cancel_consultation_for_coordinator(
        db,
        coordinator_id=coordinator.id,
        consultation_id=consultation_id,
        reason=reason,
    )
    allowed = cancelled is not None
    await write_audit(
        db, ctx, action="coord_cancel_consultation", resource_type="consultation",
        resource_id=consultation_id, allowed=allowed,
        reason=None if allowed else "not_assigned_or_not_found",
    )

    if not allowed:
        return RedirectResponse(
            url="/coord/scheduling?error=cancel_failed",
            status_code=status.HTTP_302_FOUND,
        )

    # Refund any captured payment. A coordinator cancel mirrors the admin policy:
    # if the consultation was paid, the patient is refunded in full. A Razorpay
    # hiccup must not block the cancellation — we still leave it cancelled and audit
    # the refund failure for manual follow-up from Razorpay's dashboard.
    await _refund_on_cancel(db, ctx, consultation=cancelled)

    return RedirectResponse(
        url="/coord/scheduling?success=cancelled", status_code=status.HTTP_302_FOUND
    )


@router.post("/scheduling/{consultation_id}/reschedule")
async def reschedule_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    slot_id: uuid.UUID = Form(...),
) -> RedirectResponse:
    """Move a consultation to a new slot. Payment and status carry over —
    no cancel/refund/rebook cycle for the patient."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    rescheduled = await coord_repo.reschedule_consultation_for_coordinator(
        db,
        coordinator_id=coordinator.id,
        consultation_id=consultation_id,
        slot_id=slot_id,
    )
    allowed = rescheduled is not None

    if not allowed:
        # Undo the released-slot update so the original booking stays intact,
        # then record the denial (audit rows must survive the rollback).
        await db.rollback()
        await write_audit(
            db, ctx, action="coord_reschedule_consultation", resource_type="consultation",
            resource_id=consultation_id, allowed=False,
            reason="not_assigned_or_slot_unavailable",
        )
        await db.commit()
        return RedirectResponse(
            url="/coord/scheduling?error=reschedule_failed",
            status_code=status.HTTP_302_FOUND,
        )

    await write_audit(
        db, ctx, action="coord_reschedule_consultation", resource_type="consultation",
        resource_id=consultation_id, allowed=True,
        log_metadata={"slot_id": str(slot_id)},
    )
    return RedirectResponse(
        url="/coord/scheduling?success=rescheduled", status_code=status.HTTP_302_FOUND
    )


async def _refund_on_cancel(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    consultation: object,
) -> None:
    """Refund a coordinator-cancelled consultation's captured payment, if any.

    Mirrors ``consultation_service.admin_cancel_consultation``: a paid consultation
    is refunded in full. Razorpay failures are non-fatal — the consultation stays
    cancelled and the refund failure is audited so ops can retry manually.
    """
    from app.models.clinic import Consultation as ConsultationModel
    from app.models.payment import Payment
    from app.services import payment_service

    assert isinstance(consultation, ConsultationModel)

    payment_id = consultation.payment_id
    fee_paise = consultation.consultation_fee_paise or 0
    # Nothing to refund: no payment linked, or a zero-fee booking.
    if payment_id is None or fee_paise <= 0:
        return

    payment = await db.get(Payment, payment_id)
    if payment is None or payment.status != PaymentStatus.PAID:
        return

    try:
        await payment_service.initiate_refund(
            db,
            payment_id=payment.id,
            user_id=payment.user_id,
            reason="coordinator_cancellation",
        )
        await write_audit(
            db, ctx, action="coord_refund_consultation", resource_type="payment",
            resource_id=payment.id, allowed=True,
            log_metadata={"consultation_id": str(consultation.id), "amount_paise": payment.amount_paise},
        )
    except payment_service.PaymentError as exc:
        # Audit the failed attempt for manual follow-up. The audit row must survive
        # even though the consultation cancellation itself is already committed by
        # the request-scoped transaction; record allowed=False with the reason.
        await write_audit(
            db, ctx, action="coord_refund_consultation", resource_type="payment",
            resource_id=payment.id, allowed=False, reason=exc.code,
            log_metadata={"consultation_id": str(consultation.id)},
        )
        logger.error(
            "coord_refund_on_cancel_failed",
            consultation_id=str(consultation.id),
            payment_id=str(payment.id),
            reason=exc.code,
        )


async def _notify_patient_booked(
    db: AsyncSession, *, consultation_id: uuid.UUID
) -> None:
    """Best-effort: dispatch a booking confirmation to the patient.

    A coordinator-booked consultation goes straight to SCHEDULED, so the patient
    is told their appointment is set (push + WhatsApp + email, channel-gated by the
    patient's preferences inside the service). The notification service resolves the
    patient's contact details itself from the consultation id.

    Notification dispatch is fire-and-forget: a broker/email outage must never fail
    the booking flow, so all errors are swallowed after logging.
    """
    from app.services.notifications import notify_appointment_confirmed

    try:
        await notify_appointment_confirmed(db, consultation_id=consultation_id)
    except Exception:
        logger.exception(
            "coord_notify_patient_booked_failed",
            consultation_id=str(consultation_id),
        )
