from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import ConsentType, DataSubjectRequestStatus, DataSubjectRequestType, enum_values
from app.db.mixins import TimestampMixin, UUIDMixin


class ConsentRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ad_consent_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    consent_type: Mapped[ConsentType] = mapped_column(
        SAEnum(ConsentType, name="consent_type", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    granted: Mapped[bool] = mapped_column(nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    consent_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DataSubjectRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ad_data_subject_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    request_type: Mapped[DataSubjectRequestType] = mapped_column(
        SAEnum(DataSubjectRequestType, name="data_subject_request_type", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    status: Mapped[DataSubjectRequestStatus] = mapped_column(
        SAEnum(
            DataSubjectRequestStatus,
            name="data_subject_request_status",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(nullable=True)
