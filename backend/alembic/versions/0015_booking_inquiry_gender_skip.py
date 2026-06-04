"""Add gender and skipped_intake columns to ad_booking_inquiries.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # gender is nullable so existing rows default to NULL (unknown)
    op.execute(
        """
        ALTER TABLE ad_booking_inquiries
            ADD COLUMN gender       VARCHAR(10),
            ADD COLUMN skipped_intake BOOLEAN NOT NULL DEFAULT false
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE ad_booking_inquiries
            DROP COLUMN IF EXISTS gender,
            DROP COLUMN IF EXISTS skipped_intake
        """
    )