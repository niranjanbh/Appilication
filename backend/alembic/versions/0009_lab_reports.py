"""Lab reports: kc_lab_reports table with OCR pipeline status tracking.

Creates two new ENUM types and the kc_lab_reports table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── New ENUM types ─────────────────────────────────────────────────────────
    # DO...EXCEPTION guards handle the edge case where a previous partial run
    # created the types but then rolled back the alembic_version stamp.
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE lab_report_source AS ENUM ('patient_upload', 'kyros_order');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE lab_report_status AS ENUM (
                'upload_pending', 'ocr_pending', 'ocr_processing',
                'ocr_complete', 'ocr_failed', 'patient_review_needed'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    # ── kc_lab_reports ─────────────────────────────────────────────────────────
    # Use raw SQL (matching the pattern of 0008_consultations.py) to avoid
    # SQLAlchemy firing CREATE TYPE again via the before_create event.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS kc_lab_reports (
            id                      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            patient_id              UUID        NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            uploaded_by_user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            source                  lab_report_source NOT NULL DEFAULT 'patient_upload',
            lab_name                VARCHAR(255),
            report_date             DATE,
            file_url                VARCHAR(500),
            original_filename       VARCHAR(255) NOT NULL,
            content_type            VARCHAR(100) NOT NULL,
            file_size_bytes         INT          NOT NULL,
            status                  lab_report_status NOT NULL DEFAULT 'upload_pending',
            parsed_json             JSONB,
            ocr_confidence_avg      NUMERIC(3,2),
            low_confidence_fields   JSONB,
            patient_corrected       BOOL         NOT NULL DEFAULT FALSE,
            doctor_reviewed_by_id   UUID         REFERENCES dr_doctors(id) ON DELETE SET NULL,
            processing_failed_reason TEXT,
            created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kc_lab_reports_patient_id ON kc_lab_reports (patient_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kc_lab_reports_status ON kc_lab_reports (status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kc_lab_reports")
    op.execute("DROP TYPE IF EXISTS lab_report_status")
    op.execute("DROP TYPE IF EXISTS lab_report_source")
