"""Notification center: wn_notifications inbox + users.notification_preferences.

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # Per-user channel preferences stored on the users row.
    # Nullable → always has a server default; safe zero-downtime add.
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS notification_preferences JSONB
            NOT NULL DEFAULT '{"push": true, "whatsapp": true, "email": true}'::jsonb
    """)

    # Notification inbox table — one row per notification event sent to a patient.
    op.execute("""
        CREATE TABLE wn_notifications (
            id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            template_name VARCHAR(100) NOT NULL,
            title         VARCHAR(255) NOT NULL,
            body          VARCHAR(1000) NOT NULL,
            channels      JSONB       NOT NULL DEFAULT '[]'::jsonb,
            data          JSONB       NOT NULL DEFAULT '{}'::jsonb,
            read_at       TIMESTAMPTZ,
            sent_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Primary access pattern: list a user's inbox newest-first.
    op.execute("""
        CREATE INDEX ix_wn_notifications_user_sent
        ON wn_notifications (user_id, sent_at DESC)
    """)

    # Fast unread-count query.
    op.execute("""
        CREATE INDEX ix_wn_notifications_user_unread
        ON wn_notifications (user_id)
        WHERE read_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_wn_notifications_user_unread")
    op.execute("DROP INDEX IF EXISTS ix_wn_notifications_user_sent")
    op.execute("DROP TABLE IF EXISTS wn_notifications")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS notification_preferences")
