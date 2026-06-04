from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adminui.router import admin_router, admin_static
from app.adminui.views.coord.router import coord_router
from app.api.errors import register_exception_handlers
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.observability.middleware import AccessLogMiddleware, RequestIDMiddleware
from app.observability.sentry import init_sentry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(debug=settings.debug)
    init_sentry()
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
    async def readyz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
