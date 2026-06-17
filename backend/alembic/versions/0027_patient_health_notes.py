"""Patient health notes: kc_patient_notes table.

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE kc_patient_notes (
            id              UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            patient_user_id UUID        NOT NULL
                REFERENCES users(id) ON DELETE RESTRICT,
            body            TEXT        NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_kc_patient_notes_patient_user_id ON kc_patient_notes (patient_user_id)"
    )
    op.execute(
        "CREATE INDEX ix_kc_patient_notes_created_at ON kc_patient_notes (patient_user_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_kc_patient_notes_created_at")
    op.execute("DROP INDEX IF EXISTS ix_kc_patient_notes_patient_user_id")
    op.execute("DROP TABLE IF EXISTS kc_patient_notes")
