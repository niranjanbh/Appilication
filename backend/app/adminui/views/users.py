"""Admin user management views."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import (
    require_admin_session,
    require_fresh_super_admin,
    require_super_admin_session,
)
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, OtpResetChannel
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo
from app.repositories import users as users_repo
from app.services.staff_service import (
    StaffServiceError,
    reset_staff_password,
    revoke_staff_sessions,
)

_MIN_PASSWORD_LENGTH = 12

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")

_ROLES = ["patient", "doctor", "coordinator", "admin", "super_admin"]


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


@router.get("/users", response_class=HTMLResponse)
async def user_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    search: str = "",
    role: str = "",
    page: int = 1,
) -> HTMLResponse:
    users, total = await admin_repo.list_users(
        db, search=search or None, role_filter=role or None, page=page
    )
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "admin/_users_rows.html" if is_htmx else "admin/users.html"
    return templates.TemplateResponse(
        request,
        template,
        {
            "admin": admin,
            "users": users,
            "total": total,
            "page": page,
            "search": search,
            "role": role,
            "roles": _ROLES,
            "page_size": 30,
        },
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> HTMLResponse:
    ctx = _ctx(request, admin)
    row = await admin_repo.get_user_detail(db, user_id)
    if row is None:
        await write_audit(
            db, ctx, action="admin_view_user", resource_type="user",
            resource_id=user_id, allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user, doctor, patient = row
    await write_audit(
        db, ctx, action="admin_view_user", resource_type="user",
        resource_id=user_id, allowed=True,
    )
    coordinators = await admin_repo.list_active_coordinators(db) if patient else []
    reset_errors = {
        "password_too_short": f"Password must be at least {_MIN_PASSWORD_LENGTH} characters.",
        "user_not_found": "User not found.",
        "not_a_staff_role": "Patients sign in with OTP — passwords cannot be set for them.",
        "failed": "Could not reset the password.",
    }
    revoke_errors = {
        "user_not_found": "User not found.",
        "not_a_staff_role": "Patients don't have staff sessions to revoke.",
        "failed": "Could not revoke sessions.",
    }
    return templates.TemplateResponse(
        request,
        "admin/user_detail.html",
        {
            "admin": admin,
            "user": user,
            "doctor": doctor,
            "patient": patient,
            "coordinators": coordinators,
            "reset_error": reset_errors.get(request.query_params.get("reset_error", "")),
            "reset_success": request.query_params.get("reset") == "ok",
            "assign_success": request.query_params.get("assign") == "ok",
            "revoke_error": revoke_errors.get(request.query_params.get("revoke_error", "")),
            "revoke_success": request.query_params.get("revoke") == "ok",
        },
    )


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await admin_repo.suspend_user(db, user_id)
    allowed = updated is not None
    await write_audit(
        db, ctx, action="admin_suspend_user", resource_type="user",
        resource_id=user_id, allowed=allowed,
        reason=None if allowed else "not_found",
    )
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_302_FOUND)


@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    updated = await admin_repo.reactivate_user(db, user_id)
    allowed = updated is not None
    await write_audit(
        db, ctx, action="admin_reactivate_user", resource_type="user",
        resource_id=user_id, allowed=allowed,
        reason=None if allowed else "not_found",
    )
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_302_FOUND)


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_fresh_super_admin)],
    password: str = Form(...),
) -> RedirectResponse:
    """Set a new password on a staff account. Identity action: fresh auth required."""
    ctx = _ctx(request, admin)

    if len(password) < _MIN_PASSWORD_LENGTH:
        return RedirectResponse(
            url=f"/admin/users/{user_id}?reset_error=password_too_short",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        await reset_staff_password(db, ctx, user_id=user_id, password=password)
    except StaffServiceError as exc:
        await write_audit(
            db, ctx, action="staff_password_reset", resource_type="user",
            resource_id=user_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        code = exc.code if exc.code in ("user_not_found", "not_a_staff_role") else "failed"
        return RedirectResponse(
            url=f"/admin/users/{user_id}?reset_error={code}",
            status_code=status.HTTP_302_FOUND,
        )

    return RedirectResponse(
        url=f"/admin/users/{user_id}?reset=ok", status_code=status.HTTP_302_FOUND
    )


@router.post("/users/{user_id}/revoke-sessions")
async def revoke_sessions(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_fresh_super_admin)],
) -> RedirectResponse:
    """Force-kill every live session for a staff account. Identity action: fresh auth required."""
    ctx = _ctx(request, admin)

    try:
        await revoke_staff_sessions(db, ctx, user_id=user_id)
    except StaffServiceError as exc:
        await write_audit(
            db, ctx, action="force_session_revoke", resource_type="user",
            resource_id=user_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        code = exc.code if exc.code in ("user_not_found", "not_a_staff_role") else "failed"
        return RedirectResponse(
            url=f"/admin/users/{user_id}?revoke_error={code}",
            status_code=status.HTTP_302_FOUND,
        )

    return RedirectResponse(
        url=f"/admin/users/{user_id}?revoke=ok", status_code=status.HTTP_302_FOUND
    )


@router.post("/users/{user_id}/assign-coordinator")
async def assign_coordinator(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    coordinator_id: str = Form(default=""),
) -> RedirectResponse:
    """Assign (or clear) the care coordinator for a patient user."""
    ctx = _ctx(request, admin)

    row = await admin_repo.get_user_detail(db, user_id)
    patient = row[2] if row else None
    if patient is None:
        await write_audit(
            db, ctx, action="admin_assign_coordinator", resource_type="user",
            resource_id=user_id, allowed=False, reason="not_a_patient_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    coord_uuid: uuid.UUID | None = None
    if coordinator_id:
        try:
            coord_uuid = uuid.UUID(coordinator_id)
        except ValueError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Coordinator not found") from None

    updated = await admin_repo.assign_patient_coordinator(
        db, patient_id=patient.id, coordinator_id=coord_uuid
    )
    allowed = updated is not None
    await write_audit(
        db, ctx, action="admin_assign_coordinator", resource_type="patient",
        resource_id=patient.id, allowed=allowed,
        reason=None if allowed else "coordinator_not_found",
        log_metadata={"coordinator_id": coordinator_id or None},
    )
    if not allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Coordinator not found")

    return RedirectResponse(
        url=f"/admin/users/{user_id}?assign=ok", status_code=status.HTTP_302_FOUND
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_form(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> HTMLResponse:
    row = await admin_repo.get_user_detail(db, user_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user, _doctor, _patient = row
    return templates.TemplateResponse(
        request,
        "admin/user_edit.html",
        {"admin": admin, "user": user, "error": None},
    )


@router.post("/users/{user_id}/edit")
async def user_edit_submit(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    name: str = Form(...),
    email: str = Form(...),
    reset_otp_channel: str = Form(default=""),
) -> Response:
    ctx = _ctx(request, admin)
    name = name.strip()
    email = email.strip()

    error: str | None = None
    if len(name) < 2:
        error = "Please enter the user's full name."
    elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        error = "That email address does not look valid."
    elif reset_otp_channel not in ("", "email", "sms"):
        error = "Invalid reset OTP channel."

    updated = None
    if error is None:
        updated = await admin_repo.update_user_contact(db, user_id, name=name, email=email)
        if updated is None:
            error = "Could not update — user not found or email belongs to another account."
        else:
            channel = OtpResetChannel(reset_otp_channel) if reset_otp_channel else None
            await users_repo.update_reset_otp_channel(db, user_id, channel)

    await write_audit(
        db, ctx, action="admin_edit_user_contact", resource_type="user",
        resource_id=user_id, allowed=updated is not None,
        reason=None if updated is not None else "not_found_or_email_conflict",
        log_metadata={"reset_otp_channel": reset_otp_channel or None},
    )

    if error is not None:
        row = await admin_repo.get_user_detail(db, user_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        user, _doctor, _patient = row
        return templates.TemplateResponse(
            request,
            "admin/user_edit.html",
            {"admin": admin, "user": user, "error": error},
            status_code=status.HTTP_200_OK,
        )
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=status.HTTP_302_FOUND)
