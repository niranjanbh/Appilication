from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext, write_audit
from app.db.enums import ConsentType, DataSubjectRequestType
from app.models.consent import ConsentRecord, DataSubjectRequest
from app.repositories import consent as consent_repo


async def capture_consent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    consent_type: ConsentType,
    version: str,
    granted: bool,
    ip_address: str | None,
    consent_text: str,
) -> ConsentRecord:
    """Record a consent decision. consent_text is SHA-256 hashed before storage."""
    consent_text_hash = hashlib.sha256(consent_text.encode()).hexdigest()
    return await consent_repo.create_consent_record(
        db,
        user_id=user_id,
        consent_type=consent_type,
        version=version,
        granted=granted,
        granted_at=datetime.now(UTC),
        ip_address=ip_address,
        consent_text_hash=consent_text_hash,
    )


async def revoke_consent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    consent_type: ConsentType,
) -> ConsentRecord:
    from app.core.exceptions import NotFoundError

    record = await consent_repo.get_active_consent(
        db, user_id=user_id, consent_type=consent_type
    )
    if record is None:
        raise NotFoundError("active_consent_not_found")
    await consent_repo.revoke_consent_record(
        db, consent_id=record.id, revoked_at=datetime.now(UTC)
    )
    return record


async def request_data_export(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    audit_ctx: AuditContext,
) -> DataSubjectRequest:
    dsr = await consent_repo.create_data_subject_request(
        db,
        user_id=user_id,
        request_type=DataSubjectRequestType.ACCESS,
        received_at=datetime.now(UTC),
    )
    await write_audit(
        db,
        audit_ctx,
        action="request_data_export",
        resource_type="data_subject_request",
        resource_id=dsr.id,
        allowed=True,
    )
    return dsr


async def request_erasure(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    audit_ctx: AuditContext,
) -> DataSubjectRequest:
    dsr = await consent_repo.create_data_subject_request(
        db,
        user_id=user_id,
        request_type=DataSubjectRequestType.ERASURE,
        received_at=datetime.now(UTC),
    )
    await write_audit(
        db,
        audit_ctx,
        action="request_erasure",
        resource_type="data_subject_request",
        resource_id=dsr.id,
        allowed=True,
    )
    return dsr
