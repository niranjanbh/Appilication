"""Integration tests for patient device-session management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.identity import RefreshToken
from app.models.identity import User as UserModel
from app.repositories import auth as auth_repo
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


def _auth_with_session(user: object, session_id: uuid.UUID) -> dict[str, str]:
    """Bearer headers whose access token carries a specific session_id."""
    from app.core.security import create_access_token

    assert isinstance(user, UserModel)
    token = create_access_token(user.id, user.role, session_id)
    return {"Authorization": f"Bearer {token}"}


async def _add_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    expires_in_days: int = 7,
    user_agent: str = "iPhone 15; Kyros/1.0",
    ip: str = "203.0.113.5",
) -> RefreshToken:
    return await auth_repo.create_refresh_token(
        db,
        user_id=user_id,
        session_id=session_id,
        token_hash=uuid.uuid4().hex,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        ip_address=ip,
        user_agent=user_agent,
    )


# ── List ────────────────────────────────────────────────────────────────────────


async def test_list_sessions_returns_active_sessions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)

    sess_a, sess_b = uuid.uuid4(), uuid.uuid4()
    await _add_token(db_session, user_id=patient.id, session_id=sess_a)
    await _add_token(db_session, user_id=patient.id, session_id=sess_b)

    resp = await client.get("/v1/users/me/sessions", headers=make_auth_headers(patient))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert {i["session_id"] for i in items} == {str(sess_a), str(sess_b)}
    assert all(i["user_agent"] == "iPhone 15; Kyros/1.0" for i in items)


async def test_list_sessions_marks_current(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)

    current, other = uuid.uuid4(), uuid.uuid4()
    await _add_token(db_session, user_id=patient.id, session_id=current)
    await _add_token(db_session, user_id=patient.id, session_id=other)

    resp = await client.get(
        "/v1/users/me/sessions", headers=_auth_with_session(patient, current)
    )
    assert resp.status_code == 200
    by_id = {i["session_id"]: i for i in resp.json()["items"]}
    assert by_id[str(current)]["is_current"] is True
    assert by_id[str(other)]["is_current"] is False


async def test_list_sessions_excludes_revoked_and_expired(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)

    live = uuid.uuid4()
    revoked = uuid.uuid4()
    expired = uuid.uuid4()
    await _add_token(db_session, user_id=patient.id, session_id=live)
    rt = await _add_token(db_session, user_id=patient.id, session_id=revoked)
    await auth_repo.revoke_token(db_session, rt.id)
    await _add_token(db_session, user_id=patient.id, session_id=expired, expires_in_days=-1)

    resp = await client.get("/v1/users/me/sessions", headers=make_auth_headers(patient))
    assert resp.status_code == 200
    ids = {i["session_id"] for i in resp.json()["items"]}
    assert ids == {str(live)}


async def test_list_sessions_collapses_rotated_family(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)

    session = uuid.uuid4()
    await _add_token(db_session, user_id=patient.id, session_id=session)
    await _add_token(db_session, user_id=patient.id, session_id=session)

    resp = await client.get("/v1/users/me/sessions", headers=make_auth_headers(patient))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["session_id"] == str(session)


# ── Revoke ────────────────────────────────────────────────────────────────────────


async def test_revoke_session_revokes_whole_family(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)

    session = uuid.uuid4()
    await _add_token(db_session, user_id=patient.id, session_id=session)
    await _add_token(db_session, user_id=patient.id, session_id=session)

    resp = await client.delete(
        f"/v1/users/me/sessions/{session}", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 200
    assert resp.json()["revoked"] == 2

    # All tokens in the family are now revoked
    rows = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.session_id == session)
        )
    ).scalars().all()
    assert all(t.revoked_at is not None for t in rows)


async def test_revoke_other_users_session_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    assert isinstance(patient_a, UserModel)
    assert isinstance(patient_b, UserModel)

    session_b = uuid.uuid4()
    await _add_token(db_session, user_id=patient_b.id, session_id=session_b)

    resp = await client.delete(
        f"/v1/users/me/sessions/{session_b}", headers=make_auth_headers(patient_a)
    )
    assert resp.status_code == 404

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_a.id,
            AuditLog.action == "revoke_session",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"

    # Patient B's session is untouched
    rows = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.session_id == session_b)
        )
    ).scalars().all()
    assert all(t.revoked_at is None for t in rows)


async def test_revoke_unknown_session_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.delete(
        f"/v1/users/me/sessions/{uuid.uuid4()}", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 404


# ── RBAC ──────────────────────────────────────────────────────────────────────────


async def test_list_sessions_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me/sessions")
    assert resp.status_code == 401


async def test_list_sessions_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/users/me/sessions", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_revoke_session_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.delete(f"/v1/users/me/sessions/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_revoke_session_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.delete(
        f"/v1/users/me/sessions/{uuid.uuid4()}", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403
