"""Public booking inquiries table for pre-account consultation requests.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-02
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ad_booking_inquiries (
            id                 UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            name               VARCHAR(255) NOT NULL,
            phone              VARCHAR(20)  NOT NULL,
            email              VARCHAR(255),
            condition_category VARCHAR(50)  NOT NULL,
            intake_responses   JSONB        NOT NULL DEFAULT '{}',
            ip_address         INET,
            user_agent         VARCHAR(500),
            status             VARCHAR(50)  NOT NULL DEFAULT 'new',
            created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at         TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_ad_booking_inquiries_status ON ad_booking_inquiries (status, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_ad_booking_inquiries_phone ON ad_booking_inquiries (phone)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ad_booking_inquiries")
