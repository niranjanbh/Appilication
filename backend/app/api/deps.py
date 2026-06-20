from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext
from app.core.rbac import (  # noqa: F401 — re-exported for router convenience
    enforce_role,
    get_admin_user,
    get_coordinator_user,
    get_current_user,
    get_doctor_user,
    get_patient_user,
    get_staff_user,
    get_super_admin_user,
)
from app.db.enums import ActorRole
from app.db.redis import RedisClient, get_redis
from app.db.session import get_db

# Re-exports for router convenience
DbSession = Annotated[AsyncSession, Depends(get_db)]
Redis = Annotated[RedisClient, Depends(get_redis)]


async def get_db_dep() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def get_audit_context(request: Request) -> AuditContext:
    ip_address = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    request_id = getattr(request.state, "request_id", "")
    return AuditContext(
        actor_user_id=None,
        actor_role=ActorRole.SYSTEM,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


AuditCtx = Annotated[AuditContext, Depends(get_audit_context)]
