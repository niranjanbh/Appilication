"""Admin-portal repository — platform-wide aggregation queries for super admin.

Read queries plus the super-admin state changes (doctor status, user contact,
password reset, coordinator assignment). No patient PHI is returned in
aggregated views — individual patient access is scoped to detail pages and
always audit-logged by the caller.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    ConsultationStatus,
    CoordinatorStatus,
    DoctorStatus,
    LabReportStatus,
    PaymentStatus,
    UserRole,
)
from app.models.admin import Coordinator
from app.models.clinic import Consultation, LabReport, Patient
from app.models.doctor import Doctor
from app.models.identity import User
from app.models.payment import Payment

# ── Dashboard stats ────────────────────────────────────────────────────────────


async def count_users_by_role(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(User.role, func.count().label("n"))
        .where(User.deleted_at.is_(None))
        .group_by(User.role)
    )
    return {row.role.value: row.n for row in result}


async def count_consultations_today(db: AsyncSession) -> int:
    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(
        select(func.count())
        .select_from(Consultation)
        .where(
            Consultation.scheduled_start_at >= day_start,
            Consultation.scheduled_start_at < day_end,
            Consultation.deleted_at.is_(None),
        )
    )
    return result.scalar_one()


async def count_active_doctors(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Doctor)
        .where(Doctor.status == DoctorStatus.ACTIVE, Doctor.deleted_at.is_(None))
    )
    return result.scalar_one()


async def count_pending_ocr(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(LabReport)
        .where(LabReport.status == LabReportStatus.OCR_PENDING)
    )
    return result.scalar_one()


async def count_new_registrations(db: AsyncSession, days: int = 7) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(User.created_at >= cutoff, User.deleted_at.is_(None))
    )
    return result.scalar_one()


# ── User management ────────────────────────────────────────────────────────────


async def list_users(
    db: AsyncSession,
    *,
    search: str | None = None,
    role_filter: str | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[User], int]:
    base = select(User).where(User.deleted_at.is_(None))

    if search:
        term = f"%{search.lower()}%"
        base = base.where(
            or_(
                func.lower(User.name).like(term),
                User.phone.like(term),
                func.lower(func.coalesce(User.email, "")).like(term),
            )
        )
    if role_filter:
        try:
            base = base.where(User.role == UserRole(role_filter))
        except ValueError:
            pass

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(rows.scalars().all()), total


async def get_user_detail(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[User, Doctor | None, Patient | None] | None:
    user_result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        return None

    doctor_result = await db.execute(
        select(Doctor).where(Doctor.user_id == user_id, Doctor.deleted_at.is_(None))
    )
    doctor = doctor_result.scalar_one_or_none()

    patient_result = await db.execute(
        select(Patient).where(Patient.user_id == user_id, Patient.deleted_at.is_(None))
    )
    patient = patient_result.scalar_one_or_none()

    return user, doctor, patient


async def suspend_user(
    db: AsyncSession, user_id: uuid.UUID
) -> User | None:
    from sqlalchemy import update

    result = await db.execute(
        update(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC))
        .returning(User)
    )
    return result.scalar_one_or_none()


async def reactivate_user(
    db: AsyncSession, user_id: uuid.UUID
) -> User | None:
    from sqlalchemy import update

    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(deleted_at=None)
        .returning(User)
    )
    return result.scalar_one_or_none()


async def update_user_contact(
    db: AsyncSession, user_id: uuid.UUID, *, name: str, email: str
) -> User | None:
    """Edit name/email. Phone is deliberately not editable here — it is the
    login key and OTP target; changing it requires a re-verification flow.
    Returns None when the user doesn't exist or the email belongs to another
    account."""
    from sqlalchemy import update

    email_owner = await db.scalar(select(User).where(User.email == email))
    if email_owner is not None and email_owner.id != user_id:
        return None

    result = await db.execute(
        update(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .values(name=name, email=email)
        .returning(User)
    )
    return result.scalar_one_or_none()


# ── Coordinator assignment ─────────────────────────────────────────────────────


async def list_active_coordinators(
    db: AsyncSession,
) -> list[tuple[Coordinator, User]]:
    result = await db.execute(
        select(Coordinator, User)
        .join(User, User.id == Coordinator.user_id)
        .where(
            Coordinator.status == CoordinatorStatus.ACTIVE,
            Coordinator.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
        .order_by(User.name)
    )
    return [(row.Coordinator, row.User) for row in result]


async def assign_patient_coordinator(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    coordinator_id: uuid.UUID | None,
) -> Patient | None:
    """Assign (or unassign, coordinator_id=None) a patient's care coordinator.

    Keeps both sides in sync: kc_patients.assigned_coordinator_id and the
    coordinator's assigned_patient_ids JSONB list (the coordinator portal
    scopes by the latter). Returns None when patient or coordinator is missing.
    """
    patient = await db.scalar(
        select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
    )
    if patient is None:
        return None

    target: Coordinator | None = None
    if coordinator_id is not None:
        target = await db.scalar(
            select(Coordinator).where(
                Coordinator.id == coordinator_id,
                Coordinator.deleted_at.is_(None),
            )
        )
        if target is None:
            return None

    # Remove the patient from every coordinator list that currently holds it.
    pid = str(patient_id)
    holders = await db.scalars(
        select(Coordinator).where(Coordinator.assigned_patient_ids.contains([pid]))
    )
    for holder in holders:
        holder.assigned_patient_ids = [p for p in holder.assigned_patient_ids if p != pid]

    if target is not None and pid not in target.assigned_patient_ids:
        target.assigned_patient_ids = [*target.assigned_patient_ids, pid]

    patient.assigned_coordinator_id = coordinator_id
    await db.flush()
    return patient


# ── Payments ───────────────────────────────────────────────────────────────────


async def list_payments(
    db: AsyncSession,
    *,
    status_filter: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[tuple[Payment, User]], int]:
    """Return (Payment, paying_user) pairs, newest first."""
    base = (
        select(Payment, User)
        .join(User, User.id == Payment.user_id)
    )
    if status_filter:
        try:
            base = base.where(Payment.status == PaymentStatus(status_filter))
        except ValueError:
            pass
    if search:
        term = f"%{search.lower()}%"
        base = base.where(
            or_(
                func.lower(User.name).like(term),
                User.phone.like(term),
                Payment.razorpay_order_id.like(term),
                func.coalesce(Payment.razorpay_payment_id, "").like(term),
            )
        )

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(Payment.created_at.desc()).offset(offset).limit(page_size)
    )
    return [(row.Payment, row.User) for row in rows], total


async def get_payment(db: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    return await db.scalar(select(Payment).where(Payment.id == payment_id))


# ── Doctor management ──────────────────────────────────────────────────────────


async def list_doctors(
    db: AsyncSession,
    *,
    search: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[tuple[Doctor, User]], int]:
    base = (
        select(Doctor, User)
        .join(User, User.id == Doctor.user_id)
        .where(Doctor.deleted_at.is_(None), User.deleted_at.is_(None))
    )

    if search:
        term = f"%{search.lower()}%"
        base = base.where(
            or_(
                func.lower(User.name).like(term),
                Doctor.nmc_registration_number.like(term),
            )
        )
    if status_filter:
        try:
            base = base.where(Doctor.status == DoctorStatus(status_filter))
        except ValueError:
            pass

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(Doctor.created_at.desc()).offset(offset).limit(page_size)
    )
    pairs = [(row.Doctor, row.User) for row in rows]
    return pairs, total


async def get_doctor_detail(
    db: AsyncSession, doctor_id: uuid.UUID
) -> tuple[Doctor, User] | None:
    result = await db.execute(
        select(Doctor, User)
        .join(User, User.id == Doctor.user_id)
        .where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None))
    )
    row = result.first()
    if row is None:
        return None
    return row.Doctor, row.User


async def update_doctor_status(
    db: AsyncSession,
    doctor_id: uuid.UUID,
    new_status: DoctorStatus,
) -> Doctor | None:
    from sqlalchemy import update

    result = await db.execute(
        update(Doctor)
        .where(Doctor.id == doctor_id)
        .values(status=new_status, updated_at=datetime.now(UTC))
        .returning(Doctor)
    )
    return result.scalar_one_or_none()


async def update_doctor_revenue_share(
    db: AsyncSession,
    doctor_id: uuid.UUID,
    revenue_share_pct: Decimal,
) -> Doctor | None:
    from sqlalchemy import update

    result = await db.execute(
        update(Doctor)
        .where(Doctor.id == doctor_id)
        .values(revenue_share_pct=revenue_share_pct, updated_at=datetime.now(UTC))
        .returning(Doctor)
    )
    return result.scalar_one_or_none()


async def update_doctor_profile(
    db: AsyncSession,
    doctor_id: uuid.UUID,
    *,
    bio_short: str | None,
    bio_long: str | None,
    specialty: list[str],
    conditions_treated: list[str],
    consultation_languages: list[str],
) -> Doctor | None:
    from sqlalchemy import update

    result = await db.execute(
        update(Doctor)
        .where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None))
        .values(
            bio_short=bio_short,
            bio_long=bio_long,
            specialty=specialty,
            conditions_treated=conditions_treated,
            consultation_languages=consultation_languages,
            updated_at=datetime.now(UTC),
        )
        .returning(Doctor)
    )
    return result.scalar_one_or_none()


async def count_doctors_by_status(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(Doctor.status, func.count().label("n"))
        .where(Doctor.deleted_at.is_(None))
        .group_by(Doctor.status)
    )
    return {row.status.value: row.n for row in result}


# ── Consultation management ────────────────────────────────────────────────────


async def list_all_consultations(
    db: AsyncSession,
    *,
    doctor_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    date_from: datetime | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[tuple[Consultation, User, User]], int]:
    """Return (Consultation, patient_user, doctor_user) triples."""
    base = (
        select(Consultation, Patient, User)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(Consultation.deleted_at.is_(None), Patient.deleted_at.is_(None))
    )

    if doctor_id:
        base = base.where(Consultation.doctor_id == doctor_id)
    if status_filter:
        try:
            base = base.where(Consultation.status == ConsultationStatus(status_filter))
        except ValueError:
            pass
    if date_from:
        base = base.where(Consultation.scheduled_start_at >= date_from)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(Consultation.scheduled_start_at.desc()).offset(offset).limit(page_size)
    )
    triples: list[tuple[Consultation, User, User]] = []
    for row in rows:
        # Fetch doctor user separately (simple, avoids complex alias join)
        dr_result = await db.execute(
            select(Doctor, User)
            .join(User, User.id == Doctor.user_id)
            .where(Doctor.id == row.Consultation.doctor_id)
        )
        dr_row = dr_result.first()
        doctor_user = dr_row.User if dr_row else None
        triples.append((row.Consultation, row.User, doctor_user))  # type: ignore[arg-type]
    return triples, total


async def get_consultation_detail(
    db: AsyncSession, consultation_id: uuid.UUID
) -> tuple[Consultation, User, User | None] | None:
    """Return (Consultation, patient_user, doctor_user) for one consultation."""
    result = await db.execute(
        select(Consultation, User)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(User, User.id == Patient.user_id)
        .where(Consultation.id == consultation_id, Consultation.deleted_at.is_(None))
    )
    row = result.first()
    if row is None:
        return None
    dr_result = await db.execute(
        select(User)
        .join(Doctor, Doctor.user_id == User.id)
        .where(Doctor.id == row.Consultation.doctor_id)
    )
    return row.Consultation, row.User, dr_result.scalar_one_or_none()


# ── Audit log ──────────────────────────────────────────────────────────────────


async def list_audit_log(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID | None = None,
    action_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Any], int]:
    from app.models.audit import AuditLog

    base = select(AuditLog)

    if actor_id:
        base = base.where(AuditLog.actor_user_id == actor_id)
    if action_filter:
        base = base.where(AuditLog.action.ilike(f"%{action_filter}%"))
    if date_from:
        base = base.where(AuditLog.timestamp >= date_from)
    if date_to:
        base = base.where(AuditLog.timestamp <= date_to)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size)
    )
    return list(rows.scalars().all()), total
