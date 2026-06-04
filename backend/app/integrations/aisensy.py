"""AiSensy WhatsApp Business API integration.

Sends WhatsApp utility template messages via the AiSensy direct API.
When aisensy_api_key is blank (dev/test), logs a warning and returns without
making an API call. No PHI is logged — only phone hash and template name.

────────────────────────────────────────────────────────────────────────────────
META TEMPLATE APPROVAL — REQUIRED BEFORE LIVE DELIVERY
────────────────────────────────────────────────────────────────────────────────
WhatsApp utility templates must be submitted to Meta via the AiSensy dashboard
and approved before messages can be delivered to real numbers. Template
approvals typically take 24-48 hours.

Templates to submit (category: Utility, language: en):

1. appointment_confirmation
   Body: "Hi {{1}}, your Kyros appointment is confirmed for {{2}} at {{3}} IST.
          Your consultation link will be available 15 minutes before the call.
          - Team Kyros"
   Variables: [patient_first_name, date, time]

2. appointment_reminder
   Body: "Hi {{1}}, a reminder: your Kyros appointment is tomorrow at {{2}} IST.
          Please complete your pre-consultation questionnaire if you haven't yet.
          - Team Kyros"
   Variables: [patient_first_name, time]

3. lab_result_ready
   Body: "Hi {{1}}, your lab report has been processed and is ready to view in
          the Kyros app. Please review any flagged values.
          - Team Kyros"
   Variables: [patient_first_name]

4. pre_consult_report_ready
   Body: "Hi {{1}}, your pre-consultation report is ready. Your doctor will
          review it before your appointment at {{2}} IST.
          - Team Kyros"
   Variables: [patient_first_name, time]

5. medication_reminder
   Body: "Hi {{1}}, this is a reminder to take your scheduled medication.
          Log it in the Kyros app when done.
          - Team Kyros"
   Variables: [patient_first_name]

Submit via: AiSensy dashboard → Campaigns → Templates → Create Template
Set apiCampaignName to the template key above (e.g. "appointment_confirmation").
────────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib

import structlog

logger = structlog.get_logger(__name__)

_AISENSY_URL = "https://backend.aisensy.com/direct-apis/t1/messages"


def _phone_hash(phone: str) -> str:
    """One-way hash for log safety — never log raw phone numbers."""
    return hashlib.sha256(phone.encode()).hexdigest()[:12]


async def send_whatsapp_template(
    *,
    phone: str,
    template_name: str,
    params: list[str],
) -> bool:
    """Send a WhatsApp utility template message.

    phone: E.164 format (e.g. +919876543210)
    template_name: one of the five approved template names above
    params: positional variable values for the template body

    Returns True on success, False on any failure (non-raising).
    """
    from app.core.config import settings

    if not settings.aisensy_api_key:
        logger.warning(
            "aisensy.not_configured_skipped",
            template=template_name,
            phone_hash=_phone_hash(phone),
        )
        return False

    import httpx

    payload = {
        "apiKey": settings.aisensy_api_key,
        "campaignName": template_name,
        "destination": phone.lstrip("+"),
        "userName": "Kyros Clinic",
        "templateParams": params,
        "source": "kyros-backend",
        "media": {},
        "buttons": [],
        "carouselCards": [],
        "location": {},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_AISENSY_URL, json=payload)
        if resp.status_code not in (200, 201):
            logger.error(
                "aisensy.http_error",
                status=resp.status_code,
                template=template_name,
                phone_hash=_phone_hash(phone),
            )
            return False

        logger.info(
            "aisensy.sent",
            template=template_name,
            phone_hash=_phone_hash(phone),
        )
        return True

    except Exception:
        logger.exception(
            "aisensy.exception",
            template=template_name,
            phone_hash=_phone_hash(phone),
        )
        return False
