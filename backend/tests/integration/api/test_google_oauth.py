"""Integration tests: Sign in with Google (patient-only, admin-gated)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UserRole
from app.integrations.google_oauth import GoogleIdentity
from tests.conftest import (
    _synth_email,
    create_doctor_user,
    create_patient_user,
)


async def _enable_google(db: AsyncSession) -> None:
    from app.repositories import platform_settings as settings_repo
    from app.services import platform_settings_service

    await settings_repo.upsert(
        db, key=platform_settings_service.GOOGLE_OAUTH_ENABLED, value=True, updated_by=None
    )
    await db.flush()


def _patch_verify(monkeypatch: pytest.MonkeyPatch, identity: GoogleIdentity | None) -> None:
    async def _fake(_token: str) -> GoogleIdentity | None:
        return identity

    monkeypatch.setattr("app.integrations.google_oauth.verify_id_token", _fake)


async def test_google_login_disabled_returns_401(client: AsyncClient) -> None:
    # Flag defaults to off — feature does nothing until an admin enables it.
    resp = await client.post("/v1/auth/google", json={"id_token": "anything"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "google_signin_disabled"


async def test_google_login_invalid_token_returns_401(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _enable_google(db_session)
    _patch_verify(monkeypatch, None)
    resp = await client.post("/v1/auth/google", json={"id_token": "bad"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid_google_token"


async def test_google_login_creates_new_patient(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _enable_google(db_session)
    email = _synth_email()
    _patch_verify(
        monkeypatch,
        GoogleIdentity(sub="gsub-new-1", email=email, email_verified=True, name="New G"),
    )

    resp = await client.post("/v1/auth/google", json={"id_token": "x"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]

    from app.repositories import users as users_repo

    user = await users_repo.get_by_email(db_session, email)
    assert user is not None
    assert user.role == UserRole.PATIENT
    assert user.google_sub == "gsub-new-1"
    assert user.email_verified is True


async def test_google_login_links_existing_patient_by_email(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _enable_google(db_session)
    email = _synth_email()
    user = await create_patient_user(db_session, email=email)
    await db_session.flush()
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)

    _patch_verify(
        monkeypatch,
        GoogleIdentity(sub="gsub-link-1", email=email, email_verified=True, name="X"),
    )
    resp = await client.post("/v1/auth/google", json={"id_token": "x"})
    assert resp.status_code == 200, resp.text

    await db_session.refresh(user)
    assert user.google_sub == "gsub-link-1"


async def test_google_login_rejects_staff_account(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _enable_google(db_session)
    email = _synth_email()
    await create_doctor_user(db_session, email=email)
    await db_session.flush()

    _patch_verify(
        monkeypatch,
        GoogleIdentity(sub="gsub-staff-1", email=email, email_verified=True, name="Dr"),
    )
    resp = await client.post("/v1/auth/google", json={"id_token": "x"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "google_signin_not_allowed"


async def test_google_login_unverified_email_rejected(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _enable_google(db_session)
    _patch_verify(
        monkeypatch,
        GoogleIdentity(sub="gsub-unv-1", email=_synth_email(), email_verified=False, name="U"),
    )
    resp = await client.post("/v1/auth/google", json={"id_token": "x"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "google_email_unverified"
