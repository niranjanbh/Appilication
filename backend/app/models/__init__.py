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
from app.models.payment import Payment
from app.models.public import BookingInquiry, Lead
from app.models.wellness import HealthDatapoint, HealthSyncSession, Reminder, ReminderLog

__all__ = [
    "AuditLog",
    "Availability",
    "BookingInquiry",
    "ConsentRecord",
    "Consultation",
    "Coordinator",
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
    "Notification",
    "Patient",
    "PatientInteraction",
    "Payment",
    "PlatformSetting",
    "PreConsultationReport",
    "Prescription",
    "PrescriptionItem",
    "RefreshToken",
    "Reminder",
    "ReminderLog",
    "StaffMfa",
    "StaffRole",
    "User",
]
