"""Structured dosing timing on prescription items.

Adds machine-readable dosing fields to kc_prescription_items so the doctor portal
can capture frequency, time-of-day, and food relation as structured data rather
than one free-text string:

  - frequency_code   (enum: OD/BD/TDS/QID/HS/SOS/ALTERNATE_DAYS/WEEKLY/.../OTHER)
  - timing_slots     (JSONB list of 'morning'|'afternoon'|'evening'|'night')
  - food_relation    (enum: before_food/after_food/with_food/empty_stomach/anytime)

The existing `frequency` column becomes a server-composed display string (kept for
the PDF and patient mobile view) and is relaxed to nullable. Existing rows backfill
to frequency_code='OTHER' and timing_slots=[] via server defaults, preserving their
original free-text `frequency`.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_FREQUENCY_CODES = (
    "OD",
    "BD",
    "TDS",
    "QID",
    "HS",
    "SOS",
    "ALTERNATE_DAYS",
    "WEEKLY",
    "BIWEEKLY",
    "MONTHLY",
    "OTHER",
)
_FOOD_RELATIONS = (
    "before_food",
    "after_food",
    "with_food",
    "empty_stomach",
    "anytime",
)


def upgrade() -> None:
    frequency_code = postgresql.ENUM(*_FREQUENCY_CODES, name="frequency_code")
    food_relation = postgresql.ENUM(*_FOOD_RELATIONS, name="food_relation")
    frequency_code.create(op.get_bind(), checkfirst=True)
    food_relation.create(op.get_bind(), checkfirst=True)

    # New structured columns. Both NOT NULL columns carry server defaults so the
    # existing rows backfill in place without a separate data migration.
    op.add_column(
        "kc_prescription_items",
        sa.Column(
            "frequency_code",
            postgresql.ENUM(*_FREQUENCY_CODES, name="frequency_code", create_type=False),
            nullable=False,
            server_default="OTHER",
        ),
    )
    op.add_column(
        "kc_prescription_items",
        sa.Column(
            "timing_slots",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "kc_prescription_items",
        sa.Column(
            "food_relation",
            postgresql.ENUM(*_FOOD_RELATIONS, name="food_relation", create_type=False),
            nullable=True,
        ),
    )

    # `frequency` is now a composed display string — relax NOT NULL.
    op.alter_column("kc_prescription_items", "frequency", nullable=True)


def downgrade() -> None:
    # Re-instate NOT NULL on frequency. Backfill any nulls first so the constraint
    # can be applied cleanly (composed-only rows would otherwise have null here).
    op.execute(
        "UPDATE kc_prescription_items SET frequency = frequency_code "
        "WHERE frequency IS NULL"
    )
    op.alter_column("kc_prescription_items", "frequency", nullable=False)

    op.drop_column("kc_prescription_items", "food_relation")
    op.drop_column("kc_prescription_items", "timing_slots")
    op.drop_column("kc_prescription_items", "frequency_code")

    postgresql.ENUM(name="food_relation").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="frequency_code").drop(op.get_bind(), checkfirst=True)
