from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.enums import ConsultationStatus, ConsultationType


class AvailableSlotRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    doctor_id: uuid.UUID
    slot_start: datetime
    slot_end: datetime


class ConsultationBookRequest(BaseModel):
    doctor_id: uuid.UUID
    slot_id: uuid.UUID
    condition_category: str = Field(
        ...,
        pattern="^(thyroid|weight|pcos|skin_hair|mens_intimate|hormones_trt|longevity)$",
    )
    consultation_type: ConsultationType = ConsultationType.INITIAL
    # Fee is resolved server-side from pricing config — never supplied by the client.
    idempotency_key: uuid.UUID | None = Field(default=None)


class RazorpayOrderInfo(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    amount_paise: int
    currency: str


class ConsultationBookResponse(BaseModel):
    model_config = {"from_attributes": True}

    consultation_id: uuid.UUID
    status: ConsultationStatus
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    condition_category: str
    consultation_type: ConsultationType
    consultation_fee_paise: int
    payment: RazorpayOrderInfo


class PatientConsultationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    doctor_id: uuid.UUID
    condition_category: str
    consultation_type: ConsultationType
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    status: ConsultationStatus
    video_room_id: str | None
    consultation_fee_paise: int
    payment_id: uuid.UUID | None
    cancellation_reason: str | None
    created_at: datetime


class PatientConsultationListResponse(BaseModel):
    items: list[PatientConsultationRead]
    total: int
    page: int
    page_size: int
    pages: int


class ConsultationConfirmPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class ConsultationCancelRequest(BaseModel):
    reason: str = Field(default="", max_length=500)


class ConsultationCancelResponse(BaseModel):
    consultation_id: uuid.UUID
    status: ConsultationStatus
    refund_issued: bool


class ConsultationJoinResponse(BaseModel):
    room_id: str
    token: str
    endpoint: str = "https://prod-in2.100ms.live/hmscore"


class RecordingConsentResponse(BaseModel):
    consultation_id: uuid.UUID
    recording_consent: bool
