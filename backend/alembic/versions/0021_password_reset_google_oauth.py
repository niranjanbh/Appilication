"""Add password-reset OTP channel, Google account linkage, and platform settings.

Adds:
  - enum otp_reset_channel('email','sms')
  - users.reset_otp_channel (nullable; admin-controlled, NULL → platform default)
  - users.google_sub (nullable, unique; Google subject id for linked patients)
  - ad_platform_settings (key/value JSONB; admin-controlled non-secret config)

Seeds the two settings the app reads (default reset channel, Google toggle) so
the rows always exist; the service still defaults defensively if a key is absent.

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE otp_reset_channel AS ENUM ('email', 'sms')")

    op.add_column(
        "users",
        sa.Column(
            "reset_otp_channel",
            sa.Enum(
                "email",
                "sms",
                name="otp_reset_channel",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("google_sub", sa.String(255), nullable=True),
    )
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])

    op.create_table(
        "ad_platform_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column(
            "value", JSONB, nullable=False, server_default=sa.text("'null'::jsonb")
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Seed the keys the application reads. ON CONFLICT keeps re-runs idempotent.
    op.execute(
        """
        INSERT INTO ad_platform_settings (key, value) VALUES
            ('reset_otp_channel_default', '"sms"'::jsonb),
            ('google_oauth_enabled', 'false'::jsonb)
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("ad_platform_settings")
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "reset_otp_channel")
    op.execute("DROP TYPE IF EXISTS otp_reset_channel")
