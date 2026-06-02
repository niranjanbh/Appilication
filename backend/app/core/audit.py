from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass
class AuditContext:
    actor_user_id: UUID
    actor_role: str
    ip_address: str
    user_agent: str
    request_id: str


async def write_audit(
    db: Any,
    ctx: AuditContext,
    *,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    allowed: bool,
    reason: str = "",
) -> None:
    """Write an audit log entry. Wired to ad_audit_log in P2."""
    _ = db, ctx, action, resource_type, resource_id, allowed, reason
