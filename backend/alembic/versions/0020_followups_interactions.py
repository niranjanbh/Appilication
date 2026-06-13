"""Create ad_followups and ad_patient_interactions tables.

Coordinator follow-up queue and patient-interaction log. Both tables hold
operational notes only — clinical content never lands here (coordinators are
schema-blocked from lab values, prescriptions, and doctor notes).

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ad_followups",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "coordinator_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ad_coordinators.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("kc_patients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ad_followups_coord_status_due",
        "ad_followups",
        ["coordinator_id", "status", "due_at"],
    )

    op.create_table(
        "ad_patient_interactions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "coordinator_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ad_coordinators.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("kc_patients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ad_patient_interactions_patient",
        "ad_patient_interactions",
        ["patient_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ad_patient_interactions_patient", table_name="ad_patient_interactions")
    op.drop_table("ad_patient_interactions")
    op.drop_index("ix_ad_followups_coord_status_due", table_name="ad_followups")
    op.drop_table("ad_followups")
