"""Create ad_leads (contact-form help queries) and add contacted-tracking
columns to ad_booking_inquiries so coordinators can mark who reached out.

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-12
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Which coordinator contacted the inquirer, and when. NULL = not contacted.
    # SET NULL: losing a staff account must not delete the inquiry trail.
    op.execute(
        """
        ALTER TABLE ad_booking_inquiries
            ADD COLUMN contacted_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN contacted_at         TIMESTAMPTZ
        """
    )

    op.execute(
        """
        CREATE TABLE ad_leads (
            id                   UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            name                 VARCHAR(255) NOT NULL,
            email                VARCHAR(255) NOT NULL,
            subject              VARCHAR(50)  NOT NULL,
            message              TEXT         NOT NULL,
            ip_address           INET,
            user_agent           VARCHAR(500),
            status               VARCHAR(50)  NOT NULL DEFAULT 'new',
            contacted_by_user_id UUID         REFERENCES users(id) ON DELETE SET NULL,
            contacted_at         TIMESTAMPTZ,
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at           TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX ix_ad_leads_status ON ad_leads (status, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ad_leads")
    op.execute(
        """
        ALTER TABLE ad_booking_inquiries
            DROP COLUMN IF EXISTS contacted_by_user_id,
            DROP COLUMN IF EXISTS contacted_at
        """
    )
