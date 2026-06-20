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

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission
from app.core.rbac import permission_audit_fields, require_permission
from app.db.enums import ActorRole, DataSubjectRequestStatus
from app.models.consent import DataSubjectRequest
from app.repositories import dsr as dsr_repo

router = APIRouter(tags=["admin-dsr"])


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


def _serialize(dsr: DataSubjectRequest, user_name: str) -> DsrAdminRead:
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


@router.get("/dsr", response_model=DsrListResponse)
async def list_dsrs(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.DSR_PROCESS))],
    page: int = 1,
    page_size: int = 50,
    status_filter: str | None = None,
) -> DsrListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    sf: DataSubjectRequestStatus | None = None
    if status_filter:
        try:
            sf = DataSubjectRequestStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_status_filter"
            ) from exc

    pairs, total = await dsr_repo.list_dsr_requests(
        db, status_filter=sf, page=page, page_size=page_size
    )
    items = [_serialize(dsr, user_name) for dsr, user_name in pairs]

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
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        target = DataSubjectRequestStatus(body.new_status)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_status"
        ) from exc

    # Distinguish 404 (missing) from 409 (invalid transition) before mutating.
    pair = await dsr_repo.get_dsr_request(db, dsr_id)
    if pair is None or not dsr_repo.is_valid_transition(pair[0].status, target):
        await write_audit(
            db, ctx, action="admin_dsr_status_change",
            resource_type="data_subject_request", resource_id=dsr_id,
            allowed=False, reason="not_found_or_invalid_transition",
        )
        await db.commit()
        if pair is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
        raise HTTPException(status.HTTP_409_CONFLICT, detail="invalid_transition")

    updated = await dsr_repo.update_dsr_status(
        db, dsr_id, target, note=body.note
    )
    assert updated is not None  # validated above
    dsr, user_name = updated

    await write_audit(
        db, ctx, action="admin_dsr_status_change",
        resource_type="data_subject_request", resource_id=dsr_id,
        allowed=True, log_metadata={"new_status": target.value},
    )
    return _serialize(dsr, user_name)
