"""Analytics repository — read-only aggregation queries for super admin dashboards.

All functions return plain dicts to keep the API layer decoupled from SQLAlchemy.
No PHI is returned: results are aggregated counts and paise sums only.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ConsultationStatus, UserRole
from app.models.clinic import Consultation
from app.models.identity import User
from app.models.public import BookingInquiry

# ── Funnel ─────────────────────────────────────────────────────────────────────


async def get_funnel_data(
    db: AsyncSession,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, int]:
    """Return 4-stage acquisition funnel counts for the given date window."""
    start_dt = (
        datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
        if start_date
        else datetime(2024, 1, 1, tzinfo=UTC)
    )
    end_dt = (
        datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=UTC)
        if end_date
        else datetime.now(UTC)
    )

    # Stage 1: Booking inquiries (first tracked touchpoint)
    inq_result = await db.execute(
        select(func.count())
        .select_from(BookingInquiry)
        .where(
            BookingInquiry.created_at >= start_dt,
            BookingInquiry.created_at <= end_dt,
            BookingInquiry.deleted_at.is_(None),
        )
    )
    inquiries: int = inq_result.scalar_one()

    # Stage 2: New patient registrations
    reg_result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(
            User.role == UserRole.PATIENT,
            User.created_at >= start_dt,
            User.created_at <= end_dt,
            User.deleted_at.is_(None),
        )
    )
    registrations: int = reg_result.scalar_one()

    # Stage 3: Paid bookings (consultation with a payment_id)
    book_result = await db.execute(
        select(func.count())
        .select_from(Consultation)
        .where(
            Consultation.payment_id.isnot(None),
            Consultation.created_at >= start_dt,
            Consultation.created_at <= end_dt,
            Consultation.deleted_at.is_(None),
        )
    )
    bookings: int = book_result.scalar_one()

    # Stage 4: Completed consultations
    comp_result = await db.execute(
        select(func.count())
        .select_from(Consultation)
        .where(
            Consultation.status == ConsultationStatus.COMPLETED,
            Consultation.created_at >= start_dt,
            Consultation.created_at <= end_dt,
            Consultation.deleted_at.is_(None),
        )
    )
    completions: int = comp_result.scalar_one()

    return {
        "inquiries": inquiries,
        "registrations": registrations,
        "bookings": bookings,
        "completions": completions,
    }


# ── Retention cohorts ──────────────────────────────────────────────────────────


async def get_retention_cohorts(
    db: AsyncSession,
    *,
    cohort_months: int = 6,
) -> list[dict[str, Any]]:
    """30/60/90-day cohort retention.

    Patients are bucketed by the month of their first consultation.
    Retention at N days = % who had another consultation within N days of their first.
    """
    rows = await db.execute(
        text("""
            WITH first_consult AS (
                SELECT
                    patient_id,
                    MIN(scheduled_start_at) AS first_at
                FROM kc_consultations
                WHERE deleted_at IS NULL
                  AND status NOT IN ('cancelled', 'no_show')
                GROUP BY patient_id
            ),
            cohort AS (
                SELECT
                    fc.patient_id,
                    fc.first_at,
                    date_trunc('month', fc.first_at)::date AS cohort_month
                FROM first_consult fc
                WHERE fc.first_at >= NOW() - (CAST(:months AS INTEGER) * INTERVAL '1 month')
            ),
            followup AS (
                SELECT
                    fc.patient_id,
                    MIN(c.scheduled_start_at) AS next_at
                FROM first_consult fc
                JOIN kc_consultations c ON c.patient_id = fc.patient_id
                WHERE c.deleted_at IS NULL
                  AND c.status NOT IN ('cancelled', 'no_show')
                  AND c.scheduled_start_at > fc.first_at
                GROUP BY fc.patient_id
            )
            SELECT
                co.cohort_month,
                COUNT(co.patient_id)                                               AS cohort_size,
                COUNT(f.patient_id) FILTER (
                    WHERE f.next_at <= co.first_at + INTERVAL '30 days')           AS returned_30,
                COUNT(f.patient_id) FILTER (
                    WHERE f.next_at <= co.first_at + INTERVAL '60 days')           AS returned_60,
                COUNT(f.patient_id) FILTER (
                    WHERE f.next_at <= co.first_at + INTERVAL '90 days')           AS returned_90
            FROM cohort co
            LEFT JOIN followup f ON co.patient_id = f.patient_id
            GROUP BY co.cohort_month
            ORDER BY co.cohort_month
        """),
        {"months": cohort_months},
    )

    result: list[dict[str, Any]] = []
    for row in rows:
        size = row.cohort_size or 0
        r30 = row.returned_30 or 0
        r60 = row.returned_60 or 0
        r90 = row.returned_90 or 0
        result.append(
            {
                "cohort_month": str(row.cohort_month),
                "cohort_size": size,
                "returned_30": r30,
                "returned_60": r60,
                "returned_90": r90,
                "rate_30": round(r30 / size * 100, 1) if size else 0.0,
                "rate_60": round(r60 / size * 100, 1) if size else 0.0,
                "rate_90": round(r90 / size * 100, 1) if size else 0.0,
            }
        )
    return result


# ── Revenue ────────────────────────────────────────────────────────────────────


async def get_revenue_data(
    db: AsyncSession,
    *,
    group_by: str = "condition",
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Revenue (sum of kc_payments.amount_paise where status=paid) grouped by dimension."""
    start_dt = (
        datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
        if start_date
        else datetime.now(UTC) - timedelta(days=90)
    )
    end_dt = (
        datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=UTC)
        if end_date
        else datetime.now(UTC)
    )

    if group_by == "condition":
        rows = await db.execute(
            text("""
                SELECT
                    c.condition_category          AS dimension,
                    COUNT(c.id)                   AS consultation_count,
                    COALESCE(SUM(p.amount_paise), 0) AS revenue_paise
                FROM kc_consultations c
                JOIN kc_payments p ON p.id = c.payment_id
                WHERE p.status = 'paid'
                  AND p.created_at >= :start_dt
                  AND p.created_at <= :end_dt
                  AND c.deleted_at IS NULL
                GROUP BY c.condition_category
                ORDER BY revenue_paise DESC
            """),
            {"start_dt": start_dt, "end_dt": end_dt},
        )
        return [
            {
                "dimension": r.dimension,
                "label": r.dimension,
                "consultation_count": r.consultation_count,
                "revenue_paise": r.revenue_paise,
                "revenue_inr": round(r.revenue_paise / 100, 2),
            }
            for r in rows
        ]

    if group_by == "doctor":
        rows = await db.execute(
            text("""
                SELECT
                    d.id::text                     AS dimension,
                    u.name                         AS label,
                    COUNT(c.id)                    AS consultation_count,
                    COALESCE(SUM(p.amount_paise), 0) AS revenue_paise
                FROM kc_consultations c
                JOIN kc_payments p ON p.id = c.payment_id
                JOIN dr_doctors d ON d.id = c.doctor_id
                JOIN users u ON u.id = d.user_id
                WHERE p.status = 'paid'
                  AND p.created_at >= :start_dt
                  AND p.created_at <= :end_dt
                  AND c.deleted_at IS NULL
                  AND d.deleted_at IS NULL
                GROUP BY d.id, u.name
                ORDER BY revenue_paise DESC
            """),
            {"start_dt": start_dt, "end_dt": end_dt},
        )
        return [
            {
                "dimension": r.dimension,
                "label": r.label,
                "consultation_count": r.consultation_count,
                "revenue_paise": r.revenue_paise,
                "revenue_inr": round(r.revenue_paise / 100, 2),
            }
            for r in rows
        ]

    # group_by == "period" (weekly)
    rows = await db.execute(
        text("""
            SELECT
                date_trunc('week', p.created_at)::date AS dimension,
                COUNT(c.id)                             AS consultation_count,
                COALESCE(SUM(p.amount_paise), 0)        AS revenue_paise
            FROM kc_consultations c
            JOIN kc_payments p ON p.id = c.payment_id
            WHERE p.status = 'paid'
              AND p.created_at >= :start_dt
              AND p.created_at <= :end_dt
              AND c.deleted_at IS NULL
            GROUP BY date_trunc('week', p.created_at)
            ORDER BY dimension
        """),
        {"start_dt": start_dt, "end_dt": end_dt},
    )
    return [
        {
            "dimension": str(r.dimension),
            "label": str(r.dimension),
            "consultation_count": r.consultation_count,
            "revenue_paise": r.revenue_paise,
            "revenue_inr": round(r.revenue_paise / 100, 2),
        }
        for r in rows
    ]


