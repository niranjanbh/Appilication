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
from app.db.session import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


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


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    session_id = request.cookies.get(_COORD_SESSION_COOKIE)
    redirect = RedirectResponse(url="/coord/login", status_code=status.HTTP_302_FOUND)
    if session_id:
        clear_coord_session(redirect, session_id)
    return redirect
