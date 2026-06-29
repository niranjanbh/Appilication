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

from sqlalchemy import ColumnElement, func, or_, select, update
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


_STAFF_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.COORDINATOR,
    UserRole.DOCTOR,
)


async def list_staff(
    db: AsyncSession,
    *,
    role_filter: str | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[User], int]:
    """List staff users (admin/super_admin/coordinator/doctor primary roles)."""
    base = select(User).where(
        User.deleted_at.is_(None), User.role.in_(_STAFF_ROLES)
    )
    if role_filter:
        try:
            role = UserRole(role_filter)
        except ValueError:
            role = None
        if role in _STAFF_ROLES:
            base = base.where(User.role == role)

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

    # Backfill any open consultations that were created before an active
    # coordinator existed (coordinator_id IS NULL). Without this, a patient
    # whose consultation was submitted when no coordinator was on duty remains
    # invisible in the coordinator's queue even after assignment.
    if coordinator_id is not None:
        await db.execute(
            update(Consultation)
            .where(
                Consultation.patient_id == patient_id,
                Consultation.coordinator_id.is_(None),
                Consultation.status.in_([
                    ConsultationStatus.REQUESTED,
                    ConsultationStatus.SCHEDULED,
                ]),
                Consultation.deleted_at.is_(None),
            )
            .values(coordinator_id=coordinator_id)
        )

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
    result: Payment | None = await db.scalar(select(Payment).where(Payment.id == payment_id))
    return result


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


async def list_active_doctors(
    db: AsyncSession, *, limit: int = 200
) -> list[tuple[Doctor, User]]:
    """Return (Doctor, User) pairs for ACTIVE doctors — for on-demand select menus."""
    rows = await db.execute(
        select(Doctor, User)
        .join(User, User.id == Doctor.user_id)
        .where(
            Doctor.deleted_at.is_(None),
            User.deleted_at.is_(None),
            Doctor.status == DoctorStatus.ACTIVE,
        )
        .order_by(User.name)
        .limit(limit)
    )
    return [(row.Doctor, row.User) for row in rows]


async def search_patients(
    db: AsyncSession, *, query: str, limit: int = 20
) -> list[tuple[Patient, User]]:
    """Return (Patient, User) pairs matching a name or Kyros-ID substring.

    Backs the admin on-demand patient typeahead — scales past a fixed dropdown.
    A blank query returns nothing (the menu shows a 'type to search' prompt).
    """
    term = query.strip()
    if not term:
        return []
    like = f"%{term.lower()}%"
    rows = await db.execute(
        select(Patient, User)
        .join(User, User.id == Patient.user_id)
        .where(
            Patient.deleted_at.is_(None),
            User.deleted_at.is_(None),
            or_(
                func.lower(User.name).like(like),
                func.lower(Patient.kyros_patient_id).like(like),
            ),
        )
        .order_by(User.name)
        .limit(limit)
    )
    return [(row.Patient, row.User) for row in rows]


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


# ── Doctor lifecycle state machine ───────────────────────────────────────────────
#
# Single source of truth for doctor credentialing transitions, shared by the REST
# admin router (POST /v1/admin/doctors/{id}/advance|suspend|reactivate) and the
# Jinja admin portal. Forward pipeline runs application_received → … → active;
# active↔suspended are lateral moves.

# Forward-pipeline transitions only (one step at a time).
ADVANCE_TRANSITIONS: dict[DoctorStatus, DoctorStatus] = {
    DoctorStatus.APPLIED: DoctorStatus.DOCUMENTS_SUBMITTED,
    DoctorStatus.DOCUMENTS_SUBMITTED: DoctorStatus.VERIFIED,
    DoctorStatus.VERIFIED: DoctorStatus.ONBOARDING,
    DoctorStatus.ONBOARDING: DoctorStatus.ACTIVE,
}

SUSPEND_FROM: frozenset[DoctorStatus] = frozenset(
    {DoctorStatus.ACTIVE, DoctorStatus.INACTIVE}
)
REACTIVATE_FROM: frozenset[DoctorStatus] = frozenset(
    {DoctorStatus.SUSPENDED, DoctorStatus.INACTIVE}
)


def next_advance_status(current: DoctorStatus) -> DoctorStatus | None:
    """The single forward-pipeline target from ``current``, or None if terminal."""
    return ADVANCE_TRANSITIONS.get(current)


def can_suspend(current: DoctorStatus) -> bool:
    return current in SUSPEND_FROM


