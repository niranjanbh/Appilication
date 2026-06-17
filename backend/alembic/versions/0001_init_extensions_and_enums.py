"""Init: pgcrypto/pg_trgm/btree_gin extensions and all ENUM types.

Revision ID: 0001
Revises: None
Create Date: 2026-06-02
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('patient', 'doctor', 'coordinator', 'super_admin');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE user_gender AS ENUM ('female', 'male', 'non_binary', 'prefer_not_to_say');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE consent_type AS ENUM (
                'terms', 'privacy', 'telemedicine', 'data_processing',
                'health_sync', 'marketing', 'recording', 'research'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE data_subject_request_type AS ENUM ('access', 'correction', 'erasure', 'grievance');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE data_subject_request_status AS ENUM ('received', 'in_progress', 'completed', 'rejected');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE actor_role AS ENUM ('patient', 'doctor', 'coordinator', 'super_admin', 'system');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS actor_role")
    op.execute("DROP TYPE IF EXISTS data_subject_request_status")
    op.execute("DROP TYPE IF EXISTS data_subject_request_type")
    op.execute("DROP TYPE IF EXISTS consent_type")
    op.execute("DROP TYPE IF EXISTS user_gender")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP EXTENSION IF EXISTS btree_gin")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
