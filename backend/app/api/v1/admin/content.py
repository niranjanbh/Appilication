"""Admin education content endpoints.

GET  /v1/admin/content                          — paginated content library (all statuses)
POST /v1/admin/content                          — create draft content
POST /v1/admin/content/{id}/submit-for-review   — DRAFT → PENDING_REVIEW (any admin level)
POST /v1/admin/content/{id}/publish             — APPROVED → PUBLISHED (CONTENT_PUBLISH)

Clinical compliance: every published article must have reviewed_by_doctor_id + reviewed_at set
(set at doctor-review time). The NMC TPG requirement that every clinical asset traces back to a
qualified RMP is enforced in the doctor review step (POST /v1/doctor/content/{id}/review), not here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission
from app.core.rbac import (
    enforce_role,
    get_admin_user,
    get_super_admin_user,
    permission_audit_fields,
    require_permission,
)
from app.db.enums import ActorRole, ContentStatus, UserRole
from app.repositories import education as edu_repo
from app.services import sign_off_service
from app.services.sign_off_service import SignOffError

router = APIRouter(tags=["admin-content"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class ContentCreate(BaseModel):
    title: str
    slug: str
    content_type: str
    condition_categories: list[str]
    content_url: str | None = None
    body_md: str | None = None
    ai_disclosure: bool = False


class ContentAdminRead(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    content_type: str
    condition_categories: list[Any]
    content_url: str | None
    body_md: str | None
    reviewed_by_doctor_id: uuid.UUID | None
    reviewed_at: datetime | None
    status: str
    ai_disclosure: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentListResponse(BaseModel):
    items: list[ContentAdminRead]
    total: int
    page: int
    page_size: int


# ── Helpers ────────────────────────────────────────────────────────────────────


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    role_context, permission = permission_audit_fields(request)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
        role_context=role_context,
        permission=permission,
    )


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/content", response_model=ContentListResponse)
async def list_content(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    content_status: ContentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ContentListResponse:
    ctx = _audit_ctx(request, user)
    items, total = await edu_repo.list_all_content(
        db, status=content_status, page=page, page_size=page_size
    )
    await write_audit(
        db, ctx,
        action="list_education_content",
        resource_type="education_content",
        allowed=True,
    )
    return ContentListResponse(
        items=[ContentAdminRead.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/content", response_model=ContentAdminRead, status_code=status.HTTP_201_CREATED)
async def create_content(
    body: ContentCreate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_super_admin_user)],
) -> ContentAdminRead:
    ctx = _audit_ctx(request, user)

    content = await edu_repo.create_content(
        db,
        title=body.title,
        slug=body.slug,
        content_type=body.content_type,
        condition_categories=body.condition_categories,
        content_url=body.content_url,
        body_md=body.body_md,
        ai_disclosure=body.ai_disclosure,
    )
    await write_audit(
        db, ctx,
        action="create_education_content",
        resource_type="education_content",
        resource_id=content.id,
        allowed=True,
    )
    return ContentAdminRead.model_validate(content)


@router.post(
    "/content/{content_id}/submit-for-review",
    response_model=ContentAdminRead,
)
async def submit_content_for_review(
    content_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(enforce_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
) -> ContentAdminRead:
    """Transition DRAFT → PENDING_REVIEW. Any admin level can submit."""
    ctx = _audit_ctx(request, user)

    try:
        content = await sign_off_service.submit_for_review(db, content_id=content_id)
    except SignOffError as exc:
        await write_audit(
            db, ctx,
            action="submit_content_for_review",
            resource_type="education_content",
            resource_id=content_id,
            allowed=False,
            reason=exc.code,
        )
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.code) from exc

    await write_audit(
        db, ctx,
        action="submit_content_for_review",
        resource_type="education_content",
        resource_id=content.id,
        allowed=True,
    )
    return ContentAdminRead.model_validate(content)


@router.post("/content/{content_id}/publish", response_model=ContentAdminRead)
async def publish_content(
    content_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.CONTENT_PUBLISH))],
) -> ContentAdminRead:
    """Transition APPROVED → PUBLISHED. Requires CONTENT_PUBLISH permission (super_admin)."""
    ctx = _audit_ctx(request, user)

    try:
        content = await sign_off_service.publish_content(db, content_id=content_id)
    except SignOffError as exc:
        await write_audit(
            db, ctx,
            action="publish_education_content",
            resource_type="education_content",
            resource_id=content_id,
            allowed=False,
            reason=exc.code,
        )
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.code) from exc

    await write_audit(
        db, ctx,
        action="publish_education_content",
        resource_type="education_content",
        resource_id=content.id,
        allowed=True,
    )
    return ContentAdminRead.model_validate(content)
