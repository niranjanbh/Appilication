from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import KyrosDomainError, PhoneNotVerifiedError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=422,
            content={"detail": jsonable_encoder(exc.errors()), "request_id": request_id},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=409,
            content={"detail": "conflict", "request_id": request_id},
        )

    @app.exception_handler(KyrosDomainError)
    async def domain_error_handler(
        request: Request, exc: KyrosDomainError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        content: dict[str, object] = {"detail": exc.detail, "request_id": request_id}
        if isinstance(exc, PhoneNotVerifiedError) and exc.phone:
            content["phone"] = exc.phone
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=500,
            content={"detail": "internal_server_error", "request_id": request_id},
        )
