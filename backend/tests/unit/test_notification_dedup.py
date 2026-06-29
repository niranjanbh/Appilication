"""Unit tests for the notification dedup key (pure — no Redis).

Regression: the 24h dedup window was keyed on (channel, address, title/subject).
Because staff-aggregator emails reuse a constant subject across resources (e.g.
"A patient has been scheduled with you on Kyros"), a doctor or coordinator only
received the first alert per 24h. Notifications now pass a per-resource dedup_id;
these tests pin that distinct resources don't collide while a retry of the same
resource still dedups.
"""

from __future__ import annotations

from app.tasks.notification_tasks import _dedup_key


def test_dedup_key_distinguishes_distinct_resources() -> None:
    # Same channel + same recipient, different resource → different dedup keys.
    k1 = _dedup_key("email", "dr@test.kyros.local", "doctor_consult_assigned:c1")
    k2 = _dedup_key("email", "dr@test.kyros.local", "doctor_consult_assigned:c2")
    assert k1 != k2


def test_dedup_key_stable_for_same_resource() -> None:
    # A retry of the same notification must converge on the same key (idempotent).
    k1 = _dedup_key("email", "dr@test.kyros.local", "doctor_consult_assigned:c1")
    k2 = _dedup_key("email", "dr@test.kyros.local", "doctor_consult_assigned:c1")
    assert k1 == k2


def test_dedup_key_separates_channels() -> None:
    # The same resource on push vs email must not share a reservation.
    push = _dedup_key("push", "tok", "consultation_completed:c1")
    email = _dedup_key("email", "tok", "consultation_completed:c1")
    assert push != email


def test_dedup_key_separates_recipients() -> None:
    # Two doctors assigned the same event type get independent reservations.
    a = _dedup_key("email", "a@test.kyros.local", "coordinator_new_request:c1")
    b = _dedup_key("email", "b@test.kyros.local", "coordinator_new_request:c1")
    assert a != b
