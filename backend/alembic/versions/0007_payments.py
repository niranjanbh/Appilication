"""Payments: payment_status enum, kc_payments table, gst_invoice_seq.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE payment_status AS ENUM "
        "('created', 'attempted', 'paid', 'failed', 'refunded', 'partial_refunded')"
    )

    # Sequential GST invoice numbering
    op.execute("CREATE SEQUENCE gst_invoice_seq START 1 INCREMENT 1 NO CYCLE")

    # consultation_id FK to kc_consultations added in P12
    op.execute(
        """
        CREATE TABLE kc_payments (
            id                   UUID           NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id              UUID           NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            consultation_id      UUID,
            razorpay_order_id    VARCHAR(100)   NOT NULL UNIQUE,
            razorpay_payment_id  VARCHAR(100),
            amount_paise         INT            NOT NULL,
            currency             VARCHAR(3)     NOT NULL DEFAULT 'INR',
            status               payment_status NOT NULL DEFAULT 'created',
            gst_invoice_number   VARCHAR(50),
            gst_invoice_url      VARCHAR(500),
            created_at           TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ    NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_kc_payments_user_status ON kc_payments (user_id, status)"
    )
    op.execute(
        "CREATE INDEX ix_kc_payments_razorpay_payment ON kc_payments (razorpay_payment_id) "
        "WHERE razorpay_payment_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_kc_payments_consultation ON kc_payments (consultation_id) "
        "WHERE consultation_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kc_payments CASCADE")
    op.execute("DROP SEQUENCE IF EXISTS gst_invoice_seq")
    op.execute("DROP TYPE IF EXISTS payment_status")
