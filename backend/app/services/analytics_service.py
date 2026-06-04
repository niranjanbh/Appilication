"""Analytics service — orchestrates repository queries and CSV generation."""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncGenerator
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import analytics as analytics_repo


async def get_funnel(
    db: AsyncSession,
    *,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
    data = await analytics_repo.get_funnel_data(
        db, start_date=start_date, end_date=end_date
    )
    # Compute conversion rates between stages
    inq = data["inquiries"] or 1
    reg = data["registrations"] or 0
    book = data["bookings"] or 0
    comp = data["completions"] or 0
    return {
        **data,
        "rate_inq_to_reg": round(reg / inq * 100, 1),
        "rate_reg_to_book": round(book / max(reg, 1) * 100, 1),
        "rate_book_to_comp": round(comp / max(book, 1) * 100, 1),
    }


async def get_retention(
    db: AsyncSession,
    *,
    cohort_months: int,
) -> list[dict[str, Any]]:
    return await analytics_repo.get_retention_cohorts(db, cohort_months=cohort_months)


async def get_revenue(
    db: AsyncSession,
    *,
    group_by: str,
    start_date: date | None,
    end_date: date | None,
) -> list[dict[str, Any]]:
    return await analytics_repo.get_revenue_data(
        db, group_by=group_by, start_date=start_date, end_date=end_date
    )


async def get_condition_mix(
    db: AsyncSession,
    *,
    start_date: date | None,
    end_date: date | None,
) -> list[dict[str, Any]]:
    return await analytics_repo.get_condition_mix(
        db, start_date=start_date, end_date=end_date
    )


async def get_doctor_utilization(
    db: AsyncSession,
    *,
    weeks: int,
) -> list[dict[str, Any]]:
    return await analytics_repo.get_doctor_utilization(db, weeks=weeks)


async def csv_stream(
    db: AsyncSession,
    *,
    report: str,
    start_date: date | None,
    end_date: date | None,
) -> AsyncGenerator[str, None]:
    """Yield one or more CSV chunks for the requested report.

    Uses a generator so FastAPI StreamingResponse can forward bytes without
    materialising the full response in memory.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)

    if report == "funnel":
        data = await analytics_repo.get_funnel_data(
            db, start_date=start_date, end_date=end_date
        )
        writer.writerow(["stage", "count"])
        for k, v in data.items():
            writer.writerow([k, v])

    elif report == "retention":
        rows = await analytics_repo.get_retention_cohorts(db, cohort_months=12)
        if rows:
            writer.writerow(list(rows[0].keys()))
            for row in rows:
                writer.writerow(list(row.values()))

    elif report == "revenue":
        rows = await analytics_repo.get_revenue_data(
            db, group_by="condition", start_date=start_date, end_date=end_date
        )
        if rows:
            writer.writerow(list(rows[0].keys()))
            for row in rows:
                writer.writerow(list(row.values()))

    elif report == "condition_mix":
        rows = await analytics_repo.get_condition_mix(
            db, start_date=start_date, end_date=end_date
        )
        if rows:
            writer.writerow(list(rows[0].keys()))
            for row in rows:
                writer.writerow(list(row.values()))

    elif report == "doctor_utilization":
        rows = await analytics_repo.get_doctor_utilization(db, weeks=52)
        if rows:
            writer.writerow(list(rows[0].keys()))
            for row in rows:
                writer.writerow(list(row.values()))

    else:
        writer.writerow(["error"])
        writer.writerow([f"unknown report: {report}"])

    yield buf.getvalue()
