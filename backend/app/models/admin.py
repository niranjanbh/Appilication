from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import CoordinatorStatus, enum_values
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Coordinator(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "ad_coordinators"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    status: Mapped[CoordinatorStatus] = mapped_column(
        SAEnum(
            CoordinatorStatus,
            name="coordinator_status",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default=text("'active'"),
    )
    assigned_patient_ids: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    employee_id: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Followup(Base, UUIDMixin, TimestampMixin):
    """Coordinator follow-up task for an assigned patient.

    The note is operational ("call to check on consult #2 booking"), never
    clinical. Lab values, prescription contents, and doctor-note content must
    not be written here — coordinators are schema-blocked from those fields.
    """

    __tablename__ = "ad_followups"

    coordinator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_coordinators.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(String(500), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_ad_followups_coord_status_due", "coordinator_id", "status", "due_at"),
    )


class PatientInteraction(Base, UUIDMixin, TimestampMixin):
    """Operational log of a coordinator's contact with a patient.

    Replaces ad-hoc WhatsApp/Excel notes (a PHI-leak vector). Summary is
    operational, never clinical.
    """

    __tablename__ = "ad_patient_interactions"

    coordinator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_coordinators.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)

    __table_args__ = (
        Index("ix_ad_patient_interactions_patient", "patient_id", "created_at"),
    )


class DailyMetric(Base, UUIDMixin, TimestampMixin):
    """Pre-aggregated daily analytics rollup, populated by kyros.analytics.rollup_daily."""

    __tablename__ = "ad_daily_metrics"

    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[str] = mapped_column(
        String(128), nullable=False, server_default=text("''")
    )
    value: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )

    __table_args__ = (
        UniqueConstraint(
            "metric_date", "metric_key", "dimension", name="uq_ad_daily_metrics"
        ),
        Index("ix_ad_daily_metrics_date_key", "metric_date", "metric_key"),
    )
