from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

# Accepts any valid E.164 number: + followed by 7-15 digits
_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")

# Canonical slugs — must stay in sync with website/lib/conditions.ts (CONDITIONS)
# and the website booking flow (components/marketing/BookingFlow.tsx).
CONDITION_CATEGORIES = {
    "thyroid",
    "weight-management",
    "diabetes",
    "pmos",
    "skin-and-hair",
    "sexual-health",
    "hormones-trt",
    "longevity",
}

# 2026-06 renames (see website/public/_redirects): accept old slugs from cached
# pages or stale clients and normalize to the canonical value before storage.
LEGACY_CONDITION_ALIASES = {
    "pcos": "pmos",
    "mens-intimate-health": "sexual-health",
}

GENDER_VALUES = {"male", "female", "other"}

_OTP_RE = re.compile(r"^\d{6}$")


class BookingInquiryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    gender: Literal["male", "female", "other"] = Field(
        description="Patient's self-reported gender. Required for coordinator handoff."
    )
    phone: str = Field(description="Phone in E.164 format, e.g. +919876543210 or +12125550101")
    email: EmailStr | None = Field(default=None)
    condition_category: str = Field(description="One of the 8 Kyros verticals")
    intake_responses: dict[str, Any] = Field(
        default_factory=dict,
        description="Condition-specific intake answers. Empty when skipped.",
    )
    skipped_intake: bool = Field(
        default=False,
        description="True when the patient skipped intake and chose direct coordinator contact.",
    )
    otp: str | None = Field(
        default=None,
        description=(
            "6-digit verification code from /v1/public/booking-otp. Required only "
            "when the deployment has booking OTP verification enabled."
        ),
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError("phone must be in E.164 format, e.g. +919876543210")
        return v

    @field_validator("condition_category")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        v = LEGACY_CONDITION_ALIASES.get(v, v)
        if v not in CONDITION_CATEGORIES:
            raise ValueError(f"condition_category must be one of: {', '.join(sorted(CONDITION_CATEGORIES))}")
        return v

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str | None) -> str | None:
        if v is not None and not _OTP_RE.match(v):
            raise ValueError("otp must be exactly 6 digits")
        return v

    @field_validator("intake_responses")
    @classmethod
    def validate_intake_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(v) > 20:
            raise ValueError("intake_responses may not contain more than 20 fields")
        return v


class BookingInquiryRead(BaseModel):
    id: uuid.UUID
    message: str

    model_config = {"from_attributes": True}


class LeadCreate(BaseModel):
    """Help query from the website contact form."""

    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=10, max_length=1000)


class LeadRead(BaseModel):
    id: uuid.UUID
    message: str

    model_config = {"from_attributes": True}


class BookingOtpRequest(BaseModel):
    phone: str = Field(description="Phone in E.164 format, e.g. +919876543210")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError("phone must be in E.164 format, e.g. +919876543210")
        return v


class BookingOtpResponse(BaseModel):
    message: str
    otp_hint: str | None = None


class ConditionRead(BaseModel):
    slug: str
    name: str
    short_description: str


# Mirrors website/lib/conditions.ts — slugs, names, and display order.
_CONDITIONS: list[ConditionRead] = [
    ConditionRead(
        slug="weight-management",
        name="Weight Management",
        short_description="Doctor-supervised weight management, including GLP-1 therapy where indicated.",
    ),
    ConditionRead(
        slug="diabetes",
        name="Diabetes",
        short_description="Prediabetes, type 2 diabetes, and ongoing blood sugar management.",
    ),
    ConditionRead(
        slug="thyroid",
        name="Thyroid",
        short_description="Hypothyroidism, Hashimoto's, and thyroid hormone balance.",
    ),
    ConditionRead(
        slug="pmos",
        name="PMOS (PCOS)",
        short_description="Polycystic ovary syndrome — hormonal, metabolic, and reproductive care.",
    ),
    ConditionRead(
        slug="skin-and-hair",
        name="Skin & Hair",
        short_description="AGA, adult acne, melasma, and other dermatological conditions.",
    ),
    ConditionRead(
        slug="sexual-health",
        name="Sexual & Intimate Health",
        short_description="Sexual and intimate health concerns in men and women — evaluated medically, in private.",
    ),
    ConditionRead(
        slug="hormones-trt",
        name="Hormones & TRT",
        short_description="Low testosterone, hormonal imbalance, and supervised TRT.",
    ),
    ConditionRead(
        slug="longevity",
        name="Longevity",
        short_description="Cardiometabolic panels, biomarker monitoring, and preventive care.",
    ),
]


def get_conditions() -> list[ConditionRead]:
    return _CONDITIONS
