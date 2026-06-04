"""Admin analytics endpoints.

GET /v1/admin/analytics/funnel              — acquisition funnel (4 stages)
GET /v1/admin/analytics/retention           — 30/60/90-day cohort retention
GET /v1/admin/analytics/revenue             — revenue by condition / doctor / period
GET /v1/admin/analytics/condition-mix       — consultation distribution across 7 verticals
GET /v1/admin/analytics/doctor-utilization  — consultations per doctor per week
GET /v1/admin/analytics/export              — CSV download for any of the above

All endpoints require super_admin role and audit-log every call.
No PHI: all responses are aggregated counts or paise sums.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_admin_user
from app.db.enums import ActorRole
from app.services import analytics_service

router = APIRouter(tags=["admin-analytics"])


# ── Helpers ────────────────────────────────────────────────────────────────────


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


# ── Schemas ────────────────────────────────────────────────────────────────────


class FunnelResponse(BaseModel):
    inquiries: int
    registrations: int
    bookings: int
    completions: int
    rate_inq_to_reg: float
    rate_reg_to_book: float
    rate_book_to_comp: float
    start_date: date | None
    end_date: date | None


class RetentionRow(BaseModel):
    cohort_month: str
    cohort_size: int
    returned_30: int
    returned_60: int
    returned_90: int
    rate_30: float
    rate_60: float
    rate_90: float


class RetentionResponse(BaseModel):
    cohorts: list[RetentionRow]
    cohort_months: int


class RevenueRow(BaseModel):
    dimension: str
    label: str
    consultation_count: int
    revenue_paise: int
    revenue_inr: float


class RevenueResponse(BaseModel):
    rows: list[RevenueRow]
    group_by: str
    start_date: date | None
    end_date: date | None


class ConditionMixRow(BaseModel):
    condition: str
    count: int
    pct: float


class ConditionMixResponse(BaseModel):
    rows: list[ConditionMixRow]
    start_date: date | None
    end_date: date | None


class DoctorUtilRow(BaseModel):
    doctor_id: str
    doctor_name: str
    week_start: str
    consultation_count: int


class DoctorUtilizationResponse(BaseModel):
    rows: list[DoctorUtilRow]
    weeks: int


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/analytics/funnel", response_model=FunnelResponse)
async def analytics_funnel(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> FunnelResponse:
    ctx = _audit_ctx(request, user)
    data = await analytics_service.get_funnel(
        db, start_date=start_date, end_date=end_date
    )
    await write_audit(
        db, ctx,
        action="view_analytics_funnel",
        resource_type="analytics",
        allowed=True,
    )
    return FunnelResponse(**data, start_date=start_date, end_date=end_date)


@router.get("/analytics/retention", response_model=RetentionResponse)
async def analytics_retention(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    cohort_months: int = Query(default=6, ge=1, le=12),
) -> RetentionResponse:
    ctx = _audit_ctx(request, user)
    rows = await analytics_service.get_retention(db, cohort_months=cohort_months)
    await write_audit(
        db, ctx,
        action="view_analytics_retention",
        resource_type="analytics",
        allowed=True,
    )
    return RetentionResponse(
        cohorts=[RetentionRow(**r) for r in rows],
        cohort_months=cohort_months,
    )


@router.get("/analytics/revenue", response_model=RevenueResponse)
async def analytics_revenue(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    group_by: Literal["condition", "doctor", "period"] = Query(default="condition"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> RevenueResponse:
    ctx = _audit_ctx(request, user)
    rows = await analytics_service.get_revenue(
        db, group_by=group_by, start_date=start_date, end_date=end_date
    )
    await write_audit(
        db, ctx,
        action="view_analytics_revenue",
        resource_type="analytics",
        allowed=True,
    )
    return RevenueResponse(
        rows=[RevenueRow(**r) for r in rows],
        group_by=group_by,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/analytics/condition-mix", response_model=ConditionMixResponse)
async def analytics_condition_mix(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> ConditionMixResponse:
    ctx = _audit_ctx(request, user)
    rows = await analytics_service.get_condition_mix(
        db, start_date=start_date, end_date=end_date
    )
    await write_audit(
        db, ctx,
        action="view_analytics_condition_mix",
        resource_type="analytics",
        allowed=True,
    )
    return ConditionMixResponse(
        rows=[ConditionMixRow(**r) for r in rows],
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/analytics/doctor-utilization", response_model=DoctorUtilizationResponse)
async def analytics_doctor_utilization(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    weeks: int = Query(default=4, ge=1, le=12),
) -> DoctorUtilizationResponse:
    ctx = _audit_ctx(request, user)
    rows = await analytics_service.get_doctor_utilization(db, weeks=weeks)
    await write_audit(
        db, ctx,
        action="view_analytics_doctor_utilization",
        resource_type="analytics",
        allowed=True,
    )
    return DoctorUtilizationResponse(
        rows=[DoctorUtilRow(**r) for r in rows],
        weeks=weeks,
    )


@router.get("/analytics/export")
async def analytics_export(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_admin_user)],
    report: Literal[
        "funnel", "retention", "revenue", "condition_mix", "doctor_utilization"
    ] = Query(default="funnel"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> StreamingResponse:
    ctx = _audit_ctx(request, user)
    await write_audit(
        db, ctx,
        action="export_analytics",
        resource_type="analytics",
        allowed=True,
        log_metadata={"report": report},
    )
    # commit audit before streaming so it's recorded even if the client disconnects
    await db.commit()

    filename = f"kyros_analytics_{report}.csv"
    return StreamingResponse(
        analytics_service.csv_stream(
            db, report=report, start_date=start_date, end_date=end_date
        ),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
