from __future__ import annotations

import uuid
from typing import Any

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
