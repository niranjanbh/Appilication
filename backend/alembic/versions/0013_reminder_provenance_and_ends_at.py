"""Add wn_reminders provenance columns and ends_at.

Adds ends_at (finite-course cutoff) plus source_type / source_id / generated_by
provenance columns so prescription/care-plan generated reminders are explicitly
attributable and queries can ignore occurrences after a course ends.

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "wn_reminders",
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "wn_reminders",
        sa.Column(
            "source_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
    )
    op.add_column(
        "wn_reminders",
        sa.Column("source_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "wn_reminders",
        sa.Column(
            "generated_by",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'patient'"),
        ),
    )
    # Look up a patient's reminders by their originating prescription/care-plan row.
    op.create_index(
        "ix_wn_reminders_source",
        "wn_reminders",
        ["source_type", "source_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_wn_reminders_source", table_name="wn_reminders")
    op.drop_column("wn_reminders", "generated_by")
    op.drop_column("wn_reminders", "source_id")
    op.drop_column("wn_reminders", "source_type")
    op.drop_column("wn_reminders", "ends_at")
