"""Drug catalogue + schedule-aware prescription enforcement.

Adds:
  - kc_drug_catalogue: curated reference table of ~55 drugs with their India
    drug schedule (NONE / H / H1 / X), prohibited flag (CDSCO-banned drugs),
    and optional vertical restriction (e.g. GLP-1 agonists require 'weight').
    NOT exhaustive; NOT a hard FK target for kc_prescription_items — a curated
    enforcement-and-autocomplete aid, same pattern as kc_icd10_codes.
  - kc_prescription_items.drug_schedule VARCHAR(10) NULL: the resolved schedule
    recorded at prescription-write time for the medical record. NULL on existing
    rows = not yet assessed (pre-migration items).

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | Sequence[str] | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── kc_drug_catalogue ────────────────────────────────────────────────────
    op.create_table(
        "kc_drug_catalogue",
        sa.Column("drug_generic_name", sa.String(255), nullable=False, primary_key=True),
        sa.Column("drug_schedule", sa.String(10), nullable=False),
        sa.Column(
            "is_prohibited",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("requires_vertical", sa.String(50), nullable=True),
    )
    op.create_index("ix_kc_drug_catalogue_schedule", "kc_drug_catalogue", ["drug_schedule"])

    # Seed — curated, not exhaustive.  All names are lowercase INN.
    # Schedules follow India's Drugs & Cosmetics Act Schedule K / H / H1 / X.
    op.execute(
        """
        INSERT INTO kc_drug_catalogue
            (drug_generic_name, drug_schedule, is_prohibited, requires_vertical)
        VALUES
            -- Thyroid vertical
            ('levothyroxine',           'H',    false, NULL),
            ('methimazole',             'H',    false, NULL),
            ('propylthiouracil',        'H',    false, NULL),
            ('carbimazole',             'H',    false, NULL),

            -- Weight vertical — GLP-1 agonists (requires_vertical enforced)
            ('semaglutide',             'H',    false, 'weight'),
            ('liraglutide',             'H',    false, 'weight'),
            ('dulaglutide',             'H',    false, 'weight'),
            ('exenatide',               'H',    false, 'weight'),

            -- Weight vertical — non-GLP-1
            ('orlistat',                'H',    false, NULL),
            ('metformin',               'NONE', false, NULL),

            -- PCOS vertical
            ('spironolactone',          'H',    false, NULL),
            ('clomiphene',              'H',    false, NULL),
            ('letrozole',               'H',    false, NULL),
            ('drospirenone',            'H',    false, NULL),
            ('inositol',                'NONE', false, NULL),

            -- Skin / hair vertical
            ('tretinoin',               'H',    false, NULL),
            ('isotretinoin',            'H1',   false, NULL),
            ('doxycycline',             'H',    false, NULL),
            ('azithromycin',            'H',    false, NULL),
            ('clindamycin',             'H',    false, NULL),
            ('minoxidil',               'NONE', false, NULL),
            ('adapalene',               'NONE', false, NULL),

            -- Hair (also used in skin_hair)
            ('finasteride',             'H',    false, NULL),
            ('dutasteride',             'H',    false, NULL),

            -- Men''s intimate vertical
            ('sildenafil',              'H',    false, NULL),
            ('tadalafil',               'H',    false, NULL),
            ('vardenafil',              'H',    false, NULL),

            -- Hormones / TRT vertical
            ('testosterone',            'H',    false, 'hormones_trt'),
            ('testosterone enanthate',  'H',    false, 'hormones_trt'),
            ('testosterone cypionate',  'H',    false, 'hormones_trt'),
            ('testosterone undecanoate','H',    false, 'hormones_trt'),
            ('human chorionic gonadotropin', 'H', false, NULL),

            -- Common comorbidities / longevity
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

            -- Schedule X — blocked outright (habit-forming / narcotics)
            ('alprazolam',              'X',    false, NULL),
            ('diazepam',                'X',    false, NULL),
            ('nitrazepam',              'X',    false, NULL),
            ('clonazepam',              'X',    false, NULL),
            ('lorazepam',               'X',    false, NULL),
            ('zolpidem',                'X',    false, NULL),
            ('tramadol',                'X',    false, NULL),
            ('codeine',                 'X',    false, NULL),
            ('buprenorphine',           'X',    false, NULL),

            -- Schedule H1 — blocked via telemedicine (Kyros policy)
            ('ceftriaxone',             'H1',   false, NULL),
            ('meropenem',               'H1',   false, NULL),

            -- CDSCO-prohibited drugs (withdrawn / banned in India)
            ('sibutramine',             'NONE', true,  NULL),
            ('phenformin',              'NONE', true,  NULL),
            ('rofecoxib',               'NONE', true,  NULL),
            ('cisapride',               'NONE', true,  NULL)
        """
    )

    # ── kc_prescription_items — add drug_schedule column ────────────────────
    op.add_column(
        "kc_prescription_items",
        sa.Column("drug_schedule", sa.String(10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kc_prescription_items", "drug_schedule")
    op.drop_index("ix_kc_drug_catalogue_schedule", table_name="kc_drug_catalogue")
    op.drop_table("kc_drug_catalogue")