# ── Condition mix ──────────────────────────────────────────────────────────────


async def get_condition_mix(
    db: AsyncSession,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Count of consultations across the 7 condition verticals."""
    start_dt = (
        datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
        if start_date
        else datetime(2024, 1, 1, tzinfo=UTC)
    )
    end_dt = (
        datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=UTC)
        if end_date
        else datetime.now(UTC)
    )

    result = await db.execute(
        select(Consultation.condition_category, func.count().label("n"))
        .where(
            Consultation.created_at >= start_dt,
            Consultation.created_at <= end_dt,
            Consultation.deleted_at.is_(None),
        )
        .group_by(Consultation.condition_category)
        .order_by(func.count().desc())
    )
    rows = list(result)
    total = sum(r.n for r in rows) or 1

    return [
        {
            "condition": r.condition_category,
            "count": r.n,
            "pct": round(r.n / total * 100, 1),
        }
        for r in rows
    ]


# ── Doctor utilization ─────────────────────────────────────────────────────────


async def get_doctor_utilization(
    db: AsyncSession,
    *,
    weeks: int = 4,
) -> list[dict[str, Any]]:
    """Consultations per doctor per ISO week for the last `weeks` weeks."""
    rows = await db.execute(
        text("""
            SELECT
                d.id::text                                          AS doctor_id,
                u.name                                             AS doctor_name,
                date_trunc('week', c.scheduled_start_at)::date    AS week_start,
                COUNT(c.id)                                        AS consultation_count
            FROM kc_consultations c
            JOIN dr_doctors d ON d.id = c.doctor_id
            JOIN users u ON u.id = d.user_id
            WHERE c.scheduled_start_at >= NOW() - (CAST(:weeks AS INTEGER) * INTERVAL '1 week')
              AND c.deleted_at IS NULL
              AND d.deleted_at IS NULL
            GROUP BY d.id, u.name, date_trunc('week', c.scheduled_start_at)
            ORDER BY week_start DESC, consultation_count DESC
        """),
        {"weeks": weeks},
    )
    return [
        {
            "doctor_id": r.doctor_id,
            "doctor_name": r.doctor_name,
            "week_start": str(r.week_start),
            "consultation_count": r.consultation_count,
        }
        for r in rows
    ]


# ── Rollup upsert (used by analytics_tasks) ────────────────────────────────────


async def upsert_daily_metric(
    db: AsyncSession,
    *,
    metric_date: date,
    metric_key: str,
    dimension: str = "",
    value: int,
) -> None:
    await db.execute(
        text("""
            INSERT INTO ad_daily_metrics (metric_date, metric_key, dimension, value)
            VALUES (:metric_date, :metric_key, :dimension, :value)
            ON CONFLICT (metric_date, metric_key, dimension)
            DO UPDATE SET value = :value, updated_at = now()
        """),
        {
            "metric_date": metric_date,
            "metric_key": metric_key,
            "dimension": dimension,
            "value": value,
        },
    )
