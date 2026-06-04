"""Consultations: kc_consultations, kc_doctor_notes, kc_pre_consultation_reports.

Adds three new ENUM types and three new tables.  Also wires the deferred FK
columns that dr_availability and kc_payments declared in P10/P11 but could not
reference until kc_consultations existed.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── New ENUM types ─────────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE consultation_status AS ENUM "
        "('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show')"
    )
    op.execute(
        "CREATE TYPE consultation_type AS ENUM ('initial', 'follow_up')"
    )
    op.execute(
        "CREATE TYPE note_type AS ENUM "
        "('clinical', 'coordinator_only', 'patient_visible', 'private')"
    )

    # ── kc_pre_consultation_reports ────────────────────────────────────────────
    # Created before kc_consultations to allow the forward FK from kc_consultations
    # to reference it.  The back-FK (consultation_id → kc_consultations) is added
    # below via ALTER TABLE after kc_consultations exists.
    op.execute(
        """
        CREATE TABLE kc_pre_consultation_reports (
            id                      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            patient_id              UUID        NOT NULL REFERENCES kc_patients(id) ON DELETE CASCADE,
            consultation_id         UUID        UNIQUE,
            generated_at            TIMESTAMPTZ NOT NULL,
            lab_summary             JSONB,
            adherence_summary       JSONB,
            wearable_summary        JSONB,
            patient_flags           JSONB,
            intake_responses        JSONB,
            pdf_url                 VARCHAR(500),
            doctor_reviewed_at      TIMESTAMPTZ,
            doctor_notes_pre_consult TEXT,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_kc_pre_consult_patient ON kc_pre_consultation_reports (patient_id)"
    )

    # ── kc_consultations ───────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE kc_consultations (
            id                          UUID                  NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            patient_id                  UUID                  NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            doctor_id                   UUID                  NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            coordinator_id              UUID                  REFERENCES ad_coordinators(id) ON DELETE SET NULL,
            condition_category          condition_category    NOT NULL,
            consultation_type           consultation_type     NOT NULL DEFAULT 'initial',
            scheduled_start_at          TIMESTAMPTZ           NOT NULL,
            scheduled_end_at            TIMESTAMPTZ           NOT NULL,
            actual_start_at             TIMESTAMPTZ,
            actual_end_at               TIMESTAMPTZ,
            status                      consultation_status   NOT NULL DEFAULT 'scheduled',
            video_room_id               VARCHAR(100),
            video_session_id            VARCHAR(100),
            recording_consent           BOOL                  NOT NULL DEFAULT FALSE,
            recording_url               VARCHAR(500),
            pre_consultation_report_id  UUID                  REFERENCES kc_pre_consultation_reports(id) ON DELETE SET NULL,
            consultation_fee_paise      INT                   NOT NULL,
            payment_id                  UUID                  REFERENCES kc_payments(id) ON DELETE SET NULL,
            cancellation_reason         VARCHAR(500),
            created_at                  TIMESTAMPTZ           NOT NULL DEFAULT NOW(),
            updated_at                  TIMESTAMPTZ           NOT NULL DEFAULT NOW(),
            deleted_at                  TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_kc_consultations_patient ON kc_consultations (patient_id, scheduled_start_at DESC) "
        "WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_kc_consultations_doctor ON kc_consultations (doctor_id, scheduled_start_at) "
        "WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_kc_consultations_status ON kc_consultations (status) WHERE deleted_at IS NULL"
    )

    # ── kc_doctor_notes ────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE kc_doctor_notes (
            id               UUID      NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            consultation_id  UUID      NOT NULL REFERENCES kc_consultations(id) ON DELETE CASCADE,
            doctor_id        UUID      NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            patient_id       UUID      NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            note_type        note_type NOT NULL,
            content          TEXT      NOT NULL,
            version          INT       NOT NULL DEFAULT 1,
            superseded_by_id UUID      REFERENCES kc_doctor_notes(id) ON DELETE RESTRICT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_kc_doctor_notes_consultation ON kc_doctor_notes (consultation_id)"
    )

    # ── Wire deferred back-FKs ─────────────────────────────────────────────────
    # kc_pre_consultation_reports.consultation_id → kc_consultations.id
    op.execute(
        "ALTER TABLE kc_pre_consultation_reports "
        "ADD CONSTRAINT fk_kc_pre_consult_consultation "
        "FOREIGN KEY (consultation_id) REFERENCES kc_consultations(id) ON DELETE CASCADE"
    )

    # dr_availability.consultation_id → kc_consultations.id  (column exists, FK missing)
    op.execute(
        "ALTER TABLE dr_availability "
        "ADD CONSTRAINT fk_dr_avail_consultation "
        "FOREIGN KEY (consultation_id) REFERENCES kc_consultations(id) ON DELETE SET NULL"
    )

    # kc_payments.consultation_id → kc_consultations.id  (column exists, FK missing)
    op.execute(
        "ALTER TABLE kc_payments "
        "ADD CONSTRAINT fk_kc_payments_consultation "
        "FOREIGN KEY (consultation_id) REFERENCES kc_consultations(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    # Remove deferred FKs first
    op.execute(
        "ALTER TABLE kc_payments DROP CONSTRAINT IF EXISTS fk_kc_payments_consultation"
    )
    op.execute(
        "ALTER TABLE dr_availability DROP CONSTRAINT IF EXISTS fk_dr_avail_consultation"
    )
    op.execute(
        "ALTER TABLE kc_pre_consultation_reports "
        "DROP CONSTRAINT IF EXISTS fk_kc_pre_consult_consultation"
    )

    op.execute("DROP TABLE IF EXISTS kc_doctor_notes CASCADE")
    op.execute("DROP TABLE IF EXISTS kc_consultations CASCADE")
    op.execute("DROP TABLE IF EXISTS kc_pre_consultation_reports CASCADE")

    op.execute("DROP TYPE IF EXISTS note_type")
    op.execute("DROP TYPE IF EXISTS consultation_type")
    op.execute("DROP TYPE IF EXISTS consultation_status")
