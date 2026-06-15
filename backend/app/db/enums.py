from __future__ import annotations

import enum
from typing import Any


def enum_values(enum_cls: type[enum.Enum]) -> list[Any]:
    """Return the .value of each member — used as SAEnum values_callable.

    SQLAlchemy defaults to using Python enum .name (uppercase) as the
    Postgres enum value.  Our Postgres enums use lowercase values that match
    StrEnum .value, so we need this callable to fix the mapping.
    """
    return [e.value for e in enum_cls]


class UserRole(enum.StrEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    COORDINATOR = "coordinator"
    # Read-only tier of the admin portal: can view, cannot change state.
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class OtpResetChannel(enum.StrEnum):
    """Channel used to deliver a password-reset OTP. Admin-controlled per user;
    falls back to the platform default when unset on the user record."""

    EMAIL = "email"
    SMS = "sms"


class UserGender(enum.StrEnum):
    FEMALE = "female"
    MALE = "male"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class ConsentType(enum.StrEnum):
    TERMS = "terms"
    PRIVACY = "privacy"
    TELEMEDICINE = "telemedicine"
    DATA_PROCESSING = "data_processing"
    HEALTH_SYNC = "health_sync"
    MARKETING = "marketing"
    RECORDING = "recording"
    RESEARCH = "research"


class DataSubjectRequestType(enum.StrEnum):
    ACCESS = "access"
    CORRECTION = "correction"
    ERASURE = "erasure"
    GRIEVANCE = "grievance"


class DataSubjectRequestStatus(enum.StrEnum):
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ActorRole(enum.StrEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    COORDINATOR = "coordinator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    SYSTEM = "system"


class AppEnv(enum.StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ReminderType(enum.StrEnum):
    WATER = "water"
    SUPPLEMENT = "supplement"
    MEDICATION = "medication"
    GYM = "gym"
    CUSTOM = "custom"


class ReminderAction(enum.StrEnum):
    TAKEN = "taken"
    SKIPPED = "skipped"
    SNOOZED = "snoozed"
    MISSED = "missed"


class HealthSyncSource(enum.StrEnum):
    APPLE_HEALTH = "apple_health"
    GOOGLE_HEALTH_CONNECT = "google_health_connect"


class HealthDatapointSource(enum.StrEnum):
    APPLE_HEALTH = "apple_health"
    GOOGLE_HEALTH_CONNECT = "google_health_connect"
    MANUAL = "manual"


class HealthDatapointType(enum.StrEnum):
    STEPS = "steps"
    HEART_RATE = "heart_rate"
    RESTING_HEART_RATE = "resting_heart_rate"
    HRV = "hrv"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_QUALITY = "sleep_quality"
    WEIGHT = "weight"
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"
    BLOOD_GLUCOSE = "blood_glucose"
    WORKOUT = "workout"
    ACTIVE_CALORIES = "active_calories"


class HealthSyncStatus(enum.StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


# ── Clinic domain ──────────────────────────────────────────────────────────────


class ConditionCategory(enum.StrEnum):
    THYROID = "thyroid"
    WEIGHT = "weight"
    PCOS = "pcos"
    SKIN_HAIR = "skin_hair"
    MENS_INTIMATE = "mens_intimate"
    HORMONES_TRT = "hormones_trt"
    LONGEVITY = "longevity"


class DoctorStatus(enum.StrEnum):
    APPLIED = "applied"
    DOCUMENTS_SUBMITTED = "documents_submitted"
    VERIFIED = "verified"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class AvailabilityStatus(enum.StrEnum):
    AVAILABLE = "available"
    BOOKED = "booked"
    BLOCKED = "blocked"


class CredentialType(enum.StrEnum):
    MBBS = "mbbs"
    MD = "md"
    DNB = "dnb"
    DM = "dm"
    MCH = "mch"
    FELLOWSHIP = "fellowship"
    CERTIFICATION = "certification"


class CoordinatorStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


# ── Consultations ──────────────────────────────────────────────────────────────


class ConsultationStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ConsultationType(enum.StrEnum):
    INITIAL = "initial"
    FOLLOW_UP = "follow_up"


class NoteType(enum.StrEnum):
    CLINICAL = "clinical"
    COORDINATOR_ONLY = "coordinator_only"
    PATIENT_VISIBLE = "patient_visible"
    PRIVATE = "private"


# ── Payments ───────────────────────────────────────────────────────────────────


class PaymentStatus(enum.StrEnum):
    CREATED = "created"
    ATTEMPTED = "attempted"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIAL_REFUNDED = "partial_refunded"


# ── Lab reports ────────────────────────────────────────────────────────────────


class LabReportSource(enum.StrEnum):
    PATIENT_UPLOAD = "patient_upload"
    KYROS_ORDER = "kyros_order"


class LabReportStatus(enum.StrEnum):
    UPLOAD_PENDING = "upload_pending"
    OCR_PENDING = "ocr_pending"
    OCR_PROCESSING = "ocr_processing"
    OCR_COMPLETE = "ocr_complete"
    OCR_FAILED = "ocr_failed"
    PATIENT_REVIEW_NEEDED = "patient_review_needed"


class LabOrderStatus(enum.StrEnum):
    ORDERED = "ordered"
    SAMPLE_COLLECTED = "sample_collected"
    RESULTED = "resulted"
    REVIEWED = "reviewed"
    SUPERSEDED = "superseded"


# ── Prescriptions ──────────────────────────────────────────────────────────────


class PrescriptionStatus(enum.StrEnum):
    DRAFT = "draft"
    SIGNED = "signed"
    DISPENSED = "dispensed"
    CANCELLED = "cancelled"


class DrugForm(enum.StrEnum):
    TABLET = "tablet"
    CAPSULE = "capsule"
    SYRUP = "syrup"
    INJECTION = "injection"
    TOPICAL = "topical"
    OTHER = "other"


# ── Education ──────────────────────────────────────────────────────────────────


class ContentType(enum.StrEnum):
    ARTICLE = "article"
    VIDEO = "video"
    PDF = "pdf"


class ContentStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ── Notifications ──────────────────────────────────────────────────────────────


class NotificationChannel(enum.StrEnum):
    PUSH = "push"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
