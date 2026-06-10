"""Security hardening: production config validation, security headers,
per-IP rate limiting, and the schema-head startup check."""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings, settings

GOOD_JWT_SECRET = "prod_jwt_secret_minimum_32_characters_aaaa"
GOOD_OTP_SECRET = "prod_otp_secret_minimum_32_characters_bbbb"


def _prod_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "_env_file": None,
        "app_env": "production",
        "debug": False,
        "jwt_secret": GOOD_JWT_SECRET,
        "otp_secret": GOOD_OTP_SECRET,
        "cors_allowed_origins": ["https://kyrosclinic.com"],
    }
    kwargs.update(overrides)
    return kwargs


# ── Production settings validation (security rule 8) ─────────────────────────


def test_production_rejects_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="KYROS_JWT_SECRET"):
        Settings(**_prod_kwargs(jwt_secret="CHANGEME_minimum_32_chars_xxxxxxxxxxxxxxxx"))


def test_production_rejects_placeholder_otp_secret() -> None:
    with pytest.raises(ValidationError, match="KYROS_OTP_SECRET"):
        Settings(**_prod_kwargs(otp_secret="CHANGEME_minimum_32_chars_yyyyyyyyyyyyyyyy"))


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(ValidationError, match="KYROS_DEBUG"):
        Settings(**_prod_kwargs(debug=True))


def test_production_rejects_localhost_cors_origins() -> None:
    with pytest.raises(ValidationError, match="CORS"):
        Settings(**_prod_kwargs(cors_allowed_origins=["http://localhost:3000"]))


def test_production_accepts_safe_config() -> None:
    cfg = Settings(**_prod_kwargs())
    assert cfg.app_env == "production"
    assert cfg.openapi_url is None
    assert cfg.docs_url is None


def test_development_accepts_placeholder_secrets() -> None:
    cfg = Settings(_env_file=None, app_env="development")
    assert cfg.app_env == "development"


# ── Security headers middleware ───────────────────────────────────────────────


async def test_security_headers_present() -> None:
    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/healthz")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "permissions-policy" in resp.headers
    # HSTS only in production; tests run in development
    assert "strict-transport-security" not in resp.headers


async def test_v1_responses_are_never_cached() -> None:
    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/v1/nonexistent")
    assert resp.headers.get("cache-control") == "no-store"


async def test_hsts_emitted_in_production_mode() -> None:
    from app.observability.middleware import SecurityHeadersMiddleware

    inner = FastAPI()

    @inner.get("/x")
    async def x() -> dict[str, bool]:
        return {"ok": True}

    transport = ASGITransport(app=SecurityHeadersMiddleware(inner, production=True))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/x")
    assert resp.headers["strict-transport-security"].startswith("max-age=")


# ── Per-IP rate limiting ──────────────────────────────────────────────────────


def _limited_app(redis_obj: Any, scope: str, limit: int) -> FastAPI:
    from app.api.errors import register_exception_handlers
    from app.core.ratelimit import rate_limit
    from app.db.redis import get_redis

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/limited", dependencies=[Depends(rate_limit(scope, limit=limit))])
    async def limited() -> dict[str, bool]:
        return {"ok": True}

    async def _override() -> AsyncGenerator[Any, None]:
        yield redis_obj

    app.dependency_overrides[get_redis] = _override
    return app


async def test_rate_limit_blocks_after_limit(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    scope = f"test_{uuid.uuid4().hex[:8]}"
    app = _limited_app(redis_client, scope, limit=2)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        assert (await c.get("/limited")).status_code == 200
        assert (await c.get("/limited")).status_code == 200
        resp = await c.get("/limited")
    assert resp.status_code == 429
    assert "rate_limited" in resp.text


async def test_rate_limit_fails_open_when_redis_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)

    class BrokenRedis:
        def pipeline(self, transaction: bool = True) -> Any:
            raise ConnectionError("redis unavailable")

    app = _limited_app(BrokenRedis(), f"test_{uuid.uuid4().hex[:8]}", limit=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        assert (await c.get("/limited")).status_code == 200
        assert (await c.get("/limited")).status_code == 200


async def test_rate_limit_noop_when_disabled(redis_client: Any) -> None:
    assert settings.rate_limit_enabled is False
    scope = f"test_{uuid.uuid4().hex[:8]}"
    app = _limited_app(redis_client, scope, limit=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        assert (await c.get("/limited")).status_code == 200
        assert (await c.get("/limited")).status_code == 200


# ── Schema-head startup check (security rule 15) ─────────────────────────────


def test_script_heads_resolves() -> None:
    from app.db.schema_check import script_heads

    heads = script_heads()
    assert len(heads) == 1


async def test_schema_check_passes_on_migrated_db() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from app.db.schema_check import assert_schema_is_current

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        await assert_schema_is_current(engine)
    finally:
        await engine.dispose()
