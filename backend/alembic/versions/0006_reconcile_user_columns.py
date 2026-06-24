"""Reconcile users-table drift on environments built from the pre-squash tree.

Production was deployed from the old (pre-squash) migration lineage, where
`expo_push_token`, `notification_preferences`, `reset_otp_channel`, `google_sub`
and `erased_at` arrived in later migrations (0012/0017/0021). The squash folded
those columns into `0001`, but a database physically built by the *old* `0001`
never received them — while its `alembic_version` still advanced to the new head.
The result is a schema whose `alembic_version` reads current but whose `users`
table is missing columns the ORM selects on every auth lookup, 500-ing all login
and password-reset traffic.

This migration is **additive and idempotent**: every statement is guarded with
`IF NOT EXISTS`, so it adds the missing columns on a drifted database and is a
no-op on a correctly-built one (where `0001` already created them). It performs
no destructive change and touches no data beyond backfilling the new
NOT-NULL-with-default column.

Revision ID: 0006
Revises: 0001
Create Date: 2026-06-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum backing reset_otp_channel — create only if a pre-squash DB lacks it.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'otp_reset_channel') THEN
                CREATE TYPE otp_reset_channel AS ENUM ('email', 'sms');
            END IF;
        END$$;
        """
    )

    # Tail columns folded into 0001 by the squash. All nullable, or NOT NULL with
    # a server_default, so they apply cleanly to a table with existing rows.
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "expo_push_token VARCHAR(200)"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "notification_preferences JSONB NOT NULL "
        """DEFAULT '{"push": true, "email": true, "whatsapp": true}'::jsonb"""
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "reset_otp_channel otp_reset_channel"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "google_sub VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "erased_at TIMESTAMPTZ"
    )

    # Unique constraint on google_sub (named to match the squashed 0001).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_google_sub'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT uq_users_google_sub UNIQUE (google_sub);
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    # Forward-only reconciliation. On a correctly-built database these columns are
    # owned by 0001, so dropping them here would corrupt that schema; on a drifted
    # database there is no prior state to restore them to. Intentionally a no-op so
    # the up/down round-trip test leaves a correct schema untouched.
    pass
