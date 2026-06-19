"""Staff permission model — the contract the staff-RBAC track composes against.

Roles are permission bundles, not identities (staff-rbac-spec §1). Permissions are
granular ``resource:action[:scope]`` values, composed into per-role bundles. A
staff member holding several roles resolves to the **union** of their bundles, and
every authorized action is stamped with the role-context it was taken under.

This module is pure (no DB, no FastAPI). The DB-aware resolver and the enforcement
dependency live in ``app/core/rbac.py``; additional roles are read via
``app/repositories/staff_roles.py``.
"""

from __future__ import annotations

import enum

from app.db.enums import UserRole


class Permission(enum.StrEnum):
    # Patient data, scoped
    PATIENT_READ_ASSIGNED = "patient:read:assigned"
    PATIENT_READ_REDACTED = "patient:read:redacted"
    PATIENT_READ_ALL = "patient:read:all"

    # Consultations
    CONSULTATION_READ_ASSIGNED = "consultation:read:assigned"
    CONSULTATION_TRANSITION = "consultation:transition"

    # Clinical artifacts (doctor-only)
    CLINICAL_NOTE_READ = "clinical_note:read"
    CLINICAL_NOTE_WRITE = "clinical_note:write"
    PRESCRIPTION_CREATE = "prescription:create"
    PRESCRIPTION_SIGN = "prescription:sign"
    CARE_PLAN_CREATE = "care_plan:create"
    CARE_PLAN_ACTIVATE = "care_plan:activate"

    # Content sign-off / publication (separation of duties)
    CONTENT_APPROVE = "content:approve"
    CONTENT_PUBLISH = "content:publish"

    # Admin / compliance / ops
    AUDIT_READ = "audit:read"
    STAFF_MANAGE = "staff:manage"
    ROLE_ASSIGN = "role:assign"
    PAYOUT_COMPUTE = "payout:compute"
    PRICING_MANAGE = "pricing:manage"
    DSR_PROCESS = "dsr:process"


# ── Role → permission bundles ────────────────────────────────────────────────
#
# Encode the spec boundaries precisely. The coordinator bundle is the §4 deny-list
# expressed as ABSENCE: it gets patient:read:redacted and must never contain
# clinical_note:* or prescription:* — enforced and tested.

_DOCTOR: frozenset[Permission] = frozenset(
    {
        Permission.PATIENT_READ_ASSIGNED,
        Permission.CONSULTATION_READ_ASSIGNED,
        Permission.CONSULTATION_TRANSITION,
        Permission.CLINICAL_NOTE_READ,
        Permission.CLINICAL_NOTE_WRITE,
        Permission.PRESCRIPTION_CREATE,
        Permission.PRESCRIPTION_SIGN,
        Permission.CARE_PLAN_CREATE,
        Permission.CARE_PLAN_ACTIVATE,
        Permission.CONTENT_APPROVE,
    }
)

_COORDINATOR: frozenset[Permission] = frozenset(
    {
        Permission.PATIENT_READ_REDACTED,
        Permission.CONSULTATION_READ_ASSIGNED,
    }
)

# Read-only admin tier: can view, cannot change state.
_ADMIN: frozenset[Permission] = frozenset(
    {
        Permission.PATIENT_READ_ALL,
        Permission.CONSULTATION_READ_ASSIGNED,
        Permission.AUDIT_READ,
    }
)

# Full admin: everything the read-only tier sees, plus every state-changing power.
_SUPER_ADMIN: frozenset[Permission] = _ADMIN | frozenset(
    {
        Permission.CONTENT_PUBLISH,
        Permission.STAFF_MANAGE,
        Permission.ROLE_ASSIGN,
        Permission.PAYOUT_COMPUTE,
        Permission.PRICING_MANAGE,
        Permission.DSR_PROCESS,
    }
)

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.PATIENT: frozenset(),
    UserRole.DOCTOR: _DOCTOR,
    UserRole.COORDINATOR: _COORDINATOR,
    UserRole.ADMIN: _ADMIN,
    UserRole.SUPER_ADMIN: _SUPER_ADMIN,
}

# Precedence for role-context stamping: the clinical role wins for clinical
# permissions, so a doctor-admin signs a prescription *as the RMP*. Admin-only
# permissions (which a doctor does not hold) fall through to the admin role.
_ROLE_CONTEXT_PRECEDENCE: tuple[UserRole, ...] = (
    UserRole.DOCTOR,
    UserRole.COORDINATOR,
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.PATIENT,
)


def permissions_for_roles(roles: frozenset[UserRole]) -> frozenset[Permission]:
    """Union of the permission bundles for every role held."""
    result: frozenset[Permission] = frozenset()
    for role in roles:
        result |= ROLE_PERMISSIONS.get(role, frozenset())
    return result


def acting_role_for(
    roles: frozenset[UserRole], permission: Permission
) -> UserRole | None:
    """Return the role-context a permission is exercised under.

    The first role in precedence order that both is held and grants the
    permission. None if no held role grants it (the caller would already be
    raising 403).
    """
    for role in _ROLE_CONTEXT_PRECEDENCE:
        if role in roles and permission in ROLE_PERMISSIONS.get(role, frozenset()):
            return role
    return None
