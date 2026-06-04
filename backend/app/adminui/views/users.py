"""Admin user management views."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")

_ROLES = ["patient", "doctor", "coordinator", "super_admin"]


def _ctx(request: Request, admin: object) -> AuditContext:
    from app.models.identity import User as UserModel
    assert isinstance(admin, UserModel)
    return AuditContext(
        actor_user_id=admin.id,
        actor_role=ActorRole.SUPER_ADMIN,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/users", response_class=HTMLResponse)
async def user_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    search: str = "",
    role: str = "",
    page: int = 1,
) -> HTMLResponse:
    users, total = await admin_repo.list_users(
        db, search=search or None, role_filter=role or None, page=page
    )
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "admin/_users_rows.html" if is_htmx else "admin/users.html"
    return templates.TemplateResponse(
        request,
        template,
        {
            "admin": admin,
            "users": users,
            "total": total,
            "page": page,
            "search": search,
            "role": role,
            "roles": _ROLES,
            "page_size": 30,
        },
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> HTMLResponse:
    ctx = _ctx(request, admin)
    row = await admin_repo.get_user_detail(db, user_id)
    if row is None:
        await write_audit(
            db, ctx, action="admin_view_user", resource_type="user",
            resource_id=user_id, allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user, doctor, patient = row
    await write_audit(
        db, ctx, action="admin_view_user", resource_type="user",
        resource_id=user_id, allowed=True,
    )
    return templates.TemplateResponse(
        request,
        "admin/user_detail.html",
        {"admin": admin, "user": user, "doctor": doctor, "patient": patient},
    )


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await admin_repo.suspend_user(db, user_id)
    allowed = updated is not None
    await write_audit(
        db, ctx, action="admin_suspend_user", resource_type="user",
        resource_id=user_id, allowed=allowed,
        reason=None if allowed else "not_found",
    )
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_302_FOUND)


@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await admin_repo.reactivate_user(db, user_id)
    allowed = updated is not None
    await write_audit(
        db, ctx, action="admin_reactivate_user", resource_type="user",
        resource_id=user_id, allowed=allowed,
        reason=None if allowed else "not_found",
    )
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_302_FOUND)
