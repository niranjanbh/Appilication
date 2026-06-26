"""Integration tests for GET /v1/wellness/health-summary.

Steps are summed over the current UTC day; resting HR and HRV are the latest
readings. Synced datapoints carry type-specific JSONB shapes ({count}/{bpm}/{ms}),
which the service normalises to single numbers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import HealthDatapointSource, HealthDatapointType
from app.models.wellness import HealthDatapoint
from tests.conftest import create_patient_user, make_auth_headers


async def _add_dp(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    dp_type: HealthDatapointType,
    value: dict[str, object],
    measured_at: datetime,
    record_id: str,
) -> None:
    db.add(
        HealthDatapoint(
            user_id=user_id,
            measured_at=measured_at,
            source=HealthDatapointSource.APPLE_HEALTH,
            source_record_id=record_id,
            type=dp_type,
            value=value,
        )
    )
    await db.flush()


async def test_health_summary_aggregates_synced_metrics(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    now = datetime.now(UTC)

    # Two step samples today -> summed.
    await _add_dp(db_session, user_id=patient.id, dp_type=HealthDatapointType.STEPS,
                  value={"count": 4000}, measured_at=now - timedelta(hours=2), record_id="s1")
    await _add_dp(db_session, user_id=patient.id, dp_type=HealthDatapointType.STEPS,
                  value={"count": 4240}, measured_at=now - timedelta(hours=1), record_id="s2")
    # Two resting-HR readings -> latest wins.
    await _add_dp(db_session, user_id=patient.id, dp_type=HealthDatapointType.RESTING_HEART_RATE,
                  value={"bpm": 70}, measured_at=now - timedelta(hours=5), record_id="r1")
    await _add_dp(db_session, user_id=patient.id, dp_type=HealthDatapointType.RESTING_HEART_RATE,
                  value={"bpm": 62}, measured_at=now - timedelta(minutes=30), record_id="r2")
    await _add_dp(db_session, user_id=patient.id, dp_type=HealthDatapointType.HRV,
                  value={"ms": 48.4}, measured_at=now - timedelta(minutes=20), record_id="h1")

    resp = await client.get(
        "/v1/wellness/health-summary", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["steps_today"] == 8240
    assert body["resting_heart_rate_bpm"] == 62
    assert body["hrv_ms"] == 48.4
    assert body["updated_at"] is not None


async def test_health_summary_empty_returns_nulls(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/wellness/health-summary", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["steps_today"] is None
    assert body["resting_heart_rate_bpm"] is None
    assert body["hrv_ms"] is None
    assert body["updated_at"] is None


async def test_health_summary_excludes_prior_day_steps(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Steps are summed for the current UTC day only — yesterday's are excluded."""
    patient = await create_patient_user(db_session)
    yesterday = datetime.now(UTC) - timedelta(days=1, hours=1)
    await _add_dp(db_session, user_id=patient.id, dp_type=HealthDatapointType.STEPS,
                  value={"count": 5000}, measured_at=yesterday, record_id="y1")

    resp = await client.get(
        "/v1/wellness/health-summary", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["steps_today"] is None
