"""Admin consultation management views."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import (
    require_admin_session,
    require_fresh_super_admin,
    require_super_admin_session,
)
from app.adminui.schemas import admin as admin_schemas
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, ConsultationStatus
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo
from app.repositories import coordinator_portal as coord_repo
from app.services import consultation_service

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")

_CONDITIONS = [
    "thyroid", "weight", "pcos", "skin_hair",
    "mens_intimate", "hormones_trt", "longevity",
]


def _ctx(request: Request, admin: object) -> AuditContext:
    from app.models.identity import User as UserModel
    assert isinstance(admin, UserModel)
    return AuditContext(
        actor_user_id=admin.id,
        actor_role=ActorRole(admin.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/consultations", response_class=HTMLResponse)
async def consultation_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    status_filter: str = "",
    date_from: str = "",
    page: int = 1,
) -> HTMLResponse:
    parsed_date: datetime | None = None
    if date_from:
        try:
            parsed_date = datetime.fromisoformat(date_from)
        except ValueError:
            pass

    consultations, total = await admin_repo.list_all_consultations(
        db,
        status_filter=status_filter or None,
        date_from=parsed_date,
        page=page,
    )
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "admin/_consultations_rows.html" if is_htmx else "admin/consultations.html"
    statuses = [s.value for s in ConsultationStatus]
    # Active-doctor list for the on-demand form is only needed on the full page
    # render; patients are fetched on demand via the typeahead search endpoint.
    doctors = [] if is_htmx else await admin_repo.list_active_doctors(db)
    return templates.TemplateResponse(
        request,
        template,
        {
            "admin": admin,
            "consultations": admin_schemas.consultation_triples(consultations),
            "total": total,
            "page": page,
            "status_filter": status_filter,
            "date_from": date_from,
            "statuses": statuses,
            "doctors": doctors,
            "conditions": _CONDITIONS,
            "page_size": 30,
            "now": datetime.now(UTC),
        },
    )


@router.get("/consultations/patient-search", response_class=HTMLResponse)
async def patient_search(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    q: str = "",
) -> HTMLResponse:
    """HTMX typeahead: return <option> rows for the on-demand patient select."""
    patients = await admin_repo.search_patients(db, query=q)
    return templates.TemplateResponse(
        request,
        "admin/_patient_options.html",
        {"patients": patients},
    )


@router.post("/consultations/on-demand")
async def create_on_demand_consultation(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    patient_id: uuid.UUID = Form(...),
    doctor_id: uuid.UUID = Form(...),
    condition_category: str = Form(...),
    max_participants: int = Form(6),
) -> RedirectResponse:
    """Start an instant video consultation between any patient and any active doctor.

    Free and CONFIRMED on creation; the room is provisioned immediately and both
    parties are notified to join. The doctor still cannot OPEN the call until the
    patient's identity and telemedicine consent are on file (TPG gate).
    """
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = _ctx(request, admin)

    if condition_category not in _CONDITIONS:
        return RedirectResponse(
            url="/admin/consultations?error=invalid_condition",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        consultation = await consultation_service.create_on_demand_consultation(
            db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            condition_category=condition_category,
            max_participants=max_participants,
        )
    except consultation_service.ConsultationError as exc:
        await write_audit(
            db, ctx, action="admin_create_on_demand_consultation",
            resource_type="consultation", resource_id=None,
            allowed=False, reason=exc.code,
        )
        await db.commit()
        return RedirectResponse(
            url=f"/admin/consultations?error={exc.code}",
            status_code=status.HTTP_302_FOUND,
        )

    await write_audit(
        db, ctx, action="admin_create_on_demand_consultation",
        resource_type="consultation", resource_id=consultation.id, allowed=True,
        log_metadata={"max_participants": consultation.video_max_participants},
    )
    return RedirectResponse(
        url="/admin/consultations?success=on_demand_started",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/consultations/{consultation_id}/join-room", response_class=HTMLResponse)
async def join_room(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> Response:
    """Join a consultation's video room as a visible-identity support participant."""
    from app.core.config import settings
    from app.integrations import livekit_video
    from app.models.clinic import Consultation
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = _ctx(request, admin)

    consultation = await db.get(Consultation, consultation_id)
    if consultation is None or consultation.deleted_at is not None:
        await write_audit(
            db, ctx, action="admin_join_consultation_room",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    if consultation.status not in (
        ConsultationStatus.CONFIRMED,
        ConsultationStatus.IN_PROGRESS,
    ):
        return RedirectResponse(
            url="/admin/consultations?error=not_joinable",
            status_code=status.HTTP_302_FOUND,
        )

    room_id = await consultation_service.ensure_video_room(
        db, consultation_id=consultation.id
    )
    token = livekit_video.generate_staff_token(
        room_id=room_id, user_id=str(admin.id), role="admin"
    )
    await write_audit(
        db, ctx, action="admin_join_consultation_room",
        resource_type="consultation", resource_id=consultation.id, allowed=True,
    )
    return templates.TemplateResponse(
        request,
        "admin/video_room.html",
        {
            "admin": admin,
            "room_id": room_id,
            "token": token,
            "ws_url": settings.livekit_host,
            "role": "admin",
            "back_url": "/admin/consultations",
        },
    )


@router.post("/consultations/{consultation_id}/cancel")
async def cancel_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_fresh_super_admin)],
    reason: str = Form(...),
) -> RedirectResponse:
    """Operational cancel: full refund if paid, regardless of timing window."""
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = AuditContext(
        actor_user_id=admin.id,
        actor_role=ActorRole(admin.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )

    try:
        _consultation, refund_issued = await consultation_service.admin_cancel_consultation(
            db, consultation_id=consultation_id, reason=reason
        )
    except consultation_service.ConsultationError as exc:
        await write_audit(
            db, ctx, action="admin_cancel_consultation", resource_type="consultation",
            resource_id=consultation_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found") from exc

    await write_audit(
        db, ctx, action="admin_cancel_consultation", resource_type="consultation",
        resource_id=consultation_id, allowed=True,
        log_metadata={"refund_issued": refund_issued, "reason": reason[:200]},
    )
    return RedirectResponse(url="/admin/consultations", status_code=status.HTTP_302_FOUND)


@router.get("/consultations/{consultation_id}/reassign", response_class=HTMLResponse)
async def reassign_form(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> HTMLResponse:
    from datetime import timedelta

    row = await admin_repo.get_consultation_detail(db, consultation_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    consultation, patient_user, doctor_user = row

    now = datetime.now(UTC)
    slots = await coord_repo.list_available_slots(
        db, date_from=now, date_to=now + timedelta(days=14)
    )
    return templates.TemplateResponse(
        request,
        "admin/consultation_reassign.html",
        {
            "admin": admin,
            "consultation": admin_schemas.AdminConsultationView.model_validate(consultation),
            "patient_user": admin_schemas.AdminUserView.model_validate(patient_user),
            "doctor_user": (
                admin_schemas.AdminUserView.model_validate(doctor_user)
                if doctor_user is not None
                else None
            ),
            "slots": slots,
            "error": request.query_params.get("error"),
        },
    )


@router.post("/consultations/{consultation_id}/reassign")
async def reassign_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    slot_id: uuid.UUID = Form(...),
) -> RedirectResponse:
    """Move the consultation to a new slot (doctor sick, schedule conflict).
    Payment and confirmation status carry over — no refund cycle."""
    ctx = _ctx(request, admin)

    try:
        await consultation_service.admin_reassign_consultation(
            db, consultation_id=consultation_id, slot_id=slot_id
        )
    except consultation_service.ConsultationError as exc:
        # The service may have released the old slot before failing — undo that
        # first, then record the denial so the audit row survives the rollback.
        await db.rollback()
        await write_audit(
            db, ctx, action="admin_reassign_consultation", resource_type="consultation",
            resource_id=consultation_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        if exc.code == "slot_not_available":
            return RedirectResponse(
                url=f"/admin/consultations/{consultation_id}/reassign?error=slot_unavailable",
                status_code=status.HTTP_302_FOUND,
            )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found") from exc

    await write_audit(
        db, ctx, action="admin_reassign_consultation", resource_type="consultation",
        resource_id=consultation_id, allowed=True,
        log_metadata={"slot_id": str(slot_id)},
    )
    return RedirectResponse(url="/admin/consultations", status_code=status.HTTP_302_FOUND)


@router.post("/consultations/{consultation_id}/no-show")
async def mark_no_show(
    consultation_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> RedirectResponse:
    """Patient no-show on a past consultation. No refund — fee policy applies."""
    ctx = _ctx(request, admin)

    try:
        await consultation_service.admin_mark_no_show(db, consultation_id=consultation_id)
    except consultation_service.ConsultationError as exc:
        await write_audit(
            db, ctx, action="admin_mark_no_show", resource_type="consultation",
            resource_id=consultation_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found") from exc

    await write_audit(
        db, ctx, action="admin_mark_no_show", resource_type="consultation",
        resource_id=consultation_id, allowed=True,
    )
    return RedirectResponse(url="/admin/consultations", status_code=status.HTTP_302_FOUND)
