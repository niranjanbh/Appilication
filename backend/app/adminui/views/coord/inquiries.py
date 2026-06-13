"""Coordinator views for website booking inquiries and help queries.

These are pre-account submissions, so they are not scoped to assigned
patients — every coordinator sees the shared queue. The first coordinator
to reach out marks the item contacted (visible to everyone else).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_coord_session

# Same vocabulary as website-submitted inquiries (public booking flow slugs).
from app.api.v1.public.schemas import CONDITION_CATEGORIES
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
            "statuses": list(coord_repo.LEAD_STATUSES),
            "conditions": _CONDITIONS,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


_CONDITIONS = sorted(CONDITION_CATEGORIES)
_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


@router.post("/inquiries/new")
async def create_inquiry(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    name: str = Form(...),
    phone: str = Form(...),
    gender: str = Form(default=""),
    condition_category: str = Form(...),
    note: str = Form(default=""),
) -> RedirectResponse:
    """Manually log a lead that came in by phone call or referral."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)

    if len(name.strip()) < 2 or not _E164_RE.match(phone.strip()):
        return RedirectResponse(
            url="/coord/inquiries?error=invalid_lead", status_code=status.HTTP_302_FOUND
        )
    if condition_category not in _CONDITIONS:
        return RedirectResponse(
            url="/coord/inquiries?error=invalid_lead", status_code=status.HTTP_302_FOUND
        )

    inquiry = await coord_repo.create_manual_inquiry(
        db,
        created_by_user_id=coord.id,
        name=name.strip(),
        phone=phone.strip(),
        gender=gender or None,
        condition_category=condition_category,
        note=note.strip() or None,
    )
    await write_audit(
        db, ctx, action="coord_create_inquiry", resource_type="booking_inquiry",
        resource_id=inquiry.id, allowed=True,
    )
    return RedirectResponse(
        url="/coord/inquiries?show=all&success=lead_created",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/inquiries/{inquiry_id}/status")
async def update_inquiry_status(
    inquiry_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    new_status: str = Form(...),
) -> RedirectResponse:
    """Move a booking inquiry along the pipeline (contacted → qualified → converted/closed)."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    moved = await coord_repo.set_inquiry_status(
        db, inquiry_id=inquiry_id, user_id=coord.id, new_status=new_status
    )
    await write_audit(
        db, ctx, action="coord_update_inquiry_status", resource_type="booking_inquiry",
        resource_id=inquiry_id, allowed=moved,
        reason=None if moved else "invalid_status_or_not_found",
        log_metadata={"new_status": new_status},
    )
    if not moved:
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    return RedirectResponse(url="/coord/inquiries?show=all", status_code=status.HTTP_302_FOUND)


@router.post("/inquiries/queries/{lead_id}/status")
async def update_lead_status(
    lead_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    new_status: str = Form(...),
) -> RedirectResponse:
    """Move a help query along the pipeline."""
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)

    ctx = _ctx(request, coord)
    moved = await coord_repo.set_lead_status(
        db, lead_id=lead_id, user_id=coord.id, new_status=new_status
    )
    await write_audit(
        db, ctx, action="coord_update_lead_status", resource_type="lead",
        resource_id=lead_id, allowed=moved,
        reason=None if moved else "invalid_status_or_not_found",
        log_metadata={"new_status": new_status},
    )
    if not moved:
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    return RedirectResponse(url="/coord/inquiries?show=all", status_code=status.HTTP_302_FOUND)


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
