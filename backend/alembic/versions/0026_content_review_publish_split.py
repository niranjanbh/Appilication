"""Content review/publish split: enum values + ad_sign_off_records table.

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Extend the content_status enum ────────────────────────────────────
    # Postgres 16 allows ALTER TYPE ADD VALUE inside a transaction.
    # IF NOT EXISTS guards idempotent re-runs.
    op.execute(
        "ALTER TYPE content_status ADD VALUE IF NOT EXISTS 'pending_review'"
    )
    op.execute(
        "ALTER TYPE content_status ADD VALUE IF NOT EXISTS 'approved'"
    )
    op.execute(
        "ALTER TYPE content_status ADD VALUE IF NOT EXISTS 'rejected'"
    )

    # ── 2. Create ad_sign_off_records (append-only) ───────────────────────────
    op.execute(
        """
        CREATE TABLE ad_sign_off_records (
            id                      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            content_id              UUID        NOT NULL
                REFERENCES kc_education_content(id) ON DELETE RESTRICT,
            doctor_id               UUID        NOT NULL
                REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            nmc_registration_number VARCHAR(50) NOT NULL,
            artifact_hash           CHAR(64)    NOT NULL,
            action                  VARCHAR(20) NOT NULL,
            notes                   TEXT,
            signed_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        "CREATE INDEX ix_ad_sign_off_records_content_id ON ad_sign_off_records (content_id)"
    )

    # ── 3. Immutability trigger (same pattern as ad_audit_log in 0003) ────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_sign_off_records_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'ad_sign_off_records rows are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_sign_off_records_immutable
        BEFORE UPDATE OR DELETE ON ad_sign_off_records
        FOR EACH ROW
        EXECUTE FUNCTION fn_sign_off_records_immutable()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tg_sign_off_records_immutable ON ad_sign_off_records")
    op.execute("DROP FUNCTION IF EXISTS fn_sign_off_records_immutable()")
    op.execute("DROP TABLE IF EXISTS ad_sign_off_records")
    # NOTE: enum values ('pending_review', 'approved', 'rejected') cannot be removed
    # from a live Postgres enum. They are left in place but are unused after downgrade.
