"""Expo Push HTTP v2 integration.

Sends push notifications to Expo-managed devices via the Expo Push API.
When a device has no token or the API is unavailable this integration
degrades gracefully — it logs a warning and returns without raising.

IMPORTANT: Push notification titles and bodies must use generic language.
Never include condition names, medication names, or any PHI in push text.
Per Section 9.8: "Your appointment is confirmed" not "Your thyroid consultation".
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_notification(
    *,
    push_token: str | None,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> bool:
    """Send a single push notification via Expo.

    Returns True if the message was accepted, False on any failure (non-raising).
    No PHI must appear in title, body, or data.
    """
    if not push_token:
        logger.debug("expo_push.no_token_skipped")
        return False

    if not push_token.startswith("ExponentPushToken["):
        logger.warning("expo_push.invalid_token_format")
        return False

    import httpx

    payload = {
        "to": push_token,
        "title": title,
        "body": body,
        "sound": "default",
    }
    if data:
        payload["data"] = data  # type: ignore[assignment]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _EXPO_PUSH_URL,
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            logger.error("expo_push.http_error", status=resp.status_code)
            return False

        result = resp.json()
        ticket = result.get("data", {})
        if ticket.get("status") == "error":
            logger.warning("expo_push.ticket_error", details=ticket.get("details"))
            return False

        logger.info("expo_push.sent")
        return True

    except Exception:
        logger.exception("expo_push.exception")
        return False
