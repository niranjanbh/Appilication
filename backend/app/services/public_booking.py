"""Public (pre-account) booking inquiry flow — OTP-gated lead capture.

The website booking form is unauthenticated, so the phone number is verified
with an OTP before the inquiry row is accepted. The OTP lives in the
``otp:booking:*`` Redis namespace — deliberately separate from the auth flow's
``otp:phone:*`` keys so a booking code can never be replayed against
``/v1/auth/verify-otp``.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError
from app.db.redis import RedisClient
from app.models.public import BookingInquiry, Lead
from app.services.auth import _issue_otp, _verify_otp_code

logger = structlog.get_logger(__name__)

_BOOKING_OTP_NAMESPACE = "booking"


async def send_booking_otp(redis: RedisClient, *, phone: str) -> None:
    """Issue a booking-verification OTP to an unauthenticated visitor's phone.

    Only available when booking_otp_enabled is set — otherwise the public
    endpoint would be an open SMS-sending relay for a check nobody enforces.
    No account lookup — the booking form is pre-account by design. Delivery
    is WhatsApp with SMS fallback (no email: the form's email is unverified).
    Raises OtpCooldownError when a resend arrives inside the cooldown window.
    """
    if not settings.booking_otp_enabled:
        raise BusinessRuleError("otp_verification_disabled")
    await _issue_otp(redis, phone, namespace=_BOOKING_OTP_NAMESPACE)


async def create_booking_inquiry(
    db: AsyncSession,
    redis: RedisClient,
    *,
    name: str,
    gender: str,
    phone: str,
    email: str | None,
    condition_category: str,
    intake_responses: dict[str, Any],
    skipped_intake: bool,
    otp: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> BookingInquiry:
    """Persist the inquiry, verifying the phone OTP first when the flag is on.

    With booking_otp_enabled: raises BusinessRuleError (otp_required /
    otp_invalid / otp_expired) or OtpMaxAttemptsError when verification fails —
    no row is written in that case. With the flag off, any otp value is ignored.
    """
    if settings.booking_otp_enabled:
        if not otp:
            raise BusinessRuleError("otp_required")
        await _verify_otp_code(redis, phone, otp, namespace=_BOOKING_OTP_NAMESPACE)

    inquiry = BookingInquiry(
        name=name,
        gender=gender,
        phone=phone,
        email=email,
        condition_category=condition_category,
        intake_responses=intake_responses,
        skipped_intake=skipped_intake,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(inquiry)
    await db.flush()
    logger.info("booking_inquiry_created", condition=condition_category)
    # Ops alert is scheduled by the router as a background task so it fires
    # only after the transaction commits.
    return inquiry


async def create_lead(
    db: AsyncSession,
    *,
    name: str,
    email: str,
    subject: str,
    message: str,
    ip_address: str | None,
    user_agent: str | None,
) -> Lead:
    """Persist a contact-form help query. The router schedules the ops alert
    as a post-commit background task."""
    lead = Lead(
        name=name,
        email=email,
        subject=subject,
        message=message,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(lead)
    await db.flush()
    logger.info("lead_created", subject=subject)
    return lead
