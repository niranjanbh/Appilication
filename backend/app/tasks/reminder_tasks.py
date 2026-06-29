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

    from app.db.enums import ReminderType
    from app.db.session import AsyncSessionLocal
    from app.repositories.reminders import get_due_reminders
    from app.services.notifications import notify_medication_reminder

    async with AsyncSessionLocal() as db:
        # Schedule-aware: each pair is a reminder genuinely due in this window plus
        # its occurrence timestamp (the dispatch idempotency slot).
        due = await get_due_reminders(db, active_only=True)
        dispatched = 0
        for reminder, occurrence in due:
            # Only fire push for medication reminders; other types handled separately
            if str(reminder.type) == ReminderType.MEDICATION.value:
                await notify_medication_reminder(
                    db,
                    user_id=_uuid.UUID(str(reminder.user_id)),
                    reminder_label=reminder.label,
                    reminder_id=_uuid.UUID(str(reminder.id)),
                    occurrence=occurrence,
                )
                dispatched += 1

    return {"dispatched_count": dispatched}
