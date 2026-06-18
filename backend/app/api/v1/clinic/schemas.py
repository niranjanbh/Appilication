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


# Coarse time-of-day preferences the patient can express on a request. The
# coordinator picks the exact doctor + slot; this is only a hint.
_PREFERRED_TIME_WINDOWS = {
    "weekday_morning", "weekday_afternoon", "weekday_evening",
    "weekend_morning", "weekend_afternoon", "weekend_evening",
    "flexible",
}


class ConsultationRequestCreate(BaseModel):
    """Patient-submitted consultation request. No doctor or slot — a coordinator
    assigns those. Doctor selection is deliberately not accepted here."""

    condition_category: str
    consultation_type: ConsultationType = ConsultationType.INITIAL
    requirement_notes: str | None = Field(default=None, max_length=2000)
    preferred_time_window: str | None = Field(default=None)

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

    @field_validator("preferred_time_window")
    @classmethod
    def validate_window(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in _PREFERRED_TIME_WINDOWS:
            raise ValueError(
                f"preferred_time_window must be one of: {', '.join(sorted(_PREFERRED_TIME_WINDOWS))}"
            )
        return v


class ConsultationRequestResponse(BaseModel):
    model_config = {"from_attributes": True}

    consultation_id: uuid.UUID
    status: ConsultationStatus
    condition_category: str
    consultation_type: ConsultationType
    requirement_notes: str | None = None
    preferred_time_window: str | None = None
    created_at: datetime


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
    # None while status == 'requested' (no doctor/slot/fee assigned yet).
    doctor_id: uuid.UUID | None = None
    condition_category: str
    consultation_type: ConsultationType
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    status: ConsultationStatus
    video_room_id: str | None = None
    consultation_fee_paise: int | None = None
    requirement_notes: str | None = None
    preferred_time_window: str | None = None
    payment_id: uuid.UUID | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    # Razorpay order to pay after a coordinator assigns the doctor (status='scheduled',
    # not yet paid). None otherwise.
    payment: RazorpayOrderInfo | None = None


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
