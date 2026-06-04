"""Admin-portal repository — platform-wide aggregation queries for super admin.

All functions are read-only except update_doctor_status and update_doctor_revenue_share.
No patient PHI is returned in aggregated views — individual patient access is scoped
to detail pages and always audit-logged by the caller.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ConsultationStatus, DoctorStatus, LabReportStatus, UserRole
from app.models.clinic import Consultation, LabReport, Patient
from app.models.doctor import Doctor
from app.models.identity import User

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
