"""Clinic domain: dr_doctors, dr_credentials, dr_availability, ad_coordinators, kc_patients.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── New ENUM types ─────────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE condition_category AS ENUM "
        "('thyroid', 'weight', 'pcos', 'skin_hair', 'mens_intimate', 'hormones_trt', 'longevity')"
    )
    op.execute(
        "CREATE TYPE doctor_status AS ENUM "
        "('applied', 'documents_submitted', 'verified', 'onboarding', 'active', 'inactive', 'suspended')"
    )
    op.execute(
        "CREATE TYPE availability_status AS ENUM ('available', 'booked', 'blocked')"
    )
    op.execute(
        "CREATE TYPE credential_type AS ENUM "
        "('mbbs', 'md', 'dnb', 'dm', 'mch', 'fellowship', 'certification')"
    )
    op.execute(
        "CREATE TYPE coordinator_status AS ENUM ('active', 'inactive')"
    )

    # ── Sequence for human-readable patient IDs ───────────────────────────────
    op.execute("CREATE SEQUENCE kc_patient_id_seq START 1 INCREMENT 1 NO CYCLE")

    # ── dr_doctors ─────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE dr_doctors (
            id                                      UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id                                 UUID         NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
            nmc_registration_number                 VARCHAR(50)  NOT NULL UNIQUE,
            nmc_state_council                       VARCHAR(100),
            verified_at                             TIMESTAMPTZ,
            specialty                               JSONB        NOT NULL DEFAULT '[]',
            conditions_treated                      JSONB        NOT NULL DEFAULT '[]',
            consultation_languages                  JSONB        NOT NULL DEFAULT '["en"]',
            status                                  doctor_status NOT NULL DEFAULT 'applied',
            consultation_duration_minutes_default   INT          NOT NULL DEFAULT 20,
            revenue_share_pct                       DECIMAL(5,2),
            bank_details_encrypted                  BYTEA,
            bio_short                               VARCHAR(500),
            bio_long                                TEXT,
            photo_url                               VARCHAR(500),
            onboarding_stage                        VARCHAR(50),
            created_at                              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at                              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at                              TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_dr_doctors_status ON dr_doctors (status) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_dr_doctors_conditions ON dr_doctors USING GIN (conditions_treated) WHERE deleted_at IS NULL"
    )

    # ── dr_credentials ─────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE dr_credentials (
            id                   UUID            NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            doctor_id            UUID            NOT NULL REFERENCES dr_doctors(id) ON DELETE CASCADE,
            credential_type      credential_type NOT NULL,
            institution          VARCHAR(255)    NOT NULL,
            year                 INT             NOT NULL,
            document_url         VARCHAR(500),
            verified_by_admin_id UUID            REFERENCES users(id) ON DELETE SET NULL,
            created_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_dr_credentials_doctor ON dr_credentials (doctor_id)"
    )

    # ── dr_availability ────────────────────────────────────────────────────────
    # consultation_id FK to kc_consultations added in P12.
    op.execute(
        """
        CREATE TABLE dr_availability (
            id              UUID                NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            doctor_id       UUID                NOT NULL REFERENCES dr_doctors(id) ON DELETE CASCADE,
            slot_start      TIMESTAMPTZ         NOT NULL,
            slot_end        TIMESTAMPTZ         NOT NULL,
            status          availability_status NOT NULL DEFAULT 'available',
            consultation_id UUID,
            created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
            UNIQUE (doctor_id, slot_start)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_dr_availability_lookup ON dr_availability (doctor_id, slot_start, status)"
    )

    # ── ad_coordinators ────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE ad_coordinators (
            id                  UUID               NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id             UUID               NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
            status              coordinator_status NOT NULL DEFAULT 'active',
            assigned_patient_ids JSONB             NOT NULL DEFAULT '[]',
            employee_id         VARCHAR(50),
            created_at          TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_ad_coordinators_status ON ad_coordinators (status) WHERE deleted_at IS NULL"
    )

    # ── kc_patients ────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE kc_patients (
            id                      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id                 UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
            kyros_patient_id        VARCHAR(20) NOT NULL UNIQUE,
            abha_number             VARCHAR(20),
            primary_conditions      JSONB       NOT NULL DEFAULT '[]',
            preferred_doctor_id     UUID        REFERENCES dr_doctors(id) ON DELETE SET NULL,
            assigned_coordinator_id UUID        REFERENCES ad_coordinators(id) ON DELETE SET NULL,
            allergies               TEXT,
            chronic_conditions      TEXT,
            current_medications     TEXT,
            emergency_contact       JSONB,
            intake_complete_at      TIMESTAMPTZ,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at              TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_kc_patients_conditions ON kc_patients USING GIN (primary_conditions) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_kc_patients_coordinator ON kc_patients (assigned_coordinator_id) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kc_patients CASCADE")
    op.execute("DROP TABLE IF EXISTS ad_coordinators CASCADE")
    op.execute("DROP TABLE IF EXISTS dr_availability CASCADE")
    op.execute("DROP TABLE IF EXISTS dr_credentials CASCADE")
    op.execute("DROP TABLE IF EXISTS dr_doctors CASCADE")
    op.execute("DROP SEQUENCE IF EXISTS kc_patient_id_seq")
    op.execute("DROP TYPE IF EXISTS coordinator_status")
    op.execute("DROP TYPE IF EXISTS credential_type")
    op.execute("DROP TYPE IF EXISTS availability_status")
    op.execute("DROP TYPE IF EXISTS doctor_status")
    op.execute("DROP TYPE IF EXISTS condition_category")
