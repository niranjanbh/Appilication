"""Patient-facing care plan endpoints.

GET /v1/clinic/patient/care-plans            — list (active/completed only)
GET /v1/clinic/patient/care-plans/{id}       — detail (cross-user → 404)

Draft care plans are NEVER visible: filtered at the repository SQL layer.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from app.models.clinic import CarePlan

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import care_plans as care_plans_repo

router = APIRouter(tags=["patient-care-plans"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class PatientCarePlanItemRead(BaseModel):
    id: uuid.UUID
    category: str
    title: str
    description: str | None
    frequency: str | None
    duration: str | None
    priority: str
    order_index: int


class PatientCarePlanRead(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    title: str
    status: str
    condition_category: str | None
    goals: str | None
    notes: str | None
    valid_from: date | None
    valid_until: date | None
    activated_at: datetime | None
    completed_at: datetime | None
    version: int
    items: list[PatientCarePlanItemRead] = []


class PatientCarePlanListResponse(BaseModel):
    items: list[PatientCarePlanRead]
    total: int
    page: int
    page_size: int
    pages: int


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


async def _to_read(db: DbSession, cp: CarePlan) -> PatientCarePlanRead:
    items = await care_plans_repo.list_items(db, care_plan_id=cp.id)
    return PatientCarePlanRead(
        id=cp.id,
        consultation_id=cp.consultation_id,
        title=cp.title,
        status=cp.status.value,
        condition_category=cp.condition_category,
        goals=cp.goals,
        notes=cp.notes,
        valid_from=cp.valid_from,
        valid_until=cp.valid_until,
        activated_at=cp.activated_at,
        completed_at=cp.completed_at,
        version=cp.version,
        items=[
            PatientCarePlanItemRead(
                id=item.id,
                category=item.category.value,
                title=item.title,
                description=item.description,
                frequency=item.frequency,
                duration=item.duration,
                priority=item.priority.value,
                order_index=item.order_index,
            )
            for item in items
        ],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/care-plans", response_model=PatientCarePlanListResponse)
async def list_care_plans(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PatientCarePlanListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    plans, total = await care_plans_repo.list_for_patient(
        db,
        patient_user_id=user.id,
        page=page,
        page_size=page_size,
    )

    await write_audit(
        db, ctx, action="list_care_plans", resource_type="care_plan", allowed=True
    )

    result_items = []
    for cp in plans:
        result_items.append(await _to_read(db, cp))

    return PatientCarePlanListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if page_size else 0,
    )


@router.get("/care-plans/{care_plan_id}", response_model=PatientCarePlanRead)
async def get_care_plan(
    care_plan_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PatientCarePlanRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    cp = await care_plans_repo.get_for_patient(
        db,
        care_plan_id=care_plan_id,
        patient_user_id=user.id,
    )

    if cp is None:
        await write_audit(
            db, ctx,
            action="view_care_plan",
            resource_type="care_plan",
            resource_id=care_plan_id,
            allowed=False,
            reason="not_own_or_not_found_or_draft",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="view_care_plan",
        resource_type="care_plan",
        resource_id=care_plan_id,
        allowed=True,
    )

    return await _to_read(db, cp)
