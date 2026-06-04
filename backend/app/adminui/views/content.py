"""Admin education content views."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, ContentStatus
from app.db.session import get_db
from app.repositories import education as edu_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


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


@router.get("/content", response_class=HTMLResponse)
async def content_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    status_filter: str = "",
    page: int = 1,
) -> HTMLResponse:
    from app.db.enums import ContentStatus as ContentStatusEnum
    items, total = await edu_repo.list_all_content(
        db,
        status=ContentStatusEnum(status_filter) if status_filter else None,
        page=page,
        page_size=30,
    )
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "admin/_content_rows.html" if is_htmx else "admin/content.html"
    return templates.TemplateResponse(
        request,
        template,
        {
            "admin": admin,
            "items": items,
            "total": total,
            "page": page,
            "status_filter": status_filter,
            "statuses": [s.value for s in ContentStatus],
            "page_size": 30,
        },
    )


@router.post("/content/{content_id}/publish")
async def publish_content(
    content_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await edu_repo.update_content_status(db, content_id, ContentStatus.PUBLISHED)
    await write_audit(
        db, ctx, action="admin_publish_content", resource_type="content",
        resource_id=content_id, allowed=updated is not None,
        reason=None if updated else "not_found",
    )
    return RedirectResponse(url="/admin/content", status_code=status.HTTP_302_FOUND)


@router.post("/content/{content_id}/archive")
async def archive_content(
    content_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await edu_repo.update_content_status(db, content_id, ContentStatus.ARCHIVED)
    await write_audit(
        db, ctx, action="admin_archive_content", resource_type="content",
        resource_id=content_id, allowed=updated is not None,
        reason=None if updated else "not_found",
    )
    return RedirectResponse(url="/admin/content", status_code=status.HTTP_302_FOUND)
