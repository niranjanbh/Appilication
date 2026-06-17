"""Prescriptions: kc_prescriptions, kc_prescription_items

Revision ID: b1f309330b5b
Revises: 0010
Create Date: 2026-06-03

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = 'b1f309330b5b'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE prescription_status AS ENUM (
                'draft', 'signed', 'dispensed', 'cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE drug_form AS ENUM (
                'tablet', 'capsule', 'syrup', 'injection', 'topical', 'other'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.create_table(
        'kc_prescriptions',
        sa.Column('consultation_id', sa.UUID(), nullable=False),
        sa.Column('doctor_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM('draft', 'signed', 'dispensed', 'cancelled', name='prescription_status', create_type=False),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pdf_url', sa.String(length=500), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('superseded_by_id', sa.UUID(), nullable=True),
        sa.Column('diagnosis_note', sa.String(length=500), nullable=True),
        sa.Column('general_instructions', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['consultation_id'], ['kc_consultations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['doctor_id'], ['dr_doctors.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['patient_id'], ['kc_patients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['superseded_by_id'], ['kc_prescriptions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_kc_prescriptions_consultation_id', 'kc_prescriptions', ['consultation_id'])
    op.create_index('ix_kc_prescriptions_doctor_id', 'kc_prescriptions', ['doctor_id'])
    op.create_index('ix_kc_prescriptions_patient_id', 'kc_prescriptions', ['patient_id'])
    op.create_index('ix_kc_prescriptions_status', 'kc_prescriptions', ['status'])

    op.create_table(
        'kc_prescription_items',
        sa.Column('prescription_id', sa.UUID(), nullable=False),
        sa.Column('drug_generic_name', sa.String(length=255), nullable=False),
        sa.Column(
            'drug_form',
            postgresql.ENUM('tablet', 'capsule', 'syrup', 'injection', 'topical', 'other', name='drug_form', create_type=False),
            nullable=False,
        ),
        sa.Column('dosage', sa.String(length=100), nullable=False),
        sa.Column('frequency', sa.String(length=100), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('refill_allowed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['prescription_id'], ['kc_prescriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_kc_prescription_items_prescription_id', 'kc_prescription_items', ['prescription_id'])


def downgrade() -> None:
    op.drop_index('ix_kc_prescription_items_prescription_id', table_name='kc_prescription_items')
    op.drop_table('kc_prescription_items')
    op.drop_index('ix_kc_prescriptions_status', table_name='kc_prescriptions')
    op.drop_index('ix_kc_prescriptions_patient_id', table_name='kc_prescriptions')
    op.drop_index('ix_kc_prescriptions_doctor_id', table_name='kc_prescriptions')
    op.drop_index('ix_kc_prescriptions_consultation_id', table_name='kc_prescriptions')
    op.drop_table('kc_prescriptions')
    op.execute("DROP TYPE IF EXISTS drug_form")
    op.execute("DROP TYPE IF EXISTS prescription_status")
