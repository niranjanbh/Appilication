"""Analytics: ad_daily_metrics rollup table.

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE ad_daily_metrics (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            metric_date DATE        NOT NULL,
            metric_key  VARCHAR(64) NOT NULL,
            dimension   VARCHAR(128) NOT NULL DEFAULT '',
            value       BIGINT      NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_ad_daily_metrics
        ON ad_daily_metrics (metric_date, metric_key, dimension)
    """)
    op.execute("""
        CREATE INDEX ix_ad_daily_metrics_date_key
        ON ad_daily_metrics (metric_date, metric_key)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ad_daily_metrics_date_key")
    op.execute("DROP INDEX IF EXISTS uq_ad_daily_metrics")
    op.execute("DROP TABLE IF EXISTS ad_daily_metrics")
