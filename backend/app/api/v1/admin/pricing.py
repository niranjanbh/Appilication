"""Admin pricing configuration endpoints.

GET /v1/admin/pricing                                          — list all pricing configs
PUT /v1/admin/pricing/{condition_category}/{consultation_type} — upsert fee (PRICING_MANAGE)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission
from app.core.rbac import get_admin_user, permission_audit_fields, require_permission
from app.db.enums import ActorRole, ConsultationType
from app.repositories import pricing_config as pricing_config_repo

router = APIRouter(tags=["admin-pricing"])

_VALID_CATEGORIES = frozenset(
    {"thyroid", "weight", "pcos", "skin_hair", "mens_intimate", "hormones_trt", "longevity"}
)


# ── Schemas ────────────────────────────────────────────────────────────────────


class PricingConfigRead(BaseModel):
    id: uuid.UUID
    condition_category: str
    consultation_type: str
    fee_paise: int
    created_by_admin_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PricingUpsertBody(BaseModel):
    fee_paise: int

    @field_validator("fee_paise")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("fee_paise must be positive")
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


@router.get("/pricing", response_model=list[PricingConfigRead])
async def list_pricing(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
) -> list[PricingConfigRead]:
    ctx = _audit_ctx(request, user)
    configs = await pricing_config_repo.list_all(db)
    await write_audit(
        db, ctx, action="admin_list_pricing", resource_type="pricing_config", allowed=True
    )
    return [PricingConfigRead.model_validate(c) for c in configs]


@router.put(
    "/pricing/{condition_category}/{consultation_type}",
    response_model=PricingConfigRead,
)
async def upsert_pricing(
    condition_category: str,
    consultation_type: str,
    body: PricingUpsertBody,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission(Permission.PRICING_MANAGE))],
) -> PricingConfigRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    if condition_category not in _VALID_CATEGORIES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_condition_category"
        )
    try:
        ct = ConsultationType(consultation_type)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_consultation_type"
        ) from exc

    config = await pricing_config_repo.upsert(
        db,
        condition_category=condition_category,
        consultation_type=ct,
        fee_paise=body.fee_paise,
        admin_id=user.id,
    )
    await write_audit(
        db, ctx, action="upsert_pricing_config", resource_type="pricing_config",
        resource_id=config.id, allowed=True
    )
    return PricingConfigRead.model_validate(config)
