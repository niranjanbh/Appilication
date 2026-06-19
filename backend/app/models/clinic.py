from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import (
    CarePlanItemCategory,
    CarePlanItemPriority,
    CarePlanStatus,
    ConsultationStatus,
    ConsultationType,
    DrugForm,
    FoodRelation,
    FrequencyCode,
    LabOrderStatus,
    LabReportSource,
    LabReportStatus,
    NoteType,
    PrescriptionStatus,
    enum_values,
)
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Patient(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Extended patient profile — 1:1 with users where role=patient."""

    __tablename__ = "kc_patients"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    kyros_patient_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    abha_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    primary_conditions: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    preferred_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_coordinator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_coordinators.id", ondelete="SET NULL"),
        nullable=True,
    )
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    chronic_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    intake_complete_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PreConsultationReport(Base, UUIDMixin, TimestampMixin):
    """Auto-generated report assembled 24 h before each consultation."""

    __tablename__ = "kc_pre_consultation_reports"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # FK to kc_consultations; nullable here to allow the row to be created before
    # the consultation row in edge cases (normally set at creation time).
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_consultations.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lab_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    adherence_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    wearable_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    patient_flags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    intake_responses: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    doctor_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    doctor_notes_pre_consult: Mapped[str | None] = mapped_column(Text, nullable=True)


class Consultation(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """A single doctor-patient consultation event."""

    __tablename__ = "kc_consultations"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Nullable until a coordinator assigns a doctor (status='requested' has none).
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    coordinator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_coordinators.id", ondelete="SET NULL"),
        nullable=True,
    )
    condition_category: Mapped[str] = mapped_column(
        SAEnum(
            "thyroid", "weight", "pcos", "skin_hair", "mens_intimate",
            "hormones_trt", "longevity",
            name="condition_category", create_type=False,
        ),
        nullable=False,
    )
    consultation_type: Mapped[ConsultationType] = mapped_column(
        SAEnum(ConsultationType, name="consultation_type", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'initial'"),
    )
    # Nullable until a coordinator assigns a slot (status='requested' has none).
    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    scheduled_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Patient's free-text requirement (symptoms / what they want help with) and a
    # coarse preferred time window (e.g. 'weekday_morning'), captured at request time.
    requirement_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_time_window: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ConsultationStatus] = mapped_column(
        SAEnum(ConsultationStatus, name="consultation_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'scheduled'"),
    )
    video_room_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    video_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recording_consent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    recording_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pre_consultation_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_pre_consultation_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Nullable until assignment — the fee is priced server-side when a coordinator
    # assigns the doctor + slot, never at request time.
    consultation_fee_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_coupons.id", ondelete="RESTRICT"),
        nullable=True,
    )
    discount_paise: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Set by the erasure task — holds the row for NMC statutory retention period.
    legal_hold_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    legal_hold_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)


class DoctorNote(Base, UUIDMixin, TimestampMixin):
    """Append-only clinical notes written by a doctor during/after a consultation."""

    __tablename__ = "kc_doctor_notes"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    note_type: Mapped[NoteType] = mapped_column(
        SAEnum(NoteType, name="note_type", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    subjective: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_doctor_notes.id", ondelete="RESTRICT"),
        nullable=True,
    )


class PatientNote(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Freeform health notes written by a patient, readable by their doctors."""

    __tablename__ = "kc_patient_notes"

    patient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)


class Icd10Code(Base):
    """Curated ICD-10 reference catalog for doctor-portal autocomplete.

    Not a hard FK target for kc_diagnoses — a search aid, not the source of truth.
    """

    __tablename__ = "kc_icd10_codes"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)


