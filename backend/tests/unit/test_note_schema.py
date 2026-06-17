"""Unit tests for NoteCreate's SOAP content validator (pure — no DB)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.doctor.consultations import NoteCreate


def test_note_with_only_content_is_valid() -> None:
    note = NoteCreate(content="Patient reports fatigue.")
    assert note.content == "Patient reports fatigue."
    assert note.subjective is None


def test_note_with_only_soap_fields_is_valid() -> None:
    note = NoteCreate(
        subjective="Fatigue for 3 weeks.",
        objective="BP 120/80, TSH pending.",
        assessment="Suspected hypothyroidism.",
        plan="Order TSH, FT4; review in 2 weeks.",
    )
    assert note.content is None
    assert note.subjective == "Fatigue for 3 weeks."


def test_note_with_mix_of_content_and_soap_is_valid() -> None:
    note = NoteCreate(content="General note.", assessment="Suspected hypothyroidism.")
    assert note.content == "General note."
    assert note.assessment == "Suspected hypothyroidism."


def test_note_with_all_fields_empty_is_invalid() -> None:
    with pytest.raises(ValidationError):
        NoteCreate()


def test_note_with_all_fields_whitespace_is_invalid() -> None:
    with pytest.raises(ValidationError):
        NoteCreate(content="   ", subjective="\t", objective="", assessment=None, plan="  ")
