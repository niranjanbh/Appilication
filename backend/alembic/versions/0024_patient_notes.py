"""Create kc_patient_notes table.

Freeform health notes written by a patient, readable by their treating doctors.
Soft-deleted via deleted_at (never hard-deleted — DPDP DSR handles erasure separately).

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kc_patient_notes",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("patient_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_user_id"],
            ["users.id"],
            name="fk_kc_patient_notes_patient_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_kc_patient_notes"),
    )
    op.create_index(
        "ix_kc_patient_notes_patient_user_id",
        "kc_patient_notes",
        ["patient_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_kc_patient_notes_patient_user_id", table_name="kc_patient_notes")
    op.drop_table("kc_patient_notes")
