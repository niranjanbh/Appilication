"""Education content system: kc_education_content, kc_education_assignments.

Revision ID: 0013
Revises: 0012
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE content_type AS ENUM ('article', 'video', 'pdf')")
    op.execute("CREATE TYPE content_status AS ENUM ('draft', 'published', 'archived')")

    # ── kc_education_content ───────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE kc_education_content (
            id                      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            title                   VARCHAR(255) NOT NULL,
            slug                    VARCHAR(255) NOT NULL UNIQUE,
            content_type            content_type NOT NULL,
            condition_categories    JSONB        NOT NULL DEFAULT '[]'::jsonb,
            content_url             VARCHAR(500),
            body_md                 TEXT,
            reviewed_by_doctor_id   UUID         REFERENCES dr_doctors(id) ON DELETE SET NULL,
            reviewed_at             TIMESTAMPTZ,
            status                  content_status NOT NULL DEFAULT 'draft',
            ai_disclosure           BOOL         NOT NULL DEFAULT FALSE,
            created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_kc_education_content_status ON kc_education_content (status)"
    )
    op.execute(
        "CREATE INDEX ix_kc_education_content_slug ON kc_education_content (slug)"
    )

    # ── kc_education_assignments ───────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE kc_education_assignments (
            id                      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            content_id              UUID        NOT NULL REFERENCES kc_education_content(id) ON DELETE CASCADE,
            patient_id              UUID        NOT NULL REFERENCES kc_patients(id) ON DELETE CASCADE,
            assigned_by_doctor_id   UUID        NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            consultation_id         UUID        REFERENCES kc_consultations(id) ON DELETE SET NULL,
            read_at                 TIMESTAMPTZ,
            notes                   VARCHAR(500),
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_kc_education_assignments_patient "
        "ON kc_education_assignments (patient_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_kc_education_assignments_content "
        "ON kc_education_assignments (content_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kc_education_assignments CASCADE")
    op.execute("DROP TABLE IF EXISTS kc_education_content CASCADE")
    op.execute("DROP TYPE IF EXISTS content_status")
    op.execute("DROP TYPE IF EXISTS content_type")
