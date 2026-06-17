"""Repository-level helpers for the DPDP erasure-with-legal-hold workflow (P39).

Two concerns:
  1. anonymize_pii_values — pure function returning the UPDATE dict for a user row.
     No DB access; fully unit-testable.
  2. apply_legal_hold — sets legal_hold_until on all consultations and prescriptions
     belonging to a user.  Idempotent (only updates rows where legal_hold_until IS NULL).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Consultation, Patient, Prescription


def anonymize_pii_values(user_id: uuid.UUID, now: datetime) -> dict[str, Any]:
    """Return the SQLAlchemy UPDATE values for anonymizing a user's PII.

    Erased email is deterministic and unique: erased-<uuid>@erased.kyros.local.
    Phone is set to NULL (avoids unique-constraint conflicts; multiple erased
    users may have had different numbers, NULL doesn't violate uniqueness in Postgres).
    """
    return {
        "name": "Deleted User",
        "email": f"erased-{user_id}@erased.kyros.local",
        "phone": None,
        "date_of_birth": None,
        "city": None,
        "state": None,
        "expo_push_token": None,
        "google_sub": None,
        "password_hash": None,
        "reset_otp_channel": None,
        "erased_at": now,
        "deleted_at": now,
    }


async def apply_legal_hold(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    hold_until: datetime,
    reason: str,
) -> tuple[int, int]:
    """Stamp legal_hold_until on all consultations + their prescriptions for user_id.

    Only rows where legal_hold_until IS NULL are updated (idempotent — safe to run twice).
    Returns (consult_count, prescription_count) for inclusion in DSR audit notes.
    """
    # Resolve the kc_patients.id for this user first.
    patient_row = await db.execute(
        select(Patient.id).where(Patient.user_id == user_id)
    )
    patient_id = patient_row.scalar_one_or_none()

    if patient_id is None:
        # No patient profile — nothing to hold.
        return 0, 0

    # Step 1: update consultations
    consult_result = await db.execute(
        update(Consultation)
        .where(
            Consultation.patient_id == patient_id,
            Consultation.legal_hold_until.is_(None),
        )
        .values(legal_hold_until=hold_until, legal_hold_reason=reason)
        .returning(Consultation.id)
    )
    consult_ids = [row[0] for row in consult_result.fetchall()]
    consult_count = len(consult_ids)

    rx_count = 0
    if consult_ids:
        # Step 2: update prescriptions for those consultations
        rx_result = await db.execute(
            update(Prescription)
            .where(
                Prescription.consultation_id.in_(consult_ids),
                Prescription.legal_hold_until.is_(None),
            )
            .values(legal_hold_until=hold_until, legal_hold_reason=reason)
            .returning(Prescription.id)
        )
        rx_count = len(rx_result.fetchall())

    return consult_count, rx_count
