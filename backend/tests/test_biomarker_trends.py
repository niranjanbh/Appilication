"""Tests for biomarker trend endpoint and trend computation logic.

Covers:
  - _compute_trend: better / steady / worse with and without ref ranges
  - GET /v1/clinic/patient/biomarker-trends/{biomarker}:
      - Empty response when patient has no reports
      - Correct data points when reports contain matching biomarker
      - Range filter (7d / 30d / 90d / 1y / all)
      - Invalid range parameter → 422
      - Cross-user isolation: patient only sees own data
      - Audit log written on access
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _synth_email, _synth_phone, make_auth_headers

# ── _compute_trend unit tests ──────────────────────────────────────────────────


def _make_point(
    value: float,
    ref_low: float | None = None,
    ref_high: float | None = None,
    flag: str | None = None,
) -> object:
    from app.api.v1.clinic.biomarker_trends import BiomarkerDataPoint

    return BiomarkerDataPoint(
        report_id=uuid.uuid4(),
        report_date=date.today(),
        value=value,
        unit="mIU/L",
        ref_low=ref_low,
        ref_high=ref_high,
        flag=flag,
        lab_name=None,
        consultation_id=None,
    )


def test_compute_trend_single_point_is_steady() -> None:
    from app.api.v1.clinic.biomarker_trends import BiomarkerDataPoint, _compute_trend

    points: list[BiomarkerDataPoint] = [_make_point(2.5, ref_low=0.5, ref_high=4.5)]  # type: ignore[list-item]
    assert _compute_trend(points) == "steady"


def test_compute_trend_moving_toward_midpoint_is_better() -> None:
    from app.api.v1.clinic.biomarker_trends import BiomarkerDataPoint, _compute_trend

    # midpoint = 2.5; previous at 4.0 (far), latest at 2.6 (near)
    points: list[BiomarkerDataPoint] = [  # type: ignore[list-item]
        _make_point(4.0, ref_low=0.5, ref_high=4.5),
        _make_point(2.6, ref_low=0.5, ref_high=4.5),
    ]
    assert _compute_trend(points) == "better"


def test_compute_trend_moving_away_from_midpoint_is_worse() -> None:
    from app.api.v1.clinic.biomarker_trends import BiomarkerDataPoint, _compute_trend

    # midpoint = 2.5; previous at 2.6 (near), latest at 4.4 (far)
    points: list[BiomarkerDataPoint] = [  # type: ignore[list-item]
        _make_point(2.6, ref_low=0.5, ref_high=4.5),
        _make_point(4.4, ref_low=0.5, ref_high=4.5),
    ]
    assert _compute_trend(points) == "worse"


def test_compute_trend_tiny_change_is_steady() -> None:
    from app.api.v1.clinic.biomarker_trends import BiomarkerDataPoint, _compute_trend

    # <5% of range width (range=4.0, 5% = 0.2); dist change = 0.05
    points: list[BiomarkerDataPoint] = [  # type: ignore[list-item]
        _make_point(2.5, ref_low=0.5, ref_high=4.5),
        _make_point(2.55, ref_low=0.5, ref_high=4.5),
    ]
    assert _compute_trend(points) == "steady"


def test_compute_trend_no_ref_range_flag_normal_to_high_is_worse() -> None:
    from app.api.v1.clinic.biomarker_trends import BiomarkerDataPoint, _compute_trend

    points: list[BiomarkerDataPoint] = [  # type: ignore[list-item]
        _make_point(2.5, flag="normal"),
        _make_point(5.5, flag="high"),
    ]
    assert _compute_trend(points) == "worse"


def test_compute_trend_no_ref_range_flag_high_to_normal_is_better() -> None:
    from app.api.v1.clinic.biomarker_trends import BiomarkerDataPoint, _compute_trend

    points: list[BiomarkerDataPoint] = [  # type: ignore[list-item]
        _make_point(5.5, flag="high"),
        _make_point(2.5, flag="normal"),
    ]
    assert _compute_trend(points) == "better"


def test_compute_trend_no_ref_range_both_normal_is_steady() -> None:
    from app.api.v1.clinic.biomarker_trends import BiomarkerDataPoint, _compute_trend

    points: list[BiomarkerDataPoint] = [  # type: ignore[list-item]
        _make_point(2.4, flag="normal"),
        _make_point(2.6, flag="normal"),
    ]
    assert _compute_trend(points) == "steady"


# ── Fixtures ───────────────────────────────────────────────────────────────────


async def _make_patient(db: AsyncSession) -> object:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.models.clinic import Patient
    from app.repositories import users as users_repo

    user = await users_repo.create(
        db,
        name="Trend Patient",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    await users_repo.update_phone_verified(db, user.id)  # type: ignore[union-attr]
    patient = Patient(
        user_id=user.id,  # type: ignore[union-attr]
        kyros_patient_id=f"KP{uuid.uuid4().hex[:6].upper()}",
        primary_conditions=[],
    )
    db.add(patient)
    await db.flush()
    return user


async def _seed_lab_report(
    db: AsyncSession,
    patient_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    report_date: date,
    biomarker_value: str,
    flag: str = "normal",
    ref_low: str = "0.5",
    ref_high: str = "4.5",
) -> None:
    from app.db.enums import LabReportStatus
    from app.models.clinic import LabReport

    parsed_json = {
        "lab_name": "Test Lab",
        "report_date": str(report_date),
        "patient_info": None,
        "overall_confidence": 0.95,
        "biomarkers": [
            {
                "name": "TSH",
                "value": biomarker_value,
                "unit": "mIU/L",
                "ref_low": ref_low,
                "ref_high": ref_high,
                "flag": flag,
                "confidence": 0.95,
                "needs_patient_correction": False,
            }
        ],
    }
    report = LabReport(
        patient_id=patient_id,
        uploaded_by_user_id=uploaded_by,
        original_filename="test.pdf",
        content_type="application/pdf",
        file_size_bytes=100_000,
        status=LabReportStatus.OCR_COMPLETE,
        report_date=report_date,
        lab_name="Test Lab",
        parsed_json=parsed_json,
    )
    db.add(report)
    await db.flush()


async def _get_patient_row(db: AsyncSession, user_id: uuid.UUID) -> object:
    from sqlalchemy import select

    from app.models.clinic import Patient

    result = await db.execute(select(Patient).where(Patient.user_id == user_id))
    return result.scalar_one()


# ── Endpoint integration tests ─────────────────────────────────────────────────


async def test_biomarker_trend_no_reports_returns_empty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _make_patient(db_session)
    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_points"] == []
    assert body["trend"] == "steady"
    assert body["biomarker_name"] == "TSH"


async def test_biomarker_trend_returns_data_points_in_order(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, user.id)  # type: ignore[union-attr]
    today = date.today()

    await _seed_lab_report(
        db_session, patient.id, user.id, today - timedelta(days=60), "4.0", flag="normal"  # type: ignore[union-attr]
    )
    await _seed_lab_report(
        db_session, patient.id, user.id, today - timedelta(days=30), "2.6", flag="normal"  # type: ignore[union-attr]
    )

    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data_points"]) == 2
    # Ordered oldest first
    assert body["data_points"][0]["value"] == pytest.approx(4.0)
    assert body["data_points"][1]["value"] == pytest.approx(2.6)
    assert body["trend"] == "better"


async def test_biomarker_trend_case_insensitive_name(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, user.id)  # type: ignore[union-attr]
    today = date.today()

    await _seed_lab_report(db_session, patient.id, user.id, today, "2.5")  # type: ignore[union-attr]

    for query_name in ("TSH", "tsh", "Tsh"):
        resp = await client.get(
            f"/v1/clinic/patient/biomarker-trends/{query_name}",
            headers=make_auth_headers(user),
        )
        assert resp.status_code == 200
        assert len(resp.json()["data_points"]) == 1, f"failed for name={query_name}"


async def test_biomarker_trend_range_filter_excludes_old_reports(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, user.id)  # type: ignore[union-attr]
    today = date.today()

    await _seed_lab_report(
        db_session, patient.id, user.id, today - timedelta(days=400), "4.0"  # type: ignore[union-attr]
    )
    await _seed_lab_report(
        db_session, patient.id, user.id, today - timedelta(days=10), "2.5"  # type: ignore[union-attr]
    )

    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH?range=30d",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data_points"]) == 1
    assert body["data_points"][0]["value"] == pytest.approx(2.5)


async def test_biomarker_trend_range_all_includes_all_reports(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, user.id)  # type: ignore[union-attr]
    today = date.today()

    await _seed_lab_report(db_session, patient.id, user.id, today - timedelta(days=400), "4.0")  # type: ignore[union-attr]
    await _seed_lab_report(db_session, patient.id, user.id, today - timedelta(days=10), "2.5")  # type: ignore[union-attr]

    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH?range=all",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 200
    assert len(resp.json()["data_points"]) == 2


async def test_biomarker_trend_invalid_range_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _make_patient(db_session)
    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH?range=invalid",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 422


async def test_biomarker_trend_cross_user_isolation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Patient A's reports are not visible to Patient B via the trend endpoint."""
    user_a = await _make_patient(db_session)
    user_b = await _make_patient(db_session)
    patient_a = await _get_patient_row(db_session, user_a.id)  # type: ignore[union-attr]
    today = date.today()

    await _seed_lab_report(db_session, patient_a.id, user_a.id, today, "3.5")  # type: ignore[union-attr]

    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH",
        headers=make_auth_headers(user_b),
    )
    assert resp.status_code == 200
    assert resp.json()["data_points"] == []


async def test_biomarker_trend_audit_log_written(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.models.audit import AuditLog

    user = await _make_patient(db_session)

    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "view_biomarker_trend",
            AuditLog.actor_user_id == user.id,  # type: ignore[union-attr]
            AuditLog.allowed.is_(True),
        )
    )
    assert result.scalar_one_or_none() is not None


async def test_biomarker_trend_ref_range_from_latest_report(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _make_patient(db_session)
    patient = await _get_patient_row(db_session, user.id)  # type: ignore[union-attr]
    today = date.today()

    await _seed_lab_report(
        db_session, patient.id, user.id,  # type: ignore[union-attr]
        today - timedelta(days=30), "4.0",
        ref_low="0.4", ref_high="4.0",
    )
    await _seed_lab_report(
        db_session, patient.id, user.id,  # type: ignore[union-attr]
        today, "2.5",
        ref_low="0.5", ref_high="4.5",
    )

    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 200
    body = resp.json()
    # Canonical ref range comes from the most recent data point
    assert body["ref_low"] == pytest.approx(0.5)
    assert body["ref_high"] == pytest.approx(4.5)
