"""Admin education content endpoints.

GET  /v1/admin/content                  — paginated content library (all statuses)
POST /v1/admin/content                  — create draft content
POST /v1/admin/content/{id}/approve     — doctor approves and publishes

Clinical compliance: every published article must have reviewed_by_doctor_id +
reviewed_at set. The approve endpoint enforces this by recording the approving
doctor's ID at publish time — satisfying the NMC TPG requirement that every
clinical asset traces back to a qualified RMP.
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
from app.core.rbac import get_admin_user, permission_audit_fields, require_permission
from app.db.enums import ActorRole, ContentStatus
from app.repositories import education as edu_repo

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
    user: Annotated[object, Depends(get_admin_user)],
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


@router.post("/content/{content_id}/approve", response_model=ContentAdminRead)
async def approve_content(
    content_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.CONTENT_PUBLISH))],
) -> ContentAdminRead:
    """Publish content with doctor approval.

    The approving user must be a doctor (super_admin role with a dr_doctors row).
    Stores reviewed_by_doctor_id for NMC TPG compliance audit trail.
    """
    from app.repositories import consultations as consultations_repo

    ctx = _audit_ctx(request, user)

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)

    # Resolve doctor row — super_admin approver must have a dr_doctors profile
    doctor = await consultations_repo.get_doctor_record(db, user_id=user.id)
    if doctor is None:
        await write_audit(
            db, ctx,
            action="approve_education_content",
            resource_type="education_content",
            resource_id=content_id,
            allowed=False,
            reason="approver_has_no_doctor_profile",
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="approver_must_be_a_registered_doctor",
        )

    content = await edu_repo.approve_content(db, content_id=content_id, doctor_id=doctor.id)
    if content is None:
        await write_audit(
            db, ctx,
            action="approve_education_content",
            resource_type="education_content",
            resource_id=content_id,
            allowed=False,
            reason="content_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="approve_education_content",
        resource_type="education_content",
        resource_id=content.id,
        allowed=True,
    )
    return ContentAdminRead.model_validate(content)
