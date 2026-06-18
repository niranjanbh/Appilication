"""Coordinator-assigned consultations: add 'requested' status and request fields.

Patients now submit a consultation *request* (condition + requirement notes +
preferred time window) with no doctor, slot, or fee. A coordinator later assigns
a doctor + slot, at which point the row is priced and a payment order is created.

This makes doctor_id / scheduled_start_at / scheduled_end_at / consultation_fee_paise
nullable (a 'requested' row has none yet) and adds two request-capture columns.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Additive enum value (forward-only; safe per migration rules).
    op.execute("ALTER TYPE consultation_status ADD VALUE IF NOT EXISTS 'requested'")

    # A 'requested' consultation has no doctor, slot, or fee yet.
    op.alter_column("kc_consultations", "doctor_id", nullable=True)
    op.alter_column("kc_consultations", "scheduled_start_at", nullable=True)
    op.alter_column("kc_consultations", "scheduled_end_at", nullable=True)
    op.alter_column("kc_consultations", "consultation_fee_paise", nullable=True)

    # Request-capture columns (nullable — only set on patient-submitted requests).
    op.add_column(
        "kc_consultations",
        sa.Column("requirement_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "kc_consultations",
        sa.Column("preferred_time_window", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kc_consultations", "preferred_time_window")
    op.drop_column("kc_consultations", "requirement_notes")

    # Re-instate NOT NULL (round-trips cleanly only when no 'requested' rows exist).
    op.alter_column("kc_consultations", "consultation_fee_paise", nullable=False)
    op.alter_column("kc_consultations", "scheduled_end_at", nullable=False)
    op.alter_column("kc_consultations", "scheduled_start_at", nullable=False)
    op.alter_column("kc_consultations", "doctor_id", nullable=False)

    # Postgres cannot drop an enum value in place — recreate the type without it.
    op.execute("ALTER TYPE consultation_status RENAME TO consultation_status_old")
    op.execute(
        "CREATE TYPE consultation_status AS ENUM "
        "('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show')"
    )
    op.execute("ALTER TABLE kc_consultations ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE kc_consultations ALTER COLUMN status TYPE consultation_status "
        "USING status::text::consultation_status"
    )
    op.execute("ALTER TABLE kc_consultations ALTER COLUMN status SET DEFAULT 'scheduled'")
    op.execute("DROP TYPE consultation_status_old")
