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
