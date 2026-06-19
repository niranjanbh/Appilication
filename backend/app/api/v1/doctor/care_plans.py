"""Doctor-facing care plan endpoints.

POST  /v1/doctor/consultations/{id}/care-plan       — create draft
GET   /v1/doctor/consultations/{id}/care-plans       — list for consultation
PATCH /v1/doctor/care-plans/{id}                     — edit draft
POST  /v1/doctor/care-plans/{id}/activate            — publish (DRAFT → ACTIVE)
POST  /v1/doctor/care-plans/{id}/complete            — finish (ACTIVE → COMPLETED)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission
from app.core.rbac import get_doctor_user, permission_audit_fields, require_permission
from app.db.enums import ActorRole
from app.services import care_plan_service
from app.services.care_plan_service import _OWNERSHIP_CODES

router = APIRouter(tags=["doctor-care-plans"])


def _care_plan_http_error(exc: care_plan_service.CarePlanError) -> HTTPException:
    if exc.code in _OWNERSHIP_CODES:
        return HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.code)


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class CarePlanItemCreate(BaseModel):
    category: str
    title: str
    description: str | None = None
    frequency: str | None = None
    duration: str | None = None
    priority: str = "normal"

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v: str) -> str:
        from app.db.enums import CarePlanItemCategory
        valid = {e.value for e in CarePlanItemCategory}
        if v not in valid:
            raise ValueError(f"category must be one of: {', '.join(sorted(valid))}")
        return v

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, v: str) -> str:
        from app.db.enums import CarePlanItemPriority
        valid = {e.value for e in CarePlanItemPriority}
        if v not in valid:
            raise ValueError(f"priority must be one of: {', '.join(sorted(valid))}")
        return v


class CreateCarePlanRequest(BaseModel):
    title: str
    condition_category: str | None = None
    goals: str | None = None
    notes: str | None = None
    items: list[CarePlanItemCreate]

    @field_validator("items")
    @classmethod
    def _validate_items(cls, v: list[CarePlanItemCreate]) -> list[CarePlanItemCreate]:
        if not v:
            raise ValueError("at least one care plan item is required")
        return v


class UpdateCarePlanRequest(BaseModel):
    title: str | None = None
    condition_category: str | None = None
    goals: str | None = None
    notes: str | None = None
    items: list[CarePlanItemCreate] | None = None

    @field_validator("items")
    @classmethod
    def _validate_items(
        cls, v: list[CarePlanItemCreate] | None
    ) -> list[CarePlanItemCreate] | None:
        if v is not None and not v:
            raise ValueError("items must contain at least one entry when provided")
        return v


class CarePlanItemRead(BaseModel):
    id: uuid.UUID
    category: str
    title: str
    description: str | None
    frequency: str | None
    duration: str | None
    priority: str
    order_index: int


class CarePlanRead(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
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
    items: list[CarePlanItemRead] = []


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


async def _read_with_items(db: DbSession, cp: object) -> CarePlanRead:
    from app.models.clinic import CarePlan as CarePlanModel
    from app.repositories import care_plans as cp_repo

    assert isinstance(cp, CarePlanModel)
    items = await cp_repo.list_items(db, care_plan_id=cp.id)
    return CarePlanRead(
        id=cp.id,
        consultation_id=cp.consultation_id,
        doctor_id=cp.doctor_id,
        patient_id=cp.patient_id,
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
            CarePlanItemRead(
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


@router.get(
    "/consultations/{consultation_id}/care-plans",
    response_model=list[CarePlanRead],
)
async def list_consultation_care_plans(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> list[CarePlanRead]:
    from sqlalchemy import select

    from app.models.doctor import Doctor
    from app.models.identity import User as UserModel
    from app.repositories import care_plans as cp_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    result = await db.execute(select(Doctor).where(Doctor.user_id == user.id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        await write_audit(
            db, ctx,
            action="list_care_plans",
            resource_type="consultation",
            resource_id=consultation_id,
            allowed=False,
            reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    plans = await cp_repo.list_for_consultation_for_doctor(
        db, consultation_id=consultation_id, doctor_id=doctor.id
    )
    await write_audit(
        db, ctx,
        action="list_care_plans",
        resource_type="consultation",
        resource_id=consultation_id,
        allowed=True,
    )
    return [await _read_with_items(db, cp) for cp in plans]


@router.post(
    "/consultations/{consultation_id}/care-plan",
    response_model=CarePlanRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_care_plan(
    consultation_id: uuid.UUID,
    body: CreateCarePlanRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.CARE_PLAN_CREATE))],
) -> CarePlanRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        cp = await care_plan_service.create_draft(
            db,
            doctor_user_id=user.id,
            consultation_id=consultation_id,
            title=body.title,
            condition_category=body.condition_category,
            goals=body.goals,
            notes=body.notes,
            items=[item.model_dump() for item in body.items],
        )
    except care_plan_service.CarePlanError as exc:
        await write_audit(
            db, ctx,
            action="create_care_plan",
            resource_type="consultation",
            resource_id=consultation_id,
            allowed=False,
            reason=exc.code,
        )
        await db.commit()
        raise _care_plan_http_error(exc) from exc

    await write_audit(
        db, ctx,
        action="create_care_plan",
        resource_type="care_plan",
        resource_id=cp.id,
        allowed=True,
    )
    return await _read_with_items(db, cp)


@router.patch(
    "/care-plans/{care_plan_id}",
    response_model=CarePlanRead,
)
async def update_care_plan(
    care_plan_id: uuid.UUID,
    body: UpdateCarePlanRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> CarePlanRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        cp = await care_plan_service.update_draft(
            db,
            doctor_user_id=user.id,
            care_plan_id=care_plan_id,
            title=body.title,
            condition_category=body.condition_category,
            goals=body.goals,
            notes=body.notes,
            items=(
                [item.model_dump() for item in body.items]
                if body.items is not None
                else None
            ),
        )
    except care_plan_service.CarePlanError as exc:
        await write_audit(
            db, ctx,
            action="update_care_plan",
            resource_type="care_plan",
            resource_id=care_plan_id,
            allowed=False,
            reason=exc.code,
        )
        await db.commit()
        raise _care_plan_http_error(exc) from exc

    await write_audit(
        db, ctx,
        action="update_care_plan",
        resource_type="care_plan",
        resource_id=care_plan_id,
        allowed=True,
    )
    return await _read_with_items(db, cp)


@router.post(
    "/care-plans/{care_plan_id}/activate",
    response_model=CarePlanRead,
)
async def activate_care_plan(
    care_plan_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.CARE_PLAN_ACTIVATE))],
) -> CarePlanRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        cp = await care_plan_service.activate_care_plan(
            db,
            doctor_user_id=user.id,
            care_plan_id=care_plan_id,
        )
    except care_plan_service.CarePlanError as exc:
        await write_audit(
            db, ctx,
            action="activate_care_plan",
            resource_type="care_plan",
            resource_id=care_plan_id,
            allowed=False,
            reason=exc.code,
        )
        await db.commit()
        raise _care_plan_http_error(exc) from exc

    await write_audit(
        db, ctx,
        action="activate_care_plan",
        resource_type="care_plan",
        resource_id=care_plan_id,
        allowed=True,
    )
    return await _read_with_items(db, cp)


@router.post(
    "/care-plans/{care_plan_id}/complete",
    response_model=CarePlanRead,
)
async def complete_care_plan(
    care_plan_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> CarePlanRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        cp = await care_plan_service.complete_care_plan(
            db,
            doctor_user_id=user.id,
            care_plan_id=care_plan_id,
        )
    except care_plan_service.CarePlanError as exc:
        await write_audit(
            db, ctx,
            action="complete_care_plan",
            resource_type="care_plan",
            resource_id=care_plan_id,
            allowed=False,
            reason=exc.code,
        )
        await db.commit()
        raise _care_plan_http_error(exc) from exc

    await write_audit(
        db, ctx,
        action="complete_care_plan",
        resource_type="care_plan",
        resource_id=care_plan_id,
        allowed=True,
    )
    return await _read_with_items(db, cp)
