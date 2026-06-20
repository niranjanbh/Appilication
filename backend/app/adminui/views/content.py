"""Admin education content views."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session, require_super_admin_session
from app.adminui.schemas import admin as admin_schemas
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, ContentStatus, ContentType
from app.db.session import get_db
from app.repositories import education as edu_repo
from app.services import sign_off_service
from app.services.sign_off_service import SignOffError

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
            "items": admin_schemas.content_list(items),
            "total": total,
            "page": page,
            "status_filter": status_filter,
            "statuses": [s.value for s in ContentStatus],
            "page_size": 30,
        },
    )


@router.get("/content/new", response_class=HTMLResponse)
async def content_new_form(
    request: Request,
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin/content_new.html",
        {
            "admin": admin,
            "content_types": [t.value for t in ContentType],
            "error": None,
            "values": {},
        },
    )


@router.post("/content/new")
async def content_create(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    title: str = Form(...),
    slug: str = Form(...),
    content_type: str = Form(...),
    condition_categories: str = Form(default=""),
    content_url: str = Form(default=""),
    body_md: str = Form(default=""),
    ai_disclosure: str = Form(default=""),
) -> Response:
    ctx = _ctx(request, admin)

    title = title.strip()
    slug = slug.strip()
    categories = [c.strip() for c in condition_categories.split(",") if c.strip()]

    def _reject(message: str) -> Response:
        return templates.TemplateResponse(
            request,
            "admin/content_new.html",
            {
                "admin": admin,
                "content_types": [t.value for t in ContentType],
                "error": message,
                "values": {
                    "title": title, "slug": slug, "content_type": content_type,
                    "condition_categories": condition_categories,
                    "content_url": content_url, "body_md": body_md,
                },
            },
            status_code=status.HTTP_200_OK,
        )

    if len(title) < 2:
        return _reject("Please enter a title.")
    if not slug:
        return _reject("Please enter a slug.")
    try:
        ContentType(content_type)
    except ValueError:
        return _reject("Unknown content type.")
    if not categories:
        return _reject("Add at least one condition category.")

    content = await edu_repo.create_content(
        db,
        title=title,
        slug=slug,
        content_type=content_type,
        condition_categories=categories,
        content_url=content_url.strip() or None,
        body_md=body_md.strip() or None,
        ai_disclosure=bool(ai_disclosure),
    )
    await write_audit(
        db, ctx, action="create_education_content", resource_type="education_content",
        resource_id=content.id, allowed=True,
    )
    return RedirectResponse(
        url="/admin/content?success=created", status_code=status.HTTP_302_FOUND
    )


@router.post("/content/{content_id}/submit-for-review")
async def submit_content_for_review(
    content_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> RedirectResponse:
    """Transition DRAFT → PENDING_REVIEW. Any admin tier can submit."""
    ctx = _ctx(request, admin)

    try:
        content = await sign_off_service.submit_for_review(db, content_id=content_id)
    except SignOffError as exc:
        await write_audit(
            db, ctx, action="submit_content_for_review", resource_type="education_content",
            resource_id=content_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        return RedirectResponse(
            url=f"/admin/content?error={exc.code}", status_code=status.HTTP_302_FOUND
        )

    await write_audit(
        db, ctx, action="submit_content_for_review", resource_type="education_content",
        resource_id=content.id, allowed=True,
    )
    return RedirectResponse(
        url="/admin/content?success=submitted", status_code=status.HTTP_302_FOUND
    )


@router.post("/content/{content_id}/publish")
async def publish_content(
    content_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)

    try:
        await sign_off_service.publish_content(db, content_id=content_id)
    except SignOffError as exc:
        await write_audit(
            db, ctx, action="admin_publish_content", resource_type="content",
            resource_id=content_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        return RedirectResponse(
            url=f"/admin/content?error={exc.code}", status_code=status.HTTP_302_FOUND
        )

    await write_audit(
        db, ctx, action="admin_publish_content", resource_type="content",
        resource_id=content_id, allowed=True,
    )
    return RedirectResponse(
        url="/admin/content?success=published", status_code=status.HTTP_302_FOUND
    )


@router.post("/content/{content_id}/archive")
async def archive_content(
    content_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await edu_repo.update_content_status(db, content_id, ContentStatus.ARCHIVED)
    await write_audit(
        db, ctx, action="admin_archive_content", resource_type="content",
        resource_id=content_id, allowed=updated is not None,
        reason=None if updated else "not_found",
    )
    return RedirectResponse(url="/admin/content", status_code=status.HTTP_302_FOUND)
