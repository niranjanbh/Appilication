from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.api.deps import DbSession, Redis
from app.api.v1.public.schemas import (
    BookingInquiryCreate,
    BookingInquiryRead,
    BookingOtpRequest,
    BookingOtpResponse,
    ConditionRead,
    LeadCreate,
    LeadRead,
    get_conditions,
)
from app.core.config import settings
from app.core.ratelimit import rate_limit
from app.services import public_booking
from app.services.notifications import (
    notify_booking_inquiry_received,
    notify_ops_new_inquiry,
)

router = APIRouter(tags=["public"])


@router.get("/conditions", response_model=list[ConditionRead])
async def list_conditions() -> list[ConditionRead]:
    """Return the eight Kyros clinical verticals for display on the public website."""
    return get_conditions()


@router.post(
    "/booking-otp",
    response_model=BookingOtpResponse,
    dependencies=[Depends(rate_limit("public_booking_otp", limit=5))],
)
async def send_booking_otp(
    payload: BookingOtpRequest,
    redis: Redis,
) -> BookingOtpResponse:
    """Send a phone-verification OTP for the public booking flow.

    Only active when booking_otp_enabled is set (422 otherwise). No
    authentication required — the booking form is pre-account. Per-IP rate
    limited here, per-phone cooldown enforced in the service layer.
    """
    await public_booking.send_booking_otp(redis, phone=payload.phone)
    otp_hint: str | None = None
    if settings.debug:
        otp_hint = await redis.get(f"otp:booking:{payload.phone}:debug")
    return BookingOtpResponse(
        message="Verification code sent to your phone.",
        otp_hint=otp_hint,
    )


@router.post(
    "/booking-inquiry",
    response_model=BookingInquiryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("public_booking_inquiry", limit=10))],
)
async def create_booking_inquiry(
    payload: BookingInquiryCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
    redis: Redis,
) -> BookingInquiryRead:
    """Submit a pre-account booking inquiry from the public website booking flow.

    No authentication required. When booking_otp_enabled is set, the phone must
    be verified with the OTP issued by /booking-otp. A care coordinator will
    follow up within 4 hours. Intake responses are stored as JSONB — no PHI
    beyond name and contact details.
    """
    inquiry = await public_booking.create_booking_inquiry(
        db,
        redis,
        name=payload.name,
        gender=payload.gender,
        phone=payload.phone,
        email=payload.email,
        condition_category=payload.condition_category,
        intake_responses=payload.intake_responses,
        skipped_intake=payload.skipped_intake,
        otp=payload.otp,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    # Runs after the get_db commit — the alert never describes a rolled-back row.
    # The inquiry id is the dedup scope so each distinct submission alerts ops.
    background_tasks.add_task(
        notify_ops_new_inquiry, kind="booking_inquiry", dedup_id=str(inquiry.id)
    )
    # Acknowledge receipt to the patient by email (no-op if no email was given).
    background_tasks.add_task(
        notify_booking_inquiry_received,
        name=payload.name,
        email=payload.email,
        dedup_id=str(inquiry.id),
    )
    return BookingInquiryRead(
        id=inquiry.id,
        message=(
            "Thank you. A Kyros care coordinator will reach out "
            "on your phone within 4 hours to schedule your consultation."
        ),
    )


@router.post(
    "/lead",
    response_model=LeadRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("public_lead", limit=10))],
)
async def create_lead(
    payload: LeadCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> LeadRead:
    """Submit a help query from the public website contact form.

    No authentication required. The ops inbox is alerted; coordinators work
    the queue in the portal and reply within 1 business day.
    """
    lead = await public_booking.create_lead(
        db,
        name=payload.name,
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    background_tasks.add_task(
        notify_ops_new_inquiry, kind="lead", dedup_id=str(lead.id)
    )
    return LeadRead(
        id=lead.id,
        message="Thank you. We will reply to your email within 1 business day.",
    )
