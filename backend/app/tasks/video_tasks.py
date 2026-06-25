"""Video room provisioning tasks (LiveKit integration).

Beat task `provision_upcoming_rooms` runs every minute and dispatches
`provision_video_room` for each unprovisioned consultation in the next 15 minutes.

Idempotency: `provision_video_room` exits early if video_room_id is already set.
Redis lock per consultation prevents concurrent workers from double-provisioning.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog

from app.worker import celery_app

logger = structlog.get_logger(__name__)


class HMSTransientError(Exception):
    """Raised for retryable video-provider API errors (network, 5xx).

    Name retained for backward compatibility with existing retry wiring; the
    provider is now LiveKit.
    """


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.video.provision_upcoming_rooms",
    bind=True,
    max_retries=0,  # beat task — don't retry, next minute fires again
    acks_late=True,
)
def provision_upcoming_rooms(self: Any) -> dict[str, int]:
    """Beat task: dispatch provision_video_room for consultations starting in ≤15 min."""
    return asyncio.run(_provision_upcoming_rooms_async())


async def _provision_upcoming_rooms_async() -> dict[str, int]:
    from app.db.session import AsyncSessionLocal
    from app.repositories import consultations as consultations_repo

    async with AsyncSessionLocal() as db:
        consultations = await consultations_repo.get_unprovisioned_consultations_in_window(
            db, window_minutes=15
        )

    dispatched = 0
    for consultation in consultations:
        provision_video_room.delay(str(consultation.id))
        dispatched += 1
        logger.info("video.dispatch_provision", consultation_id=str(consultation.id))

    logger.info("video.provision_upcoming_rooms.done", dispatched=dispatched)
    return {"dispatched": dispatched}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="kyros.video.provision_video_room",
    bind=True,
    autoretry_for=(HMSTransientError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True,
)
def provision_video_room(self: Any, consultation_id: str) -> dict[str, Any]:
    """Provision a LiveKit room for one consultation and persist the room_id."""
    bound_logger = logger.bind(
        task_name="provision_video_room",
        task_id=self.request.id,
        attempt=self.request.retries + 1,
        consultation_id=consultation_id,
    )
    bound_logger.info("task.started")
    try:
        result = asyncio.run(_provision_video_room_async(consultation_id, bound_logger))
        bound_logger.info("task.completed", result=result)
        return result
    except (HMSTransientError, ConnectionError, TimeoutError):
        bound_logger.warning("task.retrying", attempt=self.request.retries + 1)
        raise
    except Exception:
        bound_logger.exception("task.failed")
        raise


async def _provision_video_room_async(
    consultation_id: str,
    bound_logger: Any,
) -> dict[str, Any]:
    from app.db.session import AsyncSessionLocal
    from app.integrations import livekit_video
    from app.repositories import consultations as consultations_repo

    consult_uuid = uuid.UUID(consultation_id)

    async with AsyncSessionLocal() as db:
        consultation = await db.get(
            __import__("app.models.clinic", fromlist=["Consultation"]).Consultation,
            consult_uuid,
        )
        if consultation is None:
            bound_logger.warning("task.skipped", reason="consultation_not_found")
            return {"skipped": True, "reason": "consultation_not_found"}

        if consultation.video_room_id is not None:
            bound_logger.info("task.skipped", reason="already_provisioned", room_id=consultation.video_room_id)
            return {"skipped": True, "reason": "already_provisioned"}

        try:
            room_id = await livekit_video.create_room(consultation_id=consultation_id)
        except Exception as exc:
            if _is_transient(exc):
                raise HMSTransientError(str(exc)) from exc
            raise

        await consultations_repo.update_consultation_video_room(
            db, consultation_id=consult_uuid, video_room_id=room_id
        )
        await db.commit()

    return {"ok": True, "room_id": room_id}


def _is_transient(exc: Exception) -> bool:
    """Return True for errors worth retrying (network, 5xx)."""
    import httpx
    if isinstance(exc, (ConnectionError, TimeoutError, httpx.NetworkError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False
