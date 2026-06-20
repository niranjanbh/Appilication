"""Coordinator dashboard — intake queue and today's schedule."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_coord_session
from app.adminui.schemas import coordinator as coord_schemas
from app.db.session import get_db
from app.repositories import coordinator_portal as coord_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
) -> HTMLResponse:
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        return templates.TemplateResponse(
            request,
            "coord/dashboard.html",
            {"coord": coord, "error": "Coordinator profile not found.",
             "today_consultations": [], "intake_queue": [],
             "assigned_count": 0, "pending_intake": 0, "pending_followups": 0},
        )

    today_consultations = await coord_repo.list_today_consultations(
        db, coordinator_id=coordinator.id
    )
    intake_queue = await coord_repo.list_intake_queue(
        db, coordinator_id=coordinator.id
    )
    assigned_count = await coord_repo.count_assigned_patients(db, coordinator.id)
    pending_intake = await coord_repo.count_pending_intake(db, coordinator.id)
    pending_followups = await coord_repo.count_pending_followups(db, coordinator.id)

    return templates.TemplateResponse(
        request,
        "coord/dashboard.html",
        {
            "coord": coord,
            "coordinator": coordinator,
            "today_consultations": coord_schemas.consultation_user_user_triples(
                today_consultations
            ),
            "intake_queue": coord_schemas.consultation_user_pairs(intake_queue),
            "assigned_count": assigned_count,
            "pending_intake": pending_intake,
            "pending_followups": pending_followups,
            "error": None,
        },
    )
