"""Unit tests for erasure_repo.anonymize_pii_values — pure function, no DB."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.repositories.erasure import anonymize_pii_values

_CLINICAL_KEYS = frozenset(
    {"consultation_fee_paise", "discount_paise", "legal_hold_until", "drug_schedule"}
)

_PII_KEYS = frozenset(
    {
        "name", "email", "phone", "date_of_birth", "city", "state",
        "expo_push_token", "google_sub", "password_hash", "reset_otp_channel",
    }
)


def test_all_pii_fields_present() -> None:
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    values = anonymize_pii_values(user_id, now)
    assert _PII_KEYS <= values.keys()


def test_erased_email_contains_uuid() -> None:
    user_id = uuid.uuid4()
    values = anonymize_pii_values(user_id, datetime.now(UTC))
    assert str(user_id) in values["email"]
    assert values["email"].endswith("@erased.kyros.local")


def test_nullable_pii_fields_are_none() -> None:
    values = anonymize_pii_values(uuid.uuid4(), datetime.now(UTC))
    for key in ("phone", "date_of_birth", "city", "state", "expo_push_token",
                "google_sub", "password_hash", "reset_otp_channel"):
        assert values[key] is None, f"{key!r} should be None after erasure"


def test_erased_at_equals_now_argument() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    values = anonymize_pii_values(uuid.uuid4(), now)
    assert values["erased_at"] == now
    assert values["deleted_at"] == now


def test_no_clinical_keys_in_values() -> None:
    values = anonymize_pii_values(uuid.uuid4(), datetime.now(UTC))
    intersection = _CLINICAL_KEYS & values.keys()
    assert not intersection, f"Clinical keys should not appear: {intersection}"
