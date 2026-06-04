"""Add kc_lab_orders table and lab_order_id FK on kc_lab_reports.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── New ENUM type ───────────────────────────────────────────────────────────
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE lab_order_status AS ENUM (
                'ordered', 'sample_collected', 'resulted', 'reviewed', 'superseded'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    # ── kc_lab_orders ───────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS kc_lab_orders (
            id                  UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            consultation_id     UUID        REFERENCES kc_consultations(id) ON DELETE SET NULL,
            doctor_id           UUID        NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            patient_id          UUID        NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            tests               JSONB       NOT NULL DEFAULT '[]'::jsonb,
            status              lab_order_status NOT NULL DEFAULT 'ordered',
            lab_name            VARCHAR(255),
            result_uploaded_at  TIMESTAMPTZ,
            result_file_url     VARCHAR(500),
            parsed_json         JSONB,
            ocr_confidence_avg  NUMERIC(3,2),
            reviewed_at         TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kc_lab_orders_patient_id ON kc_lab_orders (patient_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kc_lab_orders_doctor_id ON kc_lab_orders (doctor_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kc_lab_orders_status ON kc_lab_orders (status)"
    )

    # ── Add lab_order_id FK column to kc_lab_reports ────────────────────────────
    # Nullable ADD COLUMN — no table lock. FK declared inline (table is young, row count zero).
    op.execute(
        """
        ALTER TABLE kc_lab_reports
        ADD COLUMN IF NOT EXISTS lab_order_id UUID
            REFERENCES kc_lab_orders(id) ON DELETE SET NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE kc_lab_reports DROP COLUMN IF EXISTS lab_order_id")
    op.execute("DROP TABLE IF EXISTS kc_lab_orders")
    op.execute("DROP TYPE IF EXISTS lab_order_status")
