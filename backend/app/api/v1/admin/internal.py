"""Admin internal diagnostic endpoints — super_admin only.

GET /v1/admin/internal/db-pool-status   — SQLAlchemy connection pool stats
GET /v1/admin/internal/health-detail    — deep health check with timing (DB + Redis)

Not exposed in the public OpenAPI schema (hidden=True). Every call is audit-logged.
"""

from __future__ import annotations

import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.deps import DbSession, Redis
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_admin_user
from app.db.enums import ActorRole
from app.db.session import engine

router = APIRouter(tags=["admin-internal"], include_in_schema=False)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


# ── Schemas ────────────────────────────────────────────────────────────────────


class PoolStatusResponse(BaseModel):
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    status_string: str


class HealthDetailResponse(BaseModel):
    db_ok: bool
    db_latency_ms: float
    redis_ok: bool
    redis_latency_ms: float
    overall: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/internal/db-pool-status", response_model=PoolStatusResponse)
async def get_db_pool_status(
    request: Request,
    db: DbSession,
    user: Annotated[Any, Depends(get_admin_user)],
) -> PoolStatusResponse:
    ctx = _audit_ctx(request, user)
    await write_audit(
        db,
        ctx,
        action="view_db_pool_status",
        resource_type="internal",
        resource_id=None,
        allowed=True,
    )

    pool = engine.pool
    return PoolStatusResponse(
        pool_size=pool.size(),  # type: ignore[attr-defined]
        checked_in=pool.checkedin(),  # type: ignore[attr-defined]
        checked_out=pool.checkedout(),  # type: ignore[attr-defined]
        overflow=pool.overflow(),  # type: ignore[attr-defined]
        status_string=pool.status(),
    )


@router.get("/internal/health-detail", response_model=HealthDetailResponse)
async def get_health_detail(
    request: Request,
    db: DbSession,
    redis: Redis,
    user: Annotated[Any, Depends(get_admin_user)],
) -> HealthDetailResponse:
    ctx = _audit_ctx(request, user)
    await write_audit(
        db,
        ctx,
        action="view_health_detail",
        resource_type="internal",
        resource_id=None,
        allowed=True,
    )

    # DB check
    db_ok = False
    db_latency_ms = -1.0
    try:
        from sqlalchemy import text

        t0 = time.perf_counter()
        await db.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_ok = True
    except Exception:
        pass

    # Redis check
    redis_ok = False
    redis_latency_ms = -1.0
    try:
        probe_key = f"healthcheck:{uuid.uuid4().hex}"
        t0 = time.perf_counter()
        await redis.set(probe_key, "1", ex=5)
        await redis.delete(probe_key)
        redis_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        redis_ok = True
    except Exception:
        pass

    overall = "ok" if (db_ok and redis_ok) else "degraded"
    return HealthDetailResponse(
        db_ok=db_ok,
        db_latency_ms=db_latency_ms,
        redis_ok=redis_ok,
        redis_latency_ms=redis_latency_ms,
        overall=overall,
    )