def can_reactivate(current: DoctorStatus) -> bool:
    return current in REACTIVATE_FROM


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
) -> tuple[list[tuple[Consultation, User, User | None]], int]:
    """Return (Consultation, patient_user, doctor_user) triples."""
    from sqlalchemy.orm import aliased

    PatientUser = aliased(User, name="patient_user")  # noqa: N806 (aliased ORM entity, used class-like)
    DoctorUser = aliased(User, name="doctor_user")  # noqa: N806 (aliased ORM entity, used class-like)

    base_filter: list[ColumnElement[bool]] = [
        Consultation.deleted_at.is_(None),
        Patient.deleted_at.is_(None),
    ]
    if doctor_id:
        base_filter.append(Consultation.doctor_id == doctor_id)
    if status_filter:
        try:
            base_filter.append(Consultation.status == ConsultationStatus(status_filter))
        except ValueError:
            pass
    if date_from:
        base_filter.append(Consultation.scheduled_start_at >= date_from)

    count_base = (
        select(func.count())
        .select_from(Consultation)
        .join(Patient, Patient.id == Consultation.patient_id)
        .where(*base_filter)
    )
    total: int = (await db.execute(count_base)).scalar_one()

    query = (
        select(Consultation, PatientUser, DoctorUser)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(PatientUser, PatientUser.id == Patient.user_id)
        # Left join: `requested` consultations have no doctor yet (doctor_id is
        # NULL until a coordinator assigns one). An inner join here would drop
        # every unassigned request from the admin list.
        .outerjoin(Doctor, Doctor.id == Consultation.doctor_id)
        .outerjoin(DoctorUser, DoctorUser.id == Doctor.user_id)
        .where(*base_filter)
        .order_by(Consultation.scheduled_start_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = await db.execute(query)
    triples: list[tuple[Consultation, User, User | None]] = [
        (row[0], row[1], row[2]) for row in rows
    ]
    return triples, total


# ── Doctor credential management ───────────────────────────────────────────────


async def get_credentials_for_doctor(
    db: AsyncSession, *, doctor_id: uuid.UUID
) -> list[Any]:
    from app.models.doctor import Credential

    result = await db.execute(
        select(Credential)
        .where(Credential.doctor_id == doctor_id)
        .order_by(Credential.created_at)
    )
    return list(result.scalars().all())


async def verify_credential(
    db: AsyncSession,
    *,
    credential_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> Any | None:
    from sqlalchemy import update as sa_update

    from app.models.doctor import Credential

    result = await db.execute(
        sa_update(Credential)
        .where(Credential.id == credential_id)
        .values(verified_by_admin_id=admin_user_id, updated_at=datetime.now(UTC))
        .returning(Credential)
    )
    return result.scalar_one_or_none()


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


# ── Bulk fetch-by-ids (CSV export of a selected subset) ──────────────────────────
# These power "Export selected" — the caller passes the checked row ids and we
# return the matching rows in the same tuple shape the list functions use. A
# 30-row page is the upper bound on selection size, so an IN(...) is safe.


async def get_users_by_ids(
    db: AsyncSession, ids: list[uuid.UUID]
) -> list[User]:
    if not ids:
        return []
    rows = await db.execute(
        select(User)
        .where(User.id.in_(ids), User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
    )
    return list(rows.scalars().all())


async def get_doctors_by_ids(
    db: AsyncSession, ids: list[uuid.UUID]
) -> list[tuple[Doctor, User]]:
    if not ids:
        return []
    rows = await db.execute(
        select(Doctor, User)
        .join(User, User.id == Doctor.user_id)
        .where(
            Doctor.id.in_(ids),
            Doctor.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
        .order_by(Doctor.created_at.desc())
    )
    return [(row.Doctor, row.User) for row in rows]


async def get_consultations_by_ids(
    db: AsyncSession, ids: list[uuid.UUID]
) -> list[tuple[Consultation, User, User | None]]:
    if not ids:
        return []
    from sqlalchemy.orm import aliased

    PatientUser = aliased(User, name="patient_user")  # noqa: N806 (aliased ORM entity, used class-like)
    DoctorUser = aliased(User, name="doctor_user")  # noqa: N806 (aliased ORM entity, used class-like)
    rows = await db.execute(
        select(Consultation, PatientUser, DoctorUser)
        .join(Patient, Patient.id == Consultation.patient_id)
        .join(PatientUser, PatientUser.id == Patient.user_id)
        .outerjoin(Doctor, Doctor.id == Consultation.doctor_id)
        .outerjoin(DoctorUser, DoctorUser.id == Doctor.user_id)
        .where(Consultation.id.in_(ids), Consultation.deleted_at.is_(None))
        .order_by(Consultation.scheduled_start_at.desc())
    )
    return [(row[0], row[1], row[2]) for row in rows]


async def get_payments_by_ids(
    db: AsyncSession, ids: list[uuid.UUID]
) -> list[tuple[Payment, User]]:
    if not ids:
        return []
    rows = await db.execute(
        select(Payment, User)
        .join(User, User.id == Payment.user_id)
        .where(Payment.id.in_(ids))
        .order_by(Payment.created_at.desc())
    )
    return [(row.Payment, row.User) for row in rows]


async def get_staff_by_ids(
    db: AsyncSession, ids: list[uuid.UUID]
) -> list[User]:
    if not ids:
        return []
    rows = await db.execute(
        select(User)
        .where(
            User.id.in_(ids),
            User.deleted_at.is_(None),
            User.role.in_(_STAFF_ROLES),
        )
        .order_by(User.created_at.desc())
    )
    return list(rows.scalars().all())
