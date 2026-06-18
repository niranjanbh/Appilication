from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.db.enums import ConsultationStatus, ConsultationType

_DB_CONDITION_CATEGORIES = {
    "thyroid", "weight", "pcos", "skin_hair",
    "mens_intimate", "hormones_trt", "longevity",
}

_SLUG_TO_DB: dict[str, str] = {
    "weight-management": "weight",
    "pmos": "pcos",
    "skin-and-hair": "skin_hair",
    "sexual-health": "mens_intimate",
    "diabetes": "weight",
}


class AvailableSlotRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    doctor_id: uuid.UUID
    slot_start: datetime
    slot_end: datetime


class ConsultationBookRequest(BaseModel):
    doctor_id: uuid.UUID
    slot_id: uuid.UUID
    condition_category: str
    consultation_type: ConsultationType = ConsultationType.INITIAL
    idempotency_key: uuid.UUID | None = Field(default=None)
    coupon_code: str | None = None

    @field_validator("condition_category")
    @classmethod
    def normalize_condition(cls, v: str) -> str:
        v = _SLUG_TO_DB.get(v, v)
        if v not in _DB_CONDITION_CATEGORIES:
            raise ValueError(
                f"condition_category must be one of: {', '.join(sorted(_DB_CONDITION_CATEGORIES))} "
                f"(or website aliases: {', '.join(sorted(_SLUG_TO_DB))})"
            )
        return v


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
    discount_paise: int = 0
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
