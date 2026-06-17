"""Drop FK constraint on ad_audit_log.actor_user_id.

Audit logs must survive user erasure/deletion. The FK prevents both:
  - Test isolation (uncommitted test users fail the FK check in PHIAuditMiddleware's
    separate AsyncSessionLocal session).
  - DPDP erasure (deleting a user with audit rows raises FK violation unless rows are
    nulled first, which the erasure task already does — but the constraint adds risk).

Dropping the constraint makes the audit log append-only and actor-independent, which
is the correct design for a compliance audit trail.

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ad_audit_log_actor_user_id_fkey",
        "ad_audit_log",
        type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "ad_audit_log_actor_user_id_fkey",
        "ad_audit_log",
        "users",
        ["actor_user_id"],
        ["id"],
    )
