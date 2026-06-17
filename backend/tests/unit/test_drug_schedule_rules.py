"""Unit tests for the pure drug schedule rule checker (no DB required).

Tests check_drug_entry() in prescription_service — the synchronous function
that enforces TPG 2020 drug schedule rules given a DrugCatalogue entry.
"""

from __future__ import annotations

import types

import pytest

from app.services.prescription_service import PrescriptionError, check_drug_entry


def _entry(
    *,
    name: str = "test drug",
    schedule: str = "H",
    prohibited: bool = False,
    vertical: str | None = None,
) -> object:
    """Return a duck-typed stand-in for DrugCatalogue (avoids SQLAlchemy instrumentation)."""
    return types.SimpleNamespace(
        drug_generic_name=name,
        drug_schedule=schedule,
        is_prohibited=prohibited,
        requires_vertical=vertical,
    )


def test_unknown_drug_passes_through() -> None:
    result = check_drug_entry(
        drug_generic_name="custom compounded vitamin",
        entry=None,
        doctor_verticals=["thyroid"],
    )
    assert result is None


def test_schedule_h_drug_is_allowed() -> None:
    result = check_drug_entry(
        drug_generic_name="levothyroxine",
        entry=_entry(schedule="H"),
        doctor_verticals=["thyroid"],
    )
    assert result == "H"


def test_schedule_none_drug_is_allowed() -> None:
    result = check_drug_entry(
        drug_generic_name="metformin",
        entry=_entry(schedule="NONE"),
        doctor_verticals=["weight"],
    )
    assert result == "NONE"


def test_schedule_x_is_blocked() -> None:
    with pytest.raises(PrescriptionError) as exc_info:
        check_drug_entry(
            drug_generic_name="alprazolam",
            entry=_entry(schedule="X"),
            doctor_verticals=["thyroid"],
        )
    assert exc_info.value.code == "schedule_x_not_prescribable"


def test_schedule_h1_is_blocked_via_telemedicine() -> None:
    with pytest.raises(PrescriptionError) as exc_info:
        check_drug_entry(
            drug_generic_name="isotretinoin",
            entry=_entry(schedule="H1"),
            doctor_verticals=["skin_hair"],
        )
    assert exc_info.value.code == "schedule_h1_not_prescribable_via_telemedicine"


def test_prohibited_drug_is_blocked() -> None:
    with pytest.raises(PrescriptionError) as exc_info:
        check_drug_entry(
            drug_generic_name="sibutramine",
            entry=_entry(schedule="NONE", prohibited=True),
            doctor_verticals=["weight"],
        )
    assert exc_info.value.code == "drug_prohibited"


def test_glp1_without_weight_vertical_is_blocked() -> None:
    with pytest.raises(PrescriptionError) as exc_info:
        check_drug_entry(
            drug_generic_name="semaglutide",
            entry=_entry(schedule="H", vertical="weight"),
            doctor_verticals=["thyroid"],
        )
    assert exc_info.value.code == "drug_requires_specialist_vertical"


def test_glp1_with_weight_vertical_is_allowed() -> None:
    result = check_drug_entry(
        drug_generic_name="semaglutide",
        entry=_entry(schedule="H", vertical="weight"),
        doctor_verticals=["weight", "thyroid"],
    )
    assert result == "H"
