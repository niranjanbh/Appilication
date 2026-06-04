"""Admin consultation management views."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session
from app.db.enums import ConsultationStatus
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


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
    return templates.TemplateResponse(
        request,
        template,
        {
            "admin": admin,
            "consultations": consultations,
            "total": total,
            "page": page,
            "status_filter": status_filter,
            "date_from": date_from,
            "statuses": statuses,
            "page_size": 30,
        },
    )
