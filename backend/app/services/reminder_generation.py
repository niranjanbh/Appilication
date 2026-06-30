"""Deterministic generation of patient reminders from clinical sources.

The system **transcribes** a doctor's structured order into reminders; it never
interprets or infers a schedule (NMC TPG 2020 §3.5 — clinical judgement stays
with the RMP). A prescription line only produces reminders when its structured
fields unambiguously yield a daily schedule:

* ``frequency_code`` is a daily cadence (OD/BD/TDS/QID/HS), and
* ``timing_slots`` is non-empty (the doctor chose the times of day).

Anything else — SOS/PRN, weekly/alternate/monthly cadences, or a daily line with
no timing slots — produces **no** reminder. Those need explicit clinician or
patient scheduling rather than a guessed time.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.enums import (
    FoodRelation,
    FrequencyCode,
    ReminderGeneratedBy,
    ReminderSourceType,
    ReminderType,
    TimingSlot,
)
from app.models.clinic import Prescription, PrescriptionItem
from app.repositories import reminders as reminders_repo

logger = structlog.get_logger(__name__)

# Frequency codes that map to an every-day schedule. Non-daily cadences
# (weekly, alternate-day, monthly) and as-needed (SOS) are intentionally absent:
# their exact firing days cannot be derived from the prescription deterministically.
_DAILY_FREQUENCIES: frozenset[FrequencyCode] = frozenset(
    {
        FrequencyCode.OD,
        FrequencyCode.BD,
        FrequencyCode.TDS,
        FrequencyCode.QID,
        FrequencyCode.HS,
    }
)

# Food relations that mean "take with food", surfaced as metadata.with_food.
_WITH_FOOD: frozenset[FoodRelation] = frozenset(
    {FoodRelation.WITH_FOOD, FoodRelation.AFTER_FOOD}
)


@dataclass(frozen=True)
class ReminderSpec:
    """A single reminder to create — the pure output of the mapping step."""

    label: str
    schedule_cron: str
    type: ReminderType
    ends_at: datetime | None
    source_type: str
    source_id: uuid.UUID
    generated_by: str
    extra_metadata: dict[str, Any] = field(default_factory=dict)
    notification_channels: list[str] = field(default_factory=lambda: ["push"])


def _slot_time(slot: TimingSlot) -> tuple[int, int] | None:
    """Configured (hour, minute) IST for a timing slot, or None if unparseable."""
    raw = {
        TimingSlot.MORNING: settings.reminder_slot_time_morning,
        TimingSlot.AFTERNOON: settings.reminder_slot_time_afternoon,
        TimingSlot.EVENING: settings.reminder_slot_time_evening,
        TimingSlot.NIGHT: settings.reminder_slot_time_night,
    }.get(slot)
    if not raw:
        return None
    try:
        hh, mm = raw.split(":", 1)
        hour, minute = int(hh), int(mm)
    except (ValueError, AttributeError):
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def _slot_cron(slot: TimingSlot) -> str | None:
    hm = _slot_time(slot)
    if hm is None:
        return None
    hour, minute = hm
    return f"{minute} {hour} * * *"


def map_prescription_item_to_reminders(
    item: PrescriptionItem,
    *,
    prescription_id: uuid.UUID,
    signed_at: datetime,
) -> list[ReminderSpec]:
    """Transcribe one prescription line into zero or more daily reminders.

    Returns an empty list when the line cannot be mapped deterministically
    (non-daily cadence, no timing slots, or unknown slot values).
    """
    try:
        frequency = FrequencyCode(item.frequency_code)
    except ValueError:
        return []
    if frequency not in _DAILY_FREQUENCIES:
        return []

    raw_slots = item.timing_slots or []
    if not raw_slots:
        return []

    # End of a finite course: signed instant + duration_days. NULL = open-ended.
    ends_at: datetime | None = None
    if item.duration_days and item.duration_days > 0:
        ends_at = signed_at + timedelta(days=item.duration_days)

    food_relation = item.food_relation
    with_food = food_relation in _WITH_FOOD if food_relation is not None else False

    base_metadata: dict[str, Any] = {
        "prescription_id": str(prescription_id),
        "prescription_item_id": str(item.id),
        "dosage": item.dosage,
        "with_food": with_food,
    }
    if food_relation is not None:
        base_metadata["food_relation"] = food_relation.value
    if item.instructions:
        base_metadata["instructions"] = item.instructions

    specs: list[ReminderSpec] = []
    for raw_slot in raw_slots:
        try:
            slot = TimingSlot(raw_slot)
        except ValueError:
            continue  # unknown slot value — skip, never guess
        cron = _slot_cron(slot)
        if cron is None:
            continue
        specs.append(
            ReminderSpec(
                label=item.drug_generic_name,
                schedule_cron=cron,
                type=ReminderType.MEDICATION,
                ends_at=ends_at,
                source_type=ReminderSourceType.PRESCRIPTION.value,
                source_id=prescription_id,
                generated_by=ReminderGeneratedBy.DOCTOR.value,
                extra_metadata={**base_metadata, "timing_slot": slot.value},
                # Empty channels (not ['push']): the device never schedules a local
                # notification for a server-generated reminder, so delivery is the
                # server dispatcher's job. ['push'] would make it skip → no
                # notification at all. The mobile only schedules local for reminders
                # whose channels include 'push'.
                notification_channels=[],
            )
        )
    return specs


async def generate_for_prescription(
    db: AsyncSession,
    *,
    prescription: Prescription,
    items: list[PrescriptionItem],
    patient_user_id: uuid.UUID,
) -> int:
    """Create reminders for a freshly-signed prescription. Returns count created.

    Idempotent per prescription: any active reminders previously generated from
    this prescription are deactivated first, so a re-sign/regeneration replaces
    rather than duplicates. (A future supersede flow deactivates the prior
    version's reminders the same way, via its prescription id.)
    """
    signed_at = prescription.signed_at or datetime.now(UTC)

    await reminders_repo.deactivate_reminders_for_source(
        db,
        user_id=patient_user_id,
        source_type=ReminderSourceType.PRESCRIPTION.value,
        source_id=prescription.id,
    )

    created = 0
    for item in items:
        for spec in map_prescription_item_to_reminders(
            item, prescription_id=prescription.id, signed_at=signed_at
        ):
            await reminders_repo.create_reminder(
                db,
                user_id=patient_user_id,
                type=spec.type,
                label=spec.label,
                schedule_cron=spec.schedule_cron,
                schedule_interval_minutes=None,
                notification_channels=spec.notification_channels,
                extra_metadata=spec.extra_metadata,
                ends_at=spec.ends_at,
                source_type=spec.source_type,
                source_id=spec.source_id,
                generated_by=spec.generated_by,
            )
            created += 1

    logger.info(
        "prescription_reminders_generated",
        prescription_id=str(prescription.id),
        reminders_created=created,
        items=len(items),
    )
    return created
