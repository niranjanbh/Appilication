"""Coordinator intake and triage views."""

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


@router.get("/intake", response_class=HTMLResponse)
async def intake_queue(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
) -> HTMLResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        return templates.TemplateResponse(
            request, "coord/intake.html",
            {"coord": coord, "queue": [], "error": "No coordinator profile."},
        )

    queue = coord_schemas.consultation_user_pairs(
        await coord_repo.list_intake_queue(db, coordinator_id=coordinator.id)
    )
    return templates.TemplateResponse(
        request,
        "coord/intake.html",
        {
            "coord": coord,
            "queue": queue,
            "error": None,
            "escalated": request.query_params.get("escalated"),
        },
    )


@router.post("/intake/{consultation_id}/confirm")
async def confirm_intake(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    notes: str = Form(default=""),
) -> RedirectResponse:
    """Mark an intake consultation as confirmed and optionally add coordinator notes."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    confirmed = await coord_repo.confirm_intake_consultation(
        db,
        coordinator_id=coordinator.id,
        consultation_id=consultation_id,
        note=notes,
    )
    if confirmed is None:
        await write_audit(
            db, ctx, action="coord_confirm_intake", resource_type="consultation",
            resource_id=consultation_id, allowed=False, reason="not_assigned_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    await write_audit(
        db, ctx, action="coord_confirm_intake", resource_type="consultation",
        resource_id=consultation_id, allowed=True,
        log_metadata={"note_added": bool(notes.strip())},
    )

    return RedirectResponse(url="/coord/intake", status_code=status.HTTP_302_FOUND)


@router.post("/intake/{consultation_id}/escalate")
async def escalate_intake(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    reason: str = Form(...),
) -> RedirectResponse:
    """Escalate emergency intake to super admin."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    # Durable record first: persist the escalation as a PatientInteraction so it
    # survives even if email delivery fails. None = not assigned or not found.
    escalated = await coord_repo.escalate_intake_consultation(
        db,
        coordinator_id=coordinator.id,
        consultation_id=consultation_id,
        reason=reason,
    )
    if escalated is None:
        await write_audit(
            db, ctx, action="coord_escalate_intake", resource_type="consultation",
            resource_id=consultation_id, allowed=False, reason="not_assigned_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    await write_audit(
        db, ctx, action="coord_escalate_intake", resource_type="consultation",
        resource_id=consultation_id, allowed=True,
        log_metadata={"reason": reason[:200]},
    )

    # Notify super admin — best-effort on top of the persisted record. A failure
    # here does not lose the escalation; surface it to the coordinator.
    email_ok = True
    try:
        from app.core.config import settings
        from app.integrations.email import send_email
        if settings.admin_alert_email:
            send_email(
                to_email=settings.admin_alert_email,
                subject="[Kyros] Coordinator escalation — urgent intake",
                html_body=(
                    f"<p>Coordinator <strong>{coord.name}</strong> has escalated "
                    f"consultation <code>{consultation_id}</code>.</p>"
                    f"<p>Reason: {reason}</p>"
                ),
                text_body=f"Escalation by {coord.name}: {reason}",
            )
    except Exception:
        email_ok = False

    redirect = "/coord/intake?escalated=1" if email_ok else "/coord/intake?escalated=email_failed"
    return RedirectResponse(url=redirect, status_code=status.HTTP_302_FOUND)


