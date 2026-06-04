"""Patient-facing education content endpoints.

GET  /v1/clinic/patient/education                  — list assignments + browsable library
GET  /v1/clinic/patient/education/{content_id}     — content detail (published only)
POST /v1/clinic/patient/education/{assignment_id}/read — mark assignment read
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import education as edu_repo

router = APIRouter(tags=["patient-education"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class EducationContentRead(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    content_type: str
    condition_categories: list[Any]
    content_url: str | None
    body_md: str | None
    ai_disclosure: bool
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class AssignmentRead(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    consultation_id: uuid.UUID | None
    notes: str | None
    read_at: datetime | None
    created_at: datetime
    content: EducationContentRead

    model_config = {"from_attributes": True}


class PatientEducationResponse(BaseModel):
    assignments: list[AssignmentRead]
    library: list[EducationContentRead]
    library_total: int


class ReadResponse(BaseModel):
    assignment_id: uuid.UUID
    read_at: datetime


# ── Helpers ────────────────────────────────────────────────────────────────────


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/education", response_model=PatientEducationResponse)
async def list_patient_education(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> PatientEducationResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    pairs = await edu_repo.list_assignments_for_patient(db, patient_user_id=user.id)
    library, total = await edu_repo.list_published(db, page=page, page_size=page_size)

    await write_audit(
        db, ctx,
        action="list_education",
        resource_type="education_content",
        allowed=True,
    )

    assignments = [
        AssignmentRead(
            id=a.id,
            content_id=a.content_id,
            consultation_id=a.consultation_id,
            notes=a.notes,
            read_at=a.read_at,
            created_at=a.created_at,
            content=EducationContentRead.model_validate(c),
        )
        for a, c in pairs
    ]
    return PatientEducationResponse(
        assignments=assignments,
        library=[EducationContentRead.model_validate(c) for c in library],
        library_total=total,
    )


@router.get("/education/{content_id}", response_model=EducationContentRead)
async def get_education_content(
    content_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> EducationContentRead:
    ctx = _audit_ctx(request, user)

    content = await edu_repo.get_content_by_id(db, content_id=content_id, published_only=True)
    if content is None:
        await write_audit(
            db, ctx,
            action="view_education_content",
            resource_type="education_content",
            resource_id=content_id,
            allowed=False,
            reason="not_found_or_unpublished",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="view_education_content",
        resource_type="education_content",
        resource_id=content.id,
        allowed=True,
    )
    return EducationContentRead.model_validate(content)


@router.post(
    "/education/{assignment_id}/read",
    response_model=ReadResponse,
)
async def mark_education_read(
    assignment_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ReadResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    assignment = await edu_repo.mark_assignment_read(
        db, assignment_id=assignment_id, patient_user_id=user.id
    )
    if assignment is None:
        await write_audit(
            db, ctx,
            action="mark_education_read",
            resource_type="education_assignment",
            resource_id=assignment_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="mark_education_read",
        resource_type="education_assignment",
        resource_id=assignment.id,
        allowed=True,
    )
    from datetime import datetime as _dt
    read_at: _dt = assignment.read_at or _dt.now()  # read_at is always set after mark_assignment_read
    return ReadResponse(assignment_id=assignment.id, read_at=read_at)
