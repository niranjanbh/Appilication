"""Add kc_consultations.parent_consultation_id — follow-up linkage.

Adds a nullable self-referential FK so a follow-up consultation can point back to
the consultation it originated from. ON DELETE SET NULL: deleting a parent must not
cascade-delete its follow-up children. Forward-only, additive: one nullable column,
its FK, and its index.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "kc_consultations",
        sa.Column("parent_consultation_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_kc_consultations_parent_consultation_id",
        "kc_consultations",
        "kc_consultations",
        ["parent_consultation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_kc_consultations_parent_consultation_id",
        "kc_consultations",
        ["parent_consultation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_kc_consultations_parent_consultation_id",
        table_name="kc_consultations",
    )
    op.drop_constraint(
        "fk_kc_consultations_parent_consultation_id",
        "kc_consultations",
        type_="foreignkey",
    )
    op.drop_column("kc_consultations", "parent_consultation_id")
