from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime

from app.worker import celery_app


def _run_async(coro: object) -> None:
    import asyncio as _asyncio
    _asyncio.run(coro)  # type: ignore[arg-type]


@celery_app.task(name="kyros.admin.process_data_export", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_data_export(self: object, user_id_str: str, request_id_str: str) -> None:
    _run_async(
        _process_data_export_async(uuid.UUID(user_id_str), uuid.UUID(request_id_str))
    )


@celery_app.task(name="kyros.admin.process_erasure", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_erasure(self: object, user_id_str: str, request_id_str: str) -> None:
    _run_async(
        _process_erasure_async(uuid.UUID(user_id_str), uuid.UUID(request_id_str))
    )


async def _process_data_export_async(
    user_id: uuid.UUID,
    request_id: uuid.UUID,
    db: object = None,
) -> None:
    """Build a ZIP of the user's exportable data and mark the DSR completed.

    In tests, pass db=<AsyncSession> to reuse the test transaction instead of
    opening a new session (which would not see uncommitted test fixtures).
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.enums import DataSubjectRequestStatus
    from app.models.consent import ConsentRecord, DataSubjectRequest
    from app.models.identity import User
    from app.repositories import consent as consent_repo

    async def _run(session: AsyncSession, owns_session: bool) -> None:
        user = await session.scalar(select(User).where(User.id == user_id))
        if user is None:
            return

        consent_records = list(
            (
                await session.execute(
                    select(ConsentRecord).where(ConsentRecord.user_id == user_id)
                )
            ).scalars()
        )
        dsrs = list(
            (
                await session.execute(
                    select(DataSubjectRequest).where(DataSubjectRequest.user_id == user_id)
                )
            ).scalars()
        )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "profile.json",
                json.dumps(
                    {
                        "id": str(user.id),
                        "name": user.name,
                        "role": user.role.value,
                        "created_at": user.created_at.isoformat(),
                    },
                    ensure_ascii=False,
                ),
            )
            zf.writestr(
                "consent_records.json",
                json.dumps(
                    [
                        {
                            "id": str(r.id),
                            "consent_type": r.consent_type.value,
                            "version": r.version,
                            "granted": r.granted,
                            "granted_at": r.granted_at.isoformat(),
                            "revoked_at": (
                                r.revoked_at.isoformat() if r.revoked_at else None
                            ),
                        }
                        for r in consent_records
                    ],
                    ensure_ascii=False,
                ),
            )
            zf.writestr(
                "data_subject_requests.json",
                json.dumps(
                    [
                        {
                            "id": str(d.id),
                            "request_type": d.request_type.value,
                            "status": d.status.value,
                            "received_at": d.received_at.isoformat(),
                            "completed_at": (
                                d.completed_at.isoformat() if d.completed_at else None
                            ),
                        }
                        for d in dsrs
                    ],
                    ensure_ascii=False,
                ),
            )
        zip_size = buf.tell()

        await consent_repo.update_data_subject_request_status(
            session,
            request_id=request_id,
            status=DataSubjectRequestStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            notes=json.dumps({"zip_size_bytes": zip_size}),
        )
        if owns_session:
            await session.commit()

    if db is not None:
        assert isinstance(db, AsyncSession)
        await _run(db, owns_session=False)
    else:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as owned_db:
            await _run(owned_db, owns_session=True)


async def _process_erasure_async(
    user_id: uuid.UUID,
    request_id: uuid.UUID,
    db: object = None,
) -> None:
    """Soft-delete the user (30-day grace period) and mark the DSR completed.

    In tests, pass db=<AsyncSession> to reuse the test transaction.
    """
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.enums import DataSubjectRequestStatus
    from app.models.identity import RefreshToken, User
    from app.repositories import consent as consent_repo

    async def _run(session: AsyncSession, owns_session: bool) -> None:
        now = datetime.now(UTC)
        await session.execute(
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(deleted_at=now, updated_at=now)
        )
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await consent_repo.update_data_subject_request_status(
            session,
            request_id=request_id,
            status=DataSubjectRequestStatus.COMPLETED,
            completed_at=now,
            notes="Soft-deleted. Hard delete scheduled after 30-day grace period.",
        )
        if owns_session:
            await session.commit()

    if db is not None:
        assert isinstance(db, AsyncSession)
        await _run(db, owns_session=False)
    else:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as owned_db:
            await _run(owned_db, owns_session=True)
