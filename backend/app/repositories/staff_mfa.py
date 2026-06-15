from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import StaffMfa


async def get_for_user(db: AsyncSession, user_id: uuid.UUID) -> StaffMfa | None:
    result = await db.execute(select(StaffMfa).where(StaffMfa.user_id == user_id))
    return result.scalar_one_or_none()


async def upsert_pending(db: AsyncSession, user_id: uuid.UUID, secret_encrypted: str) -> StaffMfa:
    """Create or replace the pending (unconfirmed) TOTP secret for a user.

    Resets ``enabled_at`` and ``recovery_codes`` — a fresh enrollment invalidates any
    prior confirmation until ``confirm`` is called again.
    """
    existing = await get_for_user(db, user_id)
    if existing is None:
        entry = StaffMfa(
            user_id=user_id,
            totp_secret_encrypted=secret_encrypted,
            recovery_codes=[],
            enabled_at=None,
        )
        db.add(entry)
        await db.flush()
        return entry

    existing.totp_secret_encrypted = secret_encrypted
    existing.recovery_codes = []
    existing.enabled_at = None
    await db.flush()
    return existing


async def confirm(db: AsyncSession, user_id: uuid.UUID, recovery_code_hashes: list[str]) -> None:
    entry = await get_for_user(db, user_id)
    if entry is None:
        return
    entry.enabled_at = datetime.now(UTC)
    entry.recovery_codes = recovery_code_hashes
    await db.flush()


async def disable(db: AsyncSession, user_id: uuid.UUID) -> None:
    entry = await get_for_user(db, user_id)
    if entry is None:
        return
    await db.delete(entry)
    await db.flush()


async def consume_recovery_code(db: AsyncSession, user_id: uuid.UUID, code_hash: str) -> bool:
    """Remove ``code_hash`` from the user's recovery codes if present.

    Returns whether the code was present (and thus consumed).
    """
    entry = await get_for_user(db, user_id)
    if entry is None or code_hash not in entry.recovery_codes:
        return False
    # Reassign (not mutate in place) so SQLAlchemy detects the JSONB change.
    entry.recovery_codes = [c for c in entry.recovery_codes if c != code_hash]
    await db.flush()
    return True
