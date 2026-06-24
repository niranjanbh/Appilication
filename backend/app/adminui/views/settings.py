"""Super-admin platform settings — Google Sign-In activation and the default
password-reset OTP channel.

Both are state-changing super-admin actions and are audit-logged via the
platform_settings_service.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session, require_super_admin_session
from app.core.audit import AuditContext
from app.core.config import settings as app_settings
from app.db.enums import ActorRole, OtpResetChannel
from app.db.session import get_db
from app.services import platform_settings_service

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


def _ctx(request: Request, admin: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    return AuditContext(
        actor_user_id=admin.id,
        actor_role=ActorRole(admin.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> HTMLResponse:
    google_enabled = await platform_settings_service.is_google_oauth_enabled(db)
    signup_otp_enabled = await platform_settings_service.is_signup_otp_enabled(db)
    default_channel = await platform_settings_service.get_default_reset_channel(db)
    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {
            "admin": admin,
            "google_enabled": google_enabled,
            "signup_otp_enabled": signup_otp_enabled,
            "default_channel": default_channel.value,
            "google_client_ids_configured": bool(app_settings.google_oauth_client_id_list),
            "saved": request.query_params.get("saved") == "ok",
        },
    )


@router.post("/settings/google-oauth")
async def update_google_oauth(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    enabled: str = Form(default=""),
) -> Response:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = _ctx(request, admin)
    await platform_settings_service.set_google_oauth_enabled(
        db, ctx, enabled=bool(enabled), updated_by=admin.id
    )
    return RedirectResponse(url="/admin/settings?saved=ok", status_code=status.HTTP_302_FOUND)


@router.post("/settings/signup-otp")
async def update_signup_otp(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    enabled: str = Form(default=""),
) -> Response:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = _ctx(request, admin)
    await platform_settings_service.set_signup_otp_enabled(
        db, ctx, enabled=bool(enabled), updated_by=admin.id
    )
    return RedirectResponse(url="/admin/settings?saved=ok", status_code=status.HTTP_302_FOUND)


@router.post("/settings/reset-channel")
async def update_reset_channel(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    channel: str = Form(...),
) -> Response:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    if channel not in ("email", "sms"):
        return RedirectResponse(
            url="/admin/settings", status_code=status.HTTP_302_FOUND
        )
    ctx = _ctx(request, admin)
    await platform_settings_service.set_default_reset_channel(
        db, ctx, channel=OtpResetChannel(channel), updated_by=admin.id
    )
    return RedirectResponse(url="/admin/settings?saved=ok", status_code=status.HTTP_302_FOUND)
