"""Create kc_care_plans and kc_care_plan_items tables.

Doctor-authored treatment plans containing medication, exercise, diet,
lifestyle, follow-up, and lab-test items. Draft plans are never visible
to patients (SQL-layer filtering in the repository).

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE care_plan_status AS ENUM ('draft', 'active', 'completed', 'cancelled')
    """)
    op.execute("""
        CREATE TYPE care_plan_item_category AS ENUM (
            'medication', 'exercise', 'diet', 'lifestyle', 'follow_up', 'lab_test'
        )
    """)
    op.execute("""
        CREATE TYPE care_plan_item_priority AS ENUM ('high', 'normal', 'low')
    """)

    op.execute("""
        CREATE TABLE kc_care_plans (
            id                  UUID            NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            consultation_id     UUID            NOT NULL REFERENCES kc_consultations(id) ON DELETE RESTRICT,
            doctor_id           UUID            NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            patient_id          UUID            NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            title               VARCHAR(255)    NOT NULL,
            status              care_plan_status NOT NULL DEFAULT 'draft',
            condition_category  VARCHAR(50),
            goals               TEXT,
            notes               TEXT,
            valid_from          DATE,
            valid_until         DATE,
            activated_at        TIMESTAMPTZ,
            completed_at        TIMESTAMPTZ,
            version             INT             NOT NULL DEFAULT 1,
            created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_kc_care_plans_consultation ON kc_care_plans (consultation_id)")
    op.execute("CREATE INDEX ix_kc_care_plans_doctor ON kc_care_plans (doctor_id)")
    op.execute("CREATE INDEX ix_kc_care_plans_patient_status ON kc_care_plans (patient_id, status)")

    op.execute("""
        CREATE TABLE kc_care_plan_items (
            id              UUID                    NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            care_plan_id    UUID                    NOT NULL REFERENCES kc_care_plans(id) ON DELETE CASCADE,
            category        care_plan_item_category NOT NULL,
            title           VARCHAR(255)            NOT NULL,
            description     TEXT,
            frequency       VARCHAR(100),
            duration        VARCHAR(100),
            priority        care_plan_item_priority NOT NULL DEFAULT 'normal',
            order_index     INT                     NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ             NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_kc_care_plan_items_plan ON kc_care_plan_items (care_plan_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kc_care_plan_items")
    op.execute("DROP TABLE IF EXISTS kc_care_plans")
    op.execute("DROP TYPE IF EXISTS care_plan_item_priority")
    op.execute("DROP TYPE IF EXISTS care_plan_item_category")
    op.execute("DROP TYPE IF EXISTS care_plan_status")
