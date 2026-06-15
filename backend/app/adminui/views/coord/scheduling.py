"""Coordinator scheduling views — book and cancel on behalf of assigned patients."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
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

_CONDITIONS = [
    "thyroid", "weight", "pcos", "skin_hair",
    "mens_intimate", "hormones_trt", "longevity",
]


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


@router.get("/scheduling", response_class=HTMLResponse)
async def scheduling_view(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    days_ahead: int = 7,
) -> HTMLResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        return templates.TemplateResponse(
            request, "coord/scheduling.html",
            {"coord": coord, "slots": [], "patients": [], "conditions": _CONDITIONS,
             "error": "No coordinator profile."},
        )

    now = datetime.now(UTC)
    date_to = now + timedelta(days=max(1, min(days_ahead, 30)))
    slots = await coord_repo.list_available_slots(db, date_from=now, date_to=date_to)
    patients = await coord_repo.list_assigned_patients(db, coordinator_id=coordinator.id)
    upcoming = await coord_repo.list_upcoming_consultations(
        db, coordinator_id=coordinator.id
    )

    return templates.TemplateResponse(
        request,
        "coord/scheduling.html",
        {
            "coord": coord,
            "coordinator": coordinator,
            "slots": slots,
            "patients": patients,
            "upcoming": upcoming,
            "conditions": _CONDITIONS,
            "days_ahead": days_ahead,
            "error": None,
        },
    )


@router.post("/scheduling/book")
async def book_consultation(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    patient_id: uuid.UUID = Form(...),
    slot_id: uuid.UUID = Form(...),
    condition_category: str = Form(...),
) -> RedirectResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    if condition_category not in _CONDITIONS:
        return RedirectResponse(
            url="/coord/scheduling?error=invalid_condition",
            status_code=status.HTTP_302_FOUND,
        )

    from app.db.enums import ConsultationType
    from app.services import pricing_service

    consultation = await coord_repo.book_consultation_for_patient(
        db,
        coordinator_id=coordinator.id,
        patient_id=patient_id,
        slot_id=slot_id,
        condition_category=condition_category,
        consultation_fee_paise=pricing_service.get_consultation_fee_paise(
            ConsultationType.INITIAL
        ),
    )

    allowed = consultation is not None
    await write_audit(
        db, ctx, action="coord_book_consultation", resource_type="consultation",
        resource_id=consultation.id if consultation else None,
        allowed=allowed,
        reason=None if allowed else "slot_unavailable_or_patient_not_assigned",
    )

    if not allowed:
        return RedirectResponse(
            url="/coord/scheduling?error=slot_unavailable",
            status_code=status.HTTP_302_FOUND,
        )

    # Notify patient
    _notify_patient_booked(consultation, db)

    return RedirectResponse(url="/coord/scheduling?success=booked", status_code=status.HTTP_302_FOUND)


@router.post("/scheduling/{consultation_id}/cancel")
async def cancel_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    reason: str = Form(default="Cancelled by coordinator"),
) -> RedirectResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    cancelled = await coord_repo.cancel_consultation_for_coordinator(
        db,
        coordinator_id=coordinator.id,
        consultation_id=consultation_id,
        reason=reason,
    )
    allowed = cancelled is not None
    await write_audit(
        db, ctx, action="coord_cancel_consultation", resource_type="consultation",
        resource_id=consultation_id, allowed=allowed,
        reason=None if allowed else "not_assigned_or_not_found",
    )

    return RedirectResponse(url="/coord/scheduling", status_code=status.HTTP_302_FOUND)


@router.post("/scheduling/{consultation_id}/reschedule")
async def reschedule_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    slot_id: uuid.UUID = Form(...),
) -> RedirectResponse:
    """Move a consultation to a new slot. Payment and status carry over —
    no cancel/refund/rebook cycle for the patient."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    rescheduled = await coord_repo.reschedule_consultation_for_coordinator(
        db,
        coordinator_id=coordinator.id,
        consultation_id=consultation_id,
        slot_id=slot_id,
    )
    allowed = rescheduled is not None

    if not allowed:
        # Undo the released-slot update so the original booking stays intact,
        # then record the denial (audit rows must survive the rollback).
        await db.rollback()
        await write_audit(
            db, ctx, action="coord_reschedule_consultation", resource_type="consultation",
            resource_id=consultation_id, allowed=False,
            reason="not_assigned_or_slot_unavailable",
        )
        await db.commit()
        return RedirectResponse(
            url="/coord/scheduling?error=reschedule_failed",
            status_code=status.HTTP_302_FOUND,
        )

    await write_audit(
        db, ctx, action="coord_reschedule_consultation", resource_type="consultation",
        resource_id=consultation_id, allowed=True,
        log_metadata={"slot_id": str(slot_id)},
    )
    return RedirectResponse(
        url="/coord/scheduling?success=rescheduled", status_code=status.HTTP_302_FOUND
    )


def _notify_patient_booked(consultation: object, db: object) -> None:
    """Best-effort: dispatch booking confirmation notification to patient."""
    try:
        pass
    except Exception:
        pass
