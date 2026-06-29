"""Consultation lifecycle maintenance tasks.

Beat task `mark_auto_no_show` runs every 15 minutes and transitions stale
CONFIRMED consultations to NO_SHOW: those whose scheduled end is past by >= 30
minutes and that nobody ever joined (``actual_start_at IS NULL``).

Patterned after ``video_tasks.py`` — structlog binding, single asyncio.run bridge,
AsyncSessionLocal session lifecycle, beat task does not retry (next tick fires again).
"""

from __future__ import annotations

from typing import Any

import structlog

from app.worker import celery_app

logger = structlog.get_logger(__name__)

GRACE_MINUTES = 30


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.consultation.mark_auto_no_show",
    bind=True,
    max_retries=0,  # beat task — don't retry, next tick fires again
    acks_late=True,
)
def mark_auto_no_show(self: Any) -> dict[str, int]:
    """Beat task: transition stale CONFIRMED consultations to NO_SHOW."""
    import asyncio

    return asyncio.run(_mark_auto_no_show_async())


async def _mark_auto_no_show_async() -> dict[str, int]:
    from app.db.enums import ConsultationStatus
    from app.db.session import AsyncSessionLocal
    from app.repositories import consultations as consultations_repo

    marked = 0
    async with AsyncSessionLocal() as db:
        stale = await consultations_repo.get_stale_confirmed_consultations(
            db, grace_minutes=GRACE_MINUTES
        )
        for consultation in stale:
            updated = await consultations_repo.update_consultation(
                db,
                consultation_id=consultation.id,
                status=ConsultationStatus.NO_SHOW,
            )
            if updated is not None:
                await consultations_repo.release_slot(
                    db, consultation_id=consultation.id
                )
                marked += 1
                logger.info(
                    "consultation.auto_no_show",
                    consultation_id=str(consultation.id),
                )
        await db.commit()

    logger.info("consultation.mark_auto_no_show.done", marked=marked)
    return {"marked": marked}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.consultation.expire_unpaid_scheduled",
    bind=True,
    max_retries=0,  # beat task — don't retry, next tick fires again
    acks_late=True,
)
def expire_unpaid_scheduled(self: Any) -> dict[str, int]:
    """Beat task: cancel SCHEDULED consultations whose start time has passed unpaid.

    A SCHEDULED consultation that was never paid+confirmed (assign flow) or never
    intake-confirmed (coordinator book flow) holds its Availability slot indefinitely.
    Once its start time is past by the grace window it can never be honoured, so we
    cancel it and release the slot back to AVAILABLE. No refund is involved — these
    were never paid (a captured payment transitions the consult to CONFIRMED).
    """
    import asyncio

    return asyncio.run(_expire_unpaid_scheduled_async())


async def _expire_unpaid_scheduled_async() -> dict[str, int]:
    from app.db.enums import ConsultationStatus
    from app.db.session import AsyncSessionLocal
    from app.repositories import consultations as consultations_repo

    expired = 0
    async with AsyncSessionLocal() as db:
        stale = await consultations_repo.get_expired_unpaid_consultations(
            db, grace_minutes=GRACE_MINUTES
        )
        for consultation in stale:
            updated = await consultations_repo.update_consultation(
                db,
                consultation_id=consultation.id,
                status=ConsultationStatus.CANCELLED,
                cancellation_reason="Auto-cancelled — payment not completed before the scheduled time.",
            )
            if updated is not None:
                await consultations_repo.release_slot(
                    db, consultation_id=consultation.id
                )
                expired += 1
                logger.info(
                    "consultation.expire_unpaid",
                    consultation_id=str(consultation.id),
                )
        await db.commit()

    logger.info("consultation.expire_unpaid_scheduled.done", expired=expired)
    return {"expired": expired}
