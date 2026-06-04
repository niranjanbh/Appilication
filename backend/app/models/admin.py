from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String, UniqueConstraint, text
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
