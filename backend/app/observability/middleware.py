from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger(__name__)

_SKIP_PATHS = frozenset({"/healthz", "/readyz"})


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
