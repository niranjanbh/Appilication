from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    ConsentType,
    HealthDatapointSource,
    HealthDatapointType,
    HealthSyncSource,
    HealthSyncStatus,
)
from app.models.wellness import HealthSyncSession
from app.repositories import consent as consent_repo
from app.repositories import health_sync as health_sync_repo


@dataclass
class DatapointInput:
    type: HealthDatapointType
    source_record_id: str
    measured_at: datetime
    value: dict[str, object]


@dataclass
class SyncResult:
    session: HealthSyncSession
    inserted_count: int
    skipped_count: int
    status: HealthSyncStatus


_SOURCE_TO_DP_SOURCE: dict[HealthSyncSource, HealthDatapointSource] = {
    HealthSyncSource.APPLE_HEALTH: HealthDatapointSource.APPLE_HEALTH,
    HealthSyncSource.GOOGLE_HEALTH_CONNECT: HealthDatapointSource.GOOGLE_HEALTH_CONNECT,
}


async def process_health_sync(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source: HealthSyncSource,
    data_range_start: datetime,
    data_range_end: datetime,
    datapoints: list[DatapointInput],
) -> SyncResult:
    """Validate consent, create a sync session, and upsert datapoints idempotently.

    Raises PermissionError("health_sync_consent_required") if no active consent exists.
    """
    consent = await consent_repo.get_active_consent(
        db, user_id=user_id, consent_type=ConsentType.HEALTH_SYNC
    )
    if consent is None:
        raise PermissionError("health_sync_consent_required")

    session = await health_sync_repo.create_sync_session(
        db,
        user_id=user_id,
        source=source,
        data_range_start=data_range_start,
        data_range_end=data_range_end,
        consent_id=consent.id,
    )

    dp_source = _SOURCE_TO_DP_SOURCE[source]
    rows = [
        {
            "user_id": user_id,
            "source": dp_source,
            "source_session_id": session.id,
            "source_record_id": dp.source_record_id,
            "type": dp.type,
            "value": dp.value,
            "measured_at": dp.measured_at,
        }
        for dp in datapoints
    ]

    inserted, skipped = await health_sync_repo.upsert_datapoints(db, rows=rows)

    final_status = (
        HealthSyncStatus.SUCCESS
        if inserted + skipped == len(datapoints)
        else HealthSyncStatus.PARTIAL
    )

    await health_sync_repo.update_sync_session(
        db,
        session_id=session.id,
        status=final_status,
        record_count=inserted,
    )

    return SyncResult(
        session=session,
        inserted_count=inserted,
        skipped_count=skipped,
        status=final_status,
    )


async def log_manual_vitals(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    measured_at: datetime,
    weight_kg: float | None = None,
    blood_pressure_systolic: int | None = None,
    blood_pressure_diastolic: int | None = None,
    blood_glucose_mg_dl: float | None = None,
) -> int:
    """Record patient-entered vitals as MANUAL-source health datapoints.

    Unlike device sync this needs no health_sync consent — the patient is
    volunteering their own readings. Returns the number of datapoints written.
    """
    def _row(dp_type: HealthDatapointType, value: dict[str, object]) -> dict[str, object]:
        return {
            "user_id": user_id,
            "source": HealthDatapointSource.MANUAL,
            "source_session_id": None,
            "source_record_id": uuid.uuid4().hex,
            "type": dp_type,
            "value": value,
            "measured_at": measured_at,
        }

    rows: list[dict[str, object]] = []
    if weight_kg is not None:
        rows.append(_row(HealthDatapointType.WEIGHT, {"value": weight_kg, "unit": "kg"}))
    if blood_pressure_systolic is not None:
        rows.append(_row(
            HealthDatapointType.BLOOD_PRESSURE_SYSTOLIC,
            {"value": blood_pressure_systolic, "unit": "mmHg"},
        ))
    if blood_pressure_diastolic is not None:
        rows.append(_row(
            HealthDatapointType.BLOOD_PRESSURE_DIASTOLIC,
            {"value": blood_pressure_diastolic, "unit": "mmHg"},
        ))
    if blood_glucose_mg_dl is not None:
        rows.append(_row(
            HealthDatapointType.BLOOD_GLUCOSE,
            {"value": blood_glucose_mg_dl, "unit": "mg/dL"},
        ))

    inserted, _skipped = await health_sync_repo.upsert_datapoints(db, rows=rows)
    return inserted


def _extract_number(value: dict[str, object]) -> float | None:
    """Pull the single numeric reading out of a datapoint's JSONB value.

    Synced datapoints use type-specific keys ({'count': n}, {'bpm': n}, {'ms': n});
    manually-logged ones use {'value': n, 'unit': ...}. Either shape carries exactly
    one numeric, so the first numeric value found is the reading. Booleans are
    excluded (``bool`` is a subclass of ``int``).
    """
    for v in value.values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


async def get_health_summary(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, object]:
    """Build the lifestyle dashboard summary from synced health datapoints.

    Steps are summed over the current UTC day; resting heart rate and HRV are the
    latest readings. Any metric with no datapoints comes back as None.
    """
    from datetime import UTC, datetime

    latest = await health_sync_repo.get_latest_datapoints_by_type(
        db,
        user_id=user_id,
        types=[HealthDatapointType.RESTING_HEART_RATE, HealthDatapointType.HRV],
    )

    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    steps_rows = await health_sync_repo.list_datapoints_since(
        db, user_id=user_id, datapoint_type=HealthDatapointType.STEPS, since=day_start
    )

    steps_today: int | None = None
    if steps_rows:
        steps_today = int(round(sum((_extract_number(r.value) or 0.0) for r in steps_rows)))

    rhr = latest.get(HealthDatapointType.RESTING_HEART_RATE)
    hrv = latest.get(HealthDatapointType.HRV)
    rhr_v = _extract_number(rhr.value) if rhr is not None else None
    hrv_v = _extract_number(hrv.value) if hrv is not None else None

    updated_candidates = [dp.measured_at for dp in (rhr, hrv) if dp is not None]
    if steps_rows:
        updated_candidates.append(max(r.measured_at for r in steps_rows))

    return {
        "steps_today": steps_today,
        "resting_heart_rate_bpm": int(round(rhr_v)) if rhr_v is not None else None,
        "hrv_ms": round(hrv_v, 1) if hrv_v is not None else None,
        "updated_at": max(updated_candidates) if updated_candidates else None,
    }
