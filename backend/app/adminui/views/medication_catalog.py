"""Admin medication-catalog management views.

Portal counterpart of app.api.v1.admin.medication_catalog. Lists entries, creates
and updates them, uploads a representative image (server-side to S3 with SSE-KMS),
and soft-deletes. Writes are super-admin only and audit-logged; the list is
visible to both admin tiers.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session, require_super_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, DrugForm
from app.db.session import get_db
from app.integrations.s3 import IMAGE_CONTENT_TYPES
from app.repositories import medication_catalog as catalog_repo
from app.services import medication_catalog as catalog_service

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")

_FORM_VALUES = [f.value for f in DrugForm]


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


def _form_or_none(value: str) -> DrugForm | None:
    value = value.strip()
    return DrugForm(value) if value in _FORM_VALUES else None


@router.get("/medication-catalog", response_class=HTMLResponse)
async def catalog_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    search: str = "",
    page: int = 1,
) -> HTMLResponse:
    page_size = 30
    if search.strip():
        rows = await catalog_repo.search(db, query=search, limit=page_size, active_only=False)
        total = len(rows)
    else:
        rows, total = await catalog_repo.list_paginated(
            db, limit=page_size, offset=(page - 1) * page_size, include_inactive=True
        )
    return templates.TemplateResponse(
        request,
        "admin/medication_catalog.html",
        {
            "admin": admin,
            "items": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "search": search,
            "forms": _FORM_VALUES,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@router.get("/medication-catalog/{catalog_id}/image-view")
async def catalog_image_view(
    catalog_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> RedirectResponse:
    """Redirect to a short-lived presigned URL so <img> tags resolve lazily."""
    url = await catalog_service.get_image_url(db, catalog_id=catalog_id)
    if url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no image")
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.post("/medication-catalog")
async def catalog_create(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    name: str = Form(...),
    generic_name: str = Form(default=""),
    form: str = Form(default=""),
    strength: str = Form(default=""),
) -> RedirectResponse:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = _ctx(request, admin)

    try:
        entry = await catalog_service.create_entry(
            db,
            name=name,
            generic_name=generic_name or None,
            form=_form_or_none(form),
            strength=strength or None,
            created_by_user_id=admin.id,
        )
    except catalog_service.MedicationCatalogError:
        await write_audit(
            db, ctx, action="create_medication_catalog", resource_type="medication_catalog",
            allowed=False, reason="validation_error",
        )
        await db.commit()
        return RedirectResponse(
            url="/admin/medication-catalog?error=create_failed", status_code=status.HTTP_302_FOUND
        )
    await write_audit(
        db, ctx, action="create_medication_catalog", resource_type="medication_catalog",
        resource_id=entry.id, allowed=True,
    )
    return RedirectResponse(
        url="/admin/medication-catalog?success=created", status_code=status.HTTP_302_FOUND
    )


@router.post("/medication-catalog/{catalog_id}/update")
async def catalog_update(
    catalog_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    name: str = Form(...),
    generic_name: str = Form(default=""),
    form: str = Form(default=""),
    strength: str = Form(default=""),
    active: str = Form(default=""),
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    try:
        updated = await catalog_service.update_entry(
            db,
            catalog_id=catalog_id,
            name=name,
            generic_name=generic_name or None,
            form=_form_or_none(form),
            strength=strength or None,
            active=bool(active),
        )
    except catalog_service.MedicationCatalogError:
        return RedirectResponse(
            url="/admin/medication-catalog?error=update_failed", status_code=status.HTTP_302_FOUND
        )
    allowed = updated is not None
    await write_audit(
        db, ctx, action="update_medication_catalog", resource_type="medication_catalog",
        resource_id=catalog_id, allowed=allowed, reason=None if allowed else "not_found",
    )
    if not allowed:
        await db.commit()
        return RedirectResponse(
            url="/admin/medication-catalog?error=not_found", status_code=status.HTTP_302_FOUND
        )
    return RedirectResponse(
        url="/admin/medication-catalog?success=updated", status_code=status.HTTP_302_FOUND
    )


@router.post("/medication-catalog/{catalog_id}/image")
async def catalog_upload_image(
    catalog_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    image: UploadFile = File(...),
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    content_type = image.content_type or ""
    if content_type not in IMAGE_CONTENT_TYPES:
        return RedirectResponse(
            url="/admin/medication-catalog?error=bad_image_type", status_code=status.HTTP_302_FOUND
        )
    data = await image.read()
    filename = (image.filename or "image").replace("/", "_").replace("\\", "_")
    try:
        updated = await catalog_service.store_image_bytes(
            db, catalog_id=catalog_id, data=data, content_type=content_type, filename=filename
        )
    except catalog_service.MedicationCatalogError:
        return RedirectResponse(
            url="/admin/medication-catalog?error=bad_image", status_code=status.HTTP_302_FOUND
        )
    allowed = updated is not None
    await write_audit(
        db, ctx, action="upload_medication_catalog_image", resource_type="medication_catalog",
        resource_id=catalog_id, allowed=allowed, reason=None if allowed else "not_found",
    )
    if not allowed:
        await db.commit()
        return RedirectResponse(
            url="/admin/medication-catalog?error=not_found", status_code=status.HTTP_302_FOUND
        )
    return RedirectResponse(
        url="/admin/medication-catalog?success=image_uploaded", status_code=status.HTTP_302_FOUND
    )


@router.post("/medication-catalog/{catalog_id}/delete")
async def catalog_delete(
    catalog_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    deleted = await catalog_repo.soft_delete(db, catalog_id=catalog_id)
    await write_audit(
        db, ctx, action="delete_medication_catalog", resource_type="medication_catalog",
        resource_id=catalog_id, allowed=deleted, reason=None if deleted else "not_found",
    )
    return RedirectResponse(
        url="/admin/medication-catalog?success=deleted", status_code=status.HTTP_302_FOUND
    )
