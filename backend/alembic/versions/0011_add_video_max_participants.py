"""Add kc_consultations.video_max_participants — per-consultation room cap.

Adds a nullable integer column holding the maximum number of video-room
participants for a consultation. NULL falls back to the platform default
(settings.video_default_max_participants). Staff set it when creating an
on-demand multi-specialist consultation, up to settings.video_max_participants_cap.
Forward-only, additive: one nullable column.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "kc_consultations",
        sa.Column("video_max_participants", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kc_consultations", "video_max_participants")
