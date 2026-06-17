"""SOAP-structured clinical notes + ICD-10 diagnosis capture.

Adds:
  - kc_doctor_notes: content becomes nullable (a SOAP-only note may carry no free
    text), plus four new nullable TEXT columns (subjective, objective, assessment,
    plan). A CHECK constraint requires at least one of the five to be populated —
    mirrors the Pydantic NoteCreate validator (defense in depth).
  - kc_icd10_codes: curated reference/lookup table for doctor-portal autocomplete.
    Not a hard FK target for kc_diagnoses — a search aid, not the source of truth.
  - kc_diagnoses: per-consultation ICD-10 diagnosis capture (code + description
    denormalized onto the row, doctor- and patient-scoped).

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ICD10_SEED_CODES: list[dict[str, str]] = [
    # Thyroid
    {"code": "E03.9", "description": "Hypothyroidism, unspecified", "category": "thyroid"},
    {"code": "E05.90", "description": "Thyrotoxicosis, unspecified", "category": "thyroid"},
    {"code": "E06.3", "description": "Autoimmune thyroiditis (Hashimoto)", "category": "thyroid"},
    {"code": "E04.9", "description": "Nontoxic goiter, unspecified", "category": "thyroid"},
    # Weight management
    {"code": "E66.9", "description": "Obesity, unspecified", "category": "weight"},
    {"code": "E66.01", "description": "Morbid (severe) obesity due to excess calories", "category": "weight"},
    {"code": "E66.3", "description": "Overweight", "category": "weight"},
    # PCOS
    {"code": "E28.2", "description": "Polycystic ovarian syndrome", "category": "pcos"},
    # Skin & hair
    {"code": "L65.9", "description": "Nonscarring hair loss, unspecified", "category": "skin_hair"},
    {"code": "L70.9", "description": "Acne, unspecified", "category": "skin_hair"},
    {"code": "L68.0", "description": "Hirsutism", "category": "skin_hair"},
    # Men's intimate health
    {"code": "N52.9", "description": "Male erectile dysfunction, unspecified", "category": "mens_intimate"},
    {"code": "N53.11", "description": "Hypoactive sexual desire disorder", "category": "mens_intimate"},
    {"code": "N53.8", "description": "Other male sexual dysfunction", "category": "mens_intimate"},
    # Hormones / TRT
    {"code": "E29.1", "description": "Testicular hypofunction", "category": "hormones_trt"},
    {"code": "E34.9", "description": "Endocrine disorder, unspecified", "category": "hormones_trt"},
    # Longevity
    {"code": "Z71.3", "description": "Dietary counseling and surveillance", "category": "longevity"},
    {"code": "Z00.00", "description": "Encounter for general adult medical examination without abnormal findings", "category": "longevity"},
    {"code": "R53.83", "description": "Other fatigue", "category": "longevity"},
    # General / common comorbidities
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
    # ── kc_doctor_notes: SOAP fields ─────────────────────────────────────────
    op.alter_column("kc_doctor_notes", "content", existing_type=sa.Text(), nullable=True)
    op.add_column("kc_doctor_notes", sa.Column("subjective", sa.Text(), nullable=True))
    op.add_column("kc_doctor_notes", sa.Column("objective", sa.Text(), nullable=True))
    op.add_column("kc_doctor_notes", sa.Column("assessment", sa.Text(), nullable=True))
    op.add_column("kc_doctor_notes", sa.Column("plan", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_kc_doctor_notes_has_content",
        "kc_doctor_notes",
        "content IS NOT NULL OR subjective IS NOT NULL OR objective IS NOT NULL "
        "OR assessment IS NOT NULL OR plan IS NOT NULL",
    )

    # ── kc_icd10_codes: curated reference/lookup table ───────────────────────
    op.create_table(
        "kc_icd10_codes",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
    )
    op.create_index("ix_kc_icd10_codes_category", "kc_icd10_codes", ["category"])

    icd10_codes_table = sa.table(
        "kc_icd10_codes",
        sa.column("code", sa.String(10)),
        sa.column("description", sa.String(255)),
        sa.column("category", sa.String(50)),
    )
    op.bulk_insert(icd10_codes_table, ICD10_SEED_CODES)

    # ── kc_diagnoses ──────────────────────────────────────────────────────────
    op.create_table(
        "kc_diagnoses",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "consultation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("kc_consultations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("dr_doctors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("kc_patients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("icd10_code", sa.String(10), nullable=False),
        sa.Column("icd10_description", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
    op.create_index("ix_kc_diagnoses_consultation", "kc_diagnoses", ["consultation_id"])


def downgrade() -> None:
    op.drop_index("ix_kc_diagnoses_consultation", table_name="kc_diagnoses")
    op.drop_table("kc_diagnoses")

    op.drop_index("ix_kc_icd10_codes_category", table_name="kc_icd10_codes")
    op.drop_table("kc_icd10_codes")

    op.drop_constraint("ck_kc_doctor_notes_has_content", "kc_doctor_notes", type_="check")
    op.drop_column("kc_doctor_notes", "plan")
    op.drop_column("kc_doctor_notes", "assessment")
    op.drop_column("kc_doctor_notes", "objective")
    op.drop_column("kc_doctor_notes", "subjective")
    op.execute("UPDATE kc_doctor_notes SET content = '' WHERE content IS NULL")
    op.alter_column("kc_doctor_notes", "content", existing_type=sa.Text(), nullable=False)
