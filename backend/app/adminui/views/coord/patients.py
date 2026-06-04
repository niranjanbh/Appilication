"""Coordinator patient views — restricted to assigned patients only.

Clinical fields (lab values, prescriptions, doctor notes, wearable data)
are never exposed by this module. CoordinatorPatientView enforces this at
the schema layer.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_coord_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole
from app.db.session import get_db
from app.repositories import coordinator_portal as coord_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


def _ctx(request: Request, coord: object) -> AuditContext:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)
    return AuditContext(
        actor_user_id=coord.id,
        actor_role=ActorRole.COORDINATOR,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/patients", response_class=HTMLResponse)
async def patient_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    search: str = "",
) -> HTMLResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        return templates.TemplateResponse(
            request, "coord/patients.html",
            {"coord": coord, "patients": [], "search": search, "error": "No coordinator profile."},
        )

    patients = await coord_repo.list_assigned_patients(
        db, coordinator_id=coordinator.id, search=search or None
    )
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "coord/_patient_rows.html" if is_htmx else "coord/patients.html"
    return templates.TemplateResponse(
        request,
        template,
        {"coord": coord, "patients": patients, "search": search,
         "total": len(patients), "error": None},
    )


@router.get("/patients/{patient_id}", response_class=HTMLResponse)
async def patient_detail(
    patient_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
) -> HTMLResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    row = await coord_repo.get_assigned_patient(
        db, coordinator_id=coordinator.id, patient_id=patient_id
    )
    if row is None:
        await write_audit(
            db, ctx, action="coord_view_patient", resource_type="patient",
            resource_id=patient_id, allowed=False, reason="not_assigned_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    patient, user = row
    consults = await coord_repo.list_patient_consultations_restricted(
        db, coordinator_id=coordinator.id, patient_id=patient_id
    )
    await write_audit(
        db, ctx, action="coord_view_patient", resource_type="patient",
        resource_id=patient_id, allowed=True,
    )
    return templates.TemplateResponse(
        request,
        "coord/patient_detail.html",
        {
            "coord": coord,
            "patient": patient,
            "user": user,
            "consultations": consults,
        },
    )
