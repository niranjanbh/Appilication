"""Coordinator views for website booking inquiries and help queries.

These are pre-account submissions, so they are not scoped to assigned
patients — every coordinator sees the shared queue. The first coordinator
to reach out marks the item contacted (visible to everyone else).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
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

_IST = timezone(timedelta(hours=5, minutes=30))


def _ist(dt: datetime | None) -> str:
    """Timestamps are stored UTC; coordinators work the 4-hour SLA in IST."""
    if dt is None:
        return "—"
    return dt.astimezone(_IST).strftime("%d %b %Y %H:%M") + " IST"


templates.env.filters["ist"] = _ist


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


@router.get("/inquiries", response_class=HTMLResponse)
async def inquiries_queue(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    show: str = "new",
) -> HTMLResponse:
    """Shared queue: booking inquiries + contact-form help queries."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    only_new = show != "all"
    inquiries = await coord_repo.list_booking_inquiries(db, only_new=only_new)
    leads = await coord_repo.list_leads(db, only_new=only_new)

    await write_audit(
        db, _ctx(request, coord), action="coord_view_inquiries",
        resource_type="booking_inquiry", resource_id=None, allowed=True,
    )

    return templates.TemplateResponse(
        request,
        "coord/inquiries.html",
        {
            "coord": coord,
            "inquiries": inquiries,
            "leads": leads,
            "show": "all" if not only_new else "new",
            "error": None,
        },
    )


@router.post("/inquiries/{inquiry_id}/contacted")
async def mark_inquiry_contacted(
    inquiry_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
) -> RedirectResponse:
    """Claim a booking inquiry as contacted (first coordinator wins)."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    claimed = await coord_repo.mark_inquiry_contacted(
        db, inquiry_id=inquiry_id, user_id=coord.id
    )
    if not claimed:
        await write_audit(
            db, ctx, action="coord_contact_inquiry", resource_type="booking_inquiry",
            resource_id=inquiry_id, allowed=False, reason="already_contacted_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    await write_audit(
        db, ctx, action="coord_contact_inquiry", resource_type="booking_inquiry",
        resource_id=inquiry_id, allowed=True,
    )
    return RedirectResponse(url="/coord/inquiries", status_code=status.HTTP_302_FOUND)


@router.post("/inquiries/queries/{lead_id}/contacted")
async def mark_lead_contacted(
    lead_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
) -> RedirectResponse:
    """Claim a help query as contacted (first coordinator wins)."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    claimed = await coord_repo.mark_lead_contacted(db, lead_id=lead_id, user_id=coord.id)
    if not claimed:
        await write_audit(
            db, ctx, action="coord_contact_lead", resource_type="lead",
            resource_id=lead_id, allowed=False, reason="already_contacted_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    await write_audit(
        db, ctx, action="coord_contact_lead", resource_type="lead",
        resource_id=lead_id, allowed=True,
    )
    return RedirectResponse(url="/coord/inquiries", status_code=status.HTTP_302_FOUND)