class Diagnosis(Base, UUIDMixin, TimestampMixin):
    """A per-consultation ICD-10 diagnosis recorded by the doctor."""

    __tablename__ = "kc_diagnoses"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    icd10_code: Mapped[str] = mapped_column(String(10), nullable=False)
    icd10_description: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class LabReport(Base, UUIDMixin, TimestampMixin):
    """Patient-uploaded lab report.  Processed by the OCR pipeline after finalize."""

    __tablename__ = "kc_lab_reports"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source: Mapped[LabReportSource] = mapped_column(
        SAEnum(LabReportSource, name="lab_report_source", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'patient_upload'"),
    )
    lab_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[LabReportStatus] = mapped_column(
        SAEnum(LabReportStatus, name="lab_report_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'upload_pending'"),
        index=True,
    )
    parsed_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ocr_confidence_avg: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    low_confidence_fields: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    patient_corrected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    lab_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_lab_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    doctor_reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="SET NULL"),
        nullable=True,
    )
    doctor_commentary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    patient_attention_flags: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    processing_failed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class LabOrder(Base, UUIDMixin, TimestampMixin):
    """Doctor-issued lab test order, optionally linked to a consultation."""

    __tablename__ = "kc_lab_orders"

    consultation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_consultations.id", ondelete="SET NULL"),
        nullable=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tests: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    status: Mapped[LabOrderStatus] = mapped_column(
        SAEnum(LabOrderStatus, name="lab_order_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'ordered'"),
        index=True,
    )
    lab_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parsed_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ocr_confidence_avg: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Prescription(Base, UUIDMixin, TimestampMixin):
    """Doctor-authored prescription, append-only versioned.

    Edits create a new row (version+1) and set superseded_by_id on the new row
    pointing at its predecessor.  The "current" view filters superseded_by_id IS NULL.

    Draft prescriptions are NEVER visible to patients — filtered at the SQL
    layer in the patient-scoped repository query.
    """

    __tablename__ = "kc_prescriptions"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_consultations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[PrescriptionStatus] = mapped_column(
        SAEnum(PrescriptionStatus, name="prescription_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'draft'"),
        index=True,
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_prescriptions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    diagnosis_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    general_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set by the erasure task — holds the row for NMC statutory retention period.
    legal_hold_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    legal_hold_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)


class PrescriptionItem(Base, UUIDMixin, TimestampMixin):
    """A single drug line on a prescription."""

    __tablename__ = "kc_prescription_items"

    prescription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_prescriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drug_generic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    drug_form: Mapped[DrugForm] = mapped_column(
        SAEnum(DrugForm, name="drug_form", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    # Human-readable display string, composed server-side from the structured
    # fields below. Nullable for forward-compat; new lines always populate it.
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency_code: Mapped[FrequencyCode] = mapped_column(
        SAEnum(FrequencyCode, name="frequency_code", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'OTHER'"),
    )
    # List of TimingSlot values, e.g. ["morning", "night"] for BD dosing.
    timing_slots: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    food_relation: Mapped[FoodRelation | None] = mapped_column(
        SAEnum(FoodRelation, name="food_relation", create_type=False, values_callable=enum_values),
        nullable=True,
    )
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    refill_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    drug_schedule: Mapped[str | None] = mapped_column(String(10), nullable=True)


class CarePlan(Base, UUIDMixin, TimestampMixin):
    """Doctor-authored treatment plan for a patient.

    Draft care plans are NEVER visible to patients — filtered at the SQL layer
    in the patient-scoped repository query, same pattern as prescriptions.
    """

    __tablename__ = "kc_care_plans"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_consultations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dr_doctors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CarePlanStatus] = mapped_column(
        SAEnum(CarePlanStatus, name="care_plan_status", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'draft'"),
        index=True,
    )
    condition_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class CarePlanItem(Base, UUIDMixin, TimestampMixin):
    """A single component of a care plan (medication, exercise, diet, etc.)."""

    __tablename__ = "kc_care_plan_items"

    care_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_care_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[CarePlanItemCategory] = mapped_column(
        SAEnum(CarePlanItemCategory, name="care_plan_item_category", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[CarePlanItemPriority] = mapped_column(
        SAEnum(CarePlanItemPriority, name="care_plan_item_priority", create_type=False, values_callable=enum_values),
        nullable=False,
        server_default=text("'normal'"),
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class DrugCatalogue(Base):
    """Curated drug catalogue for schedule enforcement and autocomplete.

    NOT exhaustive — a curated reference aid. drug_generic_name is lowercase INN.
    drug_schedule: 'NONE' | 'H' | 'H1' | 'X' (India Drugs & Cosmetics Act).
    is_prohibited: True for CDSCO-banned drugs.
    requires_vertical: if set, doctor must treat that condition category.
    """

    __tablename__ = "kc_drug_catalogue"

    drug_generic_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    drug_schedule: Mapped[str] = mapped_column(String(10), nullable=False)
    is_prohibited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    requires_vertical: Mapped[str | None] = mapped_column(String(50), nullable=True)
