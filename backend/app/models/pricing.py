from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import ConsultationType, enum_values
from app.db.mixins import TimestampMixin, UUIDMixin


class PricingConfig(Base, UUIDMixin, TimestampMixin):
    """Per-vertical consultation pricing, admin-managed via /v1/admin/pricing."""

    __tablename__ = "ad_pricing_config"

    condition_category: Mapped[str] = mapped_column(
        SAEnum(
            "thyroid", "weight", "pcos", "skin_hair", "mens_intimate",
            "hormones_trt", "longevity",
            name="condition_category", create_type=False,
        ),
        nullable=False,
    )
    consultation_type: Mapped[ConsultationType] = mapped_column(
        SAEnum(
            ConsultationType,
            name="consultation_type",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    fee_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class Coupon(Base, UUIDMixin, TimestampMixin):
    """Admin-managed coupon codes with DMR-Act-constrained discount rules."""

    __tablename__ = "ad_coupons"

    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(10), nullable=False)
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    max_discount_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_order_paise: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    max_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redemption_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
