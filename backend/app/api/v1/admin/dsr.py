"""Admin REST API for DPDP data-subject request management.

GET  /v1/admin/dsr            — list all DSRs (DSR_PROCESS permission)
PATCH /v1/admin/dsr/{id}/status — manual status transition (DSR_PROCESS permission)

The Jinja2 admin queue at /admin/dsr handles the same data visually. These REST
endpoints exist for API-level access and RBAC matrix completeness.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission
from app.core.rbac import permission_audit_fields, require_permission
from app.db.enums import ActorRole, DataSubjectRequestStatus
from app.models.consent import DataSubjectRequest
from app.models.identity import User

router = APIRouter(tags=["admin-dsr"])

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


# ── Schemas ────────────────────────────────────────────────────────────────────


class DsrAdminRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    request_type: str
    status: str
    received_at: datetime
    completed_at: datetime | None
    notes: str | None

    model_config = {"from_attributes": True}


class DsrListResponse(BaseModel):
    items: list[DsrAdminRead]
    total: int


class DsrStatusPatchBody(BaseModel):
    new_status: str
    note: str = ""


# ── Helpers ────────────────────────────────────────────────────────────────────


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    role_context, permission = permission_audit_fields(request)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
        role_context=role_context,
        permission=permission,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/dsr", response_model=DsrListResponse)
async def list_dsrs(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.DSR_PROCESS))],
    page: int = 1,
    page_size: int = 50,
    status_filter: str | None = None,
) -> DsrListResponse:
    from sqlalchemy import func

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    base = select(DataSubjectRequest, User.name).join(
        User, User.id == DataSubjectRequest.user_id
    )
    if status_filter:
        try:
            sf = DataSubjectRequestStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_status_filter"
            ) from exc
        base = base.where(DataSubjectRequest.status == sf)

    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows_result = await db.execute(
        base.order_by(DataSubjectRequest.received_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = [
        DsrAdminRead(
            id=row.DataSubjectRequest.id,
            user_id=row.DataSubjectRequest.user_id,
            user_name=row.name,
            request_type=row.DataSubjectRequest.request_type.value,
            status=row.DataSubjectRequest.status.value,
            received_at=row.DataSubjectRequest.received_at,
            completed_at=row.DataSubjectRequest.completed_at,
            notes=row.DataSubjectRequest.notes,
        )
        for row in rows_result
    ]

    await write_audit(
        db, ctx, action="admin_list_dsr",
        resource_type="data_subject_request", resource_id=None, allowed=True,
    )
    return DsrListResponse(items=items, total=total)


@router.patch("/dsr/{dsr_id}/status", response_model=DsrAdminRead)
async def patch_dsr_status(
    dsr_id: uuid.UUID,
    body: DsrStatusPatchBody,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.DSR_PROCESS))],
) -> DsrAdminRead:
    from datetime import UTC, datetime

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dsr = await db.get(DataSubjectRequest, dsr_id)

    try:
        target = DataSubjectRequestStatus(body.new_status)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_status"
        ) from exc

    if dsr is None or target not in _TRANSITIONS.get(dsr.status, ()):
        await write_audit(
            db, ctx, action="admin_dsr_status_change",
            resource_type="data_subject_request", resource_id=dsr_id,
            allowed=False, reason="not_found_or_invalid_transition",
        )
        await db.commit()
        if dsr is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
        raise HTTPException(status.HTTP_409_CONFLICT, detail="invalid_transition")

    dsr.status = target
    now = datetime.now(UTC)
    if target == DataSubjectRequestStatus.COMPLETED:
        dsr.completed_at = now
    if body.note.strip():
        stamp = now.strftime("%d %b %Y")
        appended = f"[{stamp}] {body.note.strip()[:400]}"
        dsr.notes = f"{dsr.notes}\n{appended}" if dsr.notes else appended
    await db.flush()

    # Need user name for response
    user_row = await db.get(User, dsr.user_id)
    user_name = user_row.name if user_row else "Unknown"

    await write_audit(
        db, ctx, action="admin_dsr_status_change",
        resource_type="data_subject_request", resource_id=dsr_id,
        allowed=True, log_metadata={"new_status": target.value},
    )
    return DsrAdminRead(
        id=dsr.id,
        user_id=dsr.user_id,
        user_name=user_name,
        request_type=dsr.request_type.value,
        status=dsr.status.value,
        received_at=dsr.received_at,
        completed_at=dsr.completed_at,
        notes=dsr.notes,
    )
