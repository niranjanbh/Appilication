"""Erasure with legal hold: erased_at on users, legal_hold columns on clinical tables.

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. erased_at on users — separate from deleted_at ─────────────────────
    # deleted_at = soft-delete (recoverable within grace period)
    # erased_at  = PII anonymization applied (irreversible)
    op.execute(
        "ALTER TABLE users ADD COLUMN erased_at TIMESTAMPTZ NULL"
    )

    # ── 2. Legal hold columns on kc_consultations ─────────────────────────────
    # NMC Medical Records rules mandate 3–7 year retention; we use 7 years.
    op.execute(
        """
        ALTER TABLE kc_consultations
            ADD COLUMN legal_hold_until TIMESTAMPTZ NULL,
            ADD COLUMN legal_hold_reason VARCHAR(100) NULL
        """
    )

    # ── 3. Legal hold columns on kc_prescriptions ─────────────────────────────
    op.execute(
        """
        ALTER TABLE kc_prescriptions
            ADD COLUMN legal_hold_until TIMESTAMPTZ NULL,
            ADD COLUMN legal_hold_reason VARCHAR(100) NULL
        """
    )

    # ── 4. DB-layer invariant: block hard DELETE while hold is active ──────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_consult_delete_under_hold()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.legal_hold_until IS NOT NULL AND OLD.legal_hold_until > NOW() THEN
            RAISE EXCEPTION
              'consultation % is under legal hold until % — cannot delete',
              OLD.id, OLD.legal_hold_until;
          END IF;
          RETURN OLD;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prevent_consult_delete
          BEFORE DELETE ON kc_consultations
          FOR EACH ROW EXECUTE FUNCTION prevent_consult_delete_under_hold()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_consult_delete ON kc_consultations")
    op.execute("DROP FUNCTION IF EXISTS prevent_consult_delete_under_hold()")
    op.execute(
        """
        ALTER TABLE kc_prescriptions
            DROP COLUMN IF EXISTS legal_hold_reason,
            DROP COLUMN IF EXISTS legal_hold_until
        """
    )
    op.execute(
        """
        ALTER TABLE kc_consultations
            DROP COLUMN IF EXISTS legal_hold_reason,
            DROP COLUMN IF EXISTS legal_hold_until
        """
    )
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS erased_at")
