"""Integration tests for the patient activity history feed."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers

_NOW = datetime.now(UTC).isoformat()


async def test_activity_includes_mutating_actions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    headers = make_auth_headers(patient)

    # A mutating action that writes an audit row.
    await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW, "weight_kg": 70.0},
        headers=headers,
    )

    resp = await client.get("/v1/users/me/activity", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    actions = {i["action"] for i in data["items"]}
    assert "log_vitals" in actions
    logged = next(i for i in data["items"] if i["action"] == "log_vitals")
    assert logged["description"] == "Logged vitals"
    assert logged["allowed"] is True
    assert data["total"] >= 1


async def test_activity_excludes_read_actions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    headers = make_auth_headers(patient)

    # Pure reads: viewing profile + listing activity write view_*/list_* audits.
    await client.get("/v1/users/me", headers=headers)
    resp = await client.get("/v1/users/me/activity", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert not item["action"].startswith("view_")
        assert not item["action"].startswith("list_")


async def test_activity_scoped_to_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW, "weight_kg": 80.0},
        headers=make_auth_headers(patient_a),
    )

    resp = await client.get("/v1/users/me/activity", headers=make_auth_headers(patient_b))
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 0


# ── RBAC ──────────────────────────────────────────────────────────────────────────


async def test_activity_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me/activity")
    assert resp.status_code == 401


async def test_activity_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/users/me/activity", headers=make_auth_headers(doctor))
    assert resp.status_code == 403
