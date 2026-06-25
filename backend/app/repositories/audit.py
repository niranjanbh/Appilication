from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ActorRole
from app.models.audit import AuditLog


async def write(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    actor_role: ActorRole,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    allowed: bool,
    reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    log_metadata: dict[str, Any] | None = None,
    role_context: str | None = None,
    permission: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        allowed=allowed,
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
        log_metadata=log_metadata,
        role_context=role_context,
        permission=permission,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_activity_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AuditLog], int]:
    """Return the user's own meaningful audit entries (newest first) + total.

    Read-only ``view_*``/``list_*`` actions are excluded so the feed shows the
    patient's account/data activity (consents, uploads, sessions, bookings,
    denied attempts) rather than every page load.
    """
    noise_actions = ("token_refresh", "register_push_token", "send_otp")
    base = select(AuditLog).where(
        AuditLog.actor_user_id == user_id,
        ~AuditLog.action.like("view_%"),
        ~AuditLog.action.like("list_%"),
        AuditLog.action.notin_(noise_actions),
    )

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total
