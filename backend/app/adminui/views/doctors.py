"""Admin doctor management views — pipeline, detail, verify, activate."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, DoctorStatus
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")

_PIPELINE_STAGES = [
    DoctorStatus.APPLIED,
    DoctorStatus.DOCUMENTS_SUBMITTED,
    DoctorStatus.VERIFIED,
    DoctorStatus.ONBOARDING,
    DoctorStatus.ACTIVE,
]


def _ctx(request: Request, admin: object) -> AuditContext:
    from app.models.identity import User as UserModel
    assert isinstance(admin, UserModel)
    return AuditContext(
        actor_user_id=admin.id,
        actor_role=ActorRole.SUPER_ADMIN,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/doctors", response_class=HTMLResponse)
async def doctor_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    search: str = "",
    status_filter: str = "",
    page: int = 1,
) -> HTMLResponse:
    doctors, total = await admin_repo.list_doctors(
        db, search=search or None, status_filter=status_filter or None, page=page
    )
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "admin/_doctors_rows.html" if is_htmx else "admin/doctors.html"
    statuses = [s.value for s in DoctorStatus]
    return templates.TemplateResponse(
        request,
        template,
        {
            "admin": admin,
            "doctors": doctors,
            "total": total,
            "page": page,
            "search": search,
            "status_filter": status_filter,
            "statuses": statuses,
            "page_size": 30,
        },
    )


@router.get("/doctors/pipeline", response_class=HTMLResponse)
async def doctor_pipeline(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> HTMLResponse:
    by_status: dict[str, list[Any]] = {s.value: [] for s in _PIPELINE_STAGES}

    for stage in _PIPELINE_STAGES:
        stage_doctors, _ = await admin_repo.list_doctors(
            db, status_filter=stage.value, page=1, page_size=100
        )
        by_status[stage.value] = list(stage_doctors)

    return templates.TemplateResponse(
        request,
        "admin/doctors_pipeline.html",
        {
            "admin": admin,
            "by_status": by_status,
            "pipeline_stages": [s.value for s in _PIPELINE_STAGES],
        },
    )


@router.get("/doctors/{doctor_id}", response_class=HTMLResponse)
async def doctor_detail(
    doctor_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> HTMLResponse:
    ctx = _ctx(request, admin)
    row = await admin_repo.get_doctor_detail(db, doctor_id)
    if row is None:
        await write_audit(
            db, ctx, action="admin_view_doctor", resource_type="doctor",
            resource_id=doctor_id, allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")

    doctor, user = row
    await write_audit(
        db, ctx, action="admin_view_doctor", resource_type="doctor",
        resource_id=doctor_id, allowed=True,
    )
    return templates.TemplateResponse(
        request,
        "admin/doctor_detail.html",
        {
            "admin": admin,
            "doctor": doctor,
            "user": user,
            "pipeline_stages": [s.value for s in _PIPELINE_STAGES],
        },
    )


@router.post("/doctors/{doctor_id}/verify")
async def verify_doctor(
    doctor_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await admin_repo.update_doctor_status(db, doctor_id, DoctorStatus.VERIFIED)
    await write_audit(
        db, ctx, action="admin_verify_doctor", resource_type="doctor",
        resource_id=doctor_id, allowed=updated is not None,
        reason=None if updated else "not_found",
    )
    return RedirectResponse(url=f"/admin/doctors/{doctor_id}", status_code=status.HTTP_302_FOUND)


@router.post("/doctors/{doctor_id}/activate")
async def activate_doctor(
    doctor_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await admin_repo.update_doctor_status(db, doctor_id, DoctorStatus.ACTIVE)
    await write_audit(
        db, ctx, action="admin_activate_doctor", resource_type="doctor",
        resource_id=doctor_id, allowed=updated is not None,
        reason=None if updated else "not_found",
    )
    return RedirectResponse(url=f"/admin/doctors/{doctor_id}", status_code=status.HTTP_302_FOUND)


@router.post("/doctors/{doctor_id}/revenue-share")
async def set_revenue_share(
    doctor_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    revenue_share_pct: str = Form(...),
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    try:
        pct = Decimal(revenue_share_pct)
        if not (0 <= pct <= 100):
            raise ValueError
    except (ValueError, Exception):
        return RedirectResponse(
            url=f"/admin/doctors/{doctor_id}?error=invalid_pct",
            status_code=status.HTTP_302_FOUND,
        )

    updated = await admin_repo.update_doctor_revenue_share(db, doctor_id, pct)
    await write_audit(
        db, ctx, action="admin_set_revenue_share", resource_type="doctor",
        resource_id=doctor_id, allowed=updated is not None,
        reason=None if updated else "not_found",
        log_metadata={"revenue_share_pct": str(pct)},
    )
    return RedirectResponse(url=f"/admin/doctors/{doctor_id}", status_code=status.HTTP_302_FOUND)
