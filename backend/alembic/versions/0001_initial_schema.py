"""Initial schema: full Kyros platform baseline (squashed from 0001–0005).

Revision ID: 0001
Revises: None
Create Date: 2026-06-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ── Partition definitions ────────────────────────────────────────────────────
_AUDIT_PARTITIONS = [
    ("2026_06", "2026-06-01", "2026-07-01"),
    ("2026_07", "2026-07-01", "2026-08-01"),
    ("2026_08", "2026-08-01", "2026-09-01"),
    ("2026_09", "2026-09-01", "2026-10-01"),
    ("2026_10", "2026-10-01", "2026-11-01"),
    ("2026_11", "2026-11-01", "2026-12-01"),
    ("2026_12", "2026-12-01", "2027-01-01"),
    ("2027_01", "2027-01-01", "2027-02-01"),
    ("2027_02", "2027-02-01", "2027-03-01"),
    ("2027_03", "2027-03-01", "2027-04-01"),
    ("2027_04", "2027-04-01", "2027-05-01"),
    ("2027_05", "2027-05-01", "2027-06-01"),
    ("2027_06", "2027-06-01", "2027-07-01"),
]

_HEALTH_PARTITIONS = [
    ("2026_06", "2026-06-01", "2026-07-01"),
    ("2026_07", "2026-07-01", "2026-08-01"),
    ("2026_08", "2026-08-01", "2026-09-01"),
    ("2026_09", "2026-09-01", "2026-10-01"),
    ("2026_10", "2026-10-01", "2026-11-01"),
    ("2026_11", "2026-11-01", "2026-12-01"),
    ("2026_12", "2026-12-01", "2027-01-01"),
    ("2027_01", "2027-01-01", "2027-02-01"),
    ("2027_02", "2027-02-01", "2027-03-01"),
    ("2027_03", "2027-03-01", "2027-04-01"),
    ("2027_04", "2027-04-01", "2027-05-01"),
    ("2027_05", "2027-05-01", "2027-06-01"),
    ("2027_06", "2027-06-01", "2027-07-01"),
]

# ── ICD-10 seed data ─────────────────────────────────────────────────────────
ICD10_SEED_CODES: list[dict[str, str]] = [
    {"code": "E03.9", "description": "Hypothyroidism, unspecified", "category": "thyroid"},
    {"code": "E05.90", "description": "Thyrotoxicosis, unspecified", "category": "thyroid"},
    {"code": "E06.3", "description": "Autoimmune thyroiditis (Hashimoto)", "category": "thyroid"},
    {"code": "E04.9", "description": "Nontoxic goiter, unspecified", "category": "thyroid"},
    {"code": "E66.9", "description": "Obesity, unspecified", "category": "weight"},
    {"code": "E66.01", "description": "Morbid (severe) obesity due to excess calories", "category": "weight"},
    {"code": "E66.3", "description": "Overweight", "category": "weight"},
    {"code": "E28.2", "description": "Polycystic ovarian syndrome", "category": "pcos"},
    {"code": "L65.9", "description": "Nonscarring hair loss, unspecified", "category": "skin_hair"},
    {"code": "L70.9", "description": "Acne, unspecified", "category": "skin_hair"},
    {"code": "L68.0", "description": "Hirsutism", "category": "skin_hair"},
    {"code": "N52.9", "description": "Male erectile dysfunction, unspecified", "category": "mens_intimate"},
    {"code": "N53.11", "description": "Hypoactive sexual desire disorder", "category": "mens_intimate"},
    {"code": "N53.8", "description": "Other male sexual dysfunction", "category": "mens_intimate"},
    {"code": "E29.1", "description": "Testicular hypofunction", "category": "hormones_trt"},
    {"code": "E34.9", "description": "Endocrine disorder, unspecified", "category": "hormones_trt"},
    {"code": "Z71.3", "description": "Dietary counseling and surveillance", "category": "longevity"},
    {"code": "Z00.00", "description": "Encounter for general adult medical examination without abnormal findings", "category": "longevity"},
    {"code": "R53.83", "description": "Other fatigue", "category": "longevity"},
    {"code": "E55.9", "description": "Vitamin D deficiency, unspecified", "category": "general"},
    {"code": "E61.1", "description": "Iron deficiency", "category": "general"},
    {"code": "F41.9", "description": "Anxiety disorder, unspecified", "category": "general"},
    {"code": "F32.9", "description": "Major depressive disorder, single episode, unspecified", "category": "general"},
    {"code": "G47.00", "description": "Insomnia, unspecified", "category": "general"},
    {"code": "E78.5", "description": "Hyperlipidemia, unspecified", "category": "general"},
    {"code": "I10", "description": "Essential (primary) hypertension", "category": "general"},
    {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "category": "general"},
]


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════════════════════
    # 1. EXTENSIONS
    # ═══════════════════════════════════════════════════════════════════════════
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. ENUM TYPES
    # ═══════════════════════════════════════════════════════════════════════════
    op.execute("""
        CREATE TYPE user_role AS ENUM (
            'patient', 'doctor', 'coordinator', 'admin', 'super_admin'
        )
    """)
    op.execute("""
        CREATE TYPE user_gender AS ENUM (
            'female', 'male', 'non_binary', 'prefer_not_to_say'
        )
    """)
    op.execute("""
        CREATE TYPE consent_type AS ENUM (
            'terms', 'privacy', 'telemedicine', 'data_processing',
            'health_sync', 'marketing', 'recording', 'research'
        )
    """)
    op.execute("""
        CREATE TYPE data_subject_request_type AS ENUM (
            'access', 'correction', 'erasure', 'grievance'
        )
    """)
    op.execute("""
        CREATE TYPE data_subject_request_status AS ENUM (
            'received', 'in_progress', 'completed', 'rejected'
        )
    """)
    op.execute("""
        CREATE TYPE actor_role AS ENUM (
            'patient', 'doctor', 'coordinator', 'admin', 'super_admin', 'system'
        )
    """)
    op.execute("""
        CREATE TYPE otp_reset_channel AS ENUM ('email', 'sms')
    """)
    op.execute("""
        CREATE TYPE reminder_type AS ENUM (
            'water', 'supplement', 'medication', 'gym', 'custom'
        )
    """)
    op.execute("""
        CREATE TYPE reminder_action AS ENUM (
            'taken', 'skipped', 'snoozed', 'missed'
        )
    """)
    op.execute("""
        CREATE TYPE health_sync_source AS ENUM (
            'apple_health', 'google_health_connect'
        )
    """)
    op.execute("""
        CREATE TYPE health_datapoint_source AS ENUM (
            'apple_health', 'google_health_connect', 'manual'
        )
    """)
    op.execute("""
        CREATE TYPE health_datapoint_type AS ENUM (
            'steps', 'heart_rate', 'resting_heart_rate', 'hrv',
            'sleep_duration', 'sleep_quality', 'weight',
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'blood_glucose', 'workout', 'active_calories'
        )
    """)
    op.execute("""
        CREATE TYPE health_sync_status AS ENUM ('success', 'partial', 'failed')
    """)
    op.execute("""
        CREATE TYPE condition_category AS ENUM (
            'thyroid', 'weight', 'pcos', 'skin_hair',
            'mens_intimate', 'hormones_trt', 'longevity'
        )
    """)
    op.execute("""
        CREATE TYPE doctor_status AS ENUM (
            'applied', 'documents_submitted', 'verified',
            'onboarding', 'active', 'inactive', 'suspended'
        )
    """)
    op.execute("""
        CREATE TYPE availability_status AS ENUM ('available', 'booked', 'blocked')
    """)
    op.execute("""
        CREATE TYPE credential_type AS ENUM (
            'mbbs', 'md', 'dnb', 'dm', 'mch', 'fellowship', 'certification'
        )
    """)
    op.execute("""
        CREATE TYPE coordinator_status AS ENUM ('active', 'inactive')
    """)
    op.execute("""
        CREATE TYPE payment_status AS ENUM (
            'created', 'attempted', 'paid', 'failed', 'refunded', 'partial_refunded'
        )
    """)
    op.execute("""
        CREATE TYPE consultation_status AS ENUM (
            'requested', 'scheduled', 'confirmed', 'in_progress',
            'completed', 'cancelled', 'no_show'
        )
    """)
    op.execute("""
        CREATE TYPE consultation_type AS ENUM ('initial', 'follow_up')
    """)
    op.execute("""
        CREATE TYPE note_type AS ENUM (
            'clinical', 'coordinator_only', 'patient_visible', 'private'
        )
    """)
    op.execute("""
        CREATE TYPE lab_report_source AS ENUM ('patient_upload', 'kyros_order')
    """)
    op.execute("""
        CREATE TYPE lab_report_status AS ENUM (
            'upload_pending', 'ocr_pending', 'ocr_processing',
            'ocr_complete', 'ocr_failed', 'patient_review_needed'
        )
    """)
    op.execute("""
        CREATE TYPE lab_order_status AS ENUM (
            'ordered', 'sample_collected', 'resulted', 'reviewed', 'superseded'
        )
    """)
    op.execute("""
        CREATE TYPE prescription_status AS ENUM (
            'draft', 'signed', 'dispensed', 'cancelled'
        )
    """)
    op.execute("""
        CREATE TYPE drug_form AS ENUM (
            'tablet', 'capsule', 'syrup', 'injection', 'topical', 'other'
        )
    """)
    op.execute("""
        CREATE TYPE content_type AS ENUM ('article', 'video', 'pdf')
    """)
    op.execute("""
        CREATE TYPE content_status AS ENUM (
            'draft', 'pending_review', 'approved', 'rejected', 'published', 'archived'
        )
    """)
    op.execute("""
        CREATE TYPE frequency_code AS ENUM (
            'OD', 'BD', 'TDS', 'QID', 'HS', 'SOS',
            'ALTERNATE_DAYS', 'WEEKLY', 'BIWEEKLY', 'MONTHLY', 'OTHER'
        )
    """)
    op.execute("""
        CREATE TYPE food_relation AS ENUM (
            'before_food', 'after_food', 'with_food', 'empty_stomach', 'anytime'
        )
    """)
    op.execute("""
        CREATE TYPE refund_status AS ENUM ('pending', 'processed', 'failed')
    """)
    op.execute("""
        CREATE TYPE care_plan_status AS ENUM ('draft', 'active', 'completed', 'cancelled')
    """)
    op.execute("""
        CREATE TYPE care_plan_item_category AS ENUM (
            'medication', 'exercise', 'diet', 'lifestyle', 'follow_up', 'lab_test'
        )
    """)
    op.execute("""
        CREATE TYPE care_plan_item_priority AS ENUM ('high', 'normal', 'low')
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. SEQUENCES
    # ═══════════════════════════════════════════════════════════════════════════
    op.execute("CREATE SEQUENCE kc_patient_id_seq START 1 INCREMENT 1 NO CYCLE")
    op.execute("CREATE SEQUENCE gst_invoice_seq START 1 INCREMENT 1 NO CYCLE")

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. TABLES (dependency order)
    # ═══════════════════════════════════════════════════════════════════════════

    # ── users ─────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE users (
            id                          UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            role                        user_role    NOT NULL,
            email                       VARCHAR(255) UNIQUE,
            phone                       VARCHAR(20)  UNIQUE,
            phone_verified              BOOLEAN      NOT NULL DEFAULT false,
            email_verified              BOOLEAN      NOT NULL DEFAULT false,
            password_hash               VARCHAR(255),
            reset_otp_channel           otp_reset_channel,
            google_sub                  VARCHAR(255) UNIQUE,
            name                        VARCHAR(255) NOT NULL,
            date_of_birth               DATE,
            gender                      user_gender,
            city                        VARCHAR(100),
            state                       VARCHAR(100),
            language_preference         VARCHAR(10),
            timezone                    VARCHAR(50)  NOT NULL DEFAULT 'Asia/Kolkata',
            last_login_at               TIMESTAMPTZ,
            expo_push_token             VARCHAR(200),
            notification_preferences    JSONB        NOT NULL DEFAULT '{"push": true, "whatsapp": true, "email": true}'::jsonb,
            erased_at                   TIMESTAMPTZ,
            created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at                  TIMESTAMPTZ
        )
    """)

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE refresh_tokens (
            id           UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id      UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id   UUID         NOT NULL,
            token_hash   VARCHAR(64)  NOT NULL UNIQUE,
            expires_at   TIMESTAMPTZ  NOT NULL,
            revoked_at   TIMESTAMPTZ,
            parent_id    UUID         REFERENCES refresh_tokens(id) ON DELETE SET NULL,
            ip_address   INET,
            user_agent   VARCHAR(500),
            mfa_verified BOOLEAN      NOT NULL DEFAULT false,
            created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_refresh_tokens_session_id ON refresh_tokens (session_id)"
    )

    # ── ad_consent_records ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_consent_records (
            id                UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id           UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            consent_type      consent_type NOT NULL,
            version           VARCHAR(20)  NOT NULL,
            granted           BOOLEAN      NOT NULL,
            granted_at        TIMESTAMPTZ  NOT NULL,
            revoked_at        TIMESTAMPTZ,
            ip_address        INET,
            consent_text_hash VARCHAR(64)  NOT NULL,
            created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)

    # ── ad_data_subject_requests ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_data_subject_requests (
            id           UUID                        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id      UUID                        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            request_type data_subject_request_type    NOT NULL,
            status       data_subject_request_status  NOT NULL,
            received_at  TIMESTAMPTZ                  NOT NULL,
            completed_at TIMESTAMPTZ,
            notes        TEXT,
            created_at   TIMESTAMPTZ                  NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ                  NOT NULL DEFAULT NOW()
        )
    """)

    # ── ad_audit_log (partitioned, append-only, NO FK on actor_user_id) ──────
    op.execute("""
        CREATE TABLE ad_audit_log (
            id            UUID         NOT NULL DEFAULT gen_random_uuid(),
            timestamp     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            actor_user_id UUID,
            actor_role    actor_role   NOT NULL,
            action        VARCHAR(100) NOT NULL,
            resource_type VARCHAR(100),
            resource_id   UUID,
            allowed       BOOLEAN      NOT NULL,
            reason        VARCHAR(255),
            role_context  VARCHAR(20),
            permission    VARCHAR(64),
            ip_address    INET,
            user_agent    VARCHAR(500),
            metadata      JSONB,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp)
    """)
    for suffix, from_date, to_date in _AUDIT_PARTITIONS:
        op.execute(
            f"CREATE TABLE ad_audit_log_{suffix} "
            f"PARTITION OF ad_audit_log "
            f"FOR VALUES FROM ('{from_date}') TO ('{to_date}')"
        )
    op.execute(
        "CREATE INDEX ix_audit_log_actor ON ad_audit_log (actor_user_id, timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX ix_audit_log_resource ON ad_audit_log (resource_type, resource_id)"
    )

    # ── ad_booking_inquiries ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_booking_inquiries (
            id                   UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            name                 VARCHAR(255) NOT NULL,
            gender               VARCHAR(10),
            phone                VARCHAR(20)  NOT NULL,
            email                VARCHAR(255),
            condition_category   VARCHAR(50)  NOT NULL,
            intake_responses     JSONB        NOT NULL DEFAULT '{}',
            skipped_intake       BOOLEAN      NOT NULL DEFAULT false,
            ip_address           INET,
            user_agent           VARCHAR(500),
            status               VARCHAR(50)  NOT NULL DEFAULT 'new',
            contacted_by_user_id UUID         REFERENCES users(id) ON DELETE SET NULL,
            contacted_at         TIMESTAMPTZ,
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at           TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX ix_ad_booking_inquiries_status "
        "ON ad_booking_inquiries (status, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_ad_booking_inquiries_phone ON ad_booking_inquiries (phone)"
    )

    # ── ad_leads ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_leads (
            id                   UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            name                 VARCHAR(255) NOT NULL,
            email                VARCHAR(255) NOT NULL,
            subject              VARCHAR(50)  NOT NULL,
            message              TEXT         NOT NULL,
            ip_address           INET,
            user_agent           VARCHAR(500),
            status               VARCHAR(50)  NOT NULL DEFAULT 'new',
            contacted_by_user_id UUID         REFERENCES users(id) ON DELETE SET NULL,
            contacted_at         TIMESTAMPTZ,
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at           TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX ix_ad_leads_status ON ad_leads (status, created_at DESC)")

    # ── dr_doctors ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE dr_doctors (
            id                                    UUID          NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id                               UUID          NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
            nmc_registration_number               VARCHAR(50)   NOT NULL UNIQUE,
            nmc_state_council                     VARCHAR(100),
            verified_at                           TIMESTAMPTZ,
            specialty                             JSONB         NOT NULL DEFAULT '[]',
            conditions_treated                    JSONB         NOT NULL DEFAULT '[]',
            consultation_languages                JSONB         NOT NULL DEFAULT '["en"]',
            status                                doctor_status NOT NULL DEFAULT 'applied',
            consultation_duration_minutes_default INT           NOT NULL DEFAULT 20,
            buffer_time_minutes                   INT           NOT NULL DEFAULT 5,
            revenue_share_pct                     DECIMAL(5,2),
            bank_details_encrypted                BYTEA,
            bio_short                             VARCHAR(500),
            bio_long                              TEXT,
            photo_url                             VARCHAR(500),
            onboarding_stage                      VARCHAR(50),
            created_at                            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            updated_at                            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            deleted_at                            TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX ix_dr_doctors_status ON dr_doctors (status) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_dr_doctors_conditions ON dr_doctors USING GIN (conditions_treated) "
        "WHERE deleted_at IS NULL"
    )

    # ── dr_credentials ────────────────────────────────────────────────────────
    op.execute("""
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
    """)
    op.execute("CREATE INDEX ix_dr_credentials_doctor ON dr_credentials (doctor_id)")

    # ── dr_availability ───────────────────────────────────────────────────────
    # consultation_id FK added below after kc_consultations exists.
    op.execute("""
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
    """)
    op.execute(
        "CREATE INDEX ix_dr_availability_lookup "
        "ON dr_availability (doctor_id, slot_start, status)"
    )

    # ── ad_coordinators ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_coordinators (
            id                   UUID               NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id              UUID               NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
            status               coordinator_status NOT NULL DEFAULT 'active',
            assigned_patient_ids JSONB              NOT NULL DEFAULT '[]',
            employee_id          VARCHAR(50),
            created_at           TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
            deleted_at           TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX ix_ad_coordinators_status "
        "ON ad_coordinators (status) WHERE deleted_at IS NULL"
    )

    # ── kc_patients ───────────────────────────────────────────────────────────
    op.execute("""
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
    """)
    op.execute(
        "CREATE INDEX ix_kc_patients_conditions ON kc_patients USING GIN (primary_conditions) "
        "WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_kc_patients_coordinator "
        "ON kc_patients (assigned_coordinator_id) WHERE deleted_at IS NULL"
    )

    # ── wn_reminders ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE wn_reminders (
            id                        UUID          NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id                   UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type                      reminder_type NOT NULL,
            label                     VARCHAR(255)  NOT NULL,
            schedule_cron             VARCHAR(100),
            schedule_interval_minutes INT,
            active                    BOOLEAN       NOT NULL DEFAULT TRUE,
            notification_channels     JSONB         NOT NULL DEFAULT '[]',
            metadata                  JSONB,
            created_at                TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            updated_at                TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            deleted_at                TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX ix_wn_reminders_user_id "
        "ON wn_reminders (user_id) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_wn_reminders_active "
        "ON wn_reminders (user_id, active) WHERE deleted_at IS NULL"
    )

    # ── wn_reminder_logs ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE wn_reminder_logs (
            id           UUID            NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            reminder_id  UUID            NOT NULL REFERENCES wn_reminders(id) ON DELETE CASCADE,
            user_id      UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            scheduled_at TIMESTAMPTZ     NOT NULL,
            action       reminder_action NOT NULL,
            action_at    TIMESTAMPTZ     NOT NULL,
            notes        VARCHAR(500),
            created_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_wn_reminder_logs_reminder "
        "ON wn_reminder_logs (reminder_id, scheduled_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_wn_reminder_logs_user "
        "ON wn_reminder_logs (user_id, action_at DESC)"
    )

    # ── wn_health_sync_sessions ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE wn_health_sync_sessions (
            id               UUID               NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id          UUID               NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source           health_sync_source NOT NULL,
            synced_at        TIMESTAMPTZ        NOT NULL,
            data_range_start TIMESTAMPTZ        NOT NULL,
            data_range_end   TIMESTAMPTZ        NOT NULL,
            record_count     INT                NOT NULL DEFAULT 0,
            consent_id       UUID               REFERENCES ad_consent_records(id) ON DELETE SET NULL,
            status           health_sync_status NOT NULL,
            created_at       TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ        NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_wn_health_sync_sessions_user "
        "ON wn_health_sync_sessions (user_id, synced_at DESC)"
    )

    # ── wn_health_datapoints (partitioned) ────────────────────────────────────
    op.execute("""
        CREATE TABLE wn_health_datapoints (
            id                UUID                   NOT NULL DEFAULT gen_random_uuid(),
            user_id           UUID                   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source            health_datapoint_source NOT NULL,
            source_session_id UUID                   REFERENCES wn_health_sync_sessions(id) ON DELETE SET NULL,
            source_record_id  VARCHAR(255),
            type              health_datapoint_type  NOT NULL,
            value             JSONB                  NOT NULL,
            measured_at       TIMESTAMPTZ            NOT NULL,
            created_at        TIMESTAMPTZ            NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, measured_at),
            UNIQUE (user_id, source, source_record_id, measured_at)
        ) PARTITION BY RANGE (measured_at)
    """)
    for suffix, from_date, to_date in _HEALTH_PARTITIONS:
        op.execute(
            f"CREATE TABLE wn_health_datapoints_{suffix} "
            f"PARTITION OF wn_health_datapoints "
            f"FOR VALUES FROM ('{from_date}') TO ('{to_date}')"
        )
    op.execute(
        "CREATE INDEX ix_wn_health_datapoints_measured "
        "ON wn_health_datapoints USING BRIN (measured_at)"
    )
    op.execute(
        "CREATE INDEX ix_wn_health_datapoints_user_type "
        "ON wn_health_datapoints (user_id, type, measured_at DESC)"
    )

    # ── kc_payments ───────────────────────────────────────────────────────────
    # consultation_id FK added below after kc_consultations exists.
    op.execute("""
        CREATE TABLE kc_payments (
            id                  UUID           NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id             UUID           NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            consultation_id     UUID,
            razorpay_order_id   VARCHAR(100)   NOT NULL UNIQUE,
            razorpay_payment_id VARCHAR(100),
            amount_paise        INT            NOT NULL,
            currency            VARCHAR(3)     NOT NULL DEFAULT 'INR',
            status              payment_status NOT NULL DEFAULT 'created',
            gst_invoice_number  VARCHAR(50),
            gst_invoice_url     VARCHAR(500),
            created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_payments_user_status ON kc_payments (user_id, status)"
    )
    op.execute(
        "CREATE INDEX ix_kc_payments_razorpay_payment "
        "ON kc_payments (razorpay_payment_id) WHERE razorpay_payment_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_kc_payments_consultation "
        "ON kc_payments (consultation_id) WHERE consultation_id IS NOT NULL"
    )

    # ── kc_pre_consultation_reports ───────────────────────────────────────────
    # consultation_id FK added below after kc_consultations exists.
    op.execute("""
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
    """)
    op.execute(
        "CREATE INDEX ix_kc_pre_consult_patient "
        "ON kc_pre_consultation_reports (patient_id)"
    )

    # ── ad_coupons ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_coupons (
            id                  UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            code                VARCHAR(50) NOT NULL UNIQUE,
            description         TEXT,
            discount_type       VARCHAR(10) NOT NULL
                CHECK (discount_type IN ('flat', 'percent')),
            discount_value      INTEGER     NOT NULL
                CHECK (discount_value > 0),
            max_discount_paise  INTEGER,
            min_order_paise     INTEGER     NOT NULL DEFAULT 0,
            max_redemptions     INTEGER,
            redemption_count    INTEGER     NOT NULL DEFAULT 0,
            valid_from          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            valid_until         TIMESTAMPTZ,
            active              BOOLEAN     NOT NULL DEFAULT true,
            created_by_admin_id UUID        REFERENCES users(id) ON DELETE RESTRICT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_ad_coupons_code ON ad_coupons (code)")

    # ── kc_consultations ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_consultations (
            id                          UUID                NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            patient_id                  UUID                NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            doctor_id                   UUID                REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            coordinator_id              UUID                REFERENCES ad_coordinators(id) ON DELETE SET NULL,
            condition_category          condition_category  NOT NULL,
            consultation_type           consultation_type   NOT NULL DEFAULT 'initial',
            scheduled_start_at          TIMESTAMPTZ,
            scheduled_end_at            TIMESTAMPTZ,
            actual_start_at             TIMESTAMPTZ,
            actual_end_at               TIMESTAMPTZ,
            status                      consultation_status NOT NULL DEFAULT 'scheduled',
            video_room_id               VARCHAR(100),
            video_session_id            VARCHAR(100),
            recording_consent           BOOL                NOT NULL DEFAULT FALSE,
            recording_url               VARCHAR(500),
            pre_consultation_report_id  UUID                REFERENCES kc_pre_consultation_reports(id) ON DELETE SET NULL,
            consultation_fee_paise      INT,
            requirement_notes           TEXT,
            preferred_time_window       VARCHAR(50),
            coupon_id                   UUID                REFERENCES ad_coupons(id) ON DELETE RESTRICT,
            discount_paise              INT                 NOT NULL DEFAULT 0,
            payment_id                  UUID                REFERENCES kc_payments(id) ON DELETE SET NULL,
            cancellation_reason         VARCHAR(500),
            legal_hold_until            TIMESTAMPTZ,
            legal_hold_reason           VARCHAR(100),
            created_at                  TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
            updated_at                  TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
            deleted_at                  TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_consultations_patient "
        "ON kc_consultations (patient_id, scheduled_start_at DESC) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_kc_consultations_doctor "
        "ON kc_consultations (doctor_id, scheduled_start_at) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_kc_consultations_status "
        "ON kc_consultations (status) WHERE deleted_at IS NULL"
    )

    # ── Wire deferred FKs ────────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE kc_pre_consultation_reports "
        "ADD CONSTRAINT fk_kc_pre_consult_consultation "
        "FOREIGN KEY (consultation_id) REFERENCES kc_consultations(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE dr_availability "
        "ADD CONSTRAINT fk_dr_avail_consultation "
        "FOREIGN KEY (consultation_id) REFERENCES kc_consultations(id) ON DELETE SET NULL"
    )
    op.execute(
        "ALTER TABLE kc_payments "
        "ADD CONSTRAINT fk_kc_payments_consultation "
        "FOREIGN KEY (consultation_id) REFERENCES kc_consultations(id) ON DELETE SET NULL"
    )

    # ── kc_doctor_notes ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_doctor_notes (
            id               UUID      NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            consultation_id  UUID      NOT NULL REFERENCES kc_consultations(id) ON DELETE CASCADE,
            doctor_id        UUID      NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            patient_id       UUID      NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            note_type        note_type NOT NULL,
            content          TEXT,
            subjective       TEXT,
            objective        TEXT,
            assessment       TEXT,
            plan             TEXT,
            version          INT       NOT NULL DEFAULT 1,
            superseded_by_id UUID      REFERENCES kc_doctor_notes(id) ON DELETE RESTRICT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_kc_doctor_notes_has_content
                CHECK (content IS NOT NULL OR subjective IS NOT NULL
                       OR objective IS NOT NULL OR assessment IS NOT NULL
                       OR plan IS NOT NULL)
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_doctor_notes_consultation "
        "ON kc_doctor_notes (consultation_id)"
    )

    # ── kc_lab_orders ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_lab_orders (
            id                 UUID             NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            consultation_id    UUID             REFERENCES kc_consultations(id) ON DELETE SET NULL,
            doctor_id          UUID             NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            patient_id         UUID             NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            tests              JSONB            NOT NULL DEFAULT '[]'::jsonb,
            status             lab_order_status NOT NULL DEFAULT 'ordered',
            lab_name           VARCHAR(255),
            result_uploaded_at TIMESTAMPTZ,
            result_file_url    VARCHAR(500),
            parsed_json        JSONB,
            ocr_confidence_avg NUMERIC(3,2),
            reviewed_at        TIMESTAMPTZ,
            created_at         TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
            updated_at         TIMESTAMPTZ      NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_kc_lab_orders_patient_id ON kc_lab_orders (patient_id)")
    op.execute("CREATE INDEX ix_kc_lab_orders_doctor_id ON kc_lab_orders (doctor_id)")
    op.execute("CREATE INDEX ix_kc_lab_orders_status ON kc_lab_orders (status)")

    # ── kc_lab_reports ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_lab_reports (
            id                      UUID              NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            patient_id              UUID              NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            uploaded_by_user_id     UUID              NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            source                  lab_report_source NOT NULL DEFAULT 'patient_upload',
            lab_name                VARCHAR(255),
            report_date             DATE,
            file_url                VARCHAR(500),
            original_filename       VARCHAR(255)      NOT NULL,
            content_type            VARCHAR(100)      NOT NULL,
            file_size_bytes         INT               NOT NULL,
            status                  lab_report_status NOT NULL DEFAULT 'upload_pending',
            parsed_json             JSONB,
            ocr_confidence_avg      NUMERIC(3,2),
            low_confidence_fields   JSONB,
            patient_corrected       BOOL              NOT NULL DEFAULT FALSE,
            lab_order_id            UUID              REFERENCES kc_lab_orders(id) ON DELETE SET NULL,
            doctor_reviewed_by_id   UUID              REFERENCES dr_doctors(id) ON DELETE SET NULL,
            doctor_commentary       JSONB,
            patient_attention_flags JSONB,
            processing_failed_reason TEXT,
            created_at              TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ       NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_kc_lab_reports_patient_id ON kc_lab_reports (patient_id)")
    op.execute("CREATE INDEX ix_kc_lab_reports_status ON kc_lab_reports (status)")

    # ── kc_prescriptions ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_prescriptions (
            id                  UUID                NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            consultation_id     UUID                NOT NULL REFERENCES kc_consultations(id) ON DELETE RESTRICT,
            doctor_id           UUID                NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            patient_id          UUID                NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            status              prescription_status NOT NULL DEFAULT 'draft',
            signed_at           TIMESTAMPTZ,
            pdf_url             VARCHAR(500),
            version             INT                 NOT NULL DEFAULT 1,
            superseded_by_id    UUID                REFERENCES kc_prescriptions(id) ON DELETE RESTRICT,
            diagnosis_note      VARCHAR(500),
            general_instructions TEXT,
            legal_hold_until    TIMESTAMPTZ,
            legal_hold_reason   VARCHAR(100),
            created_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_prescriptions_consultation_id "
        "ON kc_prescriptions (consultation_id)"
    )
    op.execute("CREATE INDEX ix_kc_prescriptions_doctor_id ON kc_prescriptions (doctor_id)")
    op.execute("CREATE INDEX ix_kc_prescriptions_patient_id ON kc_prescriptions (patient_id)")
    op.execute("CREATE INDEX ix_kc_prescriptions_status ON kc_prescriptions (status)")

    # ── kc_prescription_items ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_prescription_items (
            id              UUID           NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            prescription_id UUID           NOT NULL REFERENCES kc_prescriptions(id) ON DELETE CASCADE,
            drug_generic_name VARCHAR(255) NOT NULL,
            drug_form       drug_form      NOT NULL,
            dosage          VARCHAR(100)   NOT NULL,
            frequency       VARCHAR(100),
            frequency_code  frequency_code NOT NULL DEFAULT 'OTHER',
            timing_slots    JSONB          NOT NULL DEFAULT '[]'::jsonb,
            food_relation   food_relation,
            duration_days   INT,
            instructions    TEXT,
            refill_allowed  BOOLEAN        NOT NULL DEFAULT false,
            order_index     INT            NOT NULL DEFAULT 0,
            drug_schedule   VARCHAR(10),
            created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_prescription_items_prescription_id "
        "ON kc_prescription_items (prescription_id)"
    )

    # ── kc_education_content ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_education_content (
            id                    UUID           NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            title                 VARCHAR(255)   NOT NULL,
            slug                  VARCHAR(255)   NOT NULL UNIQUE,
            content_type          content_type   NOT NULL,
            condition_categories  JSONB          NOT NULL DEFAULT '[]'::jsonb,
            content_url           VARCHAR(500),
            body_md               TEXT,
            reviewed_by_doctor_id UUID           REFERENCES dr_doctors(id) ON DELETE SET NULL,
            reviewed_at           TIMESTAMPTZ,
            status                content_status NOT NULL DEFAULT 'draft',
            ai_disclosure         BOOL           NOT NULL DEFAULT FALSE,
            created_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_education_content_status ON kc_education_content (status)"
    )
    op.execute(
        "CREATE INDEX ix_kc_education_content_slug ON kc_education_content (slug)"
    )

    # ── kc_education_assignments ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_education_assignments (
            id                    UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            content_id            UUID        NOT NULL REFERENCES kc_education_content(id) ON DELETE CASCADE,
            patient_id            UUID        NOT NULL REFERENCES kc_patients(id) ON DELETE CASCADE,
            assigned_by_doctor_id UUID        NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            consultation_id       UUID        REFERENCES kc_consultations(id) ON DELETE SET NULL,
            read_at               TIMESTAMPTZ,
            notes                 VARCHAR(500),
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_education_assignments_patient "
        "ON kc_education_assignments (patient_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_kc_education_assignments_content "
        "ON kc_education_assignments (content_id)"
    )

    # ── ad_sign_off_records (append-only) ─────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_sign_off_records (
            id                      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            content_id              UUID        NOT NULL
                REFERENCES kc_education_content(id) ON DELETE RESTRICT,
            doctor_id               UUID        NOT NULL
                REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            nmc_registration_number VARCHAR(50) NOT NULL,
            artifact_hash           CHAR(64)    NOT NULL,
            action                  VARCHAR(20) NOT NULL,
            notes                   TEXT,
            signed_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_ad_sign_off_records_content_id ON ad_sign_off_records (content_id)"
    )

    # ── wn_notifications ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE wn_notifications (
            id            UUID          NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id       UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            template_name VARCHAR(100)  NOT NULL,
            title         VARCHAR(255)  NOT NULL,
            body          VARCHAR(1000) NOT NULL,
            channels      JSONB         NOT NULL DEFAULT '[]'::jsonb,
            data          JSONB         NOT NULL DEFAULT '{}'::jsonb,
            read_at       TIMESTAMPTZ,
            sent_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_wn_notifications_user_sent "
        "ON wn_notifications (user_id, sent_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_wn_notifications_user_unread "
        "ON wn_notifications (user_id) WHERE read_at IS NULL"
    )

    # ── ad_daily_metrics ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_daily_metrics (
            id          UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            metric_date DATE         NOT NULL,
            metric_key  VARCHAR(64)  NOT NULL,
            dimension   VARCHAR(128) NOT NULL DEFAULT '',
            value       BIGINT       NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_ad_daily_metrics "
        "ON ad_daily_metrics (metric_date, metric_key, dimension)"
    )
    op.execute(
        "CREATE INDEX ix_ad_daily_metrics_date_key "
        "ON ad_daily_metrics (metric_date, metric_key)"
    )

    # ── ad_followups ──────────────────────────────────────────────────────────
    op.create_table(
        "ad_followups",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "coordinator_id", UUID(as_uuid=True),
            sa.ForeignKey("ad_coordinators.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "patient_id", UUID(as_uuid=True),
            sa.ForeignKey("kc_patients.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ad_followups_coord_status_due", "ad_followups",
        ["coordinator_id", "status", "due_at"],
    )

    # ── ad_patient_interactions ───────────────────────────────────────────────
    op.create_table(
        "ad_patient_interactions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "coordinator_id", UUID(as_uuid=True),
            sa.ForeignKey("ad_coordinators.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "patient_id", UUID(as_uuid=True),
            sa.ForeignKey("kc_patients.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ad_patient_interactions_patient", "ad_patient_interactions",
        ["patient_id", "created_at"],
    )

    # ── ad_staff_roles ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_staff_roles (
            id         UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role       user_role   NOT NULL,
            granted_by UUID        REFERENCES users(id) ON DELETE SET NULL,
            granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, role)
        )
    """)
    op.execute("CREATE INDEX ix_ad_staff_roles_user ON ad_staff_roles (user_id)")

    # ── ad_staff_mfa ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_staff_mfa (
            id                     UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id                UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            totp_secret_encrypted  TEXT        NOT NULL,
            recovery_codes         JSONB       NOT NULL DEFAULT '[]'::jsonb,
            enabled_at             TIMESTAMPTZ,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── ad_platform_settings ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_platform_settings (
            key        VARCHAR(64)  PRIMARY KEY,
            value      JSONB        NOT NULL DEFAULT 'null'::jsonb,
            updated_by UUID         REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)

    # ── ad_pricing_config ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_pricing_config (
            id                  UUID               NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            condition_category  condition_category NOT NULL,
            consultation_type   consultation_type  NOT NULL,
            fee_paise           INTEGER            NOT NULL,
            created_by_admin_id UUID               REFERENCES users(id) ON DELETE RESTRICT,
            created_at          TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
            UNIQUE (condition_category, consultation_type)
        )
    """)

    # ── kc_icd10_codes ────────────────────────────────────────────────────────
    op.create_table(
        "kc_icd10_codes",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
    )
    op.create_index("ix_kc_icd10_codes_category", "kc_icd10_codes", ["category"])

    # ── kc_diagnoses ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_diagnoses (
            id                UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            consultation_id   UUID        NOT NULL REFERENCES kc_consultations(id) ON DELETE CASCADE,
            doctor_id         UUID        NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            patient_id        UUID        NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            icd10_code        VARCHAR(10) NOT NULL,
            icd10_description VARCHAR(255) NOT NULL,
            is_primary        BOOLEAN     NOT NULL DEFAULT false,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_kc_diagnoses_consultation ON kc_diagnoses (consultation_id)")

    # ── kc_drug_catalogue ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_drug_catalogue (
            drug_generic_name VARCHAR(255) PRIMARY KEY,
            drug_schedule     VARCHAR(10)  NOT NULL,
            is_prohibited     BOOLEAN      NOT NULL DEFAULT false,
            requires_vertical VARCHAR(50)
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_drug_catalogue_schedule ON kc_drug_catalogue (drug_schedule)"
    )

    # ── kc_patient_notes ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_patient_notes (
            id              UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            patient_user_id UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            body            TEXT        NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_patient_notes_patient_user_id "
        "ON kc_patient_notes (patient_user_id)"
    )
    op.execute(
        "CREATE INDEX ix_kc_patient_notes_created_at "
        "ON kc_patient_notes (patient_user_id, created_at DESC)"
    )

    # ── kc_refunds ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_refunds (
            id                  UUID          NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            payment_id          UUID          NOT NULL REFERENCES kc_payments(id) ON DELETE RESTRICT,
            user_id             UUID          NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            razorpay_refund_id  VARCHAR(100),
            amount_paise        INT           NOT NULL,
            currency            VARCHAR(3)    NOT NULL DEFAULT 'INR',
            status              refund_status NOT NULL DEFAULT 'pending',
            reason              VARCHAR(500),
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX ix_kc_refunds_user_created ON kc_refunds (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_kc_refunds_payment ON kc_refunds (payment_id)"
    )
    op.execute(
        "CREATE INDEX ix_kc_refunds_razorpay_refund "
        "ON kc_refunds (razorpay_refund_id) WHERE razorpay_refund_id IS NOT NULL"
    )

    # ── kc_care_plans ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_care_plans (
            id                  UUID            NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            consultation_id     UUID            NOT NULL REFERENCES kc_consultations(id) ON DELETE RESTRICT,
            doctor_id           UUID            NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT,
            patient_id          UUID            NOT NULL REFERENCES kc_patients(id) ON DELETE RESTRICT,
            title               VARCHAR(255)    NOT NULL,
            status              care_plan_status NOT NULL DEFAULT 'draft',
            condition_category  VARCHAR(50),
            goals               TEXT,
            notes               TEXT,
            valid_from          DATE,
            valid_until         DATE,
            activated_at        TIMESTAMPTZ,
            completed_at        TIMESTAMPTZ,
            version             INT             NOT NULL DEFAULT 1,
            created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_kc_care_plans_consultation ON kc_care_plans (consultation_id)")
    op.execute("CREATE INDEX ix_kc_care_plans_doctor ON kc_care_plans (doctor_id)")
    op.execute("CREATE INDEX ix_kc_care_plans_patient_status ON kc_care_plans (patient_id, status)")

    # ── kc_care_plan_items ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE kc_care_plan_items (
            id              UUID                    NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            care_plan_id    UUID                    NOT NULL REFERENCES kc_care_plans(id) ON DELETE CASCADE,
            category        care_plan_item_category NOT NULL,
            title           VARCHAR(255)            NOT NULL,
            description     TEXT,
            frequency       VARCHAR(100),
            duration        VARCHAR(100),
            priority        care_plan_item_priority NOT NULL DEFAULT 'normal',
            order_index     INT                     NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ             NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_kc_care_plan_items_plan ON kc_care_plan_items (care_plan_id)")

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. TRIGGERS
    # ═══════════════════════════════════════════════════════════════════════════

    # Audit log: append-only (block UPDATE/DELETE)
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'ad_audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER prevent_audit_log_update
        BEFORE UPDATE OR DELETE ON ad_audit_log
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_modification()
    """)

    # Sign-off records: immutable (block UPDATE/DELETE)
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_sign_off_records_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'ad_sign_off_records rows are immutable';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER tg_sign_off_records_immutable
        BEFORE UPDATE OR DELETE ON ad_sign_off_records
        FOR EACH ROW
        EXECUTE FUNCTION fn_sign_off_records_immutable()
    """)

    # Consultations: block DELETE while under legal hold
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_consult_delete_under_hold()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.legal_hold_until IS NOT NULL AND OLD.legal_hold_until > NOW() THEN
            RAISE EXCEPTION
              'consultation % is under legal hold until % — cannot delete',
              OLD.id, OLD.legal_hold_until;
          END IF;
          RETURN OLD;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_prevent_consult_delete
          BEFORE DELETE ON kc_consultations
          FOR EACH ROW EXECUTE FUNCTION prevent_consult_delete_under_hold()
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. SEED DATA
    # ═══════════════════════════════════════════════════════════════════════════

    # Platform settings defaults
    op.execute("""
        INSERT INTO ad_platform_settings (key, value) VALUES
            ('reset_otp_channel_default', '"sms"'::jsonb),
            ('google_oauth_enabled', 'false'::jsonb)
        ON CONFLICT (key) DO NOTHING
    """)

    # ICD-10 reference codes
    icd10_table = sa.table(
        "kc_icd10_codes",
        sa.column("code", sa.String(10)),
        sa.column("description", sa.String(255)),
        sa.column("category", sa.String(50)),
    )
    op.bulk_insert(icd10_table, ICD10_SEED_CODES)

    # Drug catalogue
    op.execute("""
        INSERT INTO kc_drug_catalogue
            (drug_generic_name, drug_schedule, is_prohibited, requires_vertical)
        VALUES
            ('levothyroxine',           'H',    false, NULL),
            ('methimazole',             'H',    false, NULL),
            ('propylthiouracil',        'H',    false, NULL),
            ('carbimazole',             'H',    false, NULL),
            ('semaglutide',             'H',    false, 'weight'),
            ('liraglutide',             'H',    false, 'weight'),
            ('dulaglutide',             'H',    false, 'weight'),
            ('exenatide',               'H',    false, 'weight'),
            ('orlistat',                'H',    false, NULL),
            ('metformin',               'NONE', false, NULL),
            ('spironolactone',          'H',    false, NULL),
            ('clomiphene',              'H',    false, NULL),
            ('letrozole',               'H',    false, NULL),
            ('drospirenone',            'H',    false, NULL),
            ('inositol',                'NONE', false, NULL),
            ('tretinoin',               'H',    false, NULL),
            ('isotretinoin',            'H1',   false, NULL),
            ('doxycycline',             'H',    false, NULL),
            ('azithromycin',            'H',    false, NULL),
            ('clindamycin',             'H',    false, NULL),
            ('minoxidil',               'NONE', false, NULL),
            ('adapalene',               'NONE', false, NULL),
            ('finasteride',             'H',    false, NULL),
            ('dutasteride',             'H',    false, NULL),
            ('sildenafil',              'H',    false, NULL),
            ('tadalafil',               'H',    false, NULL),
            ('vardenafil',              'H',    false, NULL),
            ('testosterone',            'H',    false, 'hormones_trt'),
            ('testosterone enanthate',  'H',    false, 'hormones_trt'),
            ('testosterone cypionate',  'H',    false, 'hormones_trt'),
            ('testosterone undecanoate','H',    false, 'hormones_trt'),
            ('human chorionic gonadotropin', 'H', false, NULL),
            ('escitalopram',            'H',    false, NULL),
            ('sertraline',              'H',    false, NULL),
            ('buspirone',               'H',    false, NULL),
            ('atorvastatin',            'H',    false, NULL),
            ('rosuvastatin',            'H',    false, NULL),
            ('amlodipine',              'H',    false, NULL),
            ('losartan',                'H',    false, NULL),
            ('vitamin d3',              'NONE', false, NULL),
            ('omega-3 fatty acids',     'NONE', false, NULL),
            ('melatonin',               'NONE', false, NULL),
            ('ibuprofen',               'NONE', false, NULL),
            ('paracetamol',             'NONE', false, NULL),
            ('alprazolam',              'X',    false, NULL),
            ('diazepam',                'X',    false, NULL),
            ('nitrazepam',              'X',    false, NULL),
            ('clonazepam',              'X',    false, NULL),
            ('lorazepam',               'X',    false, NULL),
            ('zolpidem',                'X',    false, NULL),
            ('tramadol',                'X',    false, NULL),
            ('codeine',                 'X',    false, NULL),
            ('buprenorphine',           'X',    false, NULL),
            ('ceftriaxone',             'H1',   false, NULL),
            ('meropenem',               'H1',   false, NULL),
            ('sibutramine',             'NONE', true,  NULL),
            ('phenformin',              'NONE', true,  NULL),
            ('rofecoxib',               'NONE', true,  NULL),
            ('cisapride',               'NONE', true,  NULL)
    """)


def downgrade() -> None:
    raise NotImplementedError(
        "This is the baseline migration for a production database. "
        "downgrade is not supported — restore from backup instead."
    )
