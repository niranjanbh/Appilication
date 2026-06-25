"""Coordinator-scoped view schemas — clinical content stripped at the schema layer.

Security rule #3: coordinators never see lab values, prescription contents, or
doctor notes. These schemas are the serialization boundary between raw ORM objects
and the coordinator Jinja templates. A view that passes a raw ORM object (or a
doctor/admin schema) to a coordinator template is a code-review reject.

What is intentionally OMITTED from every schema here:
- Patient: allergies, chronic_conditions, current_medications, emergency_contact,
  abha_number, preferred_doctor_id (all clinical or sensitive).
- Consultation: requirement/clinical free-text beyond the coordinator-operational
  fields, recording_url, video_*_id, pre_consultation_report_id, doctor notes,
  diagnoses, prescriptions, lab orders.
- User: password_hash, google_sub, notification_preferences, expo_push_token,
  reset_otp_channel, and any verification internals — only contact fields remain.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel

from app.db.enums import ConsultationStatus


class CoordinatorUserView(BaseModel):
    """Contact-only projection of a User for coordinator templates.

    Coordinators need contact details to reach patients/doctors. No auth,
    verification, or notification internals are exposed.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    phone: str | None = None
    email: str | None = None
    city: str | None = None


class CoordinatorPatientView(BaseModel):
    """Patient view for coordinators — clinical fields stripped.

    Exposes identity, operational status, and the coarse condition categories a
    coordinator needs to triage/schedule. Never exposes allergies, chronic
    conditions, current medications, lab values, prescriptions, or doctor notes.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    kyros_patient_id: str
    # Coarse condition categories only (e.g. ["thyroid"]) — never clinical detail.
    primary_conditions: list[str] = []
    intake_complete_at: datetime | None = None


class CoordinatorConsultationView(BaseModel):
    """Consultation view for coordinators — no clinical content.

    Scheduling-level fields only. Carries the patient-supplied requirement notes
    and preferred window (operational scheduling inputs, captured at request time)
    but never doctor notes, diagnoses, prescriptions, lab orders, or recordings.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    condition_category: str
    consultation_type: str
    # StrEnum — templates render `.status.value`, which stays valid after serialization.
    status: ConsultationStatus
    scheduled_start_at: datetime | None = None
    created_at: datetime
    requirement_notes: str | None = None
    preferred_time_window: str | None = None
    consultation_fee_paise: int | None = None


# ── Tuple-shape serialization helpers ───────────────────────────────────────────
# The coordinator repository returns ORM tuples like (Consultation, patient_user)
# or (Patient, User). These helpers convert each element through the views above so
# templates only ever receive clinical-stripped schemas, while preserving the tuple
# shape the templates iterate over.


def patient_pairs(
    rows: Sequence[tuple[object, object]],
) -> list[tuple[CoordinatorPatientView, CoordinatorUserView]]:
    """(Patient, User) -> (CoordinatorPatientView, CoordinatorUserView)."""
    return [
        (
            CoordinatorPatientView.model_validate(patient),
            CoordinatorUserView.model_validate(user),
        )
        for patient, user in rows
    ]


def consultation_user_pairs(
    rows: Sequence[tuple[object, object]],
) -> list[tuple[CoordinatorConsultationView, CoordinatorUserView | None]]:
    """(Consultation, user_or_none) -> (CoordinatorConsultationView, CoordinatorUserView | None)."""
    return [
        (
            CoordinatorConsultationView.model_validate(consultation),
            CoordinatorUserView.model_validate(user) if user is not None else None,
        )
        for consultation, user in rows
    ]


def consultation_user_user_triples(
    rows: Sequence[tuple[object, object, object]],
) -> list[
    tuple[CoordinatorConsultationView, CoordinatorUserView, CoordinatorUserView | None]
]:
    """(Consultation, patient_user, doctor_user_or_none) -> all three serialized."""
    return [
        (
            CoordinatorConsultationView.model_validate(consultation),
            CoordinatorUserView.model_validate(patient_user),
            CoordinatorUserView.model_validate(doctor_user)
            if doctor_user is not None
            else None,
        )
        for consultation, patient_user, doctor_user in rows
    ]
