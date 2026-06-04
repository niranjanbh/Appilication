"""Unit tests for the Document AI integration module.

Tests operate entirely in stub mode (no GCP credentials required).
"""

from __future__ import annotations

from app.integrations.document_ai import (
    _DOCTOR_REVIEW_THRESHOLD,
    _PATIENT_CORRECTION_THRESHOLD,
    _apply_confidence_thresholds,
    parse_healthcare_document,
)


def test_stub_mode_returns_synthetic_response() -> None:
    """parse_healthcare_document returns stub data when no credentials are configured."""
    result = parse_healthcare_document(b"fake-pdf-bytes")
    assert "_stub" in result
    assert result["_stub"] is True
    assert "biomarkers" in result
    assert isinstance(result["biomarkers"], list)
    assert len(result["biomarkers"]) > 0


def test_stub_has_required_shape_fields() -> None:
    result = parse_healthcare_document(b"fake-pdf-bytes")
    assert "lab_name" in result
    assert "report_date" in result
    assert "patient_info" in result
    assert "overall_confidence" in result


def test_stub_biomarkers_have_confidence_field() -> None:
    result = parse_healthcare_document(b"fake-pdf-bytes")
    for bm in result["biomarkers"]:
        assert "confidence" in bm
        assert "needs_patient_correction" in bm


def test_stub_low_confidence_fields_populated() -> None:
    result = parse_healthcare_document(b"fake-pdf-bytes")
    low = result.get("_low_confidence_fields", [])
    assert isinstance(low, list)


class TestApplyConfidenceThresholds:
    def test_high_confidence_no_flags(self) -> None:
        biomarkers = [{"name": "TSH", "value": "4.8", "confidence": 0.95}]
        annotated, low = _apply_confidence_thresholds(biomarkers)
        assert annotated[0]["needs_patient_correction"] is False
        assert low == []

    def test_medium_confidence_flags_doctor_review(self) -> None:
        biomarkers = [{"name": "T4", "value": "8.5", "confidence": 0.80}]
        annotated, low = _apply_confidence_thresholds(biomarkers)
        assert annotated[0]["needs_patient_correction"] is False
        assert "T4" in low

    def test_low_confidence_flags_patient_correction(self) -> None:
        biomarkers = [{"name": "FT3", "value": "3.1", "confidence": 0.50}]
        annotated, low = _apply_confidence_thresholds(biomarkers)
        assert annotated[0]["needs_patient_correction"] is True
        assert "FT3" in low

    def test_threshold_boundary_doctor_review(self) -> None:
        # Exactly at the doctor-review threshold is NOT below it → no flag
        biomarkers = [{"name": "X", "value": "1.0", "confidence": _DOCTOR_REVIEW_THRESHOLD}]
        _, low = _apply_confidence_thresholds(biomarkers)
        assert low == []

    def test_threshold_boundary_patient_correction(self) -> None:
        # Exactly at the patient-correction threshold is NOT below it → no patient flag
        biomarkers = [{"name": "Y", "value": "2.0", "confidence": _PATIENT_CORRECTION_THRESHOLD}]
        annotated, _ = _apply_confidence_thresholds(biomarkers)
        assert annotated[0]["needs_patient_correction"] is False

    def test_just_below_patient_correction_threshold(self) -> None:
        biomarkers = [{"name": "Z", "value": "0.0", "confidence": _PATIENT_CORRECTION_THRESHOLD - 0.01}]
        annotated, low = _apply_confidence_thresholds(biomarkers)
        assert annotated[0]["needs_patient_correction"] is True
        assert "Z" in low

    def test_mixed_biomarkers(self) -> None:
        biomarkers = [
            {"name": "TSH", "value": "4.8", "confidence": 0.95},
            {"name": "T4", "value": "8.5", "confidence": 0.80},
            {"name": "FT3", "value": "3.1", "confidence": 0.55},
        ]
        annotated, low = _apply_confidence_thresholds(biomarkers)
        assert annotated[0]["needs_patient_correction"] is False
        assert annotated[1]["needs_patient_correction"] is False
        assert annotated[2]["needs_patient_correction"] is True
        assert set(low) == {"T4", "FT3"}

    def test_empty_biomarkers(self) -> None:
        annotated, low = _apply_confidence_thresholds([])
        assert annotated == []
        assert low == []

    def test_missing_confidence_defaults_to_full(self) -> None:
        biomarkers = [{"name": "B12"}]
        annotated, low = _apply_confidence_thresholds(biomarkers)
        assert annotated[0]["needs_patient_correction"] is False
        assert low == []
