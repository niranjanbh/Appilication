from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import ContentStatus, ContentType, enum_values
from app.db.mixins import TimestampMixin, UUIDMixin


class EducationContent(Base, UUIDMixin, TimestampMixin):
    """Doctor-reviewed educational content assigned to patients.

    Per clinical compliance: every published piece stores the reviewing doctor's
    NMC registration for regulatory audit. ai_disclosure=True requires a UI badge.
    """

    __tablename__ = "kc_education_content"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    content_type: Mapped[ContentType] = mapped_column(
        SAEnum(ContentType, name="content_type", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    condition_categories: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    content_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        SAEnum(ContentStatus, name="content_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'draft'"),
        index=True,
    )
    ai_disclosure: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )


class EducationAssignment(Base, UUIDMixin, TimestampMixin):
    """A specific piece of content assigned to a patient by a doctor."""

    __tablename__ = "kc_education_assignments"

    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_education_content.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by_doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_consultations.id", ondelete="SET NULL"),
        nullable=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
