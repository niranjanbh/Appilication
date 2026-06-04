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
