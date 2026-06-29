"""Integration tests for /v1/wellness/reminders/* endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def patient(db_session: AsyncSession) -> object:
    return await create_patient_user(db_session)


@pytest.fixture
async def patient_headers(patient: object) -> dict[str, str]:
    return make_auth_headers(patient)


@pytest.fixture
async def other_patient(db_session: AsyncSession) -> object:
    return await create_patient_user(db_session)


@pytest.fixture
async def doctor(db_session: AsyncSession) -> object:
    return await create_doctor_user(db_session)


@pytest.fixture
async def doctor_headers(doctor: object) -> dict[str, str]:
    return make_auth_headers(doctor)


# ── Helper ────────────────────────────────────────────────────────────────────

async def _create_reminder(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    label: str = "Morning water",
    reminder_type: str = "water",
    schedule_cron: str = "0 8 * * *",
) -> dict:
    resp = await client.post(
        "/v1/wellness/reminders",
        headers=headers,
        json={
            "type": reminder_type,
            "label": label,
            "schedule_cron": schedule_cron,
            "notification_channels": ["push"],
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ── Auth / role enforcement ───────────────────────────────────────────────────

async def test_list_reminders_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/wellness/reminders")
    assert resp.status_code == 401


async def test_create_reminder_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/wellness/reminders", json={})
    assert resp.status_code == 401


async def test_create_reminder_doctor_returns_403(
    client: AsyncClient, doctor_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/wellness/reminders",
        headers=doctor_headers,
        json={"type": "water", "label": "test"},
    )
    assert resp.status_code == 403


async def test_update_reminder_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch(f"/v1/wellness/reminders/{uuid.uuid4()}", json={})
    assert resp.status_code == 401


async def test_delete_reminder_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.delete(f"/v1/wellness/reminders/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_log_adherence_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/wellness/reminders/{uuid.uuid4()}/log", json={})
    assert resp.status_code == 401


# ── Create reminder ───────────────────────────────────────────────────────────

async def test_create_reminder_returns_201(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/wellness/reminders",
        headers=patient_headers,
        json={
            "type": "supplement",
            "label": "Vitamin D",
            "schedule_cron": "0 9 * * *",
            "notification_channels": ["push"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "supplement"
    assert data["label"] == "Vitamin D"
    assert data["active"] is True
    assert data["adherence_rate"] == 0.0


async def test_create_reminder_missing_label_returns_422(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/wellness/reminders",
        headers=patient_headers,
        json={"type": "water"},
    )
    assert resp.status_code == 422


async def test_create_reminder_invalid_type_returns_422(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/wellness/reminders",
        headers=patient_headers,
        json={"type": "not-a-type", "label": "test"},
    )
    assert resp.status_code == 422


# ── List reminders ────────────────────────────────────────────────────────────

async def test_list_reminders_returns_own_only(
    client: AsyncClient,
    patient_headers: dict[str, str],
    other_patient: object,
    db_session: AsyncSession,
) -> None:
    other_headers = make_auth_headers(other_patient)
    await _create_reminder(client, other_headers, label="Other's reminder")
    await _create_reminder(client, patient_headers, label="My water")
    await _create_reminder(client, patient_headers, label="My supplement", reminder_type="supplement")

    resp = await client.get("/v1/wellness/reminders", headers=patient_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    labels = {r["label"] for r in data["reminders"]}
    assert labels == {"My water", "My supplement"}


async def test_list_reminders_empty(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.get("/v1/wellness/reminders", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Update reminder ───────────────────────────────────────────────────────────

async def test_update_reminder_label(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    reminder_id = created["id"]

    resp = await client.patch(
        f"/v1/wellness/reminders/{reminder_id}",
        headers=patient_headers,
        json={"label": "Evening water"},
    )
    assert resp.status_code == 200
    assert resp.json()["label"] == "Evening water"


async def test_update_reminder_deactivate(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    resp = await client.patch(
        f"/v1/wellness/reminders/{created['id']}",
        headers=patient_headers,
        json={"active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["active"] is False


# ── Delete reminder ───────────────────────────────────────────────────────────

async def test_delete_reminder_returns_204(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    resp = await client.delete(
        f"/v1/wellness/reminders/{created['id']}", headers=patient_headers
    )
    assert resp.status_code == 204


async def test_deleted_reminder_not_in_list(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    await client.delete(f"/v1/wellness/reminders/{created['id']}", headers=patient_headers)
    resp = await client.get("/v1/wellness/reminders", headers=patient_headers)
    ids = [r["id"] for r in resp.json()["reminders"]]
    assert created["id"] not in ids


# ── Adherence logging ─────────────────────────────────────────────────────────

async def test_log_adherence_taken(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    resp = await client.post(
        f"/v1/wellness/reminders/{created['id']}/log",
        headers=patient_headers,
        json={
            "scheduled_at": "2026-06-03T08:00:00+00:00",
            "action": "taken",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["action"] == "taken"
    assert data["reminder_id"] == created["id"]


async def test_log_adherence_skipped(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    resp = await client.post(
        f"/v1/wellness/reminders/{created['id']}/log",
        headers=patient_headers,
        json={"scheduled_at": "2026-06-03T08:00:00+00:00", "action": "skipped"},
    )
    assert resp.status_code == 201
    assert resp.json()["action"] == "skipped"


async def test_log_adherence_snoozed_with_notes(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    resp = await client.post(
        f"/v1/wellness/reminders/{created['id']}/log",
        headers=patient_headers,
        json={
            "scheduled_at": "2026-06-03T08:00:00+00:00",
            "action": "snoozed",
            "notes": "Snooze 15 min",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["notes"] == "Snooze 15 min"


async def test_log_adherence_invalid_action_returns_422(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    resp = await client.post(
        f"/v1/wellness/reminders/{created['id']}/log",
        headers=patient_headers,
        json={"scheduled_at": "2026-06-03T08:00:00+00:00", "action": "not-valid"},
    )
    assert resp.status_code == 422


# ── Adherence rate ────────────────────────────────────────────────────────────

async def test_adherence_rate_reflected_in_list(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    created = await _create_reminder(client, patient_headers)
    rid = created["id"]
    scheduled = "2026-06-03T08:00:00+00:00"

    # 2 taken, 2 skipped → 50% taken
    for action in ["taken", "taken", "skipped", "skipped"]:
        await client.post(
            f"/v1/wellness/reminders/{rid}/log",
            headers=patient_headers,
            json={"scheduled_at": scheduled, "action": action},
        )

    resp = await client.get("/v1/wellness/reminders", headers=patient_headers)
    reminder_data = next(r for r in resp.json()["reminders"] if r["id"] == rid)
    assert reminder_data["adherence_rate"] == 0.5


# ── Cross-user 404 ────────────────────────────────────────────────────────────

async def test_update_other_patients_reminder_returns_404(
    client: AsyncClient,
    patient: object,
    other_patient: object,
    db_session: AsyncSession,
) -> None:
    other_headers = make_auth_headers(other_patient)
    patient_headers = make_auth_headers(patient)

    foreign = await _create_reminder(client, other_headers)
    resp = await client.patch(
        f"/v1/wellness/reminders/{foreign['id']}",
        headers=patient_headers,
        json={"label": "hijack"},
    )
    assert resp.status_code == 404

    # denial must be audit-logged
    from app.models.audit import AuditLog
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient.id,
            AuditLog.action == "update_reminder",
            AuditLog.allowed.is_(False),
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


async def test_delete_other_patients_reminder_returns_404(
    client: AsyncClient,
    patient: object,
    other_patient: object,
    db_session: AsyncSession,
) -> None:
    other_headers = make_auth_headers(other_patient)
    patient_headers = make_auth_headers(patient)

    foreign = await _create_reminder(client, other_headers)
    resp = await client.delete(
        f"/v1/wellness/reminders/{foreign['id']}", headers=patient_headers
    )
    assert resp.status_code == 404

    from app.models.audit import AuditLog
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient.id,
            AuditLog.action == "delete_reminder",
            AuditLog.allowed.is_(False),
        )
    )
    assert audit is not None


async def test_log_adherence_other_patients_reminder_returns_404(
    client: AsyncClient,
    patient: object,
    other_patient: object,
    db_session: AsyncSession,
) -> None:
    other_headers = make_auth_headers(other_patient)
    patient_headers = make_auth_headers(patient)

    foreign = await _create_reminder(client, other_headers)
    resp = await client.post(
        f"/v1/wellness/reminders/{foreign['id']}/log",
        headers=patient_headers,
        json={"scheduled_at": "2026-06-03T08:00:00+00:00", "action": "taken"},
    )
    assert resp.status_code == 404

    from app.models.audit import AuditLog
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient.id,
            AuditLog.action == "log_adherence",
            AuditLog.allowed.is_(False),
        )
    )
    assert audit is not None


async def test_delete_nonexistent_reminder_returns_404(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.delete(
        f"/v1/wellness/reminders/{uuid.uuid4()}", headers=patient_headers
    )
    assert resp.status_code == 404


# ── Schedule-aware dispatch (get_due_reminders) ───────────────────────────────

async def test_get_due_reminders_is_schedule_aware(
    db_session: AsyncSession, patient: object
) -> None:
    """A daily-8am reminder is due only in the window around 08:00 IST, and is
    returned paired with its occurrence (the dispatch idempotency slot)."""
    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo

    from app.db.enums import ReminderType
    from app.models.identity import User as UserModel
    from app.repositories import reminders as reminders_repo

    assert isinstance(patient, UserModel)
    ist = ZoneInfo("Asia/Kolkata")

    reminder = await reminders_repo.create_reminder(
        db_session,
        user_id=patient.id,
        type=ReminderType.MEDICATION,
        label="Thyroxine",
        schedule_cron="0 8 * * *",
        schedule_interval_minutes=None,
        notification_channels=["push"],
        extra_metadata=None,
    )
    await db_session.flush()

    # 08:02 IST — the 08:00 dose is due; occurrence is 08:00 IST expressed in UTC.
    due_now = datetime(2026, 6, 27, 8, 2, tzinfo=ist).astimezone(UTC)
    due = await reminders_repo.get_due_reminders(db_session, now=due_now)
    mine = [(r, occ) for r, occ in due if r.id == reminder.id]
    assert len(mine) == 1
    assert mine[0][1] == datetime(2026, 6, 27, 8, 0, tzinfo=ist).astimezone(UTC)

    # 09:00 IST — nothing due for this reminder.
    off_now = datetime(2026, 6, 27, 9, 0, tzinfo=ist).astimezone(UTC)
    due_off = await reminders_repo.get_due_reminders(db_session, now=off_now)
    assert all(r.id != reminder.id for r, _ in due_off)
