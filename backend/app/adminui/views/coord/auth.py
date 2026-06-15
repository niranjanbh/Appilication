"""Coordinator portal auth views: login and logout."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import (
    _COORD_SESSION_COOKIE,
    clear_coord_session,
    create_coord_session,
)
from app.db.redis import RedisClient, get_redis
from app.db.session import get_db
from app.services import auth as auth_service

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


def _reset_request_args(request: Request) -> dict[str, str]:
    return {
        "ip_address": request.client.host if request.client else "",
        "user_agent": request.headers.get("user-agent", ""),
        "request_id": getattr(request.state, "request_id", ""),
    }


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    next_url = request.query_params.get("next", "/coord/")
    return templates.TemplateResponse(
        request, "coord/login.html", {"next": next_url, "error": None}
    )


@router.post("/login")
async def login_submit(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    email_or_phone: str = Form(...),
    password: str = Form(...),
    next_url: str = Form(default="/coord/"),
) -> Response:
    from app.core.security import verify_password
    from app.db.enums import UserRole
    from app.models.identity import User as UserModel
    from app.repositories import users as users_repo

    user = await users_repo.get_by_email_or_phone(db, email_or_phone)
    if (
        user is None
        or not isinstance(user, UserModel)
        or user.password_hash is None
        or not verify_password(password, user.password_hash)
        or user.role != UserRole.COORDINATOR
    ):
        return templates.TemplateResponse(
            request,
            "coord/login.html",
            {"next": next_url, "error": "Invalid credentials or insufficient role."},
            status_code=status.HTTP_200_OK,
        )

    redirect = RedirectResponse(url=next_url or "/coord/", status_code=status.HTTP_302_FOUND)
    create_coord_session(redirect, user.id)
    return redirect


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "coord/forgot_password.html",
        {"step": "request", "identifier": "", "error": None, "notice": None},
    )


@router.post("/forgot-password")
async def forgot_password_request(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    identifier: str = Form(...),
) -> HTMLResponse:
    await auth_service.request_password_reset(
        db, redis, identifier=identifier.strip(), **_reset_request_args(request)
    )
    return templates.TemplateResponse(
        request,
        "coord/forgot_password.html",
        {
            "step": "confirm",
            "identifier": identifier.strip(),
            "error": None,
            "notice": "If an account exists, a reset code has been sent to its registered channel.",
        },
    )


@router.post("/forgot-password/confirm")
async def forgot_password_confirm(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    identifier: str = Form(...),
    otp: str = Form(...),
    new_password: str = Form(...),
) -> Response:
    from app.core.exceptions import KyrosDomainError

    def _reject(message: str) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "coord/forgot_password.html",
            {"step": "confirm", "identifier": identifier.strip(), "error": message, "notice": None},
            status_code=status.HTTP_200_OK,
        )

    if len(new_password) < 8:
        return _reject("Password must be at least 8 characters.")
    try:
        await auth_service.confirm_password_reset(
            db, redis, identifier=identifier.strip(), otp=otp.strip(),
            new_password=new_password, **_reset_request_args(request),
        )
    except KyrosDomainError:
        return _reject("Incorrect or expired code. Please request a new one.")

    return RedirectResponse(url="/coord/login?reset=ok", status_code=status.HTTP_302_FOUND)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    session_id = request.cookies.get(_COORD_SESSION_COOKIE)
    redirect = RedirectResponse(url="/coord/login", status_code=status.HTTP_302_FOUND)
    if session_id:
        clear_coord_session(redirect, session_id)
    return redirect
