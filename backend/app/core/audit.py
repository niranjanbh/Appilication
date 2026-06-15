from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ActorRole


@dataclass
class AuditContext:
    actor_user_id: uuid.UUID | None
    actor_role: ActorRole
    ip_address: str
    user_agent: str
    request_id: str
    # Set when the action was authorized via require_permission: the role-context
    # the action was taken under, and the resource:action permission exercised.
    role_context: str | None = None
    permission: str | None = None


async def write_audit(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    allowed: bool,
    reason: str | None = None,
    log_metadata: dict[str, Any] | None = None,
) -> None:
    from app.repositories import audit as audit_repo  # lazy — avoids load-time circular

    await audit_repo.write(
        db,
        actor_user_id=ctx.actor_user_id,
        actor_role=ctx.actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        allowed=allowed,
        reason=reason,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
        log_metadata=log_metadata,
        role_context=ctx.role_context,
        permission=ctx.permission,
    )
