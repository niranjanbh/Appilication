"""Coordinator patient views — restricted to assigned patients only.

Clinical fields (lab values, prescriptions, doctor notes, wearable data)
are never exposed by this module. CoordinatorPatientView enforces this at
the schema layer.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_coord_session
from app.adminui.schemas import coordinator as coord_schemas
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

    patients = coord_schemas.patient_pairs(
        await coord_repo.list_assigned_patients(
            db, coordinator_id=coordinator.id, search=search or None
        )
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

    patient_orm, user_orm = row
    patient = coord_schemas.CoordinatorPatientView.model_validate(patient_orm)
    user = coord_schemas.CoordinatorUserView.model_validate(user_orm)
    consults = coord_schemas.consultation_user_pairs(
        await coord_repo.list_patient_consultations_restricted(
            db, coordinator_id=coordinator.id, patient_id=patient_id
        )
    )
    interactions = await coord_repo.list_interactions_for_patient(
        db, coordinator_id=coordinator.id, patient_id=patient_id
    )
    intake_responses: dict[str, object] | None = None
    if patient.intake_complete_at is not None:
        intake_responses = await coord_repo.get_patient_intake_responses(
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
            "interactions": interactions,
            "intake_responses": intake_responses,
            "interaction_channels": _INTERACTION_CHANNELS,
            "success": request.query_params.get("success"),
        },
    )


_INTERACTION_CHANNELS = ["call", "whatsapp", "email", "other"]


@router.post("/patients/{patient_id}/interactions")
async def add_interaction(
    patient_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    channel: str = Form(...),
    summary: str = Form(...),
) -> RedirectResponse:
    """Log a patient contact. Operational summary only — never clinical content."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    if channel not in _INTERACTION_CHANNELS or not summary.strip():
        return RedirectResponse(
            url=f"/coord/patients/{patient_id}", status_code=status.HTTP_302_FOUND
        )

    interaction = await coord_repo.create_interaction(
        db,
        coordinator_id=coordinator.id,
        patient_id=patient_id,
        channel=channel,
        summary=summary.strip(),
    )
    allowed = interaction is not None
    await write_audit(
        db, ctx, action="coord_log_interaction", resource_type="patient",
        resource_id=patient_id, allowed=allowed,
        reason=None if allowed else "not_assigned_or_not_found",
    )
    if not allowed:
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    return RedirectResponse(
        url=f"/coord/patients/{patient_id}?success=interaction_logged",
        status_code=status.HTTP_302_FOUND,
    )
