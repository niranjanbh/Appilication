"""Unit tests for DiagnosisCreate's ICD-10 code validator (pure — no DB)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.doctor.consultations import DiagnosisCreate


@pytest.mark.parametrize("code", ["E28.2", "I10", "E66.01", "N53.11", "Z00.00"])
def test_valid_icd10_codes_are_accepted(code: str) -> None:
    diagnosis = DiagnosisCreate(icd10_code=code, icd10_description="Test diagnosis")
    assert diagnosis.icd10_code == code
    assert diagnosis.is_primary is False


@pytest.mark.parametrize("code", ["e28.2", "12345", "", "E2", "E283.456789"])
def test_invalid_icd10_codes_are_rejected(code: str) -> None:
    with pytest.raises(ValidationError):
        DiagnosisCreate(icd10_code=code, icd10_description="Test diagnosis")


def test_is_primary_can_be_set() -> None:
    diagnosis = DiagnosisCreate(
        icd10_code="E28.2", icd10_description="Polycystic ovarian syndrome", is_primary=True
    )
    assert diagnosis.is_primary is True
