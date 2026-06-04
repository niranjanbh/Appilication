"""Admin audit log view — filterable by actor, action, date range."""

from __future__ import annotations

import uuid
from datetime import datetime
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


@router.get("/audit-log", response_class=HTMLResponse)
async def audit_log(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    actor: str = "",
    action: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
) -> HTMLResponse:
    actor_id: uuid.UUID | None = None
    if actor:
        try:
            actor_id = uuid.UUID(actor)
        except ValueError:
            pass

    from_dt: datetime | None = None
    to_dt: datetime | None = None
    if date_from:
        try:
            from_dt = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            to_dt = datetime.fromisoformat(date_to)
        except ValueError:
            pass

    entries, total = await admin_repo.list_audit_log(
        db,
        actor_id=actor_id,
        action_filter=action or None,
        date_from=from_dt,
        date_to=to_dt,
        page=page,
        page_size=50,
    )
    return templates.TemplateResponse(
        request,
        "admin/audit_log.html",
        {
            "admin": admin,
            "entries": entries,
            "total": total,
            "page": page,
            "actor": actor,
            "action": action,
            "date_from": date_from,
            "date_to": date_to,
            "page_size": 50,
        },
    )
