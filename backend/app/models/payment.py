from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import PaymentStatus, RefundStatus, enum_values
from app.db.mixins import TimestampMixin, UUIDMixin


class Payment(Base, UUIDMixin, TimestampMixin):
    """Razorpay payment record. Money stored in paise (integer). No soft delete."""

    __tablename__ = "kc_payments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # FK to kc_consultations added in P12.
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    razorpay_order_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'INR'")
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'created'"),
    )
    gst_invoice_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gst_invoice_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Refund(Base, UUIDMixin, TimestampMixin):
    """Razorpay refund record. A payment may have multiple (partial) refunds.

    Money stored in paise (integer). user_id is denormalized from the parent
    payment so refunds can be scoped to a patient without joining kc_payments.
    """

    __tablename__ = "kc_refunds"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_payments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    razorpay_refund_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'INR'")
    )
    status: Mapped[RefundStatus] = mapped_column(
        SAEnum(RefundStatus, name="refund_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'pending'"),
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
