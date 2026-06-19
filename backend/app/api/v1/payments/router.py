from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import DbSession
from app.api.v1.payments.schemas import (
    CreateOrderRequest,
    PaymentRead,
    RefundListResponse,
    RefundRead,
    VerifyPaymentRequest,
)
from app.core.audit import AuditContext, write_audit
from app.core.rbac import cross_user_404, get_patient_user
from app.db.enums import ActorRole
from app.repositories import payments as payments_repo
from app.repositories import refunds as refunds_repo
from app.services import payment_service
from app.services.payment_service import PaymentError

router = APIRouter(tags=["payments"])


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


@router.post("/order", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: CreateOrderRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PaymentRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        payment = await payment_service.create_order(
            db,
            user_id=user.id,
            amount_paise=body.amount_paise,
            currency=body.currency,
            consultation_id=body.consultation_id,
            notes=body.notes,
        )
    except PaymentError as exc:
        await write_audit(
            db, ctx, action="create_payment_order", resource_type="payment",
            allowed=False, reason=exc.code,
        )
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=exc.code) from None

    await write_audit(
        db, ctx, action="create_payment_order", resource_type="payment",
        resource_id=payment.id, allowed=True,
        log_metadata={"amount_paise": body.amount_paise},
    )
    return PaymentRead.model_validate(payment)


@router.post("/verify", response_model=PaymentRead)
async def verify_payment(
    body: VerifyPaymentRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PaymentRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        payment = await payment_service.verify_and_capture(
            db,
            payment_id=body.payment_id,
            user_id=user.id,
            razorpay_payment_id=body.razorpay_payment_id,
            razorpay_order_id=body.razorpay_order_id,
            razorpay_signature=body.razorpay_signature,
        )
    except PaymentError as exc:
        await write_audit(
            db, ctx, action="verify_payment", resource_type="payment",
            resource_id=body.payment_id, allowed=False, reason=exc.code,
        )
        await db.commit()
        status_code = (
            status.HTTP_404_NOT_FOUND if exc.code == "payment_not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code, detail=exc.code) from None

    # Trigger GST invoice generation asynchronously
    from app.tasks.payment_tasks import generate_gst_invoice
    generate_gst_invoice.delay(str(payment.id))

    await write_audit(
        db, ctx, action="verify_payment", resource_type="payment",
        resource_id=payment.id, allowed=True,
    )
    return PaymentRead.model_validate(payment)


@router.get("/refunds", response_model=RefundListResponse)
async def list_refunds(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> RefundListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    items, total = await refunds_repo.list_refunds_for_user(
        db, user_id=user.id, page=page, page_size=page_size
    )
    await write_audit(
        db, ctx, action="list_refunds", resource_type="refund", allowed=True
    )
    pages = (total + page_size - 1) // page_size
    return RefundListResponse(
        items=[RefundRead.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/refunds/{refund_id}", response_model=RefundRead)
async def get_refund(
    refund_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> RefundRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    refund = await refunds_repo.get_refund_for_user(
        db, refund_id=refund_id, user_id=user.id
    )
    refund = await cross_user_404(
        db, refund, ctx,
        action="view_refund", resource_type="refund", resource_id=refund_id,
    )
    await write_audit(
        db, ctx, action="view_refund", resource_type="refund",
        resource_id=refund_id, allowed=True,
    )
    return RefundRead.model_validate(refund)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PaymentRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    payment = await payments_repo.get_payment_for_user(
        db, payment_id=payment_id, user_id=user.id
    )
    payment = await cross_user_404(
        db, payment, ctx,
        action="view_payment", resource_type="payment", resource_id=payment_id,
    )
    await write_audit(
        db, ctx, action="view_payment", resource_type="payment",
        resource_id=payment_id, allowed=True,
    )
    return PaymentRead.model_validate(payment)
