"""Doctor content review endpoints (P37).

GET  /v1/doctor/content                     — pending-review queue (CONTENT_APPROVE)
POST /v1/doctor/content/{content_id}/review — approve or reject (CONTENT_APPROVE)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission
from app.core.rbac import permission_audit_fields, require_permission
from app.db.enums import ActorRole
from app.repositories import education as edu_repo
from app.services import sign_off_service
from app.services.sign_off_service import _OWNERSHIP_CODES, SignOffError

router = APIRouter(tags=["doctor-content"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class ContentDoctorRead(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    content_type: str
    condition_categories: list[str]
    body_md: str | None
    content_url: str | None
    ai_disclosure: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentReviewBody(BaseModel):
    action: Literal["approved", "rejected"]
    notes: str | None = None


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


def _sign_off_http_error(exc: SignOffError) -> HTTPException:
    if exc.code in _OWNERSHIP_CODES:
        return HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
    return HTTPException(status.HTTP_409_CONFLICT, detail=exc.code)


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/content", response_model=list[ContentDoctorRead])
async def list_pending_review_content(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.CONTENT_APPROVE))],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> list[ContentDoctorRead]:
    ctx = _audit_ctx(request, user)
    items, _ = await edu_repo.list_pending_review(db, page=page, page_size=page_size)
    await write_audit(
        db, ctx,
        action="list_pending_review_content",
        resource_type="education_content",
        allowed=True,
    )
    return [ContentDoctorRead.model_validate(c) for c in items]


@router.post(
    "/content/{content_id}/review",
    response_model=ContentDoctorRead,
)
async def review_content(
    content_id: uuid.UUID,
    body: ContentReviewBody,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.CONTENT_APPROVE))],
) -> ContentDoctorRead:
    ctx = _audit_ctx(request, user)

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)

    try:
        content = await sign_off_service.doctor_review(
            db,
            content_id=content_id,
            doctor_user_id=user.id,
            action=body.action,
            notes=body.notes,
        )
    except SignOffError as exc:
        await write_audit(
            db, ctx,
            action="doctor_review_content",
            resource_type="education_content",
            resource_id=content_id,
            allowed=False,
            reason=exc.code,
        )
        await db.commit()
        raise _sign_off_http_error(exc) from exc

    await write_audit(
        db, ctx,
        action="doctor_review_content",
        resource_type="education_content",
        resource_id=content.id,
        allowed=True,
    )
    return ContentDoctorRead.model_validate(content)
