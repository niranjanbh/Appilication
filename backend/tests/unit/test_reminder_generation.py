"""Unit tests for the pure prescription→reminder mapping.

These assert the deterministic-transcription contract: a line maps to reminders
only when its structured fields unambiguously yield a daily schedule, and never
otherwise (no inference).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.db.enums import (
    FoodRelation,
    FrequencyCode,
    ReminderGeneratedBy,
    ReminderSourceType,
    ReminderType,
)
from app.models.clinic import PrescriptionItem
from app.services.reminder_generation import map_prescription_item_to_reminders

SIGNED_AT = datetime(2026, 6, 30, 6, 0, tzinfo=UTC)
PRESC_ID = uuid.uuid4()


def _item(**overrides: object) -> PrescriptionItem:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "prescription_id": PRESC_ID,
        "drug_generic_name": "Metformin",
        "dosage": "500 mg",
        "frequency_code": FrequencyCode.BD,
        "timing_slots": ["morning", "night"],
        "food_relation": FoodRelation.AFTER_FOOD,
        "duration_days": None,
        "instructions": None,
    }
    defaults.update(overrides)
    return PrescriptionItem(**defaults)  # type: ignore[arg-type]


def test_bd_two_slots_yields_two_daily_reminders() -> None:
    specs = map_prescription_item_to_reminders(
        _item(), prescription_id=PRESC_ID, signed_at=SIGNED_AT
    )
    assert len(specs) == 2
    crons = {s.schedule_cron for s in specs}
    assert crons == {"0 8 * * *", "0 21 * * *"}  # morning 08:00, night 21:00
    s = specs[0]
    assert s.label == "Metformin"
    assert s.type == ReminderType.MEDICATION
    assert s.source_type == ReminderSourceType.PRESCRIPTION.value
    assert s.source_id == PRESC_ID
    assert s.generated_by == ReminderGeneratedBy.DOCTOR.value
    assert s.extra_metadata["dosage"] == "500 mg"
    assert s.extra_metadata["with_food"] is True  # after_food
    assert s.extra_metadata["prescription_id"] == str(PRESC_ID)
    # Server-owned: empty channels so the backend dispatcher delivers it (a
    # ['push'] channel would make the dispatcher skip → no notification).
    assert s.notification_channels == []


def test_duration_days_sets_ends_at() -> None:
    specs = map_prescription_item_to_reminders(
        _item(frequency_code=FrequencyCode.OD, timing_slots=["morning"], duration_days=7),
        prescription_id=PRESC_ID,
        signed_at=SIGNED_AT,
    )
    assert len(specs) == 1
    assert specs[0].ends_at == SIGNED_AT + timedelta(days=7)


def test_open_ended_when_no_duration() -> None:
    specs = map_prescription_item_to_reminders(
        _item(frequency_code=FrequencyCode.OD, timing_slots=["morning"], duration_days=None),
        prescription_id=PRESC_ID,
        signed_at=SIGNED_AT,
    )
    assert specs[0].ends_at is None


def test_before_food_is_not_with_food() -> None:
    specs = map_prescription_item_to_reminders(
        _item(food_relation=FoodRelation.BEFORE_FOOD),
        prescription_id=PRESC_ID,
        signed_at=SIGNED_AT,
    )
    assert all(s.extra_metadata["with_food"] is False for s in specs)


def test_sos_yields_no_reminder() -> None:
    specs = map_prescription_item_to_reminders(
        _item(frequency_code=FrequencyCode.SOS, timing_slots=["morning"]),
        prescription_id=PRESC_ID,
        signed_at=SIGNED_AT,
    )
    assert specs == []


def test_weekly_yields_no_reminder() -> None:
    specs = map_prescription_item_to_reminders(
        _item(frequency_code=FrequencyCode.WEEKLY, timing_slots=["morning"]),
        prescription_id=PRESC_ID,
        signed_at=SIGNED_AT,
    )
    assert specs == []


def test_empty_timing_slots_yields_no_reminder() -> None:
    specs = map_prescription_item_to_reminders(
        _item(frequency_code=FrequencyCode.OD, timing_slots=[]),
        prescription_id=PRESC_ID,
        signed_at=SIGNED_AT,
    )
    assert specs == []


def test_unknown_timing_slot_is_skipped() -> None:
    specs = map_prescription_item_to_reminders(
        _item(frequency_code=FrequencyCode.OD, timing_slots=["dawn"]),
        prescription_id=PRESC_ID,
        signed_at=SIGNED_AT,
    )
    assert specs == []
