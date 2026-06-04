"""Integration tests for POST /v1/wellness/health-sync."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_patient_user, make_auth_headers


def _consent_text_hash(text: str = "test health sync consent") -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _seven_days_ago_iso() -> str:
    return (datetime.now(UTC) - timedelta(days=7)).isoformat()


def _make_datapoints(n: int = 3, seed: str | None = None) -> list[dict]:
    """Build `n` synthetic step datapoints with unique source_record_ids."""
    base = seed or uuid.uuid4().hex
    return [
        {
            "type": "steps",
            "source_record_id": f"hk-{base}-{i}",
            "measured_at": (datetime.now(UTC) - timedelta(hours=i)).isoformat(),
            "value": {"count": 1000 + i * 100},
        }
        for i in range(n)
    ]


async def _grant_health_sync_consent(db: AsyncSession, user_id: uuid.UUID) -> None:
    from app.db.enums import ConsentType
    from app.repositories import consent as consent_repo

    await consent_repo.create_consent_record(
        db,
        user_id=user_id,
        consent_type=ConsentType.HEALTH_SYNC,
        version="1.0",
        granted=True,
        granted_at=datetime.now(UTC),
        ip_address="127.0.0.1",
        consent_text_hash=_consent_text_hash(),
    )
    await db.flush()


# ── Happy path ─────────────────────────────────────────────────────────────────



async def test_health_sync_inserts_datapoints(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)
    await _grant_health_sync_consent(db_session, patient.id)

    payload = {
        "source": "apple_health",
        "data_range_start": _seven_days_ago_iso(),
        "data_range_end": _now_iso(),
        "datapoints": _make_datapoints(3),
    }

    resp = await client.post(
        "/v1/wellness/health-sync",
        json=payload,
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted_count"] == 3
    assert data["skipped_count"] == 0
    assert data["status"] == "success"
    assert "session_id" in data


# ── Idempotency ────────────────────────────────────────────────────────────────



async def test_health_sync_resync_is_noop(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)
    await _grant_health_sync_consent(db_session, patient.id)

    seed = uuid.uuid4().hex
    payload = {
        "source": "apple_health",
        "data_range_start": _seven_days_ago_iso(),
        "data_range_end": _now_iso(),
        "datapoints": _make_datapoints(2, seed=seed),
    }
    headers = make_auth_headers(patient)

    # First sync — inserts
    resp1 = await client.post("/v1/wellness/health-sync", json=payload, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["inserted_count"] == 2

    # Second sync with identical datapoints — all skipped
    resp2 = await client.post("/v1/wellness/health-sync", json=payload, headers=headers)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["inserted_count"] == 0
    assert data["skipped_count"] == 2
    assert data["status"] == "success"


# ── Empty datapoints list ─────────────────────────────────────────────────────



async def test_health_sync_empty_datapoints(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)
    await _grant_health_sync_consent(db_session, patient.id)

    payload = {
        "source": "google_health_connect",
        "data_range_start": _seven_days_ago_iso(),
        "data_range_end": _now_iso(),
        "datapoints": [],
    }

    resp = await client.post(
        "/v1/wellness/health-sync",
        json=payload,
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted_count"] == 0
    assert data["skipped_count"] == 0


# ── Consent gate ───────────────────────────────────────────────────────────────



async def test_health_sync_no_consent_returns_403(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)
    # No consent record created

    payload = {
        "source": "apple_health",
        "data_range_start": _seven_days_ago_iso(),
        "data_range_end": _now_iso(),
        "datapoints": _make_datapoints(1),
    }

    resp = await client.post(
        "/v1/wellness/health-sync",
        json=payload,
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403
    assert "health_sync_consent_required" in resp.json()["detail"]



async def test_health_sync_revoked_consent_returns_403(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from app.db.enums import ConsentType
    from app.repositories import consent as consent_repo

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)

    # Grant then revoke
    record = await consent_repo.create_consent_record(
        db_session,
        user_id=patient.id,
        consent_type=ConsentType.HEALTH_SYNC,
        version="1.0",
        granted=True,
        granted_at=datetime.now(UTC),
        ip_address="127.0.0.1",
        consent_text_hash=_consent_text_hash(),
    )
    await db_session.flush()
    await consent_repo.revoke_consent_record(
        db_session,
        consent_id=record.id,
        revoked_at=datetime.now(UTC),
    )
    await db_session.flush()

    payload = {
        "source": "apple_health",
        "data_range_start": _seven_days_ago_iso(),
        "data_range_end": _now_iso(),
        "datapoints": _make_datapoints(1),
    }

    resp = await client.post(
        "/v1/wellness/health-sync",
        json=payload,
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


# ── Audit log ─────────────────────────────────────────────────────────────────



async def test_health_sync_denial_is_audit_logged(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from sqlalchemy import select

    from app.models.audit import AuditLog

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)

    payload = {
        "source": "apple_health",
        "data_range_start": _seven_days_ago_iso(),
        "data_range_end": _now_iso(),
        "datapoints": _make_datapoints(1),
    }

    await client.post(
        "/v1/wellness/health-sync",
        json=payload,
        headers=make_auth_headers(patient),
    )

    entry = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient.id,
            AuditLog.action == "health_sync",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert entry is not None
    assert entry.reason == "consent_revoked_or_absent"
