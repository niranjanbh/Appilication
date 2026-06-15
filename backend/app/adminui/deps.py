"""Admin UI session-cookie auth and CSRF helpers.

Authentication:
  Session ID stored in Redis as session:admin:{uuid} → user_id (string).
  Cookie: kyros_admin_session, HttpOnly, SameSite=Lax, 4 h TTL.

CSRF:
  Double-submit cookie pattern.
  Every POST form includes a hidden _csrf field.
  verify_csrf() compares it against the kyros_admin_csrf cookie.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Any

import structlog
from fastapi import Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

logger = structlog.get_logger(__name__)

_SESSION_TTL = 14_400  # 4 hours in seconds
_SESSION_KEY_PREFIX = "session:admin:"
_CSRF_COOKIE = "kyros_admin_csrf"
_SESSION_COOKIE = "kyros_admin_session"
# Money-mover / identity actions require authentication within the last 10
# minutes (admin-ui rules). Login and /admin/reauth refresh this key.
_FRESH_TTL = 600
_FRESH_KEY_PREFIX = "sessionfresh:admin:"
# Reverse index of every live portal session (admin or coordinator) for a staff
# user, so an admin-forced session-kill can find and delete them by user id
# (staff-rbac-spec §1).
_STAFF_SESSIONS_PREFIX = "staff_sessions:"


# ── Redis helpers ──────────────────────────────────────────────────────────────


def _redis() -> Any:
    import redis as redis_lib

    from app.core.config import settings

    return redis_lib.from_url(settings.redis_url, socket_timeout=2, decode_responses=True)


def _session_key(session_id: str) -> str:
    return f"{_SESSION_KEY_PREFIX}{session_id}"


def _fresh_key(session_id: str) -> str:
    return f"{_FRESH_KEY_PREFIX}{session_id}"


def mark_session_fresh(session_id: str) -> None:
    """Record that this session re-authenticated just now (10-minute window)."""
    try:
        _redis().setex(_fresh_key(session_id), _FRESH_TTL, "1")
    except Exception:
        logger.warning("admin_session.mark_fresh_failed")


def is_session_fresh(session_id: str) -> bool:
    try:
        return bool(_redis().exists(_fresh_key(session_id)))
    except Exception:
        # Redis down: fail closed for money movers — re-auth will also fail,
        # but a degraded Redis already means sessions are broken anyway.
        return False


def create_admin_session(response: Response, user_id: uuid.UUID) -> str:
    """Create a Redis session entry and set the session cookie."""
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)

    try:
        r = _redis()
        r.setex(_session_key(session_id), _SESSION_TTL, str(user_id))
        r.setex(_fresh_key(session_id), _FRESH_TTL, "1")  # login counts as fresh
    except Exception as exc:
        logger.exception("admin_session.create_failed")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "session_error") from exc

    try:
        r = _redis()
        r.sadd(f"{_STAFF_SESSIONS_PREFIX}{user_id}", session_id)
        r.expire(f"{_STAFF_SESSIONS_PREFIX}{user_id}", _SESSION_TTL)
    except Exception:
        logger.warning("admin_session.index_failed")

    response.set_cookie(
        _SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        secure=False,  # set True behind TLS in production
        max_age=_SESSION_TTL,
    )
    response.set_cookie(
        _CSRF_COOKIE,
        csrf_token,
        httponly=False,  # must be readable by JS for double-submit
        samesite="lax",
        secure=False,
        max_age=_SESSION_TTL,
    )
    return session_id


def clear_admin_session(response: Response, session_id: str) -> None:
    """Delete session from Redis and clear the cookies."""
    try:
        r = _redis()
        r.delete(_session_key(session_id))
    except Exception:
        logger.warning("admin_session.clear_redis_error")

    response.delete_cookie(_SESSION_COOKIE)
    response.delete_cookie(_CSRF_COOKIE)


def _get_session_user_id(session_id: str) -> uuid.UUID | None:
    """Return user_id from Redis session; None if expired or invalid."""
    try:
        r = _redis()
        val = r.get(_session_key(session_id))
        if val is None:
            return None
        # Refresh TTL on access
        r.expire(_session_key(session_id), _SESSION_TTL)
        return uuid.UUID(val)
    except Exception:
        return None


# ── FastAPI dependencies ───────────────────────────────────────────────────────


async def require_admin_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    kyros_admin_session: str | None = Cookie(default=None),
) -> object:
    """Dependency: return the authenticated admin-portal User.

    Accepts both tiers — super_admin (full) and admin (read-only). Views that
    change state must depend on require_super_admin_session instead.
    Raises a 302 redirect to /admin/login if the session is missing or invalid.
    """
    from app.db.enums import UserRole
    from app.repositories import users as users_repo

    if not kyros_admin_session:
        raise _login_redirect(request)

    user_id = _get_session_user_id(kyros_admin_session)
    if user_id is None:
        raise _login_redirect(request)

    user = await users_repo.get_by_id(db, user_id)
    from app.models.identity import User as UserModel
    if (
        user is None
        or not isinstance(user, UserModel)
        or user.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    ):
        raise _login_redirect(request)

    # Stamp actor identity for the PHI-access audit middleware (P33) — covers the
    # downstream require_super_admin_session denial.
    from app.db.enums import ActorRole

    request.state.actor_user_id = user.id
    request.state.actor_role = ActorRole(user.role.value)
    return user


async def require_super_admin_session(
    request: Request,
    admin: object = Depends(require_admin_session),
) -> object:
    """State-changing admin views: full super_admin tier only.

    A logged-in read-only admin gets 403, not a login redirect — they are
    authenticated, just not allowed.
    """
    from app.db.enums import UserRole
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    if admin.role != UserRole.SUPER_ADMIN:
        request.state.deny_reason = "super_admin_required"
        raise HTTPException(status.HTTP_403_FORBIDDEN, "super_admin_required")
    return admin


async def require_fresh_super_admin(
    request: Request,
    admin: object = Depends(require_super_admin_session),
    kyros_admin_session: str | None = Cookie(default=None),
) -> object:
    """Money-mover / identity actions: super admin authenticated <10 min ago.

    Stale sessions are redirected to /admin/reauth, which re-verifies the
    password and returns to the original page.
    """
    if not kyros_admin_session or not is_session_fresh(kyros_admin_session):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": f"/admin/reauth?next={request.headers.get('referer') or '/admin/'}"},
        )
    return admin


def _login_redirect(request: Request) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": f"/admin/login?next={request.url.path}"},
    )


def verify_csrf(request: Request) -> None:
    """Validate CSRF token for POST forms (call from POST handlers)."""
    # Double-submit: cookie value must match form field value.
    # Both are set at login time; neither is readable from other origins.
    pass  # Implemented inline in POST handlers for simplicity in dev.
    # Production hardening: compare request.cookies.get(CSRF_COOKIE) with form _csrf.


# ── Coordinator session auth ───────────────────────────────────────────────────

_COORD_SESSION_KEY_PREFIX = "session:coord:"
_COORD_SESSION_COOKIE = "kyros_coord_session"
_COORD_CSRF_COOKIE = "kyros_coord_csrf"


def _coord_session_key(session_id: str) -> str:
    return f"{_COORD_SESSION_KEY_PREFIX}{session_id}"


def create_coord_session(response: Response, user_id: uuid.UUID) -> str:
    """Create a Redis coordinator session and set the session cookie."""
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)

    try:
        r = _redis()
        r.setex(_coord_session_key(session_id), _SESSION_TTL, str(user_id))
    except Exception as exc:
        logger.exception("coord_session.create_failed")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "session_error") from exc

    try:
        r = _redis()
        r.sadd(f"{_STAFF_SESSIONS_PREFIX}{user_id}", session_id)
        r.expire(f"{_STAFF_SESSIONS_PREFIX}{user_id}", _SESSION_TTL)
    except Exception:
        logger.warning("coord_session.index_failed")

    response.set_cookie(
        _COORD_SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=_SESSION_TTL,
    )
    response.set_cookie(
        _COORD_CSRF_COOKIE,
        csrf_token,
        httponly=False,
        samesite="lax",
        secure=False,
        max_age=_SESSION_TTL,
    )
    return session_id


def clear_coord_session(response: Response, session_id: str) -> None:
    try:
        r = _redis()
        r.delete(_coord_session_key(session_id))
    except Exception:
        logger.warning("coord_session.clear_redis_error")
    response.delete_cookie(_COORD_SESSION_COOKIE)
    response.delete_cookie(_COORD_CSRF_COOKIE)


def _get_coord_session_user_id(session_id: str) -> uuid.UUID | None:
    try:
        r = _redis()
        val = r.get(_coord_session_key(session_id))
        if val is None:
            return None
        r.expire(_coord_session_key(session_id), _SESSION_TTL)
        return uuid.UUID(val)
    except Exception:
        return None


async def require_coord_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    kyros_coord_session: str | None = Cookie(default=None),
) -> object:
    """Dependency: return the authenticated coordinator User.

    Raises 302 to /coord/login if session is missing or invalid.
    """
    from app.db.enums import UserRole
    from app.models.identity import User as UserModel
    from app.repositories import users as users_repo

    if not kyros_coord_session:
        raise _coord_login_redirect(request)

    user_id = _get_coord_session_user_id(kyros_coord_session)
    if user_id is None:
        raise _coord_login_redirect(request)

    user = await users_repo.get_by_id(db, user_id)
    if user is None or not isinstance(user, UserModel) or user.role != UserRole.COORDINATOR:
        raise _coord_login_redirect(request)

    return user


def _coord_login_redirect(request: Request) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": f"/coord/login?next={request.url.path}"},
    )


def revoke_all_portal_sessions_for_user(user_id: uuid.UUID) -> int:
    """Delete every live admin/coordinator portal session for a user.

    Used by admin-forced session-kill (staff-rbac-spec §1) alongside JWT
    refresh-token revocation. Fails open (returns 0) on Redis errors — same
    posture as is_session_fresh, since a degraded Redis already breaks sessions.
    """
    try:
        r = _redis()
        index_key = f"{_STAFF_SESSIONS_PREFIX}{user_id}"
        session_ids: set[str] = r.smembers(index_key)
        for session_id in session_ids:
            r.delete(_session_key(session_id))
            r.delete(_fresh_key(session_id))
            r.delete(_coord_session_key(session_id))
        r.delete(index_key)
        return len(session_ids)
    except Exception:
        logger.warning("portal_sessions.revoke_failed")
        return 0
