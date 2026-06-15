"""Unit tests for the staff permission model (pure — no DB)."""

from __future__ import annotations

from app.core.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    acting_role_for,
    permissions_for_roles,
)
from app.db.enums import UserRole


def test_single_role_resolves_to_its_bundle() -> None:
    assert permissions_for_roles(frozenset({UserRole.DOCTOR})) == ROLE_PERMISSIONS[UserRole.DOCTOR]


def test_multi_role_resolves_to_union() -> None:
    both = frozenset({UserRole.DOCTOR, UserRole.SUPER_ADMIN})
    perms = permissions_for_roles(both)
    # Holds clinical (from doctor) AND admin-only (from super_admin) permissions.
    assert Permission.PRESCRIPTION_CREATE in perms
    assert Permission.STAFF_MANAGE in perms
    assert perms == ROLE_PERMISSIONS[UserRole.DOCTOR] | ROLE_PERMISSIONS[UserRole.SUPER_ADMIN]


def test_coordinator_deny_list_excludes_clinical_permissions() -> None:
    """The §4 deny-list, expressed as the ABSENCE of clinical permissions."""
    coord = permissions_for_roles(frozenset({UserRole.COORDINATOR}))
    assert Permission.PATIENT_READ_REDACTED in coord
    assert not any(
        p.startswith("clinical_note:") or p.startswith("prescription:") for p in coord
    )


def test_patient_holds_no_staff_permissions() -> None:
    assert permissions_for_roles(frozenset({UserRole.PATIENT})) == frozenset()


def test_acting_role_clinical_precedence() -> None:
    """A doctor-admin signs a prescription *as the RMP* — clinical role wins."""
    both = frozenset({UserRole.DOCTOR, UserRole.SUPER_ADMIN})
    assert acting_role_for(both, Permission.PRESCRIPTION_CREATE) == UserRole.DOCTOR


def test_acting_role_admin_only_permission() -> None:
    """An admin-only permission (doctor lacks it) stamps the admin role."""
    both = frozenset({UserRole.DOCTOR, UserRole.SUPER_ADMIN})
    assert acting_role_for(both, Permission.STAFF_MANAGE) == UserRole.SUPER_ADMIN


def test_acting_role_none_when_unheld() -> None:
    assert acting_role_for(frozenset({UserRole.COORDINATOR}), Permission.PRESCRIPTION_SIGN) is None
