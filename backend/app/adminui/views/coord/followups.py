"""Coordinator follow-up queue — operational tasks for assigned patients.

Notes are operational ("call about consult #2 booking"), never clinical.
Lab values, prescription contents, and doctor-note content must not be
entered here; the form copy reminds coordinators of that rule.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
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


@router.get("/followups", response_class=HTMLResponse)
async def followup_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    show: str = "pending",
) -> HTMLResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        return templates.TemplateResponse(
            request, "coord/followups.html",
            {"coord": coord, "followups": [], "patients": [], "show": show,
             "now": datetime.now(UTC), "error": "No coordinator profile."},
        )

    status_value = "done" if show == "done" else "pending"
    followups = await coord_repo.list_followups(
        db, coordinator_id=coordinator.id, status=status_value
    )
    patients = await coord_repo.list_assigned_patients(db, coordinator_id=coordinator.id)

    return templates.TemplateResponse(
        request,
        "coord/followups.html",
        {
            "coord": coord,
            "followups": followups,
            "patients": patients,
            "show": show,
            "now": datetime.now(UTC),
            "error": None,
            "success": request.query_params.get("success"),
        },
    )


@router.post("/followups")
async def create_followup(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    patient_id: uuid.UUID = Form(...),
    note: str = Form(...),
    due_date: str = Form(...),
) -> RedirectResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    try:
        due_at = datetime.fromisoformat(due_date).replace(tzinfo=UTC)
    except ValueError:
        return RedirectResponse(
            url="/coord/followups?success=invalid_date", status_code=status.HTTP_302_FOUND
        )

    followup = await coord_repo.create_followup(
        db,
        coordinator_id=coordinator.id,
        patient_id=patient_id,
        note=note.strip(),
        due_at=due_at,
    )
    allowed = followup is not None
    await write_audit(
        db, ctx, action="coord_create_followup", resource_type="followup",
        resource_id=followup.id if followup else None, allowed=allowed,
        reason=None if allowed else "patient_not_assigned",
    )
    if not allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    return RedirectResponse(
        url="/coord/followups?success=created", status_code=status.HTTP_302_FOUND
    )


@router.post("/followups/{followup_id}/complete")
async def complete_followup(
    followup_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
) -> RedirectResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    done = await coord_repo.complete_followup(
        db, coordinator_id=coordinator.id, followup_id=followup_id
    )
    allowed = done is not None
    await write_audit(
        db, ctx, action="coord_complete_followup", resource_type="followup",
        resource_id=followup_id, allowed=allowed,
        reason=None if allowed else "not_found_or_not_own",
    )
    if not allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    return RedirectResponse(url="/coord/followups", status_code=status.HTTP_302_FOUND)
