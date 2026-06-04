from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import AvailabilityStatus, CredentialType, DoctorStatus, enum_values
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Doctor(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "dr_doctors"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    nmc_registration_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    nmc_state_council: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    specialty: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    conditions_treated: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    consultation_languages: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[\"en\"]'::jsonb")
    )
    status: Mapped[DoctorStatus] = mapped_column(
        SAEnum(DoctorStatus, name="doctor_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'applied'"),
    )
    consultation_duration_minutes_default: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("20")
    )
    buffer_time_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("5")
    )
    revenue_share_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    bank_details_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    bio_short: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio_long: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    onboarding_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Availability(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "dr_availability"
    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_start", name="uq_dr_avail_doctor_slot"),
    )

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AvailabilityStatus] = mapped_column(
        SAEnum(
            AvailabilityStatus,
            name="availability_status",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default=text("'available'"),
    )
    # FK to kc_consultations added in P12 when that table is created.
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )


class Credential(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "dr_credentials"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_type: Mapped[CredentialType] = mapped_column(
        SAEnum(
            CredentialType,
            name="credential_type",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verified_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
