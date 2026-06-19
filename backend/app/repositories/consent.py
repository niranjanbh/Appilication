from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DataSubjectRequestStatus, DataSubjectRequestType
from app.models.consent import ConsentRecord, DataSubjectRequest


async def create_consent_record(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    consent_type: Any,
    version: str,
    granted: bool,
    granted_at: datetime,
    ip_address: str | None,
    consent_text_hash: str,
) -> ConsentRecord:
    record = ConsentRecord(
        user_id=user_id,
        consent_type=consent_type,
        version=version,
        granted=granted,
        granted_at=granted_at,
        ip_address=ip_address,
        consent_text_hash=consent_text_hash,
    )
    db.add(record)
    await db.flush()
    return record


async def get_active_consent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    consent_type: Any,
) -> ConsentRecord | None:
    result = await db.execute(
        select(ConsentRecord)
        .where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.granted.is_(True),
            ConsentRecord.revoked_at.is_(None),
        )
        .order_by(ConsentRecord.granted_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def revoke_consent_record(
    db: AsyncSession,
    *,
    consent_id: uuid.UUID,
    revoked_at: datetime,
) -> None:
    await db.execute(
        update(ConsentRecord)
        .where(ConsentRecord.id == consent_id)
        .values(revoked_at=revoked_at, updated_at=datetime.now(UTC))
    )


async def create_data_subject_request(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    request_type: DataSubjectRequestType,
    received_at: datetime,
) -> DataSubjectRequest:
    dsr = DataSubjectRequest(
        user_id=user_id,
        request_type=request_type,
        status=DataSubjectRequestStatus.RECEIVED,
        received_at=received_at,
    )
    db.add(dsr)
    await db.flush()
    return dsr


async def list_consents_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[ConsentRecord]:
    result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id)
        .order_by(ConsentRecord.granted_at.desc())
    )
    return list(result.scalars().all())


async def get_data_subject_request_for_user(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    user_id: uuid.UUID,
) -> DataSubjectRequest | None:
    result = await db.execute(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == request_id,
            DataSubjectRequest.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_data_subject_requests_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    request_type: DataSubjectRequestType,
) -> list[DataSubjectRequest]:
    """List a user's DSRs of a given type, newest first."""
    result = await db.execute(
        select(DataSubjectRequest)
        .where(
            DataSubjectRequest.user_id == user_id,
            DataSubjectRequest.request_type == request_type,
        )
        .order_by(DataSubjectRequest.received_at.desc())
    )
    return list(result.scalars().all())


async def update_data_subject_request_status(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    status: DataSubjectRequestStatus,
    completed_at: datetime | None = None,
    notes: str | None = None,
) -> None:
    values: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(UTC),
    }
    if completed_at is not None:
        values["completed_at"] = completed_at
    if notes is not None:
        values["notes"] = notes
    await db.execute(
        update(DataSubjectRequest).where(DataSubjectRequest.id == request_id).values(**values)
    )
