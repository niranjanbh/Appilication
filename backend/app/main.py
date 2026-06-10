from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.adminui.router import admin_router, admin_static
from app.adminui.views.coord.router import coord_router
from app.api.errors import register_exception_handlers
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.observability.middleware import (
    AccessLogMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.observability.sentry import init_sentry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(debug=settings.debug)
    init_sentry()
    if settings.startup_schema_check:
        from app.db.schema_check import assert_schema_is_current
        from app.db.session import engine
        await assert_schema_is_current(engine)
    yield
    from app.db.session import engine
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Kyros API",
        version=settings.app_version,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(
        SecurityHeadersMiddleware, production=settings.app_env == "production"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    )
    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/v1")
    app.include_router(admin_router, prefix="/admin")
    app.mount("/admin/static", admin_static, name="admin-static")
    app.include_router(coord_router, prefix="/coord")
    app.mount("/coord/static", admin_static, name="coord-static")

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz() -> JSONResponse:
        from sqlalchemy import text

        from app.db.redis import get_redis_client
        from app.db.session import engine

        checks: dict[str, str] = {}
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"
        redis = get_redis_client()
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
        finally:
            await redis.aclose()
        healthy = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={"status": "ok" if healthy else "degraded", **checks},
        )

    return app


app = create_app()
