from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from typing import Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings
from app.db.enums import ActorRole

logger = structlog.get_logger(__name__)

_SKIP_PATHS = frozenset({"/healthz", "/readyz"})
# Paths exempt from PHIAuditMiddleware's denial-audit writes: no PHI is ever reached
# on these (auth/public/webhook endpoints, health checks, API docs).
_PHI_AUDIT_EXEMPT_PREFIXES = ("/v1/auth", "/v1/public", "/v1/webhooks")


class RequestIDMiddleware:
    """Pure-ASGI middleware — does NOT use BaseHTTPMiddleware/anyio task groups.

    Reads X-Request-ID from the request headers (or generates one), stores it
    on scope["state"]["request_id"], binds it to the structlog context, and
    echoes it back in the response headers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        raw_headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        request_id = next(
            (v.decode() for k, v in raw_headers if k.lower() == b"x-request-id"),
            None,
        ) or str(uuid.uuid4())

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = dict(message)
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            structlog.contextvars.clear_contextvars()


class SecurityHeadersMiddleware:
    """Pure-ASGI middleware adding security response headers.

    HSTS is only emitted in production (TLS terminates at the ALB; sending it
    over plain-HTTP dev would be ignored anyway). Cache-Control: no-store is
    forced on /v1 API responses so PHI never lands in shared caches; existing
    Cache-Control headers set by a route are respected.
    """

    def __init__(self, app: ASGIApp, *, production: bool) -> None:
        self.app = app
        self.production = production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                existing = {k.lower() for k, _ in headers}
                additions: list[tuple[bytes, bytes]] = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                ]
                if self.production:
                    additions.append((
                        b"strict-transport-security",
                        b"max-age=31536000; includeSubDomains; preload",
                    ))
                if path.startswith("/v1") and b"cache-control" not in existing:
                    additions.append((b"cache-control", b"no-store"))
                headers.extend((k, v) for k, v in additions if k not in existing)
                message = dict(message)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, _send)


class AccessLogMiddleware:
    """Pure-ASGI access-log middleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path in _SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        start = time.perf_counter()
        status_code: list[int] = []

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code.append(message["status"])
            await send(message)

        await self.app(scope, receive, _send)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        state: Any = scope.get("state", {})
        request_id = getattr(state, "request_id", state.get("request_id", "") if isinstance(state, dict) else "")

        logger.info(
            "http_request",
            method=method,
            path=path,
            status=status_code[0] if status_code else 0,
            duration_ms=duration_ms,
            request_id=request_id,
        )


def _is_phi_audit_exempt(path: str) -> bool:
    if path in _SKIP_PATHS or path in (settings.docs_url, settings.openapi_url):
        return True
    return any(path.startswith(prefix) for prefix in _PHI_AUDIT_EXEMPT_PREFIXES)


def _resource_from_path_params(
    path_params: Mapping[str, Any],
) -> tuple[str | None, uuid.UUID | None]:
    """Derive (resource_type, resource_id) from the route's path params.

    Takes the last path-param key ending in ``_id`` — e.g. ``report_id`` on
    ``/v1/doctor/patients/{patient_id}/lab-reports/{report_id}/annotate`` yields
    ``resource_type="report"``. Returns ``(None, None)`` if no such key exists or
    its value does not parse as a UUID.
    """
    resource_key: str | None = None
    for key in path_params:
        if key.endswith("_id"):
            resource_key = key

    if resource_key is None:
        return None, None

    try:
        resource_id = uuid.UUID(str(path_params[resource_key]))
    except (ValueError, AttributeError, TypeError):
        return None, None

    return resource_key.removesuffix("_id"), resource_id


class PHIAuditMiddleware:
    """Pure-ASGI middleware that audit-logs role/permission-level access denials.

    Closes the denial-side half of staff-rbac-spec §5 ("audit is middleware, not
    per-endpoint"). app.core.rbac (get_current_user, require_mfa, enforce_role,
    require_permission) and app.adminui.deps (require_admin_session,
    require_coord_session, require_super_admin_session) stamp scope["state"] with
    actor_user_id/actor_role and a deny_reason before raising 401/403. This
    middleware reads those stamps after the response is produced and writes a
    denial row to ad_audit_log.

    Deliberately does not log the allowed path (stays per-handler, P31) or 401s
    where no actor could be identified (no PHI was reached).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.phi_audit_middleware_enabled:
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if _is_phi_audit_exempt(path):
            await self.app(scope, receive, send)
            return

        status_code: list[int] = []

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code.append(message["status"])
            await send(message)

        await self.app(scope, receive, _send)

        if not status_code or status_code[0] not in (401, 403):
            return

        state: dict[str, Any] = scope.get("state", {})
        if state.get("actor_user_id") is None:
            return

        await self._write_denial(scope, state, status_code[0])

    async def _write_denial(self, scope: Scope, state: dict[str, Any], status_code: int) -> None:
        from app.core.audit import AuditContext, write_audit
        from app.db.session import AsyncSessionLocal

        try:
            method: str = scope.get("method", "")
            path: str = scope.get("path", "")
            raw_headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
            user_agent = next(
                (v.decode() for k, v in raw_headers if k.lower() == b"user-agent"), ""
            )
            client = scope.get("client")
            ip_address = client[0] if client else ""

            ctx = AuditContext(
                actor_user_id=state["actor_user_id"],
                actor_role=state.get("actor_role", ActorRole.SYSTEM),
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=state.get("request_id", ""),
                role_context=state.get("role_context"),
                permission=state.get("permission"),
            )
            resource_type, resource_id = _resource_from_path_params(scope.get("path_params", {}))

            async with AsyncSessionLocal() as db:
                await write_audit(
                    db,
                    ctx,
                    action=f"{method} {path}"[:100],
                    resource_type=resource_type,
                    resource_id=resource_id,
                    allowed=False,
                    reason=state.get("deny_reason", "access_denied"),
                )
                await db.commit()
        except Exception:
            logger.warning(
                "phi_audit.write_failed", path=scope.get("path", ""), status=status_code
            )
