"""Add partial unique index — one active consultation per (patient, condition).

Backstops the read-check in ``request_consultation``: a TOCTOU race between two
concurrent POSTs could both observe "no active consultation" and both insert,
creating duplicates. This partial unique index makes the database the source of
truth — only one non-terminal, non-deleted consultation may exist per
(patient_id, condition_category). The terminal statuses (completed, cancelled,
no_show) and soft-deleted rows are excluded so a patient can re-request the same
condition after a prior consultation closes.

Created CONCURRENTLY (outside a transaction) to avoid locking writes on
kc_consultations during the build. Forward-only, additive: one index.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEX_NAME = "uq_active_consultation_per_condition"


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            f"""
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX_NAME}
            ON kc_consultations (patient_id, condition_category)
            WHERE status NOT IN ('completed', 'cancelled', 'no_show')
              AND deleted_at IS NULL
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX_NAME}")
