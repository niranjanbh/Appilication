"""Add wn_symptom_checkins table for daily mood/energy check-ins.

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wn_symptom_checkins",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mood", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_wn_symptom_checkins_user_id", "wn_symptom_checkins", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_wn_symptom_checkins_user_id", table_name="wn_symptom_checkins")
    op.drop_table("wn_symptom_checkins")
