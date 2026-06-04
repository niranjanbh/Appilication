from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, String, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class BookingInquiry(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "ad_booking_inquiries"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    condition_category: Mapped[str] = mapped_column(String(50), nullable=False)
    intake_responses: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    skipped_intake: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="new"
    )
    # id field comes from UUIDMixin but needs UUID dialect type here
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
