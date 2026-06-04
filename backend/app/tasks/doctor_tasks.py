"""Doctor-related Celery tasks.

bank_details_verification — notify super admin when a doctor submits bank details.
"""

from __future__ import annotations

import structlog

from app.worker import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.doctor.bank_details_verification",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    max_retries=3,
    default_retry_delay=60,
)
def bank_details_verification(self: object, *, doctor_id: str, doctor_name: str) -> None:
    """Send an alert email to super admin when a doctor updates bank details.

    No PHI in arguments — doctor_id is a UUID, doctor_name is non-sensitive.
    """
    from app.core.config import settings
    from app.integrations.email import send_email

    if not settings.admin_alert_email:
        logger.warning("doctor_tasks.bank_verification.no_admin_email")
        return

    html_body = (
        f"<p>Doctor <strong>{doctor_name}</strong> (ID: {doctor_id}) "
        "has submitted updated bank details for revenue share verification.</p>"
        "<p>Please log in to the Kyros admin portal to review and verify.</p>"
    )
    text_body = (
        f"Doctor {doctor_name} (ID: {doctor_id}) submitted updated bank details. "
        "Log in to the admin portal to verify."
    )

    send_email(
        to_email=settings.admin_alert_email,
        subject="[Kyros] Doctor bank details require verification",
        html_body=html_body,
        text_body=text_body,
    )
    logger.info("doctor_tasks.bank_verification.sent", doctor_id=doctor_id)
