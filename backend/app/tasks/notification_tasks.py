"""Notification Celery tasks — push, WhatsApp, email.

All three tasks route to the 'notifications' queue.
Idempotency: Redis SETNX with 24h TTL prevents duplicate delivery for the
same (channel, resource_id) pair within a 24-hour window.

Tasks accept only primitive values — no ORM objects cross the task boundary.
No PHI in task arguments beyond email address (needed for delivery) and
first name (needed in message body per template).
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

import structlog

from app.worker import celery_app

logger = structlog.get_logger(__name__)


def _dedup_key(channel: str, token_or_addr: str, title: str) -> str:
    digest = hashlib.sha256(f"{channel}:{token_or_addr}:{title}".encode()).hexdigest()[:20]
    return f"notif:dedup:{digest}"


def _check_dedup(key: str, ttl_seconds: int = 86400) -> bool:
    """Return True if this notification was already sent (and should be skipped)."""
    import redis as redis_lib

    from app.core.config import settings

    try:
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
        return not bool(r.set(key, "1", ex=ttl_seconds, nx=True))
    except Exception:
        # Redis unavailable — allow delivery rather than silently dropping
        return False


# ── Push ──────────────────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.notification.send_push",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_push_notification_task(
    self: Any,
    *,
    push_token: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Send a push notification via Expo Push HTTP v2."""
    log = logger.bind(task_name="send_push", task_id=self.request.id)
    log.info("task.started")

    key = _dedup_key("push", push_token, title)
    if _check_dedup(key):
        log.info("task.deduped")
        return {"status": "deduped"}

    try:
        result = asyncio.run(
            _send_push_async(push_token=push_token, title=title, body=body, data=data)
        )
        log.info("task.completed", delivered=result)
        return {"status": "sent" if result else "skipped"}
    except Exception as exc:
        log.exception("task.failed")
        raise self.retry(exc=exc) from exc


async def _send_push_async(
    *, push_token: str, title: str, body: str, data: dict[str, str] | None
) -> bool:
    from app.integrations.expo_push import send_push_notification
    return await send_push_notification(push_token=push_token, title=title, body=body, data=data)


# ── WhatsApp ──────────────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.notification.send_whatsapp",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_whatsapp_task(
    self: Any,
    *,
    phone: str,
    template_name: str,
    params: list[str],
) -> dict[str, Any]:
    """Send a WhatsApp utility template message via authkey.io."""
    log = logger.bind(task_name="send_whatsapp", task_id=self.request.id, template=template_name)
    log.info("task.started")

    key = _dedup_key("whatsapp", phone, template_name)
    if _check_dedup(key):
        log.info("task.deduped")
        return {"status": "deduped"}

    try:
        result = asyncio.run(
            _send_whatsapp_async(phone=phone, template_name=template_name, params=params)
        )
        log.info("task.completed", delivered=result)
        return {"status": "sent" if result else "skipped"}
    except Exception as exc:
        log.exception("task.failed")
        raise self.retry(exc=exc) from exc


async def _send_whatsapp_async(
    *, phone: str, template_name: str, params: list[str]
) -> bool:
    from app.integrations.authkey import send_whatsapp_template
    return await send_whatsapp_template(phone=phone, template_name=template_name, params=params)


# ── Email ─────────────────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.notification.send_email",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_email_task(
    self: Any,
    *,
    to_email: str,
    subject: str,
    html_body: str,
) -> dict[str, Any]:
    """Send an HTML email via SMTP."""
    log = logger.bind(task_name="send_email", task_id=self.request.id)
    log.info("task.started")

    key = _dedup_key("email", to_email, subject)
    if _check_dedup(key):
        log.info("task.deduped")
        return {"status": "deduped"}

    try:
        from app.integrations.email import send_email
        result = send_email(to_email=to_email, subject=subject, html_body=html_body)
        log.info("task.completed", delivered=result)
        return {"status": "sent" if result else "skipped"}
    except Exception as exc:
        log.exception("task.failed")
        raise self.retry(exc=exc) from exc
