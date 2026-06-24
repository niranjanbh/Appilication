"""Doctor-facing medication-catalog search.

GET /v1/doctor/medication-catalog              — search by name (doctor)
GET /v1/doctor/medication-catalog/{id}/image-url — presigned view URL (doctor)

Doctors pick a catalog entry by name when building a reminder/prescription; the
chosen entry's image is then shown to the patient. Read-only — catalog
authoring stays in the admin surface.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import medication_catalog as catalog_repo
from app.services import medication_catalog as catalog_service

router = APIRouter(tags=["doctor-medication-catalog"])


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


class CatalogSearchItem(BaseModel):
    id: uuid.UUID
    name: str
    generic_name: str | None
    form: str | None
    strength: str | None
    has_image: bool


class CatalogSearchResponse(BaseModel):
    items: list[CatalogSearchItem]


class ImageUrlResponse(BaseModel):
    url: str


@router.get("/medication-catalog", response_model=CatalogSearchResponse)
async def search_catalog(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    search: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
) -> CatalogSearchResponse:
    ctx = _audit_ctx(request, user)
    rows = await catalog_repo.search(db, query=search, limit=limit, active_only=True)
    await write_audit(
        db, ctx, action="search_medication_catalog", resource_type="medication_catalog", allowed=True
    )
    return CatalogSearchResponse(
        items=[
            CatalogSearchItem(
                id=r.id,
                name=r.name,
                generic_name=r.generic_name,
                form=r.form.value if r.form else None,
                strength=r.strength,
                has_image=r.image_s3_key is not None,
            )
            for r in rows
        ]
    )


@router.get("/medication-catalog/{catalog_id}/image-url", response_model=ImageUrlResponse)
async def get_image_url(
    request: Request,
    db: DbSession,
    catalog_id: uuid.UUID,
    user: Annotated[object, Depends(get_doctor_user)],
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
