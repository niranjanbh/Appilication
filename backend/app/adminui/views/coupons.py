"""Admin coupon management views.

Portal counterpart of app.api.v1.admin.coupons. Lists coupons, creates a coupon,
and deactivates one. Writes are super-admin only and audit-logged; the list is
visible to both admin tiers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session, require_super_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole
from app.db.session import get_db
from app.repositories import coupons as coupon_repo

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


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


def _parse_dt(value: str) -> datetime | None:
    """Parse an <input type=datetime-local> value to an aware UTC datetime."""
    value = value.strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


@router.get("/coupons", response_class=HTMLResponse)
async def coupon_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    active_only: str = "",
    page: int = 1,
) -> HTMLResponse:
    items, total = await coupon_repo.list_coupons(
        db, active_only=bool(active_only), page=page, page_size=30
    )
    return templates.TemplateResponse(
        request,
        "admin/coupons.html",
        {
            "admin": admin,
            "items": items,
            "total": total,
            "page": page,
            "page_size": 30,
            "active_only": active_only,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@router.post("/coupons")
async def coupon_create(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    code: str = Form(...),
    description: str = Form(default=""),
    discount_type: str = Form(...),
    discount_value: str = Form(...),
    max_discount_rupees: str = Form(default=""),
    min_order_rupees: str = Form(default="0"),
    max_redemptions: str = Form(default=""),
    valid_from: str = Form(...),
    valid_until: str = Form(default=""),
) -> RedirectResponse:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = _ctx(request, admin)

    def _reject(reason: str) -> RedirectResponse:
        return RedirectResponse(
            url=f"/admin/coupons?error={reason}", status_code=status.HTTP_302_FOUND
        )

    code = code.strip().upper()
    if not code:
        return _reject("invalid_code")
    if discount_type not in ("flat", "percent"):
        return _reject("invalid_type")

    try:
        # For percent, discount_value is the percentage; for flat, rupees → paise.
        if discount_type == "percent":
            value = int(discount_value)
        else:
            value = round(float(discount_value) * 100)
        if value <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return _reject("invalid_value")

    valid_from_dt = _parse_dt(valid_from)
    if valid_from_dt is None:
        return _reject("invalid_valid_from")
    valid_until_dt = _parse_dt(valid_until)

    max_discount_paise: int | None = None
    if max_discount_rupees.strip():
        try:
            max_discount_paise = round(float(max_discount_rupees) * 100)
        except (TypeError, ValueError):
            return _reject("invalid_max_discount")

    try:
        min_order_paise = round(float(min_order_rupees or "0") * 100)
    except (TypeError, ValueError):
        return _reject("invalid_min_order")

    max_redemptions_val: int | None = None
    if max_redemptions.strip():
        try:
            max_redemptions_val = int(max_redemptions)
        except (TypeError, ValueError):
            return _reject("invalid_max_redemptions")

    existing = await coupon_repo.get_by_code(db, code=code)
    if existing is not None:
        await write_audit(
            db, ctx, action="create_coupon", resource_type="coupon",
            allowed=False, reason="duplicate_code",
        )
        await db.commit()
        return _reject("duplicate_code")

    coupon = await coupon_repo.create_coupon(
        db,
        code=code,
        description=description.strip() or None,
        discount_type=discount_type,
        discount_value=value,
        max_discount_paise=max_discount_paise,
        min_order_paise=min_order_paise,
        max_redemptions=max_redemptions_val,
        valid_from=valid_from_dt,
        valid_until=valid_until_dt,
        admin_id=admin.id,
    )
    await write_audit(
        db, ctx, action="create_coupon", resource_type="coupon",
        resource_id=coupon.id, allowed=True,
    )
    return RedirectResponse(
        url="/admin/coupons?success=created", status_code=status.HTTP_302_FOUND
    )


@router.post("/coupons/{coupon_id}/deactivate")
async def coupon_deactivate(
    coupon_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    deactivated = await coupon_repo.deactivate_coupon(db, coupon_id=coupon_id)
    allowed = deactivated is not None
    await write_audit(
        db, ctx, action="deactivate_coupon", resource_type="coupon",
        resource_id=coupon_id, allowed=allowed,
        reason=None if allowed else "not_found",
    )
    return RedirectResponse(
        url="/admin/coupons?success=deactivated", status_code=status.HTTP_302_FOUND
    )
