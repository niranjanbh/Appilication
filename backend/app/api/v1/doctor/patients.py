"""Doctor panel-patients endpoints.

GET /v1/doctor/patients           — paginated list of this doctor's panel
GET /v1/doctor/patients/{id}      — patient detail (cross-doctor 404)

Security: coordinator fields (lab values, prescription contents) are never
returned here per security rule 4.  This endpoint returns demographics and
aggregate consultation counts only.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import doctor_portal as dr_repo

router = APIRouter(tags=["doctor-patients"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class PanelPatientSummary(BaseModel):
    patient_id: uuid.UUID
    user_id: uuid.UUID
    kyros_patient_id: str
    name: str
    phone: str | None
    primary_conditions: list[str]
    allergies: str | None
    chronic_conditions: str | None


class PanelPatientDetail(BaseModel):
    patient_id: uuid.UUID
    user_id: uuid.UUID
    kyros_patient_id: str
    name: str
    phone: str | None
    email: str | None
    primary_conditions: list[str]
    allergies: str | None
    chronic_conditions: str | None
    current_medications: str | None
    consultation_counts: dict[str, int]


class PanelPatientListResponse(BaseModel):
    items: list[PanelPatientSummary]
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


async def _require_doctor(db: DbSession, user: object) -> object:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    return row


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/patients", response_model=PanelPatientListResponse)
async def list_panel_patients(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PanelPatientListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="list_panel_patients",
            resource_type="patient", allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    pairs, total = await dr_repo.list_panel_patients(
        db, doctor_id=doctor.id, search=search, page=page, page_size=page_size
    )

    await write_audit(
        db, ctx, action="list_panel_patients",
        resource_type="patient", allowed=True,
    )

    pages = max(1, -(-total // page_size))
    return PanelPatientListResponse(
        items=[
            PanelPatientSummary(
                patient_id=pt.id,
                user_id=u.id,
                kyros_patient_id=pt.kyros_patient_id,
                name=u.name,
                phone=u.phone,
                primary_conditions=list(pt.primary_conditions),
                allergies=pt.allergies,
                chronic_conditions=pt.chronic_conditions,
            )
            for pt, u in pairs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/patients/{patient_id}", response_model=PanelPatientDetail)
async def get_panel_patient(
    patient_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> PanelPatientDetail:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="view_panel_patient",
            resource_type="patient", resource_id=patient_id,
            allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    pt_row = await dr_repo.get_panel_patient(db, doctor_id=doctor.id, patient_id=patient_id)
    if pt_row is None:
        await write_audit(
            db, ctx, action="view_panel_patient",
            resource_type="patient", resource_id=patient_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    pt, u = pt_row
    counts = await dr_repo.count_patient_consultations(
        db, doctor_id=doctor.id, patient_id=patient_id
    )

    await write_audit(
        db, ctx, action="view_panel_patient",
        resource_type="patient", resource_id=patient_id, allowed=True,
    )
    return PanelPatientDetail(
        patient_id=pt.id,
        user_id=u.id,
        kyros_patient_id=pt.kyros_patient_id,
        name=u.name,
        phone=u.phone,
        email=u.email,
        primary_conditions=list(pt.primary_conditions),
        allergies=pt.allergies,
        chronic_conditions=pt.chronic_conditions,
        current_medications=pt.current_medications,
        consultation_counts=counts,
    )
