"""Add kc_consultations.recording_egress_id — stoppable recordings.

Adds a nullable column holding the LiveKit S3-egress id for an in-flight
recording. It is set when the doctor joins (recording starts) and cleared when
the consultation completes, so the egress can be explicitly stopped on demand
rather than relying on LiveKit's room empty-timeout. Without it, a consented
recording cannot be halted, undermining per-consultation recording consent
(security rule #20). Forward-only, additive: one nullable column.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "kc_consultations",
        sa.Column("recording_egress_id", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kc_consultations", "recording_egress_id")
