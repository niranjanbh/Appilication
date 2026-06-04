from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import HealthSyncSource, HealthSyncStatus
from app.models.wellness import HealthDatapoint, HealthSyncSession


async def create_sync_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source: HealthSyncSource,
    data_range_start: datetime,
    data_range_end: datetime,
    consent_id: uuid.UUID | None,
) -> HealthSyncSession:
    session = HealthSyncSession(
        user_id=user_id,
        source=source,
        synced_at=datetime.now(UTC),
        data_range_start=data_range_start,
        data_range_end=data_range_end,
        record_count=0,
        consent_id=consent_id,
        status=HealthSyncStatus.PARTIAL,
    )
    db.add(session)
    await db.flush()
    return session


async def update_sync_session(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    status: HealthSyncStatus,
    record_count: int,
) -> None:
    await db.execute(
        update(HealthSyncSession)
        .where(HealthSyncSession.id == session_id)
        .values(status=status, record_count=record_count, updated_at=datetime.now(UTC))
    )


async def upsert_datapoints(
    db: AsyncSession,
    *,
    rows: list[dict[str, Any]],
) -> tuple[int, int]:
    """Bulk-insert datapoints, skipping duplicates on (user_id, source, source_record_id, measured_at).

    Returns (inserted_count, skipped_count). Uses RETURNING to count only rows
    actually written (PostgreSQL skips conflicting rows and omits them from RETURNING).
    """
    if not rows:
        return 0, 0

    stmt = (
        pg_insert(HealthDatapoint.__table__)  # type: ignore[arg-type]
        .values(rows)
        .on_conflict_do_nothing()
        .returning(HealthDatapoint.__table__.c.id)
    )
    result = await db.execute(stmt)
    inserted = len(result.fetchall())
    return inserted, len(rows) - inserted
