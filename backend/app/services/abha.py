"""ABHA business logic — verify existing health ID and create via Aadhaar OTP.

Redis is used to hold in-flight txn_ids with a 10-minute TTL, scoped per
user to prevent cross-user txn replay.

PHI discipline:
- ABHA numbers are never logged. Structlog uses abha_linked=True/False.
- Aadhaar numbers are never stored or logged here.
- Redis keys contain only the user_id (UUID), not the Aadhaar or ABHA.
"""

from __future__ import annotations

import re
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import RedisClient
from app.integrations import abha as abha_client
from app.repositories import patients as patients_repo

logger = structlog.get_logger(__name__)

_ABHA_TXN_TTL = 600  # 10 minutes
_ABHA_NUMBER_PLAIN = re.compile(r"^\d{14}$")
_ABHA_NUMBER_DASHED = re.compile(r"^\d{2}-\d{4}-\d{4}-\d{4}$")


def _normalize_abha(raw: str) -> str:
    """Strip dashes; validate format. Raises ValueError on bad input."""
    cleaned = raw.replace("-", "")
    if not re.match(r"^\d{14}$", cleaned):
        raise ValueError("invalid_abha_format")
    return cleaned


def _txn_redis_key(user_id: uuid.UUID) -> str:
    return f"abha_txn:{user_id}"


# ── Status ────────────────────────────────────────────────────────────────────


async def get_abha_status(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, object]:
    patient = await patients_repo.get_patient_for_user(db, user_id=user_id)
    if patient is None:
        return {"abha_number": None, "linked": False, "patient_exists": False}
    linked = patient.abha_number is not None
    return {
        "abha_number": patient.abha_number,
        "linked": linked,
        "patient_exists": True,
    }


# ── Link existing ABHA ────────────────────────────────────────────────────────


async def link_abha_number(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    abha_number: str,
) -> dict[str, object]:
    """Validate, verify via ABDM sandbox, and persist an existing ABHA number."""
    normalized = _normalize_abha(abha_number)

    patient = await patients_repo.get_patient_for_user(db, user_id=user_id)
    if patient is None:
        return {"abha_number": None, "linked": False, "patient_exists": False}

    exists = await abha_client.verify_abha_exists(normalized)
    if not exists:
        return {"abha_number": None, "linked": False, "patient_exists": True, "error": "abha_not_found"}

    await patients_repo.update_abha_number(db, patient_id=patient.id, abha_number=normalized)
    logger.info("abha_linked", user_id=str(user_id), abha_linked=True)
    return {"abha_number": normalized, "linked": True, "patient_exists": True}


# ── Create ABHA via Aadhaar OTP — init ───────────────────────────────────────


async def init_abha_creation(
    db: AsyncSession,
    redis: RedisClient,
    *,
    user_id: uuid.UUID,
    aadhaar_number: str,
) -> dict[str, object]:
    """Trigger OTP to the Aadhaar-linked mobile. Stores txn_id in Redis."""
    patient = await patients_repo.get_patient_for_user(db, user_id=user_id)
    if patient is None:
        return {"txn_id": None, "patient_exists": False}

    txn_id = await abha_client.generate_aadhaar_otp(aadhaar_number)
    await redis.set(_txn_redis_key(user_id), txn_id, ex=_ABHA_TXN_TTL)
    logger.info("abha_creation_otp_sent", user_id=str(user_id), aadhaar_scrubbed=True)
    return {"txn_id": txn_id, "patient_exists": True}


# ── Create ABHA via Aadhaar OTP — confirm ────────────────────────────────────


async def confirm_abha_creation(
    db: AsyncSession,
    redis: RedisClient,
    *,
    user_id: uuid.UUID,
    txn_id: str,
    otp: str,
) -> dict[str, object]:
    """Verify OTP, create ABHA account on ABDM, persist the ABHA number."""
    patient = await patients_repo.get_patient_for_user(db, user_id=user_id)
    if patient is None:
        return {"abha_number": None, "linked": False, "patient_exists": False}

    # Guard: txn_id must match what we stored for this user, preventing cross-user replay.
    stored_txn = await redis.get(_txn_redis_key(user_id))
    if stored_txn != txn_id:
        return {"abha_number": None, "linked": False, "patient_exists": True, "error": "invalid_or_expired_txn"}

    try:
        confirmed_txn = await abha_client.verify_aadhaar_otp(txn_id, otp)
    except ValueError:
        return {"abha_number": None, "linked": False, "patient_exists": True, "error": "invalid_otp"}

    result = await abha_client.create_abha_account(confirmed_txn)
    abha_number = result["abha_number"]

    await patients_repo.update_abha_number(db, patient_id=patient.id, abha_number=abha_number)
    await redis.delete(_txn_redis_key(user_id))
    logger.info("abha_created_and_linked", user_id=str(user_id), abha_linked=True)
    return {"abha_number": abha_number, "linked": True, "patient_exists": True}
