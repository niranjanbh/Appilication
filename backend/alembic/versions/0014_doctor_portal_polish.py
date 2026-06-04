"""Doctor portal polish: buffer_time_minutes on dr_doctors, annotations on kc_lab_reports.

Revision ID: 0014
Revises: 0013
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # dr_doctors: buffer time between consultations (minutes)
    op.execute(
        "ALTER TABLE dr_doctors ADD COLUMN IF NOT EXISTS "
        "buffer_time_minutes INTEGER NOT NULL DEFAULT 5"
    )

    # kc_lab_reports: doctor commentary (JSONB keyed by biomarker name → text)
    op.execute(
        "ALTER TABLE kc_lab_reports ADD COLUMN IF NOT EXISTS "
        "doctor_commentary JSONB"
    )

    # kc_lab_reports: biomarkers flagged for patient attention (array of names)
    op.execute(
        "ALTER TABLE kc_lab_reports ADD COLUMN IF NOT EXISTS "
        "patient_attention_flags JSONB"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE kc_lab_reports DROP COLUMN IF EXISTS patient_attention_flags")
    op.execute("ALTER TABLE kc_lab_reports DROP COLUMN IF EXISTS doctor_commentary")
    op.execute("ALTER TABLE dr_doctors DROP COLUMN IF EXISTS buffer_time_minutes")
