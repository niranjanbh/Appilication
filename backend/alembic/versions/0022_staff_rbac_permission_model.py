"""Staff RBAC: multi-role table + audit role-context columns.

Adds:
  - ad_staff_roles: additional staff roles held beyond users.role (permission
    bundles resolve as the union; staff-rbac-spec §1).
  - ad_audit_log.role_context + ad_audit_log.permission: nullable, additive. The
    table is partitioned by RANGE(timestamp) and append-only via trigger — ADD
    COLUMN on the parent cascades to partitions and the trigger only blocks
    UPDATE/DELETE, so this is safe. No backfill.

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ad_staff_roles",
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
        ),
        sa.Column(
            "role",
            ENUM(name="user_role", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "granted_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.UniqueConstraint("user_id", "role", name="uq_ad_staff_roles_user_role"),
    )
    op.create_index("ix_ad_staff_roles_user", "ad_staff_roles", ["user_id"])

    # Additive, nullable — cascades to all ad_audit_log partitions.
    op.add_column(
        "ad_audit_log", sa.Column("role_context", sa.String(20), nullable=True)
    )
    op.add_column(
        "ad_audit_log", sa.Column("permission", sa.String(64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("ad_audit_log", "permission")
    op.drop_column("ad_audit_log", "role_context")
    op.drop_index("ix_ad_staff_roles_user", table_name="ad_staff_roles")
    op.drop_table("ad_staff_roles")
