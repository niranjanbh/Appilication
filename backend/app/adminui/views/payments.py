"""Admin payments views — platform-wide payment list and standalone refunds.

Refunds here are money movers: require_fresh_super_admin (re-auth <10 min).
Consultation-linked refunds normally flow through the consultation cancel
action; this standalone refund covers reconciliation cases (duplicate charge,
goodwill refund after a bad consult, Razorpay dashboard mismatch).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session, require_fresh_super_admin
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, PaymentStatus
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo
from app.services import payment_service

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


@router.get("/payments", response_class=HTMLResponse)
async def payment_list(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    status_filter: str = "",
    search: str = "",
    page: int = 1,
) -> HTMLResponse:
    payments, total = await admin_repo.list_payments(
        db,
        status_filter=status_filter or None,
        search=search or None,
        page=page,
    )
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "admin/_payments_rows.html" if is_htmx else "admin/payments.html"
    return templates.TemplateResponse(
        request,
        template,
        {
            "admin": admin,
            "payments": payments,
            "total": total,
            "page": page,
            "status_filter": status_filter,
            "search": search,
            "statuses": [s.value for s in PaymentStatus],
            "page_size": 30,
        },
    )


@router.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_fresh_super_admin)],
    reason: str = Form(...),
) -> RedirectResponse:
    """Full refund of a paid payment via Razorpay. Money mover: fresh auth."""
    ctx = _ctx(request, admin)

    payment = await admin_repo.get_payment(db, payment_id)
    if payment is None:
        await write_audit(
            db, ctx, action="admin_refund_payment", resource_type="payment",
            resource_id=payment_id, allowed=False, reason="not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    try:
        await payment_service.initiate_refund(
            db, payment_id=payment.id, user_id=payment.user_id
        )
    except payment_service.PaymentError as exc:
        await write_audit(
            db, ctx, action="admin_refund_payment", resource_type="payment",
            resource_id=payment_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        return RedirectResponse(
            url=f"/admin/payments?error={exc.code}", status_code=status.HTTP_302_FOUND
        )

    await write_audit(
        db, ctx, action="admin_refund_payment", resource_type="payment",
        resource_id=payment_id, allowed=True,
        log_metadata={"reason": reason[:200]},
    )
    return RedirectResponse(
        url="/admin/payments?success=refunded", status_code=status.HTTP_302_FOUND
    )
