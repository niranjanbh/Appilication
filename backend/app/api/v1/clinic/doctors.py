"""Patient-facing doctor discovery endpoints.

GET /v1/clinic/patient/doctors/available — list active, verified doctors
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import doctor_listing as doctor_repo

router = APIRouter(tags=["patient-doctors"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class AvailableDoctorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    specialty: list[str]
    conditions_treated: list[str]
    consultation_languages: list[str]
    bio_short: str | None = None
    photo_url: str | None = None
    consultation_duration_minutes_default: int
    verified_at: datetime | None = None


class AvailableDoctorListResponse(BaseModel):
    items: list[AvailableDoctorRead]
    total: int
    page: int
    page_size: int
    pages: int


# ── Helpers ───────────────────────────────────────────────────────────────────


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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/doctors/available", response_model=AvailableDoctorListResponse)
async def list_available_doctors(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    condition_category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AvailableDoctorListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    pairs, total = await doctor_repo.list_available_doctors(
        db,
        condition_category=condition_category,
        page=page,
        page_size=page_size,
    )

    await write_audit(
        db, ctx,
        action="list_available_doctors",
        resource_type="doctor",
        allowed=True,
        log_metadata={"condition_category": condition_category},
    )

    pages = max(1, -(-total // page_size))
    return AvailableDoctorListResponse(
        items=[
            AvailableDoctorRead(
                id=doctor.id,
                name=dr_user.name,
                specialty=list(doctor.specialty),
                conditions_treated=list(doctor.conditions_treated),
                consultation_languages=list(doctor.consultation_languages),
                bio_short=doctor.bio_short,
                photo_url=doctor.photo_url,
                consultation_duration_minutes_default=doctor.consultation_duration_minutes_default,
                verified_at=doctor.verified_at,
            )
            for doctor, dr_user in pairs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
