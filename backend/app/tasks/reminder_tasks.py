from __future__ import annotations

import asyncio
from typing import Any

from app.worker import celery_app


def _run_async(coro: Any) -> Any:
    return asyncio.run(coro)


@celery_app.task(name="kyros.reminder.dispatch_due", bind=True)  # type: ignore[untyped-decorator]
def dispatch_due_reminders(self: object) -> dict[str, Any]:
    """Find active reminders and dispatch push notifications for due slots.

    Runs every 5 minutes via Celery beat. Idempotent: dispatching the same
    reminder twice in the same window will deduplicate at the notification layer
    via a Redis SETNX marker (future work once push integration is wired up).
    """
    return _run_async(_dispatch_due_async())  # type: ignore[no-any-return]


async def _dispatch_due_async() -> dict[str, Any]:
    import uuid as _uuid

    from app.db.session import AsyncSessionLocal
    from app.repositories.reminders import get_due_reminders
    from app.services.notifications import notify_reminder_due

    async with AsyncSessionLocal() as db:
        due = await get_due_reminders(db, active_only=True)
        dispatched = 0
        skipped_local = 0
        for reminder, _occurrence in due:
            # Skip server push when the device already has a local notification
            # scheduled — sending both would double-notify the patient.
            channels = reminder.notification_channels or []
            if "push" in channels:
                skipped_local += 1
                continue
            await notify_reminder_due(
                db,
                user_id=_uuid.UUID(str(reminder.user_id)),
                reminder_label=reminder.label,
                reminder_type=reminder.type.value,
            )
            dispatched += 1

    return {"dispatched_count": dispatched, "skipped_local_count": skipped_local}
