from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ReminderAction, ReminderType
from app.integrations import s3
from app.models.wellness import Reminder, ReminderLog
from app.repositories import medication_catalog as catalog_repo
from app.repositories import reminders as reminders_repo

_ALLOWED_IMAGE_TYPES = s3.IMAGE_CONTENT_TYPES
_MAX_IMAGE_BYTES = s3.MAX_IMAGE_SIZE_BYTES


class ReminderImageError(Exception):
    """Raised for reminder-image validation failures (bad type/size)."""


async def create_reminder(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: ReminderType,
    label: str,
    schedule_cron: str | None,
    schedule_interval_minutes: int | None,
    notification_channels: list[Any],
    extra_metadata: dict[str, Any] | None,
) -> Reminder:
    return await reminders_repo.create_reminder(
        db,
        user_id=user_id,
        type=type,
        label=label,
        schedule_cron=schedule_cron,
        schedule_interval_minutes=schedule_interval_minutes,
        notification_channels=notification_channels,
        extra_metadata=extra_metadata,
    )


async def log_adherence(
    db: AsyncSession,
    *,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    scheduled_at: datetime,
    action: ReminderAction,
    notes: str | None,
) -> ReminderLog:
    return await reminders_repo.log_adherence(
        db,
        reminder_id=reminder_id,
        user_id=user_id,
        scheduled_at=scheduled_at,
        action=action,
        action_at=datetime.now(UTC),
        notes=notes,
    )


# ── Reminder image (patient-uploaded custom photo) ──────────────────────────────
#
# The S3 key + content-type live in the reminder's JSONB metadata under
# `image_key` / `image_content_type`. A doctor-attached catalog image is instead
# referenced by `catalog_id`. get_image_url resolves whichever is present.


def _validate_image(content_type: str, file_size_bytes: int) -> None:
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise ReminderImageError(
            f"content_type must be one of: {', '.join(sorted(_ALLOWED_IMAGE_TYPES))}"
        )
    if file_size_bytes <= 0 or file_size_bytes > _MAX_IMAGE_BYTES:
        raise ReminderImageError(
            f"file_size_bytes must be between 1 and {_MAX_IMAGE_BYTES}"
        )


async def initiate_image_upload(
    db: AsyncSession,
    *,
    reminder: Reminder,
    filename: str,
    content_type: str,
    file_size_bytes: int,
) -> dict[str, Any]:
    """Presigned POST for a patient's custom reminder photo; store pending key."""
    _validate_image(content_type, file_size_bytes)
    key = s3.reminder_image_s3_key(reminder.user_id, reminder.id, filename)
    presigned = s3.generate_image_upload_url(s3_key=key, content_type=content_type)

    meta = dict(reminder.extra_metadata or {})
    meta["image_key"] = key
    meta["image_content_type"] = content_type
    await reminders_repo.update_reminder(
        db, reminder_id=reminder.id, user_id=reminder.user_id, extra_metadata=meta
    )
    return {
        "reminder_id": reminder.id,
        "upload_url": presigned["upload_url"],
        "fields": presigned["fields"],
        "s3_key": presigned["s3_key"],
        "content_type": content_type,
    }


async def finalize_image_upload(db: AsyncSession, *, reminder: Reminder) -> bool:
    """Verify the uploaded object exists in S3."""
    key = (reminder.extra_metadata or {}).get("image_key")
    if not key:
        raise ReminderImageError("No pending image upload to finalize")
    meta = await asyncio.to_thread(s3.head_object, s3_key=key)
    if meta is None:
        raise ReminderImageError(
            "Upload not found in S3. Complete the upload before finalizing."
        )
    return True


async def get_image_url(db: AsyncSession, *, reminder: Reminder) -> str | None:
    """Presigned GET URL for a reminder image.

    Resolution: patient custom photo (`image_key`) first, then a doctor-attached
    catalog image (`catalog_id`). None if neither is set.
    """
    meta = reminder.extra_metadata or {}
    key = meta.get("image_key")
    if key:
        return s3.generate_download_url(s3_key=key)

    catalog_id = meta.get("catalog_id")
    if catalog_id:
        try:
            cid = uuid.UUID(str(catalog_id))
        except ValueError:
            return None
        entry = await catalog_repo.get(db, catalog_id=cid)
        if entry is not None and entry.image_s3_key is not None:
            return s3.generate_download_url(s3_key=entry.image_s3_key)
    return None


async def remove_image(db: AsyncSession, *, reminder: Reminder) -> None:
    """Delete the patient's custom photo from S3 and drop its metadata reference.

    Only the patient-uploaded object (`image_key`) is removed. A doctor-attached
    catalog image (`catalog_id`) is shared and owned by the catalog, so it is
    never deleted here.
    """
    meta = dict(reminder.extra_metadata or {})
    key = meta.pop("image_key", None)
    meta.pop("image_content_type", None)
    if key:
        await asyncio.to_thread(s3.delete_object, s3_key=str(key))
    await reminders_repo.update_reminder(
        db, reminder_id=reminder.id, user_id=reminder.user_id, extra_metadata=meta
    )


async def delete_reminder(db: AsyncSession, *, reminder: Reminder) -> None:
    """Soft-delete a reminder, cleaning up its custom S3 photo first.

    The S3 object would otherwise be orphaned, since the soft delete leaves the
    row (and its `image_key` metadata) in place. The catalog image, if any, is
    left untouched.
    """
    key = (reminder.extra_metadata or {}).get("image_key")
    if key:
        await asyncio.to_thread(s3.delete_object, s3_key=str(key))
    await reminders_repo.soft_delete_reminder(
        db, reminder_id=reminder.id, user_id=reminder.user_id
    )
