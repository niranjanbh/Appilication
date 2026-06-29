"""Staff account creation — shared by the CLI bootstrap script and the
super-admin portal form. Staff accounts never come from public signup.

Roles handled: super_admin, admin (read-only portal tier), coordinator
(Coordinator profile row), doctor (Doctor profile row, NMC required).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext, write_audit
from app.core.security import hash_password
from app.db.enums import CoordinatorStatus, DoctorStatus, UserRole
from app.models.admin import Coordinator
from app.models.doctor import Doctor
from app.models.identity import User

logger = structlog.get_logger(__name__)

STAFF_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.COORDINATOR,
    UserRole.DOCTOR,
)


class StaffServiceError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


@dataclass
class StaffCreateResult:
    user: User
    created: bool  # False = existing same-role account was updated
    profile_note: str


async def reset_staff_password(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    user_id: uuid.UUID,
    password: str,
) -> User:
    """Set a new password on a staff account (super-admin action, fresh auth).

    Raises StaffServiceError:
      user_not_found    — no active user with this id
      not_a_staff_role  — target is a patient (OTP login; no admin-set passwords)
    """
    user = await db.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if user is None:
        raise StaffServiceError("user_not_found")
    if user.role not in STAFF_ROLES:
        raise StaffServiceError("not_a_staff_role")

    user.password_hash = hash_password(password)
    await db.flush()

    await write_audit(
        db,
        ctx,
        action="staff_password_reset",
        resource_type="user",
        resource_id=user.id,
        allowed=True,
        log_metadata={"role": user.role.value},
    )
    logger.info("staff_password_reset", role=user.role.value, user_id=str(user.id))
    return user


async def revoke_staff_sessions(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    user_id: uuid.UUID,
) -> dict[str, int]:
    """Force-kill every live session for a staff account (super-admin action).

    Revokes both JWT refresh-token families and admin/coordinator portal session
    cookies (staff-rbac-spec §1).

    Raises StaffServiceError:
      user_not_found    — no active user with this id
      not_a_staff_role  — target is a patient
    """
    from app.adminui.deps import revoke_all_portal_sessions_for_user
    from app.repositories import auth as auth_repo

    user = await db.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if user is None:
        raise StaffServiceError("user_not_found")
    if user.role not in STAFF_ROLES:
        raise StaffServiceError("not_a_staff_role")

    import asyncio

    jwt_sessions_revoked = await auth_repo.revoke_all_for_user(db, user.id)
    portal_sessions_revoked = await asyncio.to_thread(
        revoke_all_portal_sessions_for_user, user.id
    )

    await write_audit(
        db,
        ctx,
        action="force_session_revoke",
        resource_type="user",
        resource_id=user.id,
        allowed=True,
        log_metadata={
            "role": user.role.value,
            "jwt_sessions_revoked": jwt_sessions_revoked,
            "portal_sessions_revoked": portal_sessions_revoked,
        },
    )
    logger.info(
        "force_session_revoke",
        role=user.role.value,
        user_id=str(user.id),
        jwt_sessions_revoked=jwt_sessions_revoked,
        portal_sessions_revoked=portal_sessions_revoked,
    )
    return {
        "jwt_sessions_revoked": jwt_sessions_revoked,
        "portal_sessions_revoked": portal_sessions_revoked,
    }


async def create_staff_user(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    role: UserRole,
    name: str,
    email: str,
    phone: str,
    password: str,
    employee_id: str | None = None,
    nmc: str | None = None,
    state_council: str | None = None,
    specialty: list[str] | None = None,
    languages: list[str] | None = None,
    activate_doctor: bool = False,
) -> StaffCreateResult:
    """Create or update a staff account. Idempotent by phone within one role.

    Raises StaffServiceError:
      not_a_staff_role  — role is patient or unknown
      nmc_required      — doctor without an NMC number
      phone_role_conflict — phone belongs to a user with a different role
      email_in_use      — email belongs to a different account
    """
    if role not in STAFF_ROLES:
        raise StaffServiceError("not_a_staff_role")
    if role == UserRole.DOCTOR and not nmc:
        raise StaffServiceError("nmc_required")

    # Exclude soft-deleted accounts so they neither block new accounts nor get
    # silently revived/overwritten.
    user = await db.scalar(
        select(User).where(User.phone == phone, User.deleted_at.is_(None))
    )
    if user is not None and user.role != role:
        raise StaffServiceError(
            "phone_role_conflict",
            f"{phone} already belongs to a '{user.role.value}' account",
        )

    # Check ALL rows (including soft-deleted) — the DB unique constraint on email
    # covers every row regardless of deleted_at, so a soft-deleted account holding
    # this email would still cause an IntegrityError on INSERT.
    email_owner = await db.scalar(select(User).where(User.email == email))
    if email_owner is not None and (user is None or email_owner.id != user.id):
        raise StaffServiceError("email_in_use", f"{email} belongs to another account")

    # Pre-check NMC uniqueness before flush to give a friendly error instead of
    # an IntegrityError 500 when a duplicate NMC is submitted.
    if role == UserRole.DOCTOR and nmc:
        existing_nmc = await db.scalar(
            select(Doctor).where(Doctor.nmc_registration_number == nmc)
        )
        if existing_nmc is not None and existing_nmc.user_id != (user.id if user else None):
            raise StaffServiceError("nmc_in_use", f"NMC {nmc} is already registered")

    created = user is None
    if user is None:
        user = User(
            name=name,
            role=role,
            phone=phone,
            email=email,
            password_hash=hash_password(password),
            phone_verified=True,  # staff skip the patient OTP flow
        )
        db.add(user)
        await db.flush()
    else:
        user.name = name
        user.email = email
        user.password_hash = hash_password(password)
        user.phone_verified = True
        await db.flush()

    profile_note = ""
    if role == UserRole.COORDINATOR:
        coordinator = await db.scalar(
            select(Coordinator).where(Coordinator.user_id == user.id)
        )
        if coordinator is None:
            db.add(
                Coordinator(
                    user_id=user.id,
                    status=CoordinatorStatus.ACTIVE,
                    employee_id=employee_id or f"COORD-{phone[-4:]}",
                )
            )
            await db.flush()
            profile_note = "Coordinator profile created."
        else:
            profile_note = "Coordinator profile already exists."

    elif role == UserRole.DOCTOR:
        assert nmc is not None  # enforced above (nmc_required)
        doctor = await db.scalar(select(Doctor).where(Doctor.user_id == user.id))
        if doctor is None:
            db.add(
                Doctor(
                    user_id=user.id,
                    nmc_registration_number=nmc,
                    nmc_state_council=state_council,
                    specialty=specialty or [],
                    consultation_languages=languages or ["en"],
                    status=DoctorStatus.ACTIVE if activate_doctor else DoctorStatus.APPLIED,
                    verified_at=datetime.now(UTC) if activate_doctor else None,
                )
            )
            await db.flush()
            profile_note = (
                "Doctor profile created "
                + ("(active)." if activate_doctor else
                   "(status 'applied' — verify and activate via /admin/doctors).")
            )
        else:
            profile_note = "Doctor profile already exists (status unchanged)."

    await write_audit(
        db,
        ctx,
        action="staff_user_created" if created else "staff_user_updated",
        resource_type="user",
        resource_id=user.id,
        allowed=True,
        log_metadata={"role": role.value},
    )
    logger.info(
        "staff_user_created" if created else "staff_user_updated",
        role=role.value,
        user_id=str(user.id),
    )
    return StaffCreateResult(user=user, created=created, profile_note=profile_note)
