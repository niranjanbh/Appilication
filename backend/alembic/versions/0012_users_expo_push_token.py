"""Add users.expo_push_token for Expo Push notification delivery.

Revision ID: 0012
Revises: b1f309330b5b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "b1f309330b5b"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("expo_push_token", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "expo_push_token")
