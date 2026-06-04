from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import RefreshToken


async def create_refresh_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
    parent_id: uuid.UUID | None = None,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id,
        session_id=session_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        parent_id=parent_id,
    )
    db.add(token)
    await db.flush()
    return token


async def get_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def revoke_token(db: AsyncSession, token_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == token_id)
        .values(revoked_at=datetime.now(UTC))
    )


async def revoke_session_family(db: AsyncSession, session_id: uuid.UUID) -> int:
    """Revoke all tokens in a session family. Returns number of rows updated."""
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.session_id == session_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount  # type: ignore[attr-defined, no-any-return]
