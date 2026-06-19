"""Create kc_refunds table and refund_status enum.

Refunds become first-class records so the Razorpay refund id, amount, status,
and timestamp survive beyond the parent payment's status flip. A payment may
have multiple (partial) refunds.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE refund_status AS ENUM ('pending', 'processed', 'failed')
    """)
    op.execute("""
        CREATE TABLE kc_refunds (
            id                  UUID          NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            payment_id          UUID          NOT NULL REFERENCES kc_payments(id) ON DELETE RESTRICT,
            user_id             UUID          NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            razorpay_refund_id  VARCHAR(100),
            amount_paise        INT           NOT NULL,
            currency            VARCHAR(3)    NOT NULL DEFAULT 'INR',
            status              refund_status NOT NULL DEFAULT 'pending',
            reason              VARCHAR(500),
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_refunds_user_created ON kc_refunds (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_kc_refunds_payment ON kc_refunds (payment_id)"
    )
    op.execute(
        "CREATE INDEX ix_kc_refunds_razorpay_refund "
        "ON kc_refunds (razorpay_refund_id) WHERE razorpay_refund_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kc_refunds")
    op.execute("DROP TYPE IF EXISTS refund_status")
