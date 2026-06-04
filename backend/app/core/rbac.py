from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext, write_audit
from app.core.security import decode_access_token
from app.db.enums import UserRole
from app.db.session import get_db

T = TypeVar("T")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


async def get_current_user(
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
    return user


def enforce_role(*allowed: UserRole) -> Callable[..., Any]:
    async def dep(user: object = Depends(get_current_user)) -> object:
        from app.models.identity import User as UserModel

        assert isinstance(user, UserModel)
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return dep


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
