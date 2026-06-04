"""ABDM / ABHA sandbox integration.

M1 scope: ABHA number verification (existing ID) and creation via Aadhaar OTP.

Stub mode is active when KYROS_ABHA_CLIENT_ID is empty — returns synthetic
responses so local dev and tests work without sandbox credentials.

ABDM sandbox base: https://sandbox.abdm.gov.in

PHI discipline:
- Aadhaar numbers are never logged. structlog calls use abha_scrubbed=True.
- ABHA numbers are never logged. Only abha_linked=True / abha_unlinked=True.
"""

from __future__ import annotations

import base64
import time
import uuid
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ── In-process M2M token cache ─────────────────────────────────────────────────
_token_cache: dict[str, Any] = {}  # {"token": str, "expires_at": float}

_STUB_TXN_ID = "STUB-TXN-"
_STUB_ABHA_NUMBER = "91000000000000"
_STUB_OTP = "000000"


def _is_configured() -> bool:
    return bool(settings.abha_client_id and settings.abha_client_secret)


def _base_url() -> str:
    return settings.abha_sandbox_url.rstrip("/")


# ── M2M Authentication ────────────────────────────────────────────────────────


async def get_m2m_token() -> str:
    """Return a valid M2M bearer token, refreshing if within 60 s of expiry."""
    now = time.monotonic()
    cached: str | None = _token_cache.get("token")
    expires_at: float = _token_cache.get("expires_at", 0.0)
    if cached and now < expires_at - 60:
        return cached

    if not _is_configured():
        logger.warning("abha_not_configured_using_stub_token")
        return "stub-m2m-token"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_base_url()}/v0.5/sessions",
            json={"clientId": settings.abha_client_id, "clientSecret": settings.abha_client_secret},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    token: str = data["accessToken"]
    expires_in: int = int(data.get("expiresIn", 1800))
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expires_in
    return token


# ── Public key / encryption ────────────────────────────────────────────────────


async def _get_public_cert() -> bytes:
    """Fetch ABDM RSA certificate PEM used to encrypt Aadhaar + OTP fields."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_base_url()}/v1/auth/cert")
        resp.raise_for_status()
        return resp.content


def _rsa_encrypt(plaintext: str, pem_cert: bytes) -> str:
    """RSA PKCS1v15 encrypt `plaintext` using an X.509 PEM certificate.

    ABDM uses RSA/ECB/PKCS1Padding (PKCS1v15 in Python's cryptography library).
    Returns base64-encoded ciphertext.
    """
    from cryptography.hazmat.primitives.asymmetric import padding as _padding
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    from cryptography.x509 import load_pem_x509_certificate

    cert = load_pem_x509_certificate(pem_cert)
    pub_key = cert.public_key()
    if not isinstance(pub_key, RSAPublicKey):
        raise ValueError("ABDM certificate does not contain an RSA public key")
    encrypted = pub_key.encrypt(plaintext.encode(), _padding.PKCS1v15())
    return base64.b64encode(encrypted).decode()


# ── ABHA existence verification ────────────────────────────────────────────────


async def verify_abha_exists(abha_number: str) -> bool:
    """Check whether an ABHA health ID exists in the ABDM registry.

    In stub mode always returns True for correctly formatted IDs.
    In real mode calls ABDM /v1/search/searchByHealthId.
    """
    if not _is_configured():
        logger.info("abha_verify_stub", abha_linked=True)
        return True

    token = await get_m2m_token()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{_base_url()}/v1/search/searchByHealthId",
                json={"healthId": abha_number},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return True
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return False
        logger.error("abha_verify_error", status=exc.response.status_code)
        raise


# ── Aadhaar OTP — init ────────────────────────────────────────────────────────


async def generate_aadhaar_otp(aadhaar_number: str) -> str:
    """Trigger an OTP to the Aadhaar-linked mobile. Returns txn_id.

    Aadhaar number is RSA-encrypted with ABDM public cert before transmission.
    It is never stored or logged here — only `aadhaar_scrubbed=True` appears.
    """
    if not _is_configured():
        txn_id = f"{_STUB_TXN_ID}{uuid.uuid4().hex[:8]}"
        logger.info("abha_aadhaar_otp_stub", aadhaar_scrubbed=True, stub_txn=True)
        return txn_id

    token = await get_m2m_token()
    pem_cert = await _get_public_cert()
    encrypted_aadhaar = _rsa_encrypt(aadhaar_number, pem_cert)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_base_url()}/v1/registration/aadhaar/generateOtp",
            json={"aadhaar": encrypted_aadhaar},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    logger.info("abha_aadhaar_otp_sent", aadhaar_scrubbed=True)
    return str(data["txnId"])


# ── Aadhaar OTP — confirm ─────────────────────────────────────────────────────


async def verify_aadhaar_otp(txn_id: str, otp: str) -> str:
    """Verify the Aadhaar OTP. Returns txn_id on success.

    OTP is RSA-encrypted before transmission. Never logged.
    In stub mode accepts otp == '000000'.
    """
    if not _is_configured():
        if otp != _STUB_OTP:
            raise ValueError("stub_otp_mismatch")
        logger.info("abha_aadhaar_otp_verified_stub", stub=True)
        return txn_id

    token = await get_m2m_token()
    pem_cert = await _get_public_cert()
    encrypted_otp = _rsa_encrypt(otp, pem_cert)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_base_url()}/v1/registration/aadhaar/verifyOTP",
            json={"txnId": txn_id, "otp": encrypted_otp},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    logger.info("abha_aadhaar_otp_verified")
    return str(data["txnId"])


# ── ABHA account creation ──────────────────────────────────────────────────────


async def create_abha_account(txn_id: str) -> dict[str, str]:
    """Create a new ABHA account after Aadhaar OTP verification.

    Returns {"abha_number": "12345678901234", "name": "Patient Name"}.
    """
    if not _is_configured():
        logger.info("abha_create_stub", abha_linked=True)
        return {"abha_number": _STUB_ABHA_NUMBER, "name": "Stub Patient"}

    token = await get_m2m_token()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_base_url()}/v1/registration/aadhaar/createHealthId",
            json={"txnId": txn_id},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    abha_number: str = data.get("healthIdNumber") or data.get("healthId", "")
    name: str = data.get("name", "")
    logger.info("abha_account_created", abha_linked=True)
    return {"abha_number": abha_number, "name": name}
