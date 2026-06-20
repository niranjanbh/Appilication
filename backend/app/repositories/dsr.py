"""DPDP data-subject-request repository.

Single source of truth for DSR queries and the status state machine, shared by
the Jinja admin queue (``/admin/dsr``) and the REST admin API
(``/v1/admin/dsr``). Keeps the inline SQL out of the view/router layers per the
repository-pattern rule.

The repository does not write the audit log or manage the transaction boundary —
the caller (router/view) owns auth, audit, and commit/rollback.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DataSubjectRequestStatus
from app.models.consent import DataSubjectRequest
from app.models.identity import User

# The status state machine — terminal states have no outbound transitions.
DSR_TRANSITIONS: dict[DataSubjectRequestStatus, tuple[DataSubjectRequestStatus, ...]] = {
    DataSubjectRequestStatus.RECEIVED: (
        DataSubjectRequestStatus.IN_PROGRESS,
        DataSubjectRequestStatus.REJECTED,
    ),
    DataSubjectRequestStatus.IN_PROGRESS: (
        DataSubjectRequestStatus.COMPLETED,
        DataSubjectRequestStatus.REJECTED,
    ),
    DataSubjectRequestStatus.COMPLETED: (),
    DataSubjectRequestStatus.REJECTED: (),
}

# Open (actionable) statuses, for the default queue view.
OPEN_STATUSES: tuple[DataSubjectRequestStatus, ...] = (
    DataSubjectRequestStatus.RECEIVED,
    DataSubjectRequestStatus.IN_PROGRESS,
)


def is_valid_transition(
    current: DataSubjectRequestStatus, target: DataSubjectRequestStatus
) -> bool:
    return target in DSR_TRANSITIONS.get(current, ())


async def list_dsr_requests(
    db: AsyncSession,
    *,
    status_filter: DataSubjectRequestStatus | None = None,
    open_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[tuple[DataSubjectRequest, str]], int]:
    """Return ``(DataSubjectRequest, user_name)`` pairs plus the total count.

    ``status_filter`` restricts to one status; ``open_only`` restricts to the
    actionable queue. They are mutually exclusive in practice (status_filter
    wins if both are supplied).
    """
    base = select(DataSubjectRequest, User.name).join(
        User, User.id == DataSubjectRequest.user_id
    )
    if status_filter is not None:
        base = base.where(DataSubjectRequest.status == status_filter)
    elif open_only:
        base = base.where(DataSubjectRequest.status.in_(OPEN_STATUSES))

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(DataSubjectRequest.received_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return [(row.DataSubjectRequest, row.name) for row in rows], total


async def get_dsr_request(
    db: AsyncSession, dsr_id: uuid.UUID
) -> tuple[DataSubjectRequest, str] | None:
    """Return one ``(DataSubjectRequest, user_name)`` pair, or None if missing."""
    result = await db.execute(
        select(DataSubjectRequest, User.name)
        .join(User, User.id == DataSubjectRequest.user_id)
        .where(DataSubjectRequest.id == dsr_id)
    )
    row = result.first()
    if row is None:
        return None
    return row.DataSubjectRequest, row.name


async def update_dsr_status(
    db: AsyncSession,
    dsr_id: uuid.UUID,
    new_status: DataSubjectRequestStatus,
    *,
    note: str | None = None,
) -> tuple[DataSubjectRequest, str] | None:
    """Transition a DSR to ``new_status`` if the move is valid.

    Returns the updated ``(DataSubjectRequest, user_name)`` pair on success.
    Returns None when the request does not exist OR the transition is not allowed
    from its current status — the caller maps None to its own 404/409 + denial
    audit (ambiguous by design, like the cross-user 404 pattern). Flushes; the
    caller commits.
    """
    pair = await get_dsr_request(db, dsr_id)
    if pair is None:
        return None
    dsr, user_name = pair

    if not is_valid_transition(dsr.status, new_status):
        return None

    now = datetime.now(UTC)
    dsr.status = new_status
    if new_status == DataSubjectRequestStatus.COMPLETED:
        dsr.completed_at = now
    if note and note.strip():
        stamp = now.strftime("%d %b %Y")
        appended = f"[{stamp}] {note.strip()[:400]}"
        dsr.notes = f"{dsr.notes}\n{appended}" if dsr.notes else appended
    await db.flush()
    return dsr, user_name
