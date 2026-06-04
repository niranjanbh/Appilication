from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import DbSession
from app.api.v1.public.schemas import (
    BookingInquiryCreate,
    BookingInquiryRead,
    ConditionRead,
    get_conditions,
)

router = APIRouter(tags=["public"])


@router.get("/conditions", response_model=list[ConditionRead])
async def list_conditions() -> list[ConditionRead]:
    """Return the seven Kyros clinical verticals for display on the public website."""
    return get_conditions()


@router.post(
    "/booking-inquiry",
    response_model=BookingInquiryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking_inquiry(
    payload: BookingInquiryCreate,
    request: Request,
    db: DbSession,
) -> BookingInquiryRead:
    """Submit a pre-account booking inquiry from the public website booking flow.

    No authentication required. A care coordinator will follow up within 4 hours.
    Intake responses are stored as JSONB — no PHI beyond name and contact details.
    """
    from app.models.public import BookingInquiry

    inquiry = BookingInquiry(
        name=payload.name,
        gender=payload.gender,
        phone=payload.phone,
        email=payload.email,
        condition_category=payload.condition_category,
        intake_responses=payload.intake_responses,
        skipped_intake=payload.skipped_intake,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(inquiry)
    await db.flush()
    return BookingInquiryRead(
        id=inquiry.id,
        message=(
            "Thank you. A Kyros care coordinator will reach out "
            "on your phone within 4 hours to schedule your consultation."
        ),
    )
