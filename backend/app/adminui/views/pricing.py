"""Admin pricing configuration views.

Portal counterpart of app.api.v1.admin.pricing. Lists all pricing configs and
lets a super admin update the per-(condition, type) fee. Writes are super-admin
only and audit-logged; reads are visible to both admin tiers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session, require_super_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, ConsultationType
from app.db.session import get_db
from app.repositories import pricing_config as pricing_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")

_VALID_CATEGORIES = frozenset(
    {"thyroid", "weight", "pcos", "skin_hair", "mens_intimate", "hormones_trt", "longevity"}
)


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


@router.get("/pricing", response_class=HTMLResponse)
async def pricing_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
) -> HTMLResponse:
    configs = await pricing_repo.list_all(db)
    return templates.TemplateResponse(
        request,
        "admin/pricing.html",
        {
            "admin": admin,
            "configs": configs,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@router.post("/pricing/{condition_category}/{consultation_type}")
async def pricing_update(
    condition_category: str,
    consultation_type: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    fee_rupees: str = Form(...),
) -> RedirectResponse:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = _ctx(request, admin)

    def _reject(reason: str) -> RedirectResponse:
        return RedirectResponse(
            url=f"/admin/pricing?error={reason}", status_code=status.HTTP_302_FOUND
        )

    if condition_category not in _VALID_CATEGORIES:
        return _reject("invalid_category")
    try:
        ct = ConsultationType(consultation_type)
    except ValueError:
        return _reject("invalid_type")

    try:
        fee_paise = round(float(fee_rupees) * 100)
    except (TypeError, ValueError):
        return _reject("invalid_fee")
    if fee_paise <= 0:
        return _reject("invalid_fee")

    config = await pricing_repo.upsert(
        db,
        condition_category=condition_category,
        consultation_type=ct,
        fee_paise=fee_paise,
        admin_id=admin.id,
    )
    await write_audit(
        db, ctx, action="upsert_pricing_config", resource_type="pricing_config",
        resource_id=config.id, allowed=True,
        log_metadata={
            "condition_category": condition_category,
            "consultation_type": consultation_type,
            "fee_paise": fee_paise,
        },
    )
    return RedirectResponse(
        url="/admin/pricing?success=saved", status_code=status.HTTP_302_FOUND
    )
