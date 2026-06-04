from __future__ import annotations

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_MSG91_OTP_URL = "https://api.msg91.com/api/v5/otp"


async def send_otp_sms(phone: str, otp: str) -> None:
    """Send OTP via MSG91 SMS gateway.

    When msg91_auth_key is blank (dev/test), logs a warning and returns without
    making an API call. OTP is NEVER logged — only the phone (scrubbed in prod).
    """
    if not settings.msg91_auth_key:
        logger.warning("msg91_not_configured_otp_skipped", phone_e164=phone)
        return

    import httpx

    payload = {
        "template_id": settings.msg91_template_id,
        "mobile": phone.lstrip("+"),
        "authkey": settings.msg91_auth_key,
        "otp": otp,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(_MSG91_OTP_URL, json=payload)
        if resp.status_code != 200:
            logger.error(
                "msg91_send_failed",
                status=resp.status_code,
            )
            resp.raise_for_status()
