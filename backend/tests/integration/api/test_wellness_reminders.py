"""Integration tests for /v1/wellness/reminders/* endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
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


def _recent_slot_iso() -> str:
    """A scheduled_at one day ago — inside the 30-day adherence-rate window
    regardless of when the suite runs."""
    from datetime import UTC, datetime, timedelta

    return (datetime.now(UTC) - timedelta(days=1)).replace(microsecond=0).isoformat()


async def _adherence_rate(
    client: AsyncClient, headers: dict[str, str], reminder_id: str
) -> float:
    resp = await client.get("/v1/wellness/reminders", headers=headers)
    assert resp.status_code == 200
    for r in resp.json()["reminders"]:
        if r["id"] == reminder_id:
            return r["adherence_rate"]
    raise AssertionError("reminder not found in list")


async def test_log_adherence_same_slot_is_idempotent(
    client: AsyncClient, patient_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """Logging the same (reminder, scheduled_at) slot twice updates one row
    instead of stacking duplicates that would skew adherence_rate."""
    from app.models.wellness import ReminderLog

    created = await _create_reminder(client, patient_headers)
    rid = created["id"]
    slot = _recent_slot_iso()

    first = await client.post(
        f"/v1/wellness/reminders/{rid}/log",
        headers=patient_headers,
        json={"scheduled_at": slot, "action": "taken"},
    )
    assert first.status_code == 201

    second = await client.post(
        f"/v1/wellness/reminders/{rid}/log",
        headers=patient_headers,
        json={"scheduled_at": slot, "action": "taken"},
    )
    assert second.status_code == 201
    # Same row reused, not a duplicate.
    assert second.json()["id"] == first.json()["id"]

    count = await db_session.scalar(
        select(func.count())
        .select_from(ReminderLog)
        .where(ReminderLog.reminder_id == uuid.UUID(rid))
    )
    assert count == 1
    # Two "taken" logs would otherwise read as 100%; one row also reads 100%,
    # so assert the changed-decision case below for the discriminating check.
    assert await _adherence_rate(client, patient_headers, rid) == 1.0


async def test_log_adherence_changed_decision_overwrites_slot(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    """Changing a slot from skipped to taken yields 100%, not 50% — the skipped
    row is overwritten, not kept alongside a new taken row."""
    created = await _create_reminder(client, patient_headers)
    rid = created["id"]
    slot = _recent_slot_iso()

    await client.post(
        f"/v1/wellness/reminders/{rid}/log",
        headers=patient_headers,
        json={"scheduled_at": slot, "action": "skipped"},
    )
    assert await _adherence_rate(client, patient_headers, rid) == 0.0

    await client.post(
        f"/v1/wellness/reminders/{rid}/log",
        headers=patient_headers,
        json={"scheduled_at": slot, "action": "taken"},
    )
    assert await _adherence_rate(client, patient_headers, rid) == 1.0


def _today_slot_iso() -> str:
    """A scheduled_at in the current IST day window, for daily-summary tests."""
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat()


async def test_daily_summary_reports_resolved_reminder_ids(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    """resolved_reminder_ids lists reminders taken or skipped today, but not
    snoozed (still pending) ones — so the client can surface true overdues."""
    taken = await _create_reminder(client, patient_headers, label="Med A")
    skipped = await _create_reminder(client, patient_headers, label="Med B")
    snoozed = await _create_reminder(client, patient_headers, label="Med C")
    slot = _today_slot_iso()

    for reminder, action in ((taken, "taken"), (skipped, "skipped"), (snoozed, "snoozed")):
        resp = await client.post(
            f"/v1/wellness/reminders/{reminder['id']}/log",
            headers=patient_headers,
            json={"scheduled_at": slot, "action": action},
        )
        assert resp.status_code == 201

    summary = await client.get("/v1/wellness/reminders/daily-summary", headers=patient_headers)
    assert summary.status_code == 200
    body = summary.json()
    resolved = set(body["resolved_reminder_ids"])
    completed = set(body["completed_reminder_ids"])
    # Resolved = taken or skipped; snoozed stays pending.
    assert taken["id"] in resolved
    assert skipped["id"] in resolved
    assert snoozed["id"] not in resolved
    # Completed = taken only; a skip resolves but does not complete.
    assert taken["id"] in completed
    assert skipped["id"] not in completed
    assert snoozed["id"] not in completed


async def test_daily_summary_skip_then_take_marks_completed(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    """Changing a slot from skipped to taken moves the reminder into completed."""
    reminder = await _create_reminder(client, patient_headers)
    rid = reminder["id"]
    slot = _today_slot_iso()
    for action in ("skipped", "taken"):
        resp = await client.post(
            f"/v1/wellness/reminders/{rid}/log",
            headers=patient_headers,
            json={"scheduled_at": slot, "action": action},
        )
        assert resp.status_code == 201

    body = (await client.get("/v1/wellness/reminders/daily-summary", headers=patient_headers)).json()
    assert rid in set(body["resolved_reminder_ids"])
    assert rid in set(body["completed_reminder_ids"])


async def test_daily_summary_resolved_ids_empty_without_logs(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    await _create_reminder(client, patient_headers)
    summary = await client.get("/v1/wellness/reminders/daily-summary", headers=patient_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["resolved_reminder_ids"] == []
    assert body["completed_reminder_ids"] == []


async def _log_taken_today(
    client: AsyncClient, headers: dict[str, str], reminder_id: str, slot: str
) -> None:
    resp = await client.post(
        f"/v1/wellness/reminders/{reminder_id}/log",
        headers=headers,
        json={"scheduled_at": slot, "action": "taken"},
    )
    assert resp.status_code == 201


async def test_streak_below_80_percent_does_not_count(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    """3 of 5 daily reminders taken today = 60% < 80% → no streak."""
    ids = [
        (await _create_reminder(client, patient_headers, label=f"R{i}"))["id"]
        for i in range(5)
    ]
    slot = _today_slot_iso()
    for rid in ids[:3]:
        await _log_taken_today(client, patient_headers, rid, slot)

    summary = (await client.get("/v1/wellness/reminders/daily-summary", headers=patient_headers)).json()
    assert summary["streak"] == 0


async def test_streak_at_80_percent_counts_day(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    """4 of 5 daily reminders taken today = 80% → streak of 1."""
    ids = [
        (await _create_reminder(client, patient_headers, label=f"R{i}"))["id"]
        for i in range(5)
    ]
    slot = _today_slot_iso()
    for rid in ids[:4]:
        await _log_taken_today(client, patient_headers, rid, slot)

    summary = (await client.get("/v1/wellness/reminders/daily-summary", headers=patient_headers)).json()
    assert summary["streak"] == 1


async def test_adherence_summary_reflects_logs(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    """Patient adherence-summary returns overall rate, streaks and last-missed."""
    taken = await _create_reminder(client, patient_headers, label="Taken med")
    skipped = await _create_reminder(client, patient_headers, label="Skipped med")
    slot = _today_slot_iso()
    await _log_taken_today(client, patient_headers, taken["id"], slot)
    await client.post(
        f"/v1/wellness/reminders/{skipped['id']}/log",
        headers=patient_headers,
        json={"scheduled_at": slot, "action": "skipped"},
    )

    resp = await client.get("/v1/wellness/reminders/adherence-summary", headers=patient_headers)
    assert resp.status_code == 200
    body = resp.json()
    # 1 taken / (1 taken + 1 skipped) = 0.5
    assert body["adherence_rate_30d"] == 0.5
    assert body["last_missed_at"] is not None
    assert body["active_prescription_reminders"] == 0  # all self-created
    assert "current_streak" in body
    assert "longest_streak" in body


async def test_adherence_summary_empty_without_reminders(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.get("/v1/wellness/reminders/adherence-summary", headers=patient_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["adherence_rate_30d"] == 0.0
    assert body["current_streak"] == 0
    assert body["longest_streak"] == 0
    assert body["last_missed_at"] is None
    assert body["active_prescription_reminders"] == 0


async def test_deactivate_ended_reminders(
    db_session: AsyncSession, patient: object
) -> None:
    """The cleanup deactivates only reminders whose ends_at has passed; future
    and open-ended reminders stay active."""
    from datetime import UTC, datetime, timedelta

    from app.db.enums import ReminderType
    from app.models.identity import User as UserModel
    from app.repositories import reminders as reminders_repo

    assert isinstance(patient, UserModel)

    ended = await reminders_repo.create_reminder(
        db_session, user_id=patient.id, type=ReminderType.MEDICATION, label="Finished course",
        schedule_cron="0 8 * * *", schedule_interval_minutes=None, notification_channels=[],
        extra_metadata=None, ends_at=datetime.now(UTC) - timedelta(days=1),
        source_type="prescription", source_id=uuid.uuid4(), generated_by="doctor",
    )
    ongoing = await reminders_repo.create_reminder(
        db_session, user_id=patient.id, type=ReminderType.MEDICATION, label="Ongoing course",
        schedule_cron="0 8 * * *", schedule_interval_minutes=None, notification_channels=[],
        extra_metadata=None, ends_at=datetime.now(UTC) + timedelta(days=5),
        source_type="prescription", source_id=uuid.uuid4(), generated_by="doctor",
    )
    open_ended = await reminders_repo.create_reminder(
        db_session, user_id=patient.id, type=ReminderType.WATER, label="Hydration",
        schedule_cron="0 8 * * *", schedule_interval_minutes=None,
        notification_channels=["push"], extra_metadata=None,
    )

    count = await reminders_repo.deactivate_ended_reminders(db_session)
    assert count == 1

    for r in (ended, ongoing, open_ended):
        await db_session.refresh(r)
    assert ended.active is False
    assert ongoing.active is True
    assert open_ended.active is True


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
