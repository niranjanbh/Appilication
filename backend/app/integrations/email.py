"""SMTP email integration.

Uses Python smtplib + email.mime for delivery.
In local dev / test: targets mailhog on port 1025 (no auth required).
In production: real SMTP credentials via settings.smtp_host/user/password.

No PHI in log messages — only recipient hash and subject.
"""

from __future__ import annotations

import asyncio
import hashlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

logger = structlog.get_logger(__name__)


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:12]


def send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    """Send an HTML email via SMTP.

    Synchronous — call from a Celery task, not from async request handlers.
    Returns True on success, False on any failure (non-raising).
    """
    from app.core.config import settings

    if not settings.smtp_host:
        logger.warning("email.smtp_not_configured_skipped", email_hash=_email_hash(to_email))
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_user and settings.smtp_password:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()  # re-identify after TLS; exposes TLS-only AUTH mechanisms
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(settings.email_from, [to_email], msg.as_string())

        logger.info("email.sent", email_hash=_email_hash(to_email), subject=subject)
        return True

    except Exception:
        logger.exception("email.exception", email_hash=_email_hash(to_email))
        return False


async def send_email_async(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    """Async wrapper for send_email — runs the blocking smtplib call in a
    worker thread so request handlers can await it without stalling the loop.
    """
    return await asyncio.to_thread(
        send_email,
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )
