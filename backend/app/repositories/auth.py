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
    mfa_verified: bool = False,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id,
        session_id=session_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        parent_id=parent_id,
        mfa_verified=mfa_verified,
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


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Revoke every live refresh token for a user. Returns rows updated.

    Used after a password reset so all existing sessions are forced to re-auth.
    """
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount  # type: ignore[attr-defined, no-any-return]


async def revoke_same_device_sessions(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_agent: str | None,
) -> int:
    """Revoke active sessions from the same device (matched by user_agent).

    Called before minting a new session on login so the same device doesn't
    accumulate duplicate session entries in the linked-devices list.
    """
    if not user_agent:
        return 0
    now = datetime.now(UTC)
    # Find distinct session_ids with matching user_agent that are still live.
    sub = (
        select(RefreshToken.session_id)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.user_agent == user_agent,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .distinct()
        .subquery()
    )
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.session_id.in_(select(sub.c.session_id)),
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    return result.rowcount  # type: ignore[attr-defined, no-any-return]


async def list_active_sessions_for_user(
    db: AsyncSession, *, user_id: uuid.UUID
) -> list[dict[str, object]]:
    """Return one entry per active session (live, unexpired token family).

    Refresh tokens rotate within a ``session_id`` family, so this collapses the
    family to a single device row: earliest token = session start, latest token =
    last activity + current device metadata.
    """
    now = datetime.now(UTC)
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .order_by(RefreshToken.session_id, RefreshToken.created_at)
    )
    sessions: dict[uuid.UUID, dict[str, object]] = {}
    for t in result.scalars().all():
        existing = sessions.get(t.session_id)
        if existing is None:
            sessions[t.session_id] = {
                "session_id": t.session_id,
                "ip_address": str(t.ip_address) if t.ip_address is not None else None,
                "user_agent": t.user_agent,
                "created_at": t.created_at,
                "last_used_at": t.created_at,
                "expires_at": t.expires_at,
            }
        else:
            # Tokens are ordered by created_at asc, so each later row is more recent.
            existing["last_used_at"] = t.created_at
            existing["expires_at"] = t.expires_at
            if t.ip_address is not None:
                existing["ip_address"] = str(t.ip_address)
            if t.user_agent is not None:
                existing["user_agent"] = t.user_agent
    return sorted(
        sessions.values(),
        key=lambda s: s["last_used_at"],  # type: ignore[arg-type, return-value]
        reverse=True,
    )


async def session_belongs_to_user(
    db: AsyncSession, *, session_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """True if any token in the session family is owned by the user.

    Checks ownership regardless of revoked/expired state so revoke is idempotent
    and cross-user probes get the same answer as unknown sessions (404).
    """
    result = await db.execute(
        select(RefreshToken.id)
        .where(
            RefreshToken.session_id == session_id,
            RefreshToken.user_id == user_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


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
