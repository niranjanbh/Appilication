"""Doctor schedule management endpoints.

GET    /v1/doctor/schedule                  — list own availability slots
POST   /v1/doctor/schedule/bulk             — bulk-create up to 20 slots
DELETE /v1/doctor/schedule/{slot_id}        — delete an available slot
PATCH  /v1/doctor/schedule/preferences      — update duration + buffer time
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import doctor_portal as dr_repo

router = APIRouter(tags=["doctor-schedule"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class SlotRead(BaseModel):
    id: uuid.UUID
    slot_start: datetime
    slot_end: datetime
    status: str


class SlotCreate(BaseModel):
    slot_start: datetime
    slot_end: datetime

    @field_validator("slot_end")
    @classmethod
    def _end_after_start(cls, v: datetime, info: object) -> datetime:
        from pydantic_core import InitErrorDetails  # noqa: F401

        values = getattr(info, "data", {})
        start = values.get("slot_start")
        if start is not None and v <= start:
            raise ValueError("slot_end must be after slot_start")
        return v


class BulkCreateRequest(BaseModel):
    slots: list[SlotCreate] = Field(..., min_length=1, max_length=20)


class BulkCreateResponse(BaseModel):
    created: list[SlotRead]
    skipped_count: int


class PreferencesUpdate(BaseModel):
    consultation_duration_minutes_default: int | None = Field(default=None, ge=10, le=120)
    buffer_time_minutes: int | None = Field(default=None, ge=0, le=60)


class PreferencesRead(BaseModel):
    consultation_duration_minutes_default: int
    buffer_time_minutes: int


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


async def _get_doctor_or_404(db: DbSession, user: object) -> object:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
    return row[0]  # Doctor


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/schedule", response_model=list[SlotRead])
async def list_schedule(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> list[SlotRead]:
    from app.models.doctor import Availability

    ctx = _audit_ctx(request, user)
    doctor = await _get_doctor_or_404(db, user)

    from app.models.doctor import Doctor as DoctorModel

    assert isinstance(doctor, DoctorModel)
    slots = await dr_repo.list_availability(
        db, doctor_id=doctor.id, start=start, end=end
    )
    await write_audit(
        db, ctx, action="list_schedule",
        resource_type="availability", allowed=True,
    )
    return [
        SlotRead(
            id=s.id,
            slot_start=s.slot_start,
            slot_end=s.slot_end,
            status=s.status.value if hasattr(s.status, "value") else str(s.status),
        )
        for s in slots
        if isinstance(s, Availability)
    ]


@router.post("/schedule/bulk", response_model=BulkCreateResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_slots(
    body: BulkCreateRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> BulkCreateResponse:
    from app.models.doctor import Availability
    from app.models.doctor import Doctor as DoctorModel

    ctx = _audit_ctx(request, user)
    doctor = await _get_doctor_or_404(db, user)
    assert isinstance(doctor, DoctorModel)

    pairs = [(s.slot_start, s.slot_end) for s in body.slots]
    created = await dr_repo.create_availability_slots(
        db, doctor_id=doctor.id, slots=pairs
    )
    skipped = len(body.slots) - len(created)

    await write_audit(
        db, ctx, action="bulk_create_schedule",
        resource_type="availability", allowed=True,
        log_metadata={"requested": len(body.slots), "created": len(created)},
    )

    return BulkCreateResponse(
        created=[
            SlotRead(
                id=s.id,
                slot_start=s.slot_start,
                slot_end=s.slot_end,
                status=s.status.value if hasattr(s.status, "value") else str(s.status),
            )
            for s in created
            if isinstance(s, Availability)
        ],
        skipped_count=skipped,
    )


@router.delete("/schedule/{slot_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_slot(
    slot_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> None:
    from app.models.doctor import Doctor as DoctorModel

    ctx = _audit_ctx(request, user)
    doctor = await _get_doctor_or_404(db, user)
    assert isinstance(doctor, DoctorModel)

    result = await dr_repo.delete_availability_slot(
        db, doctor_id=doctor.id, slot_id=slot_id
    )
    if result is None:
        await write_audit(
            db, ctx, action="delete_schedule_slot",
            resource_type="availability", resource_id=slot_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    if result is False:
        await write_audit(
            db, ctx, action="delete_schedule_slot",
            resource_type="availability", resource_id=slot_id,
            allowed=False, reason="slot_not_available",
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="slot_not_available: only available slots can be deleted",
        )

    await write_audit(
        db, ctx, action="delete_schedule_slot",
        resource_type="availability", resource_id=slot_id, allowed=True,
    )


@router.patch("/schedule/preferences", response_model=PreferencesRead)
async def update_preferences(
    body: PreferencesUpdate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> PreferencesRead:
    from app.models.doctor import Doctor as DoctorModel

    ctx = _audit_ctx(request, user)
    doctor = await _get_doctor_or_404(db, user)
    assert isinstance(doctor, DoctorModel)

    patch: dict[str, object] = {}
    if body.consultation_duration_minutes_default is not None:
        patch["consultation_duration_minutes_default"] = body.consultation_duration_minutes_default
    if body.buffer_time_minutes is not None:
        patch["buffer_time_minutes"] = body.buffer_time_minutes

    updated = await dr_repo.update_doctor_preferences(db, doctor_id=doctor.id, fields=patch)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="update_schedule_preferences",
        resource_type="doctor", resource_id=doctor.id, allowed=True,
    )
    assert isinstance(updated, DoctorModel)
    return PreferencesRead(
        consultation_duration_minutes_default=updated.consultation_duration_minutes_default,
        buffer_time_minutes=updated.buffer_time_minutes,
    )
