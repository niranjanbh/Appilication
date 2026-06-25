"""Admin-portal view schemas — the ORM→template serialization boundary.

The super-admin portal is allowed to see everything (unlike the coordinator
portal, which strips clinical content at the schema layer). These schemas exist
to satisfy the architecture rule that routers/views never hand a raw ORM object
to a template: every admin view serializes through one of these first.

Design notes:
- Enum-typed fields are kept as their StrEnum type (not coerced to ``str``), so
  the existing Jinja templates that render ``{{ obj.status.value }}`` keep working
  unchanged. This mirrors ``CoordinatorConsultationView.status``.
- Tuple-shape helpers at the bottom convert the ``(Doctor, User)`` /
  ``(Payment, User)`` / ``(Consultation, User, User|None)`` rows the admin
  repository returns, preserving the tuple shape the templates iterate over.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.db.enums import (
    ConsultationStatus,
    ConsultationType,
    ContentStatus,
    ContentType,
    DataSubjectRequestStatus,
    DataSubjectRequestType,
    DoctorStatus,
    OtpResetChannel,
    PaymentStatus,
    UserRole,
)


class AdminUserView(BaseModel):
    """Full user projection for admin templates and detail pages."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    email: str | None = None
    phone: str | None = None
    role: UserRole
    city: str | None = None
    state: str | None = None
    reset_otp_channel: OtpResetChannel | None = None
    phone_verified: bool = False
    email_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    deleted_at: datetime | None = None
    erased_at: datetime | None = None


class AdminDoctorView(BaseModel):
    """Doctor profile projection for admin templates."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    nmc_registration_number: str
    nmc_state_council: str | None = None
    specialty: list[Any] = []
    conditions_treated: list[Any] = []
    consultation_languages: list[Any] = []
    status: DoctorStatus
    consultation_duration_minutes_default: int
    buffer_time_minutes: int
    revenue_share_pct: Decimal | None = None
    bank_details_encrypted: bytes | None = None
    bio_short: str | None = None
    bio_long: str | None = None
    onboarding_stage: str | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminConsultationView(BaseModel):
    """Consultation projection for admin templates — all operational fields."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None = None
    condition_category: str
    consultation_type: ConsultationType
    status: ConsultationStatus
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    consultation_fee_paise: int | None = None
    cancellation_reason: str | None = None
    created_at: datetime


class AdminPaymentView(BaseModel):
    """Payment projection for admin templates. Money stays in paise (int)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    consultation_id: uuid.UUID | None = None
    razorpay_order_id: str
    razorpay_payment_id: str | None = None
    amount_paise: int
    currency: str
    status: PaymentStatus
    gst_invoice_number: str | None = None
    gst_invoice_url: str | None = None
    created_at: datetime


class AdminDsrView(BaseModel):
    """Data-subject-request projection for the admin DSR queue."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    request_type: DataSubjectRequestType
    status: DataSubjectRequestStatus
    received_at: datetime
    completed_at: datetime | None = None
    notes: str | None = None


class AdminContentView(BaseModel):
    """Education-content projection for the admin content library."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    slug: str
    content_type: ContentType
    condition_categories: list[Any] = []
    content_url: str | None = None
    body_md: str | None = None
    reviewed_by_doctor_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    status: ContentStatus
    ai_disclosure: bool = False
    created_at: datetime
    updated_at: datetime


# ── Tuple-shape serialization helpers ────────────────────────────────────────────
# The admin repository returns ORM tuples; these convert each element through the
# views above while preserving the tuple shape the templates iterate over.


def user_list(rows: list[Any]) -> list[AdminUserView]:
    return [AdminUserView.model_validate(u) for u in rows]


def content_list(rows: list[Any]) -> list[AdminContentView]:
    return [AdminContentView.model_validate(c) for c in rows]


def doctor_pairs(
    rows: Sequence[tuple[object, object]],
) -> list[tuple[AdminDoctorView, AdminUserView]]:
    """(Doctor, User) -> (AdminDoctorView, AdminUserView)."""
    return [
        (AdminDoctorView.model_validate(doctor), AdminUserView.model_validate(user))
        for doctor, user in rows
    ]


def payment_pairs(
    rows: Sequence[tuple[object, object]],
) -> list[tuple[AdminPaymentView, AdminUserView]]:
    """(Payment, payer User) -> (AdminPaymentView, AdminUserView)."""
    return [
        (AdminPaymentView.model_validate(payment), AdminUserView.model_validate(payer))
        for payment, payer in rows
    ]


def consultation_triples(
    rows: Sequence[tuple[object, object, object]],
) -> list[tuple[AdminConsultationView, AdminUserView, AdminUserView | None]]:
    """(Consultation, patient_user, doctor_user|None) -> all three serialized."""
    return [
        (
            AdminConsultationView.model_validate(consultation),
            AdminUserView.model_validate(patient_user),
            AdminUserView.model_validate(doctor_user)
            if doctor_user is not None
            else None,
        )
        for consultation, patient_user, doctor_user in rows
    ]


def dsr_pairs(
    rows: Sequence[tuple[object, str]],
) -> list[tuple[AdminDsrView, str]]:
    """(DataSubjectRequest, user_name) -> (AdminDsrView, user_name)."""
    return [(AdminDsrView.model_validate(dsr), name) for dsr, name in rows]
