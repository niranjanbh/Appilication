"""Add 'admin' to user_role and actor_role enums — the read-only admin tier.

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-13
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum changes are additive only (migration rules). On Postgres 12+ this is
    # transaction-safe as long as the new value isn't used in the same migration.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin'")
    op.execute("ALTER TYPE actor_role ADD VALUE IF NOT EXISTS 'admin'")


def downgrade() -> None:
    # Postgres cannot remove enum values. Leaving 'admin' in place is harmless:
    # no rows reference it after the application code is rolled back.
    pass
