"""Sign-off repository — write/read ad_sign_off_records (append-only)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sign_off import SignOffRecord


async def create_sign_off(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
    doctor_id: uuid.UUID,
    nmc_registration_number: str,
    artifact_hash: str,
    action: str,
    notes: str | None,
) -> SignOffRecord:
    record = SignOffRecord(
        content_id=content_id,
        doctor_id=doctor_id,
        nmc_registration_number=nmc_registration_number,
        artifact_hash=artifact_hash,
        action=action,
        notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


async def list_for_content(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
) -> list[SignOffRecord]:
    result = await db.execute(
        select(SignOffRecord)
        .where(SignOffRecord.content_id == content_id)
        .order_by(SignOffRecord.signed_at.asc())
    )
    return list(result.scalars().all())
