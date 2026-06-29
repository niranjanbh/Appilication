"""Re-export all ORM models so Alembic autogenerate sees every table."""

from app.models.admin import (
    Coordinator,
    DailyMetric,
    Followup,
    PatientInteraction,
    PlatformSetting,
    StaffMfa,
    StaffRole,
)
from app.models.audit import AuditLog
from app.models.clinic import (
    Consultation,
    DoctorNote,
    LabOrder,
    LabReport,
    MedicationCatalog,
    Patient,
    PreConsultationReport,
    Prescription,
    PrescriptionItem,
)
from app.models.consent import ConsentRecord, DataSubjectRequest
from app.models.doctor import Availability, Credential, Doctor
from app.models.education import EducationAssignment, EducationContent
from app.models.identity import RefreshToken, User
from app.models.notifications import Notification
from app.models.payment import Payment, Refund
from app.models.pricing import Coupon, PricingConfig
from app.models.public import BookingInquiry, Lead
from app.models.sign_off import SignOffRecord
from app.models.wellness import HealthDatapoint, HealthSyncSession, Reminder, ReminderLog, SymptomCheckIn

__all__ = [
    "AuditLog",
    "Availability",
    "BookingInquiry",
    "ConsentRecord",
    "Consultation",
    "Coordinator",
    "Coupon",
    "Credential",
    "DailyMetric",
    "DataSubjectRequest",
    "Doctor",
    "DoctorNote",
    "EducationAssignment",
    "EducationContent",
    "Followup",
    "HealthDatapoint",
    "HealthSyncSession",
    "LabOrder",
    "LabReport",
    "Lead",
    "MedicationCatalog",
    "Notification",
    "Patient",
    "PatientInteraction",
    "Payment",
    "PlatformSetting",
    "PreConsultationReport",
    "Prescription",
    "PrescriptionItem",
    "PricingConfig",
    "RefreshToken",
    "Refund",
    "Reminder",
    "ReminderLog",
    "SignOffRecord",
    "SymptomCheckIn",
    "StaffMfa",
    "StaffRole",
    "User",
]
