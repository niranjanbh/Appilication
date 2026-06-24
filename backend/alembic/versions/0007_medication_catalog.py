"""Medication catalog — admin-curated drug reference with representative image.

Adds ``kc_medication_catalog``: an admin-managed table of medication names with
an optional S3 image key. Doctors search it by name when building a
reminder/prescription so the patient is shown a photo of the medication. The
``drug_form`` enum already exists (created in 0001), so this migration reuses it.

Forward-only, additive: creates one table and its indexes. Guarded with
IF NOT EXISTS so a re-run is a no-op.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS kc_medication_catalog (
            id                  UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            name                VARCHAR(255) NOT NULL,
            generic_name        VARCHAR(255),
            form                drug_form,
            strength            VARCHAR(100),
            image_s3_key        VARCHAR(500),
            image_content_type  VARCHAR(100),
            active              BOOLEAN      NOT NULL DEFAULT true,
            created_by_user_id  UUID         REFERENCES users(id) ON DELETE SET NULL,
            created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ
        )
        """
    )
    # Unique medication name (case-sensitive); also serves name lookups.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_kc_medication_catalog_name "
        "ON kc_medication_catalog (name)"
    )
    # Partial index for the common active-only search path.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kc_medication_catalog_active "
        "ON kc_medication_catalog (active) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kc_medication_catalog")
