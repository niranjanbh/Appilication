from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

# Accepts any valid E.164 number: + followed by 7-15 digits
_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")

CONDITION_CATEGORIES = {
    "thyroid",
    "weight-management",
    "pcos",
    "skin-and-hair",
    "mens-intimate-health",
    "hormones-trt",
    "longevity",
}

GENDER_VALUES = {"male", "female", "other"}


class BookingInquiryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    gender: Literal["male", "female", "other"] = Field(
        description="Patient's self-reported gender. Required for coordinator handoff."
    )
    phone: str = Field(description="Phone in E.164 format, e.g. +919876543210 or +12125550101")
    email: EmailStr | None = Field(default=None)
    condition_category: str = Field(description="One of the 7 Kyros verticals")
    intake_responses: dict[str, Any] = Field(
        default_factory=dict,
        description="Condition-specific intake answers. Empty when skipped.",
    )
    skipped_intake: bool = Field(
        default=False,
        description="True when the patient skipped intake and chose direct coordinator contact.",
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
        if v not in CONDITION_CATEGORIES:
            raise ValueError(f"condition_category must be one of: {', '.join(sorted(CONDITION_CATEGORIES))}")
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


class ConditionRead(BaseModel):
    slug: str
    name: str
    short_description: str


_CONDITIONS: list[ConditionRead] = [
    ConditionRead(
        slug="thyroid",
        name="Thyroid",
        short_description="Hypothyroidism, Hashimoto's, and thyroid hormone balance.",
    ),
    ConditionRead(
        slug="weight-management",
        name="Weight Management",
        short_description="Doctor-supervised weight management including GLP-1 therapy where indicated.",
    ),
    ConditionRead(
        slug="pcos",
        name="PCOS",
        short_description="Polycystic ovary syndrome — hormonal, metabolic, and reproductive care.",
    ),
    ConditionRead(
        slug="skin-and-hair",
        name="Skin & Hair",
        short_description="AGA, adult acne, melasma, and other dermatological conditions.",
    ),
    ConditionRead(
        slug="mens-intimate-health",
        name="Men's Intimate Health",
        short_description="ED, premature ejaculation, and related sexual health evaluation.",
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
