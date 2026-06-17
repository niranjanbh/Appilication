"""Pricing-as-config + coupon management tables + consultation coupon columns.

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. ad_pricing_config — one row per (condition_category, consultation_type) ──
    op.execute(
        """
        CREATE TABLE ad_pricing_config (
            id                  UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            condition_category  condition_category NOT NULL,
            consultation_type   consultation_type  NOT NULL,
            fee_paise           INTEGER     NOT NULL,
            created_by_admin_id UUID        REFERENCES users(id) ON DELETE RESTRICT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (condition_category, consultation_type)
        )
        """
    )

    # ── 2. ad_coupons — DMR-Act-constrained discount codes ──────────────────────
    op.execute(
        """
        CREATE TABLE ad_coupons (
            id                  UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            code                VARCHAR(50) NOT NULL,
            description         TEXT,
            discount_type       VARCHAR(10) NOT NULL
                CHECK (discount_type IN ('flat', 'percent')),
            discount_value      INTEGER     NOT NULL
                CHECK (discount_value > 0),
            max_discount_paise  INTEGER,
            min_order_paise     INTEGER     NOT NULL DEFAULT 0,
            max_redemptions     INTEGER,
            redemption_count    INTEGER     NOT NULL DEFAULT 0,
            valid_from          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            valid_until         TIMESTAMPTZ,
            active              BOOLEAN     NOT NULL DEFAULT true,
            created_by_admin_id UUID        REFERENCES users(id) ON DELETE RESTRICT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (code)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_ad_coupons_code ON ad_coupons (code)"
    )

    # ── 3. Add coupon columns to kc_consultations (additive, nullable/defaulted) ─
    op.execute(
        """
        ALTER TABLE kc_consultations
            ADD COLUMN coupon_id      UUID
                REFERENCES ad_coupons(id) ON DELETE RESTRICT,
            ADD COLUMN discount_paise INTEGER NOT NULL DEFAULT 0
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE kc_consultations
            DROP COLUMN IF EXISTS discount_paise,
            DROP COLUMN IF EXISTS coupon_id
        """
    )
    op.execute("DROP TABLE IF EXISTS ad_coupons")
    op.execute("DROP TABLE IF EXISTS ad_pricing_config")
