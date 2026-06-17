"""Admin doctor credentialing endpoints.

GET  /v1/admin/doctors                                         — list doctors
GET  /v1/admin/doctors/{doctor_id}                             — doctor detail
POST /v1/admin/doctors/{doctor_id}/advance                     — advance pipeline status
POST /v1/admin/doctors/{doctor_id}/suspend                     — suspend (ACTIVE/INACTIVE→SUSPENDED)
POST /v1/admin/doctors/{doctor_id}/reactivate                  — reactivate (SUSPENDED/INACTIVE→ACTIVE)
GET  /v1/admin/doctors/{doctor_id}/credentials                 — list credentials
POST /v1/admin/doctors/{doctor_id}/credentials/{cred_id}/verify — verify a credential
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission
from app.core.rbac import get_admin_user, permission_audit_fields, require_permission
from app.db.enums import ActorRole, DoctorStatus
from app.repositories import admin_portal

router = APIRouter(tags=["admin-doctors"])

# Forward-pipeline transitions only. Lateral transitions (suspend/reactivate) are
# separate endpoints.
_ADVANCE_TRANSITIONS: dict[DoctorStatus, DoctorStatus] = {
    DoctorStatus.APPLIED: DoctorStatus.DOCUMENTS_SUBMITTED,
    DoctorStatus.DOCUMENTS_SUBMITTED: DoctorStatus.VERIFIED,
    DoctorStatus.VERIFIED: DoctorStatus.ONBOARDING,
    DoctorStatus.ONBOARDING: DoctorStatus.ACTIVE,
}

_SUSPEND_FROM: frozenset[DoctorStatus] = frozenset(
    {DoctorStatus.ACTIVE, DoctorStatus.INACTIVE}
)
_REACTIVATE_FROM: frozenset[DoctorStatus] = frozenset(
    {DoctorStatus.SUSPENDED, DoctorStatus.INACTIVE}
)


# ── Schemas ────────────────────────────────────────────────────────────────────


class DoctorAdminRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    nmc_registration_number: str
    nmc_state_council: str | None
    specialty: list[Any]
    conditions_treated: list[Any]
    status: str
    onboarding_stage: str | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DoctorAdminListResponse(BaseModel):
    items: list[DoctorAdminRead]
    total: int
    page: int
    page_size: int


class DoctorAdvanceBody(BaseModel):
    target_status: DoctorStatus


class CredentialRead(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    credential_type: str
    institution: str
    year: int
    document_url: str | None
    verified_by_admin_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


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


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/doctors", response_model=DoctorAdminListResponse)
async def list_doctors(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
) -> DoctorAdminListResponse:
    ctx = _audit_ctx(request, user)
    pairs, total = await admin_portal.list_doctors(
        db, search=search, status_filter=status_filter, page=page, page_size=page_size
    )
    await write_audit(
        db, ctx, action="admin_list_doctors", resource_type="doctor", allowed=True
    )
    return DoctorAdminListResponse(
        items=[DoctorAdminRead.model_validate(doc) for doc, _ in pairs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/doctors/{doctor_id}", response_model=DoctorAdminRead)
async def get_doctor(
    doctor_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
) -> DoctorAdminRead:
    ctx = _audit_ctx(request, user)
    row = await admin_portal.get_doctor_detail(db, doctor_id=doctor_id)
    if row is None:
        await write_audit(
            db, ctx, action="admin_view_doctor", resource_type="doctor",
            resource_id=doctor_id, allowed=False, reason="not_found"
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
    doctor, _ = row
    await write_audit(
        db, ctx, action="admin_view_doctor", resource_type="doctor",
        resource_id=doctor_id, allowed=True
    )
    return DoctorAdminRead.model_validate(doctor)


@router.post("/doctors/{doctor_id}/advance", response_model=DoctorAdminRead)
async def advance_doctor_status(
    doctor_id: uuid.UUID,
    body: DoctorAdvanceBody,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.STAFF_MANAGE))],
) -> DoctorAdminRead:
    ctx = _audit_ctx(request, user)
    row = await admin_portal.get_doctor_detail(db, doctor_id=doctor_id)
    if row is None:
        await write_audit(
            db, ctx, action="advance_doctor_status", resource_type="doctor",
            resource_id=doctor_id, allowed=False, reason="not_found"
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = row
    allowed_next = _ADVANCE_TRANSITIONS.get(doctor.status)
    if allowed_next is None or allowed_next != body.target_status:
        await write_audit(
            db, ctx, action="advance_doctor_status", resource_type="doctor",
            resource_id=doctor_id, allowed=False, reason="invalid_transition"
        )
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="invalid_transition")

    updated = await admin_portal.update_doctor_status(
        db, doctor_id=doctor_id, new_status=body.target_status
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="advance_doctor_status", resource_type="doctor",
        resource_id=doctor_id, allowed=True
    )
    return DoctorAdminRead.model_validate(updated)


@router.post("/doctors/{doctor_id}/suspend", response_model=DoctorAdminRead)
async def suspend_doctor(
    doctor_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.STAFF_MANAGE))],
) -> DoctorAdminRead:
    ctx = _audit_ctx(request, user)
    row = await admin_portal.get_doctor_detail(db, doctor_id=doctor_id)
    if row is None:
        await write_audit(
            db, ctx, action="suspend_doctor", resource_type="doctor",
            resource_id=doctor_id, allowed=False, reason="not_found"
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = row
    if doctor.status not in _SUSPEND_FROM:
        await write_audit(
            db, ctx, action="suspend_doctor", resource_type="doctor",
            resource_id=doctor_id, allowed=False, reason="invalid_transition"
        )
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="invalid_transition")

    updated = await admin_portal.update_doctor_status(
        db, doctor_id=doctor_id, new_status=DoctorStatus.SUSPENDED
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="suspend_doctor", resource_type="doctor",
        resource_id=doctor_id, allowed=True
    )
    return DoctorAdminRead.model_validate(updated)


@router.post("/doctors/{doctor_id}/reactivate", response_model=DoctorAdminRead)
async def reactivate_doctor(
    doctor_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.STAFF_MANAGE))],
) -> DoctorAdminRead:
    ctx = _audit_ctx(request, user)
    row = await admin_portal.get_doctor_detail(db, doctor_id=doctor_id)
    if row is None:
        await write_audit(
            db, ctx, action="reactivate_doctor", resource_type="doctor",
            resource_id=doctor_id, allowed=False, reason="not_found"
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = row
    if doctor.status not in _REACTIVATE_FROM:
        await write_audit(
            db, ctx, action="reactivate_doctor", resource_type="doctor",
            resource_id=doctor_id, allowed=False, reason="invalid_transition"
        )
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="invalid_transition")

    updated = await admin_portal.update_doctor_status(
        db, doctor_id=doctor_id, new_status=DoctorStatus.ACTIVE
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="reactivate_doctor", resource_type="doctor",
        resource_id=doctor_id, allowed=True
    )
    return DoctorAdminRead.model_validate(updated)


@router.get("/doctors/{doctor_id}/credentials", response_model=list[CredentialRead])
async def list_credentials(
    doctor_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
) -> list[CredentialRead]:
    ctx = _audit_ctx(request, user)
    credentials = await admin_portal.get_credentials_for_doctor(
        db, doctor_id=doctor_id
    )
    await write_audit(
        db, ctx, action="admin_list_credentials", resource_type="credential",
        resource_id=doctor_id, allowed=True
    )
    return [CredentialRead.model_validate(c) for c in credentials]


@router.post(
    "/doctors/{doctor_id}/credentials/{credential_id}/verify",
    response_model=CredentialRead,
)
async def verify_credential(
    doctor_id: uuid.UUID,
    credential_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.STAFF_MANAGE))],
) -> CredentialRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    credential = await admin_portal.verify_credential(
        db, credential_id=credential_id, admin_user_id=user.id
    )
    if credential is None:
        await write_audit(
            db, ctx, action="verify_credential", resource_type="credential",
            resource_id=credential_id, allowed=False, reason="not_found"
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="verify_credential", resource_type="credential",
        resource_id=credential_id, allowed=True
    )
    return CredentialRead.model_validate(credential)
