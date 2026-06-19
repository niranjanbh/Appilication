from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import PaymentStatus, RefundStatus


class CreateOrderRequest(BaseModel):
    amount_paise: int = Field(..., gt=0, description="Amount in paise (1 INR = 100 paise)")
    currency: str = Field("INR", max_length=3)
    consultation_id: uuid.UUID | None = None
    notes: dict[str, Any] | None = None


class VerifyPaymentRequest(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str = Field(..., max_length=100)
    razorpay_payment_id: str = Field(..., max_length=100)
    razorpay_signature: str = Field(..., max_length=255)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    consultation_id: uuid.UUID | None
    razorpay_order_id: str
    razorpay_payment_id: str | None
    amount_paise: int
    currency: str
    status: PaymentStatus
    gst_invoice_number: str | None
    gst_invoice_url: str | None


class RefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_id: uuid.UUID
    razorpay_refund_id: str | None
    amount_paise: int
    currency: str
    status: RefundStatus
    reason: str | None
    created_at: datetime


class RefundListResponse(BaseModel):
    items: list[RefundRead]
    total: int
    page: int
    page_size: int
    pages: int
