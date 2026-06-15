from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext, write_audit
from app.core.permissions import Permission, acting_role_for, permissions_for_roles
from app.core.security import audience_for_role, decode_access_token
from app.db.enums import ActorRole, UserRole
from app.db.session import get_db

T = TypeVar("T")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> object:
    from app.models.identity import User
    from app.repositories import users as users_repo

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_access_token(token)
    user: User | None = await users_repo.get_by_id(db, uuid.UUID(claims.sub))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user_not_found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Stamp actor identity for the PHI-access audit middleware (P33) — set as soon as a
    # user is resolved, so downstream denials (audience mismatch, MFA, role/permission)
    # can be attributed to an actor even though they raise before any handler runs.
    request.state.actor_user_id = user.id
    request.state.actor_role = ActorRole(user.role.value)
    # Validate against the user's *current* role, not just the claim — a role change
    # (e.g. patient promoted to staff) invalidates outstanding tokens for the old
    # audience (staff-rbac-spec §1).
    if claims.aud != audience_for_role(user.role):
        request.state.deny_reason = "audience_mismatch"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="audience_mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.mfa_verified = claims.mfa
    return user


async def require_mfa(request: Request, user: object = Depends(get_current_user)) -> object:
    if not getattr(request.state, "mfa_verified", False):
        request.state.deny_reason = "mfa_required"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="mfa_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def enforce_role(*allowed: UserRole) -> Callable[..., Any]:
    async def dep(request: Request, user: object = Depends(get_current_user)) -> object:
        from app.models.identity import User as UserModel

        assert isinstance(user, UserModel)
        if user.role not in allowed:
            request.state.deny_reason = "forbidden"
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return dep


def require_permission(*needed: Permission) -> Callable[..., Any]:
    """Authorize by permission (staff-rbac-spec §1), not by flat role.

    Resolves the caller's permissions as the union of their primary ``users.role``
    and any additional staff roles, then 403s if a required permission is absent.
    Stashes the role-context the action was taken under and the permission
    exercised on ``request.state`` so the handler's audit write can stamp them.

    Returns the authenticated ``User`` (same shape as ``enforce_role``), so handlers
    keep their ``assert isinstance(user, UserModel)`` pattern.
    """

    async def dep(
        request: Request,
        user: object = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> object:
        from app.models.identity import User as UserModel
        from app.repositories import staff_roles as staff_roles_repo

        assert isinstance(user, UserModel)

        additional = await staff_roles_repo.list_roles_for_user(db, user.id)
        roles_held = frozenset({user.role, *additional})
        granted = permissions_for_roles(roles_held)

        if any(perm not in granted for perm in needed):
            if needed:
                request.state.permission = needed[0].value
            request.state.deny_reason = "forbidden"
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        # Stamp the acting role + exercised permission for the handler's audit row.
        if needed:
            primary = needed[0]
            acting = acting_role_for(roles_held, primary)
            request.state.role_context = acting.value if acting else None
            request.state.permission = primary.value
        return user

    return dep


def permission_audit_fields(request: Request) -> tuple[str | None, str | None]:
    """(role_context, permission) stamped by require_permission, for AuditContext."""
    return (
        getattr(request.state, "role_context", None),
        getattr(request.state, "permission", None),
    )


async def cross_user_404[T](
    db: AsyncSession,
    resource: T | None,
    ctx: AuditContext,
    *,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
) -> T:
    """Commit a denial audit entry and raise 404 if resource is None.

    Commits before raising so the denial is recorded even when the outer
    transaction later rolls back (e.g. on test teardown).
    Returns resource unchanged when it is not None.
    """
    if resource is None:
        await write_audit(
            db,
            ctx,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return resource


# Pre-built role dependencies — import these in routers instead of calling enforce_role inline.
get_patient_user = enforce_role(UserRole.PATIENT)
get_doctor_user = enforce_role(UserRole.DOCTOR)
get_coordinator_user = enforce_role(UserRole.COORDINATOR)
get_admin_user = enforce_role(UserRole.SUPER_ADMIN)
get_staff_user = enforce_role(UserRole.DOCTOR, UserRole.COORDINATOR, UserRole.SUPER_ADMIN)
get_any_staff_user = enforce_role(
    UserRole.DOCTOR, UserRole.COORDINATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN
)
