"""Staff auth plane hardening: TOTP MFA + session audience.

Adds:
  - ad_staff_mfa: one row per staff user holding an encrypted TOTP secret and
    hashed recovery codes. enabled_at IS NULL means a secret has been generated
    but not yet confirmed (pending enrollment, freely regenerable).
  - refresh_tokens.mfa_verified: additive, nullable=False with a default of
    false. Carries the session's MFA status across /refresh rotations so access
    tokens can stamp an `mfa` claim without re-checking TOTP every refresh
    (staff-rbac-spec §1).

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ad_staff_mfa",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("totp_secret_encrypted", sa.Text(), nullable=False),
        sa.Column(
            "recovery_codes",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.add_column(
        "refresh_tokens",
        sa.Column(
            "mfa_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("refresh_tokens", "mfa_verified")
    op.drop_table("ad_staff_mfa")
