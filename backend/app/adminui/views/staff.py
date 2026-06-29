"""Super-admin staff creation — portal counterpart of scripts/create_staff_user.py.

Both call services.staff_service.create_staff_user. Creating identities is a
fresh-auth action: the POST requires re-authentication within 10 minutes.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import (
    require_admin_session,
    require_fresh_super_admin,
    require_super_admin_session,
)
from app.adminui.schemas import admin as admin_schemas
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, UserRole
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo
from app.services.staff_service import StaffServiceError, create_staff_user

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LENGTH = 12

_STAFF_ROLE_CHOICES = ["admin", "coordinator", "doctor", "super_admin"]

DOCTOR_SPECIALTIES = [
    "Endocrinology",
    "Gynaecology (PCOS)",
    "Thyroid Disorders",
    "Weight Management",
    "Dermatology (Skin & Hair)",
    "Andrology (Men's Health)",
    "Sexual Medicine",
    "Longevity Medicine",
    "General Medicine",
    "Psychiatry",
    "Nutrition & Dietetics",
]


def _form_context(error: str | None = None, **values: str) -> dict[str, object]:
    return {
        "roles": _STAFF_ROLE_CHOICES,
        "specialties": DOCTOR_SPECIALTIES,
        "error": error,
        "values": values,
    }


_STAFF_LIST_ROLES = ["super_admin", "admin", "coordinator", "doctor"]


@router.get("/staff", response_class=HTMLResponse)
async def staff_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    role: str = "",
    page: int = 1,
) -> HTMLResponse:
    staff, total = await admin_repo.list_staff(
        db, role_filter=role or None, page=page
    )
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "admin/_staff_rows.html" if is_htmx else "admin/staff.html"
    return templates.TemplateResponse(
        request,
        template,
        {
            "admin": admin,
            "staff": admin_schemas.user_list(staff),
            "total": total,
            "page": page,
            "role": role,
            "roles": _STAFF_LIST_ROLES,
            "page_size": 30,
        },
    )


@router.get("/staff/new", response_class=HTMLResponse)
async def staff_new_form(
    request: Request,
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "admin/staff_new.html", {"admin": admin, **_form_context()}
    )


@router.post("/staff")
async def staff_create(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_fresh_super_admin)],
    role: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    employee_id: str = Form(default=""),
    nmc: str = Form(default=""),
    state_council: str = Form(default=""),
    specialty: str = Form(default=""),
    languages: str = Form(default="en"),
    activate_doctor: str = Form(default=""),
) -> Response:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)

    def _reject(message: str) -> Response:
        return templates.TemplateResponse(
            request,
            "admin/staff_new.html",
            {
                "admin": admin,
                **_form_context(
                    message,
                    role=role, name=name, email=email, phone=phone,
                    employee_id=employee_id, nmc=nmc, state_council=state_council,
                    specialty=specialty, languages=languages,
                ),
            },
            status_code=status.HTTP_200_OK,
        )

    if role not in _STAFF_ROLE_CHOICES:
        return _reject("Unknown role.")
    if len(name.strip()) < 2:
        return _reject("Please enter the person's full name.")
    if not _E164_RE.match(phone):
        return _reject("Phone must be E.164, e.g. +919876543210.")
    if not _EMAIL_RE.match(email):
        return _reject("That email address does not look valid.")
    if len(password) < _MIN_PASSWORD_LENGTH:
        return _reject(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters.")
    if role == "doctor" and not nmc.strip():
        return _reject("Doctors require an NMC registration number.")

    ctx = AuditContext(
        actor_user_id=admin.id,
        actor_role=ActorRole(admin.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    try:
        result = await create_staff_user(
            db,
            ctx,
            role=UserRole(role),
            name=name.strip(),
            email=email.strip(),
            phone=phone.strip(),
            password=password,
            employee_id=employee_id.strip() or None,
            nmc=nmc.strip() or None,
            state_council=state_council.strip() or None,
            specialty=[s.strip() for s in specialty.split(",") if s.strip()],
            languages=[lang.strip() for lang in languages.split(",") if lang.strip()],
            activate_doctor=bool(activate_doctor),
        )
    except StaffServiceError as exc:
        messages = {
            "phone_role_conflict": "That phone number already belongs to an account with a different role.",
            "email_in_use": "That email already belongs to another account.",
            "nmc_required": "Doctors require an NMC registration number.",
            "nmc_in_use": "That NMC registration number is already registered to another doctor.",
            "not_a_staff_role": "Unknown role.",
        }
        await write_audit(
            db, ctx, action="admin_create_staff", resource_type="user",
            resource_id=None, allowed=False, reason=exc.code,
            log_metadata={"role": role},
        )
        await db.commit()
        return _reject(messages.get(exc.code, "Could not create the account."))
    except Exception as exc:
        from sqlalchemy.exc import IntegrityError

        if isinstance(exc, IntegrityError):
            # Race on NMC/phone/email between pre-check and flush.
            # Roll back the failed transaction before writing the audit row.
            await db.rollback()
            await write_audit(
                db, ctx, action="admin_create_staff", resource_type="user",
                resource_id=None, allowed=False, reason="integrity_error",
                log_metadata={"role": role},
            )
            await db.commit()
            return _reject(
                "Could not create the account — a conflicting record was created concurrently. "
                "Please check for an existing account and try again."
            )
        raise

    return RedirectResponse(
        url=f"/admin/users/{result.user.id}", status_code=status.HTTP_302_FOUND
    )
