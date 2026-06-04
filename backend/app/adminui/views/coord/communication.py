"""Coordinator communication views — WhatsApp and email to assigned patients.

Coordinators can only send scheduling/logistics messages.
Clinical advice is prohibited by policy; this interface provides
only pre-approved templates to prevent clinical content from being sent.
"""

from __future__ import annotations

import uuid
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

# Approved non-clinical message templates only.
_TEMPLATES = {
    "booking_confirmation": "Your consultation has been confirmed. Please join on time.",
    "reminder_24h": "Reminder: your consultation is tomorrow. Please be ready 5 minutes early.",
    "reminder_1h": "Your consultation starts in 1 hour. Please join on time.",
    "post_consult_followup": "Thank you for your consultation today. Please let us know if you have scheduling questions.",
    "rescheduled": "Your consultation has been rescheduled. Please check the new time in your app.",
    "cancelled": "Your consultation has been cancelled. Please contact us to rebook.",
}


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


@router.get("/communication", response_class=HTMLResponse)
async def communication_view(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    patient_id: str = "",
) -> HTMLResponse:
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        return templates.TemplateResponse(
            request, "coord/communication.html",
            {"coord": coord, "patients": [], "templates": _TEMPLATES,
             "selected_patient": None, "error": "No coordinator profile."},
        )

    patients = await coord_repo.list_assigned_patients(db, coordinator_id=coordinator.id)
    selected_patient = None
    if patient_id:
        try:
            pid = uuid.UUID(patient_id)
            selected_patient = next(
                ((p, u) for p, u in patients if str(p.id) == str(pid)), None
            )
        except ValueError:
            pass

    return templates.TemplateResponse(
        request,
        "coord/communication.html",
        {
            "coord": coord,
            "patients": patients,
            "templates": _TEMPLATES,
            "selected_patient": selected_patient,
            "patient_id": patient_id,
            "error": None,
            "success": request.query_params.get("success"),
        },
    )


@router.post("/communication/send")
async def send_message(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    patient_id: uuid.UUID = Form(...),
    channel: str = Form(...),
    template_key: str = Form(...),
) -> RedirectResponse:
    """Send a pre-approved template message via WhatsApp or email."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)

    if template_key not in _TEMPLATES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid template")
    if channel not in ("whatsapp", "email"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid channel")

    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    row = await coord_repo.get_assigned_patient(
        db, coordinator_id=coordinator.id, patient_id=patient_id
    )
    if row is None:
        await write_audit(
            db, ctx, action="coord_send_message", resource_type="patient",
            resource_id=patient_id, allowed=False, reason="not_assigned_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    _patient, user = row
    message_text = _TEMPLATES[template_key]

    await write_audit(
        db, ctx, action="coord_send_message", resource_type="patient",
        resource_id=patient_id, allowed=True,
        log_metadata={"channel": channel, "template": template_key},
    )

    _dispatch_message(channel, user, message_text)

    return RedirectResponse(
        url=f"/coord/communication?patient_id={patient_id}&success=sent",
        status_code=status.HTTP_302_FOUND,
    )


def _dispatch_message(channel: str, user: object, message_text: str) -> None:
    """Dispatch via existing notification infrastructure (best-effort)."""
    from app.models.identity import User as UserModel
    if not isinstance(user, UserModel):
        return

    try:
        if channel == "email" and user.email:
            from app.integrations.email import send_email
            send_email(
                to_email=user.email,
                subject="Message from Kyros",
                html_body=f"<p>{message_text}</p>",
                text_body=message_text,
            )
        elif channel == "whatsapp" and user.phone:
            from app.tasks.notification_tasks import send_whatsapp_task
            send_whatsapp_task.delay(
                phone=user.phone,
                first_name=user.name.split()[0] if user.name else "Patient",
                title="Kyros",
                body=message_text,
                resource_id=str(user.id),
            )
    except Exception:
        pass
