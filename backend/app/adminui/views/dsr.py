"""DPDP data-subject request queue — access/correction/erasure/grievance.

Workflow management only: status transitions and notes, fully audit-logged.
The actual data export or anonymization is executed per the DPDP runbook;
this queue is the record that it happened and when (72-hour clock).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_super_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, DataSubjectRequestStatus
from app.db.session import get_db
from app.models.consent import DataSubjectRequest
from app.models.identity import User

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")

_TRANSITIONS: dict[DataSubjectRequestStatus, tuple[DataSubjectRequestStatus, ...]] = {
    DataSubjectRequestStatus.RECEIVED: (
        DataSubjectRequestStatus.IN_PROGRESS,
        DataSubjectRequestStatus.REJECTED,
    ),
    DataSubjectRequestStatus.IN_PROGRESS: (
        DataSubjectRequestStatus.COMPLETED,
        DataSubjectRequestStatus.REJECTED,
    ),
    DataSubjectRequestStatus.COMPLETED: (),
    DataSubjectRequestStatus.REJECTED: (),
}


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


@router.get("/dsr", response_class=HTMLResponse)
async def dsr_queue(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    show: str = "open",
) -> HTMLResponse:
    stmt = (
        select(DataSubjectRequest, User.name)
        .join(User, User.id == DataSubjectRequest.user_id)
        .order_by(DataSubjectRequest.received_at.asc())
        .limit(200)
    )
    if show != "all":
        stmt = stmt.where(
            DataSubjectRequest.status.in_(
                (DataSubjectRequestStatus.RECEIVED, DataSubjectRequestStatus.IN_PROGRESS)
            )
        )
    result = await db.execute(stmt)
    requests = [(row.DataSubjectRequest, row.name) for row in result]

    await write_audit(
        db, _ctx(request, admin), action="admin_view_dsr_queue",
        resource_type="data_subject_request", resource_id=None, allowed=True,
    )
    return templates.TemplateResponse(
        request,
        "admin/dsr.html",
        {
            "admin": admin,
            "requests": requests,
            "show": show,
            "transitions": {k.value: [s.value for s in v] for k, v in _TRANSITIONS.items()},
            "now": datetime.now(UTC),
            "error": None,
        },
    )


@router.post("/dsr/{request_id}/status")
async def dsr_set_status(
    request_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    new_status: str = Form(...),
    note: str = Form(default=""),
) -> RedirectResponse:
    ctx = _ctx(request, admin)

    dsr = await db.get(DataSubjectRequest, request_id)
    try:
        target = DataSubjectRequestStatus(new_status)
    except ValueError:
        target = None  # type: ignore[assignment]

    if dsr is None or target is None or target not in _TRANSITIONS.get(dsr.status, ()):
        await write_audit(
            db, ctx, action="admin_dsr_status_change",
            resource_type="data_subject_request", resource_id=request_id,
            allowed=False, reason="not_found_or_invalid_transition",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    dsr.status = target
    if target == DataSubjectRequestStatus.COMPLETED:
        dsr.completed_at = datetime.now(UTC)
    if note.strip():
        stamp = datetime.now(UTC).strftime("%d %b %Y")
        appended = f"[{stamp}] {note.strip()[:400]}"
        dsr.notes = f"{dsr.notes}\n{appended}" if dsr.notes else appended
    await db.flush()

    await write_audit(
        db, ctx, action="admin_dsr_status_change",
        resource_type="data_subject_request", resource_id=request_id, allowed=True,
        log_metadata={"new_status": target.value},
    )
    return RedirectResponse(url="/admin/dsr", status_code=status.HTTP_302_FOUND)