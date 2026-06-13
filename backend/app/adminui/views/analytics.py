"""Analytics dashboard views — super admin portal."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole
from app.db.session import get_db
from app.services import analytics_service

router = APIRouter()
templates = Jinja2Templates(directory="app/adminui/templates")


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    tab: str = "funnel",
    start_date: str = "",
    end_date: str = "",
    cohort_months: int = 6,
    group_by: str = "condition",
    weeks: int = 4,
) -> HTMLResponse:
    sd = _parse_date(start_date)
    ed = _parse_date(end_date)

    funnel = condition_mix = retention = revenue = doctor_util = None

    if tab == "funnel" or not request.headers.get("HX-Request"):
        funnel = await analytics_service.get_funnel(db, start_date=sd, end_date=ed)
        condition_mix = await analytics_service.get_condition_mix(
            db, start_date=sd, end_date=ed
        )

    if tab == "retention":
        retention = await analytics_service.get_retention(
            db, cohort_months=cohort_months
        )

    if tab == "revenue":
        revenue = await analytics_service.get_revenue(
            db, group_by=group_by, start_date=sd, end_date=ed
        )

    if tab == "utilization":
        doctor_util = await analytics_service.get_doctor_utilization(db, weeks=weeks)

    ctx = {
        "admin": admin,
        "tab": tab,
        "start_date": start_date,
        "end_date": end_date,
        "cohort_months": cohort_months,
        "group_by": group_by,
        "weeks": weeks,
        "funnel": funnel,
        "condition_mix": condition_mix,
        "retention": retention,
        "revenue": revenue,
        "doctor_util": doctor_util,
    }

    if request.headers.get("HX-Request") == "true":
        partial_map = {
            "funnel": "admin/_analytics_funnel.html",
            "retention": "admin/_analytics_retention.html",
            "revenue": "admin/_analytics_revenue.html",
            "utilization": "admin/_analytics_doctor_util.html",
        }
        template = partial_map.get(tab, "admin/_analytics_funnel.html")
        return templates.TemplateResponse(request, template, ctx)

    return templates.TemplateResponse(request, "admin/analytics.html", ctx)


@router.get("/analytics/export")
async def analytics_export(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    report: Literal[
        "funnel", "retention", "revenue", "condition_mix", "doctor_utilization"
    ] = Query(default="funnel"),
    start_date: str = "",
    end_date: str = "",
) -> StreamingResponse:
    """Session-cookie CSV export. The JWT twin at /v1/admin/analytics/export
    serves API clients; browsers can't send a Bearer token from an <a> link."""
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    ctx = AuditContext(
        actor_user_id=admin.id,
        actor_role=ActorRole(admin.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    await write_audit(
        db, ctx, action="export_analytics", resource_type="analytics",
        allowed=True, log_metadata={"report": report},
    )
    # commit audit before streaming so it's recorded even if the client disconnects
    await db.commit()

    filename = f"kyros_analytics_{report}.csv"
    return StreamingResponse(
        analytics_service.csv_stream(
            db, report=report, start_date=_parse_date(start_date), end_date=_parse_date(end_date)
        ),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
