"""Admin medication-catalog management.

GET    /v1/admin/medication-catalog                  — list/search (admin read)
POST   /v1/admin/medication-catalog                  — create (super_admin)
GET    /v1/admin/medication-catalog/{id}             — detail (admin read)
PATCH  /v1/admin/medication-catalog/{id}             — update (super_admin)
DELETE /v1/admin/medication-catalog/{id}             — soft-delete (super_admin)
POST   /v1/admin/medication-catalog/{id}/image-initiate  — presigned upload (super_admin)
POST   /v1/admin/medication-catalog/{id}/image-finalize  — confirm upload (super_admin)
GET    /v1/admin/medication-catalog/{id}/image-url   — presigned view URL (admin read)

Image bytes live in S3 (SSE-KMS, private). Only the key is stored in Postgres.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_admin_user, get_super_admin_user
from app.db.enums import ActorRole, DrugForm
from app.integrations.s3 import IMAGE_CONTENT_TYPES, MAX_IMAGE_SIZE_BYTES
from app.repositories import medication_catalog as catalog_repo
from app.services import medication_catalog as catalog_service

router = APIRouter(tags=["admin-medication-catalog"])


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


# ── Schemas ────────────────────────────────────────────────────────────────────


def _valid_form(v: str | None) -> str | None:
    if v is None:
        return None
    if v not in {f.value for f in DrugForm}:
        raise ValueError(f"form must be one of: {', '.join(f.value for f in DrugForm)}")
    return v


class MedicationCatalogRead(BaseModel):
    id: uuid.UUID
    name: str
    generic_name: str | None
    form: str | None
    strength: str | None
    has_image: bool
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_entry(cls, e: object) -> MedicationCatalogRead:
        from app.models.clinic import MedicationCatalog

        assert isinstance(e, MedicationCatalog)
        return cls(
            id=e.id,
            name=e.name,
            generic_name=e.generic_name,
            form=e.form.value if e.form else None,
            strength=e.strength,
            has_image=e.image_s3_key is not None,
            active=e.active,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class MedicationCatalogListResponse(BaseModel):
    items: list[MedicationCatalogRead]
    total: int


class MedicationCatalogCreateBody(BaseModel):
    name: str
    generic_name: str | None = None
    form: str | None = None
    strength: str | None = None

    @field_validator("form")
    @classmethod
    def _check_form(cls, v: str | None) -> str | None:
        return _valid_form(v)


class MedicationCatalogUpdateBody(BaseModel):
    name: str | None = None
    generic_name: str | None = None
    form: str | None = None
    strength: str | None = None
    active: bool | None = None

    @field_validator("form")
    @classmethod
    def _check_form(cls, v: str | None) -> str | None:
        return _valid_form(v)


class ImageInitiateBody(BaseModel):
    filename: str
    content_type: str
    file_size_bytes: int

    @field_validator("content_type")
    @classmethod
    def _ct(cls, v: str) -> str:
        if v not in IMAGE_CONTENT_TYPES:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(IMAGE_CONTENT_TYPES))}")
        return v

    @field_validator("file_size_bytes")
    @classmethod
    def _size(cls, v: int) -> int:
        if v <= 0 or v > MAX_IMAGE_SIZE_BYTES:
            raise ValueError(f"file_size_bytes must be between 1 and {MAX_IMAGE_SIZE_BYTES}")
        return v


class ImageInitiateResponse(BaseModel):
    catalog_id: uuid.UUID
    upload_url: str
    fields: dict[str, str]
    s3_key: str
    content_type: str


class ImageUrlResponse(BaseModel):
    url: str


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/medication-catalog", response_model=MedicationCatalogListResponse)
async def list_catalog(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    search: str | None = Query(None),
    include_inactive: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> MedicationCatalogListResponse:
    ctx = _audit_ctx(request, user)
    if search:
        rows = await catalog_repo.search(
            db, query=search, limit=limit, active_only=not include_inactive
        )
        total = len(rows)
    else:
        rows, total = await catalog_repo.list_paginated(
            db, limit=limit, offset=offset, include_inactive=include_inactive
        )
    await write_audit(db, ctx, action="list_medication_catalog", resource_type="medication_catalog", allowed=True)
    return MedicationCatalogListResponse(
        items=[MedicationCatalogRead.from_orm_entry(r) for r in rows], total=total
    )


@router.post("/medication-catalog", response_model=MedicationCatalogRead, status_code=status.HTTP_201_CREATED)
async def create_catalog(
    request: Request,
    db: DbSession,
    body: MedicationCatalogCreateBody,
    user: Annotated[object, Depends(get_super_admin_user)],
) -> MedicationCatalogRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    try:
        entry = await catalog_service.create_entry(
            db,
            name=body.name,
            generic_name=body.generic_name,
            form=DrugForm(body.form) if body.form else None,
            strength=body.strength,
            created_by_user_id=user.id,
        )
    except catalog_service.MedicationCatalogError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await write_audit(
        db, ctx, action="create_medication_catalog", resource_type="medication_catalog",
        resource_id=entry.id, allowed=True,
    )
    return MedicationCatalogRead.from_orm_entry(entry)


@router.get("/medication-catalog/{catalog_id}", response_model=MedicationCatalogRead)
async def get_catalog(
    request: Request,
    db: DbSession,
    catalog_id: uuid.UUID,
    user: Annotated[object, Depends(get_admin_user)],
) -> MedicationCatalogRead:
    ctx = _audit_ctx(request, user)
    entry = await catalog_repo.get(db, catalog_id=catalog_id)
    if entry is None:
        await write_audit(
            db, ctx, action="view_medication_catalog", resource_type="medication_catalog",
            resource_id=catalog_id, allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await write_audit(
        db, ctx, action="view_medication_catalog", resource_type="medication_catalog",
        resource_id=entry.id, allowed=True,
    )
    return MedicationCatalogRead.from_orm_entry(entry)


@router.patch("/medication-catalog/{catalog_id}", response_model=MedicationCatalogRead)
async def update_catalog(
    request: Request,
    db: DbSession,
    catalog_id: uuid.UUID,
    body: MedicationCatalogUpdateBody,
    user: Annotated[object, Depends(get_super_admin_user)],
) -> MedicationCatalogRead:
    ctx = _audit_ctx(request, user)
    try:
        entry = await catalog_service.update_entry(
            db,
            catalog_id=catalog_id,
            name=body.name,
            generic_name=body.generic_name,
            form=DrugForm(body.form) if body.form else None,
            strength=body.strength,
            active=body.active,
        )
    except catalog_service.MedicationCatalogError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if entry is None:
        await write_audit(
            db, ctx, action="update_medication_catalog", resource_type="medication_catalog",
            resource_id=catalog_id, allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await write_audit(
        db, ctx, action="update_medication_catalog", resource_type="medication_catalog",
        resource_id=entry.id, allowed=True,
    )
    return MedicationCatalogRead.from_orm_entry(entry)


@router.delete("/medication-catalog/{catalog_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_catalog(
    request: Request,
    db: DbSession,
    catalog_id: uuid.UUID,
    user: Annotated[object, Depends(get_super_admin_user)],
) -> None:
    ctx = _audit_ctx(request, user)
    deleted = await catalog_repo.soft_delete(db, catalog_id=catalog_id)
    if not deleted:
        await write_audit(
            db, ctx, action="delete_medication_catalog", resource_type="medication_catalog",
            resource_id=catalog_id, allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await write_audit(
        db, ctx, action="delete_medication_catalog", resource_type="medication_catalog",
        resource_id=catalog_id, allowed=True,
    )


@router.post("/medication-catalog/{catalog_id}/image-initiate", response_model=ImageInitiateResponse)
async def initiate_image(
    request: Request,
    db: DbSession,
    catalog_id: uuid.UUID,
    body: ImageInitiateBody,
    user: Annotated[object, Depends(get_super_admin_user)],
) -> ImageInitiateResponse:
    ctx = _audit_ctx(request, user)
    try:
        result = await catalog_service.initiate_image_upload(
            db,
            catalog_id=catalog_id,
            filename=body.filename,
            content_type=body.content_type,
            file_size_bytes=body.file_size_bytes,
        )
    except catalog_service.MedicationCatalogError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        await write_audit(
            db, ctx, action="upload_medication_catalog_image", resource_type="medication_catalog",
            resource_id=catalog_id, allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await write_audit(
        db, ctx, action="upload_medication_catalog_image", resource_type="medication_catalog",
        resource_id=catalog_id, allowed=True,
    )
    return ImageInitiateResponse(**result)


@router.post("/medication-catalog/{catalog_id}/image-finalize")
async def finalize_image(
    request: Request,
    db: DbSession,
    catalog_id: uuid.UUID,
    user: Annotated[object, Depends(get_super_admin_user)],
) -> dict[str, object]:
    ctx = _audit_ctx(request, user)
    try:
        result = await catalog_service.finalize_image_upload(db, catalog_id=catalog_id)
    except catalog_service.MedicationCatalogError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await write_audit(
        db, ctx, action="finalize_medication_catalog_image", resource_type="medication_catalog",
        resource_id=catalog_id, allowed=True,
    )
    return result


@router.get("/medication-catalog/{catalog_id}/image-url", response_model=ImageUrlResponse)
async def get_image_url(
    request: Request,
    db: DbSession,
    catalog_id: uuid.UUID,
    user: Annotated[object, Depends(get_admin_user)],
) -> ImageUrlResponse:
    ctx = _audit_ctx(request, user)
    url = await catalog_service.get_image_url(db, catalog_id=catalog_id)
    if url is None:
        await write_audit(
            db, ctx, action="view_medication_catalog_image", resource_type="medication_catalog",
            resource_id=catalog_id, allowed=False, reason="no_image_or_not_found",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await write_audit(
        db, ctx, action="view_medication_catalog_image", resource_type="medication_catalog",
        resource_id=catalog_id, allowed=True,
    )
    return ImageUrlResponse(url=url)
