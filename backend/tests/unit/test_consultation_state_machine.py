"""Unit tests for the consultation lifecycle transition table (pure — no DB)."""

from __future__ import annotations

import pytest

from app.db.enums import ConsultationStatus
from app.services.consultation_service import (
    _ALLOWED_TRANSITIONS,
    ConsultationError,
    _assert_transition,
)


def test_terminal_statuses_have_no_outgoing_transitions() -> None:
    for terminal in (
        ConsultationStatus.COMPLETED,
        ConsultationStatus.CANCELLED,
        ConsultationStatus.NO_SHOW,
    ):
        assert _ALLOWED_TRANSITIONS[terminal] == frozenset()


def test_scheduled_can_advance_to_confirmed_cancelled_or_no_show() -> None:
    assert _ALLOWED_TRANSITIONS[ConsultationStatus.SCHEDULED] == frozenset(
        {ConsultationStatus.CONFIRMED, ConsultationStatus.CANCELLED, ConsultationStatus.NO_SHOW}
    )


def test_confirmed_can_advance_to_in_progress_cancelled_or_no_show() -> None:
    assert _ALLOWED_TRANSITIONS[ConsultationStatus.CONFIRMED] == frozenset(
        {ConsultationStatus.IN_PROGRESS, ConsultationStatus.CANCELLED, ConsultationStatus.NO_SHOW}
    )


def test_in_progress_can_only_advance_to_completed() -> None:
    assert _ALLOWED_TRANSITIONS[ConsultationStatus.IN_PROGRESS] == frozenset(
        {ConsultationStatus.COMPLETED}
    )


def test_assert_transition_allows_confirmed_to_in_progress() -> None:
    _assert_transition(
        ConsultationStatus.CONFIRMED,
        ConsultationStatus.IN_PROGRESS,
        error_code="consultation_not_open_eligible",
    )


def test_assert_transition_allows_in_progress_to_completed() -> None:
    _assert_transition(
        ConsultationStatus.IN_PROGRESS,
        ConsultationStatus.COMPLETED,
        error_code="consultation_not_in_progress",
    )


def test_assert_transition_rejects_scheduled_to_in_progress() -> None:
    with pytest.raises(ConsultationError) as excinfo:
        _assert_transition(
            ConsultationStatus.SCHEDULED,
            ConsultationStatus.IN_PROGRESS,
            error_code="consultation_not_open_eligible",
        )
    assert excinfo.value.code == "consultation_not_open_eligible"


def test_assert_transition_rejects_confirmed_to_completed() -> None:
    with pytest.raises(ConsultationError) as excinfo:
        _assert_transition(
            ConsultationStatus.CONFIRMED,
            ConsultationStatus.COMPLETED,
            error_code="consultation_not_in_progress",
        )
    assert excinfo.value.code == "consultation_not_in_progress"


def test_assert_transition_rejects_from_terminal_status() -> None:
    with pytest.raises(ConsultationError) as excinfo:
        _assert_transition(
            ConsultationStatus.COMPLETED,
            ConsultationStatus.IN_PROGRESS,
            error_code="consultation_not_open_eligible",
        )
    assert excinfo.value.code == "consultation_not_open_eligible"


def test_assert_transition_default_error_code() -> None:
    with pytest.raises(ConsultationError) as excinfo:
        _assert_transition(ConsultationStatus.SCHEDULED, ConsultationStatus.COMPLETED)
    assert excinfo.value.code == "invalid_transition"
