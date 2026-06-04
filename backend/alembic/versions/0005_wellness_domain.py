"""Wellness domain: wn_reminders, wn_reminder_logs, wn_health_sync_sessions,
wn_health_datapoints (partitioned monthly).

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Monthly partitions to pre-create (2026-06 through 2026-11)
_HEALTH_PARTITIONS = [
    ("2026_06", "2026-06-01", "2026-07-01"),
    ("2026_07", "2026-07-01", "2026-08-01"),
    ("2026_08", "2026-08-01", "2026-09-01"),
    ("2026_09", "2026-09-01", "2026-10-01"),
    ("2026_10", "2026-10-01", "2026-11-01"),
    ("2026_11", "2026-11-01", "2026-12-01"),
]


def upgrade() -> None:
    # ── Enum types ─────────────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE reminder_type AS ENUM ('water', 'supplement', 'medication', 'gym', 'custom')"
    )
    op.execute(
        "CREATE TYPE reminder_action AS ENUM ('taken', 'skipped', 'snoozed', 'missed')"
    )
    op.execute(
        "CREATE TYPE health_sync_source AS ENUM ('apple_health', 'google_health_connect')"
    )
    op.execute(
        "CREATE TYPE health_datapoint_source AS ENUM "
        "('apple_health', 'google_health_connect', 'manual')"
    )
    op.execute(
        "CREATE TYPE health_datapoint_type AS ENUM "
        "('steps', 'heart_rate', 'resting_heart_rate', 'hrv', 'sleep_duration', "
        "'sleep_quality', 'weight', 'blood_pressure_systolic', 'blood_pressure_diastolic', "
        "'blood_glucose', 'workout', 'active_calories')"
    )
    op.execute(
        "CREATE TYPE health_sync_status AS ENUM ('success', 'partial', 'failed')"
    )

    # ── wn_reminders ───────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE wn_reminders (
            id                          UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id                     UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type                        reminder_type NOT NULL,
            label                       VARCHAR(255) NOT NULL,
            schedule_cron               VARCHAR(100),
            schedule_interval_minutes   INT,
            active                      BOOLEAN      NOT NULL DEFAULT TRUE,
            notification_channels       JSONB        NOT NULL DEFAULT '[]',
            metadata                    JSONB,
            created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at                  TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_wn_reminders_user_id ON wn_reminders (user_id) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_wn_reminders_active ON wn_reminders (user_id, active) WHERE deleted_at IS NULL"
    )

    # ── wn_reminder_logs ──────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE wn_reminder_logs (
            id           UUID           NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            reminder_id  UUID           NOT NULL REFERENCES wn_reminders(id) ON DELETE CASCADE,
            user_id      UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            scheduled_at TIMESTAMPTZ    NOT NULL,
            action       reminder_action NOT NULL,
            action_at    TIMESTAMPTZ    NOT NULL,
            notes        VARCHAR(500),
            created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_wn_reminder_logs_reminder ON wn_reminder_logs (reminder_id, scheduled_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_wn_reminder_logs_user ON wn_reminder_logs (user_id, action_at DESC)"
    )

    # ── wn_health_sync_sessions ────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE wn_health_sync_sessions (
            id               UUID              NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id          UUID              NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source           health_sync_source NOT NULL,
            synced_at        TIMESTAMPTZ       NOT NULL,
            data_range_start TIMESTAMPTZ       NOT NULL,
            data_range_end   TIMESTAMPTZ       NOT NULL,
            record_count     INT               NOT NULL DEFAULT 0,
            consent_id       UUID              REFERENCES ad_consent_records(id) ON DELETE SET NULL,
            status           health_sync_status NOT NULL,
            created_at       TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ       NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_wn_health_sync_sessions_user ON wn_health_sync_sessions (user_id, synced_at DESC)"
    )

    # ── wn_health_datapoints (partitioned) ────────────────────────────────────
    op.execute(
        """
        CREATE TABLE wn_health_datapoints (
            id               UUID                    NOT NULL DEFAULT gen_random_uuid(),
            user_id          UUID                    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source           health_datapoint_source  NOT NULL,
            source_session_id UUID                   REFERENCES wn_health_sync_sessions(id) ON DELETE SET NULL,
            source_record_id VARCHAR(255),
            type             health_datapoint_type   NOT NULL,
            value            JSONB                   NOT NULL,
            measured_at      TIMESTAMPTZ             NOT NULL,
            created_at       TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, measured_at),
            UNIQUE (user_id, source, source_record_id, measured_at)
        ) PARTITION BY RANGE (measured_at)
        """
    )

    for suffix, from_date, to_date in _HEALTH_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE wn_health_datapoints_{suffix}
            PARTITION OF wn_health_datapoints
            FOR VALUES FROM ('{from_date}') TO ('{to_date}')
            """
        )

    # BRIN index for time-range scans
    op.execute(
        "CREATE INDEX ix_wn_health_datapoints_measured ON wn_health_datapoints USING BRIN (measured_at)"
    )
    # BTREE for "latest 30 days of metric X for user Y"
    op.execute(
        "CREATE INDEX ix_wn_health_datapoints_user_type ON wn_health_datapoints (user_id, type, measured_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS wn_health_datapoints CASCADE")
    op.execute("DROP TABLE IF EXISTS wn_health_sync_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS wn_reminder_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS wn_reminders CASCADE")
    op.execute("DROP TYPE IF EXISTS health_sync_status")
    op.execute("DROP TYPE IF EXISTS health_datapoint_type")
    op.execute("DROP TYPE IF EXISTS health_datapoint_source")
    op.execute("DROP TYPE IF EXISTS health_sync_source")
    op.execute("DROP TYPE IF EXISTS reminder_action")
    op.execute("DROP TYPE IF EXISTS reminder_type")
