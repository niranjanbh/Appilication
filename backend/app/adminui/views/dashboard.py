"""Admin dashboard view — platform-wide stats."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> HTMLResponse:
    users_by_role = await admin_repo.count_users_by_role(db)
    today_consults = await admin_repo.count_consultations_today(db)
    active_doctors = await admin_repo.count_active_doctors(db)
    pending_ocr = await admin_repo.count_pending_ocr(db)
    new_this_week = await admin_repo.count_new_registrations(db, days=7)
    doctors_by_status = await admin_repo.count_doctors_by_status(db)

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "admin": admin,
            "users_by_role": users_by_role,
            "today_consults": today_consults,
            "active_doctors": active_doctors,
            "pending_ocr": pending_ocr,
            "new_this_week": new_this_week,
            "doctors_by_status": doctors_by_status,
            "total_users": sum(users_by_role.values()),
        },
    )
