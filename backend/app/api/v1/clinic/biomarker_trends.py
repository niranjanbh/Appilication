"""Biomarker trend endpoint — patient-scoped longitudinal view.

GET /v1/clinic/patient/biomarker-trends/{biomarker}?range=7d|30d|90d|1y|all

Aggregates biomarker values from kc_lab_reports.parsed_json across all processed
reports for the authenticated patient.  Returns data points in chronological order
plus a computed trend direction (better / steady / worse).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import lab_reports as lab_reports_repo

router = APIRouter(tags=["biomarker-trends"])

# ── Range parameter mapping ────────────────────────────────────────────────────

_RANGE_DAYS: dict[str, int | None] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
    "all": None,
}

# ── Pydantic schemas ───────────────────────────────────────────────────────────


class BiomarkerDataPoint(BaseModel):
    report_id: uuid.UUID
    report_date: date | None
    value: float
    unit: str
    ref_low: float | None
    ref_high: float | None
    flag: str | None
    lab_name: str | None
    consultation_id: uuid.UUID | None


class BiomarkerTrendResponse(BaseModel):
    biomarker_name: str
    unit: str
    data_points: list[BiomarkerDataPoint]
    ref_low: float | None
    ref_high: float | None
    trend: Literal["better", "steady", "worse"]


# ── Trend computation ──────────────────────────────────────────────────────────


def _compute_trend(
    points: list[BiomarkerDataPoint],
) -> Literal["better", "steady", "worse"]:
    """Compare the two most recent data points.

    If a reference range is present, trend is based on distance from the midpoint
    (closer = better).  Threshold: >5% of range width counts as directional.
    Without a reference range, flag changes drive the direction.
    """
    if len(points) < 2:
        return "steady"

    latest = points[-1]
    previous = points[-2]

    if latest.ref_low is not None and latest.ref_high is not None:
        midpoint = (latest.ref_low + latest.ref_high) / 2.0
        range_width = latest.ref_high - latest.ref_low
        if range_width > 0:
            latest_dist = abs(latest.value - midpoint)
            prev_dist = abs(previous.value - midpoint)
            change_ratio = (prev_dist - latest_dist) / range_width
            if change_ratio > 0.05:
                return "better"
            if change_ratio < -0.05:
                return "worse"
        return "steady"

    latest_normal = latest.flag in (None, "normal")
    previous_normal = previous.flag in (None, "normal")

    if not previous_normal and latest_normal:
        return "better"
    if previous_normal and not latest_normal:
        return "worse"
    return "steady"


# ── Helpers ────────────────────────────────────────────────────────────────────


def _parse_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


class BiomarkerSummary(BaseModel):
    name: str
    latest_value: float | None
    unit: str
    ref_low: float | None
    ref_high: float | None
    flag: str | None
    report_date: date | None


class BiomarkerListResponse(BaseModel):
    biomarkers: list[BiomarkerSummary]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/biomarkers",
    response_model=BiomarkerListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_biomarkers(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> BiomarkerListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    rows = await lab_reports_repo.list_distinct_biomarkers_for_patient(
        db, patient_user_id=user.id,
    )
    await write_audit(db, ctx, action="list_biomarkers", allowed=True)

    biomarkers = [
        BiomarkerSummary(
            name=str(row["name"]),
            latest_value=_parse_float(row.get("latest_value")),
            unit=str(row.get("unit") or ""),
            ref_low=_parse_float(row.get("ref_low")),
            ref_high=_parse_float(row.get("ref_high")),
            flag=row.get("flag"),
            report_date=row.get("report_date"),
        )
        for row in rows
    ]
    return BiomarkerListResponse(biomarkers=biomarkers)


@router.get(
    "/biomarker-trends/{biomarker}",
    response_model=BiomarkerTrendResponse,
    status_code=status.HTTP_200_OK,
)
async def get_biomarker_trend(
    biomarker: str,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    range: str = Query(default="all", pattern=r"^(7d|30d|90d|1y|all)$"),
) -> BiomarkerTrendResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    range_days = _RANGE_DAYS[range]

    rows = await lab_reports_repo.get_biomarker_trend_for_patient(
        db,
        patient_user_id=user.id,
        biomarker_name=biomarker,
        range_days=range_days,
    )

    await write_audit(
        db,
        ctx,
        action="view_biomarker_trend",
        allowed=True,
    )

    if not rows:
        return BiomarkerTrendResponse(
            biomarker_name=biomarker,
            unit="",
            data_points=[],
            ref_low=None,
            ref_high=None,
            trend="steady",
        )

    data_points: list[BiomarkerDataPoint] = []
    for row in rows:
        value = _parse_float(row.get("value"))
        if value is None:
            continue
        data_points.append(
            BiomarkerDataPoint(
                report_id=uuid.UUID(str(row["report_id"])),
                report_date=row.get("report_date"),
                value=value,
                unit=str(row.get("unit") or ""),
                ref_low=_parse_float(row.get("ref_low")),
                ref_high=_parse_float(row.get("ref_high")),
                flag=row.get("flag"),
                lab_name=row.get("lab_name"),
                consultation_id=(
                    uuid.UUID(str(row["consultation_id"]))
                    if row.get("consultation_id")
                    else None
                ),
            )
        )

    if not data_points:
        return BiomarkerTrendResponse(
            biomarker_name=biomarker,
            unit="",
            data_points=[],
            ref_low=None,
            ref_high=None,
        )

    latest = data_points[-1]
    canonical_ref_low = latest.ref_low
    canonical_ref_high = latest.ref_high

    return BiomarkerTrendResponse(
        biomarker_name=str(rows[0].get("biomarker_name") or biomarker),
        unit=data_points[0].unit if data_points else "",
        data_points=data_points,
        ref_low=canonical_ref_low,
        ref_high=canonical_ref_high,
        trend=_compute_trend(data_points),
    )
