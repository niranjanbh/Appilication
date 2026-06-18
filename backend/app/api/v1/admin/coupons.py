"""Admin coupon management endpoints.

GET    /v1/admin/coupons             — list coupons (PRICING_MANAGE)
POST   /v1/admin/coupons             — create coupon (PRICING_MANAGE)
PATCH  /v1/admin/coupons/{id}        — update coupon (PRICING_MANAGE)
DELETE /v1/admin/coupons/{id}        — deactivate coupon (PRICING_MANAGE)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission
from app.core.rbac import permission_audit_fields, require_permission
from app.db.enums import ActorRole
from app.repositories import coupons as coupon_repo

router = APIRouter(tags=["admin-coupons"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class CouponAdminRead(BaseModel):
    id: uuid.UUID
    code: str
    description: str | None
    discount_type: str
    discount_value: int
    max_discount_paise: int | None
    min_order_paise: int
    max_redemptions: int | None
    redemption_count: int
    valid_from: datetime
    valid_until: datetime | None
    active: bool
    created_by_admin_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CouponListResponse(BaseModel):
    items: list[CouponAdminRead]
    total: int
    page: int
    page_size: int


class CouponCreateBody(BaseModel):
    code: str
    description: str | None = None
    discount_type: str
    discount_value: int
    max_discount_paise: int | None = None
    min_order_paise: int = 0
    max_redemptions: int | None = None
    valid_from: datetime
    valid_until: datetime | None = None

    @field_validator("discount_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        if v not in ("flat", "percent"):
            raise ValueError("discount_type must be 'flat' or 'percent'")
        return v

    @field_validator("discount_value")
    @classmethod
    def positive_value(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("discount_value must be positive")
        return v


class CouponUpdateBody(BaseModel):
    description: str | None = None
    discount_value: int | None = None
    max_discount_paise: int | None = None
    min_order_paise: int | None = None
    max_redemptions: int | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    active: bool | None = None

    @field_validator("discount_value")
    @classmethod
    def positive_value(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("discount_value must be positive")
        return v


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


@router.get("/coupons", response_model=CouponListResponse)
async def list_coupons(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.PRICING_MANAGE))],
    active_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
) -> CouponListResponse:
    ctx = _audit_ctx(request, user)
    items, total = await coupon_repo.list_coupons(
        db, active_only=active_only, page=page, page_size=page_size
    )
    await write_audit(
        db, ctx, action="admin_list_coupons", resource_type="coupon", allowed=True
    )
    return CouponListResponse(
        items=[CouponAdminRead.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/coupons", response_model=CouponAdminRead, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    body: CouponCreateBody,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.PRICING_MANAGE))],
) -> CouponAdminRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    coupon = await coupon_repo.create_coupon(
        db,
        code=body.code,
        description=body.description,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        max_discount_paise=body.max_discount_paise,
        min_order_paise=body.min_order_paise,
        max_redemptions=body.max_redemptions,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        admin_id=user.id,
    )
    await write_audit(
        db, ctx, action="create_coupon", resource_type="coupon",
        resource_id=coupon.id, allowed=True
    )
    return CouponAdminRead.model_validate(coupon)


@router.patch("/coupons/{coupon_id}", response_model=CouponAdminRead)
async def update_coupon(
    coupon_id: uuid.UUID,
    body: CouponUpdateBody,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.PRICING_MANAGE))],
) -> CouponAdminRead:
    ctx = _audit_ctx(request, user)

    fields = body.model_dump(exclude_unset=True)
    if not fields:
        existing = await coupon_repo.get_by_id(db, coupon_id=coupon_id)
        if existing is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
        return CouponAdminRead.model_validate(existing)

    updated = await coupon_repo.update_coupon(db, coupon_id=coupon_id, **fields)
    if updated is None:
        await write_audit(
            db, ctx, action="update_coupon", resource_type="coupon",
            resource_id=coupon_id, allowed=False, reason="not_found"
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="update_coupon", resource_type="coupon",
        resource_id=coupon_id, allowed=True
    )
    return CouponAdminRead.model_validate(updated)


@router.delete("/coupons/{coupon_id}", response_model=CouponAdminRead)
async def deactivate_coupon(
    coupon_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.PRICING_MANAGE))],
) -> CouponAdminRead:
    ctx = _audit_ctx(request, user)

    deactivated = await coupon_repo.deactivate_coupon(db, coupon_id=coupon_id)
    if deactivated is None:
        await write_audit(
            db, ctx, action="deactivate_coupon", resource_type="coupon",
            resource_id=coupon_id, allowed=False, reason="not_found"
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="deactivate_coupon", resource_type="coupon",
        resource_id=coupon_id, allowed=True
    )
    return CouponAdminRead.model_validate(deactivated)
