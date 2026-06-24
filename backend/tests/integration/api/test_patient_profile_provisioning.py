"""A patient's 1:1 clinic profile (kc_patients) must be created at registration.

Without it, every clinic flow (consultations, lab reports, ABHA) fails with
``patient_profile_not_found``. These tests pin that both the normal signup and
the Google sign-in paths provision the profile.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.google_oauth import GoogleIdentity
from app.repositories import patients as patients_repo
from app.repositories import users as users_repo
from tests.conftest import _synth_email, _synth_phone


async def _enable_google(db: AsyncSession) -> None:
    from app.repositories import platform_settings as settings_repo
    from app.services import platform_settings_service

    await settings_repo.upsert(
        db, key=platform_settings_service.GOOGLE_OAUTH_ENABLED, value=True, updated_by=None
    )
    await db.flush()


async def test_signup_creates_patient_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    phone = _synth_phone()
    resp = await client.post(
        "/v1/auth/signup",
        json={
            "name": "Profile Test",
            "phone": phone,
            "email": _synth_email(),
            "password": "TestPass123!",
        },
    )
    assert resp.status_code == 201, resp.text

    user = await users_repo.get_by_phone(db_session, phone)
    assert user is not None
    profile = await patients_repo.get_patient_for_user(db_session, user_id=user.id)
    assert profile is not None
    assert profile.kyros_patient_id  # a human-facing id was assigned


async def test_google_login_creates_patient_profile(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _enable_google(db_session)
    email = _synth_email()

    async def _fake(_token: str) -> GoogleIdentity | None:
        return GoogleIdentity(sub="gsub-profile-1", email=email, email_verified=True, name="G")

    monkeypatch.setattr("app.integrations.google_oauth.verify_id_token", _fake)

    resp = await client.post("/v1/auth/google", json={"id_token": "x"})
    assert resp.status_code == 200, resp.text

    user = await users_repo.get_by_email(db_session, email)
    assert user is not None
    profile = await patients_repo.get_patient_for_user(db_session, user_id=user.id)
    assert profile is not None


async def test_get_or_create_for_user_is_idempotent(db_session: AsyncSession) -> None:
    from tests.conftest import create_patient_user

    user = await create_patient_user(db_session)
    await db_session.flush()

    first = await patients_repo.get_or_create_for_user(db_session, user_id=user.id)  # type: ignore[union-attr]
    second = await patients_repo.get_or_create_for_user(db_session, user_id=user.id)  # type: ignore[union-attr]
    assert first.id == second.id
    assert first.kyros_patient_id == second.kyros_patient_id


async def test_new_patient_is_routed_to_least_loaded_coordinator(
    db_session: AsyncSession,
) -> None:
    """A new patient must be assigned to a coordinator, else their consultation
    requests are created with coordinator_id=None and never reach a queue."""
    import uuid

    from app.db.enums import CoordinatorStatus
    from app.models.admin import Coordinator
    from tests.conftest import create_coordinator_user, create_patient_user

    busy_user = await create_coordinator_user(db_session)
    free_user = await create_coordinator_user(db_session)
    busy = Coordinator(
        user_id=busy_user.id,
        status=CoordinatorStatus.ACTIVE,
        assigned_patient_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
    )
    free = Coordinator(
        user_id=free_user.id,
        status=CoordinatorStatus.ACTIVE,
        assigned_patient_ids=[],
    )
    db_session.add_all([busy, free])
    await db_session.flush()

    user = await create_patient_user(db_session)
    await db_session.flush()
    patient = await patients_repo.get_or_create_for_user(db_session, user_id=user.id)

    # Routed to the coordinator holding fewer patients, both sides in sync.
    assert patient.assigned_coordinator_id == free.id
    await db_session.refresh(free)
    assert str(patient.id) in free.assigned_patient_ids
    await db_session.refresh(busy)
    assert str(patient.id) not in busy.assigned_patient_ids


async def test_new_patient_unassigned_when_no_active_coordinator(
    db_session: AsyncSession,
) -> None:
    """With no active coordinator to route to, the patient is left unassigned
    (an admin can assign later) — provisioning must still succeed."""
    from app.db.enums import CoordinatorStatus
    from app.models.admin import Coordinator
    from tests.conftest import create_coordinator_user, create_patient_user

    # An inactive coordinator must not receive the patient.
    inactive_user = await create_coordinator_user(db_session)
    db_session.add(
        Coordinator(
            user_id=inactive_user.id,
            status=CoordinatorStatus.INACTIVE,
            assigned_patient_ids=[],
        )
    )
    await db_session.flush()

    user = await create_patient_user(db_session)
    await db_session.flush()
    patient = await patients_repo.get_or_create_for_user(db_session, user_id=user.id)

    assert patient.assigned_coordinator_id is None
