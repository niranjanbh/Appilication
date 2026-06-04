"""authkey.io integration — OTP (WhatsApp + SMS) and WhatsApp utility templates.

Replaces MSG91 (OTP SMS) and AiSensy (WhatsApp templates) with a single provider.

────────────────────────────────────────────────────────────────────────────────
SETUP CHECKLIST
────────────────────────────────────────────────────────────────────────────────
1. Add to your .env / Secrets Manager (see required keys below).

2. In the authkey.io dashboard → WhatsApp Templates, create and submit for
   Meta approval the following utility templates (language: en):

   a) kyros_otp  (for OTP delivery)
      Body: "Your Kyros verification code is {{1}}. Valid for 5 minutes.
             Do not share this with anyone. - Team Kyros"
      Variables: [otp_code]

   b) appointment_confirmation
      Body: "Hi {{1}}, your Kyros appointment is confirmed for {{2}} at
             {{3}} IST. Your consultation link will be available 15 minutes
             before the call. - Team Kyros"
      Variables: [patient_first_name, date, time]

   c) appointment_reminder
      Body: "Hi {{1}}, a reminder: your Kyros appointment is tomorrow at
             {{2}} IST. Please complete your pre-consultation questionnaire
             if you haven't yet. - Team Kyros"
      Variables: [patient_first_name, time]

   d) lab_result_ready
      Body: "Hi {{1}}, your lab report has been processed and is ready to
             view in the Kyros app. Please review any flagged values.
             - Team Kyros"
      Variables: [patient_first_name]

   e) pre_consult_report_ready
      Body: "Hi {{1}}, your pre-consultation report is ready. Your doctor
             will review it before your appointment at {{2}} IST.
             - Team Kyros"
      Variables: [patient_first_name, time]

   f) medication_reminder
      Body: "Hi {{1}}, this is a reminder to take your scheduled medication.
             Log it in the Kyros app when done. - Team Kyros"
      Variables: [patient_first_name]

   Template approvals typically take 24-48 hours.

3. Copy the approved template names exactly into your .env (they must match
   what you registered in the authkey dashboard).

────────────────────────────────────────────────────────────────────────────────
REQUIRED ENV VARS
────────────────────────────────────────────────────────────────────────────────
  KYROS_AUTHKEY_API_KEY=<your authkey.io API key>
  KYROS_AUTHKEY_OTP_TEMPLATE_NAME=kyros_otp    # your approved OTP template name
  KYROS_AUTHKEY_SENDER_ID=KYROS                # SMS sender ID (DLT-registered)
  KYROS_AUTHKEY_SMS_TEMPLATE_ID=               # DLT SMS template ID for OTP (fallback)
────────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib

import structlog

logger = structlog.get_logger(__name__)

_AUTHKEY_BASE_URL = "https://api.authkey.io/request"

# Approved WhatsApp utility template names — must match authkey dashboard exactly
_VALID_TEMPLATES = frozenset(
    {
        "appointment_confirmation",
        "appointment_reminder",
        "lab_result_ready",
        "pre_consult_report_ready",
        "medication_reminder",
    }
)


def _phone_hash(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()[:12]


def _split_phone(phone: str) -> tuple[str, str]:
    """Return (country_code, number) from E.164 (e.g. +919876543210 → '91', '9876543210')."""
    stripped = phone.lstrip("+")
    if stripped.startswith("91") and len(stripped) == 12:
        return "91", stripped[2:]
    # Fallback: assume India, use as-is
    return "91", stripped


# ── OTP via WhatsApp ─────────────────────────────────────────────────────────


async def send_otp_whatsapp(phone: str, otp: str) -> bool:
    """Deliver an OTP via WhatsApp using authkey.io.

    Returns True on success, False on failure (non-raising).
    Falls back gracefully — the caller should call send_otp_sms on False.

    OTP is NEVER logged — only the phone hash.
    """
    from app.core.config import settings

    if not settings.authkey_api_key:
        logger.warning("authkey.not_configured_otp_skipped", channel="whatsapp", phone_hash=_phone_hash(phone))
        return False

    import httpx

    country_code, mobile = _split_phone(phone)

    params = {
        "authkey": settings.authkey_api_key,
        "mobile": mobile,
        "country_code": country_code,
        "type": "whatsapp",
        "template_name": settings.authkey_otp_template_name,
        "body_variables": [otp],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_AUTHKEY_BASE_URL, json=params)

        if resp.status_code not in (200, 201):
            logger.error(
                "authkey.otp_whatsapp_failed",
                status=resp.status_code,
                phone_hash=_phone_hash(phone),
            )
            return False

        data = resp.json() if resp.text else {}
        if str(data.get("type", "")).lower() == "error":
            logger.error(
                "authkey.otp_whatsapp_api_error",
                message=data.get("message"),
                phone_hash=_phone_hash(phone),
            )
            return False

        logger.info("authkey.otp_whatsapp_sent", phone_hash=_phone_hash(phone))
        return True

    except Exception:
        logger.exception("authkey.otp_whatsapp_exception", phone_hash=_phone_hash(phone))
        return False


# ── OTP via SMS (fallback) ───────────────────────────────────────────────────


async def send_otp_sms(phone: str, otp: str) -> bool:
    """Deliver an OTP via SMS using authkey.io as fallback when WhatsApp fails.

    The SMS template must be DLT-registered (TRAI) with your sender ID.
    OTP is NEVER logged — only the phone hash.
    """
    from app.core.config import settings

    if not settings.authkey_api_key:
        logger.warning("authkey.not_configured_otp_skipped", channel="sms", phone_hash=_phone_hash(phone))
        return False

    import httpx

    country_code, mobile = _split_phone(phone)

    params = {
        "authkey": settings.authkey_api_key,
        "mobile": mobile,
        "country_code": country_code,
        "type": "sms",
        "sender_id": settings.authkey_sender_id,
        "template_id": settings.authkey_sms_template_id,
        "otp": otp,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_AUTHKEY_BASE_URL, json=params)

        if resp.status_code not in (200, 201):
            logger.error(
                "authkey.otp_sms_failed",
                status=resp.status_code,
                phone_hash=_phone_hash(phone),
            )
            return False

        logger.info("authkey.otp_sms_sent", phone_hash=_phone_hash(phone))
        return True

    except Exception:
        logger.exception("authkey.otp_sms_exception", phone_hash=_phone_hash(phone))
        return False


# ── WhatsApp utility templates ───────────────────────────────────────────────


async def send_whatsapp_template(
    *,
    phone: str,
    template_name: str,
    params: list[str],
) -> bool:
    """Send an approved WhatsApp utility template via authkey.io.

    phone: E.164 format (e.g. +919876543210)
    template_name: one of the approved template keys in _VALID_TEMPLATES
    params: positional variable values for the template body (e.g. [first_name, date, time])

    Returns True on success, False on any failure (non-raising).
    No PHI logged — only phone hash and template name.
    """
    from app.core.config import settings

    if not settings.authkey_api_key:
        logger.warning(
            "authkey.not_configured_whatsapp_skipped",
            template=template_name,
            phone_hash=_phone_hash(phone),
        )
        return False

    if template_name not in _VALID_TEMPLATES:
        logger.error("authkey.unknown_template", template=template_name)
        return False

    import httpx

    country_code, mobile = _split_phone(phone)

    payload = {
        "authkey": settings.authkey_api_key,
        "mobile": mobile,
        "country_code": country_code,
        "type": "whatsapp",
        "template_name": template_name,
        "body_variables": params,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_AUTHKEY_BASE_URL, json=payload)

        if resp.status_code not in (200, 201):
            logger.error(
                "authkey.whatsapp_template_failed",
                status=resp.status_code,
                template=template_name,
                phone_hash=_phone_hash(phone),
            )
            return False

        data = resp.json() if resp.text else {}
        if str(data.get("type", "")).lower() == "error":
            logger.error(
                "authkey.whatsapp_template_api_error",
                message=data.get("message"),
                template=template_name,
                phone_hash=_phone_hash(phone),
            )
            return False

        logger.info(
            "authkey.whatsapp_template_sent",
            template=template_name,
            phone_hash=_phone_hash(phone),
        )
        return True

    except Exception:
        logger.exception(
            "authkey.whatsapp_template_exception",
            template=template_name,
            phone_hash=_phone_hash(phone),
        )
        return False
