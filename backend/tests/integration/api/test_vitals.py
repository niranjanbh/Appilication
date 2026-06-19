"""Integration tests for manual vitals logging."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers

_NOW = datetime.now(UTC).isoformat()


# ── Log ─────────────────────────────────────────────────────────────────────────


async def test_log_weight_only(client: AsyncClient, db_session: AsyncSession) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW, "weight_kg": 72.5},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["logged_count"] == 1


async def test_log_full_vitals_creates_four_datapoints(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/wellness/vitals",
        json={
            "measured_at": _NOW,
            "weight_kg": 70.0,
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "blood_glucose_mg_dl": 95.0,
        },
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["logged_count"] == 4


async def test_log_vitals_partial_bp_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW, "blood_pressure_systolic": 120},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 422


async def test_log_vitals_empty_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 422


# ── List ─────────────────────────────────────────────────────────────────────────


async def test_list_vitals_returns_logged(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    headers = make_auth_headers(patient)
    await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW, "weight_kg": 68.0, "blood_glucose_mg_dl": 90.0},
        headers=headers,
    )

    resp = await client.get("/v1/wellness/vitals", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    types = {i["type"] for i in items}
    assert types == {"weight", "blood_glucose"}
    weight = next(i for i in items if i["type"] == "weight")
    assert weight["value"] == {"value": 68.0, "unit": "kg"}


async def test_list_vitals_filtered_by_type(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    headers = make_auth_headers(patient)
    await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW, "weight_kg": 68.0, "blood_glucose_mg_dl": 90.0},
        headers=headers,
    )

    resp = await client.get("/v1/wellness/vitals?type=weight", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [i["type"] for i in items] == ["weight"]


async def test_list_vitals_scoped_to_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW, "weight_kg": 80.0},
        headers=make_auth_headers(patient_a),
    )

    resp = await client.get("/v1/wellness/vitals", headers=make_auth_headers(patient_b))
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── RBAC ──────────────────────────────────────────────────────────────────────────


async def test_log_vitals_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/wellness/vitals", json={"measured_at": _NOW, "weight_kg": 70.0})
    assert resp.status_code == 401


async def test_log_vitals_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": _NOW, "weight_kg": 70.0},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_list_vitals_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/wellness/vitals")
    assert resp.status_code == 401


async def test_list_vitals_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/wellness/vitals", headers=make_auth_headers(doctor))
    assert resp.status_code == 403
