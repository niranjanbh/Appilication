"""Audit log: ad_audit_log partitioned by month, append-only trigger, 6 partitions.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-02
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Monthly partitions to pre-create (2026-06 through 2026-11)
_PARTITIONS = [
    ("2026_06", "2026-06-01", "2026-07-01"),
    ("2026_07", "2026-07-01", "2026-08-01"),
    ("2026_08", "2026-08-01", "2026-09-01"),
    ("2026_09", "2026-09-01", "2026-10-01"),
    ("2026_10", "2026-10-01", "2026-11-01"),
    ("2026_11", "2026-11-01", "2026-12-01"),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ad_audit_log (
            id          UUID         NOT NULL DEFAULT gen_random_uuid(),
            timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            actor_user_id UUID        REFERENCES users(id),
            actor_role  actor_role   NOT NULL,
            action      VARCHAR(100) NOT NULL,
            resource_type VARCHAR(100),
            resource_id UUID,
            allowed     BOOLEAN      NOT NULL,
            reason      VARCHAR(255),
            ip_address  INET,
            user_agent  VARCHAR(500),
            metadata    JSONB,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp)
        """
    )

    for suffix, from_date, to_date in _PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE ad_audit_log_{suffix}
            PARTITION OF ad_audit_log
            FOR VALUES FROM ('{from_date}') TO ('{to_date}')
            """
        )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'ad_audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER prevent_audit_log_update
        BEFORE UPDATE OR DELETE ON ad_audit_log
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_modification()
        """
    )

    op.execute(
        "CREATE INDEX ix_audit_log_actor ON ad_audit_log (actor_user_id, timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX ix_audit_log_resource ON ad_audit_log (resource_type, resource_id)"
    )


def downgrade() -> None:
    raise NotImplementedError(
        "downgrade of ad_audit_log is not supported — "
        "dropping a partitioned table with live data is irreversible"
    )
