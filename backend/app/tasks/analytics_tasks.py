"""Celery tasks for daily analytics rollup.

kyros.analytics.rollup_daily — scheduled at 02:30 UTC via beat.
Pre-aggregates key metrics into ad_daily_metrics so admin dashboards
can read from the rollup table rather than scanning source tables at query time.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

from app.worker import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="kyros.analytics.rollup_daily")  # type: ignore[untyped-decorator]
def rollup_daily() -> dict[str, str | int]:
    """Compute and upsert daily metrics for yesterday into ad_daily_metrics."""
    return asyncio.run(_rollup_daily_async())


async def _rollup_daily_async() -> dict[str, str | int]:
    from sqlalchemy import func, select, text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.core.config import settings
    from app.db.enums import ConsultationStatus, PaymentStatus, UserRole
    from app.models.clinic import Consultation
    from app.models.identity import User
    from app.models.payment import Payment
    from app.repositories.analytics import upsert_daily_metric

    yesterday: date = (datetime.now(UTC) - timedelta(days=1)).date()
    day_start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    upserted = 0

    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            # New patient registrations
            reg_result = await db.execute(
                select(func.count())
                .select_from(User)
                .where(
                    User.role == UserRole.PATIENT,
                    User.created_at >= day_start,
                    User.created_at < day_end,
                    User.deleted_at.is_(None),
                )
            )
            await upsert_daily_metric(
                db,
                metric_date=yesterday,
                metric_key="new_patients",
                value=reg_result.scalar_one(),
            )
            upserted += 1

            # Completed consultations
            comp_result = await db.execute(
                select(func.count())
                .select_from(Consultation)
                .where(
                    Consultation.status == ConsultationStatus.COMPLETED,
                    Consultation.created_at >= day_start,
                    Consultation.created_at < day_end,
                    Consultation.deleted_at.is_(None),
                )
            )
            await upsert_daily_metric(
                db,
                metric_date=yesterday,
                metric_key="consultations_completed",
                value=comp_result.scalar_one(),
            )
            upserted += 1

            # Daily revenue (paise)
            rev_result = await db.execute(
                select(func.coalesce(func.sum(Payment.amount_paise), 0))
                .select_from(Payment)
                .where(
                    Payment.status == PaymentStatus.PAID,
                    Payment.created_at >= day_start,
                    Payment.created_at < day_end,
                )
            )
            await upsert_daily_metric(
                db,
                metric_date=yesterday,
                metric_key="revenue_paise",
                value=rev_result.scalar_one(),
            )
            upserted += 1

            # Revenue + consultation count per condition category
            cond_rows = await db.execute(
                text("""
                    SELECT
                        c.condition_category,
                        COUNT(c.id)                    AS cnt,
                        COALESCE(SUM(p.amount_paise), 0) AS rev
                    FROM kc_consultations c
                    JOIN kc_payments p ON p.id = c.payment_id
                    WHERE p.status = 'paid'
                      AND p.created_at >= :day_start
                      AND p.created_at < :day_end
                      AND c.deleted_at IS NULL
                    GROUP BY c.condition_category
                """),
                {"day_start": day_start, "day_end": day_end},
            )
            for row in cond_rows:
                await upsert_daily_metric(
                    db,
                    metric_date=yesterday,
                    metric_key="consultations_by_condition",
                    dimension=row.condition_category,
                    value=row.cnt,
                )
                await upsert_daily_metric(
                    db,
                    metric_date=yesterday,
                    metric_key="revenue_paise_by_condition",
                    dimension=row.condition_category,
                    value=row.rev,
                )
                upserted += 2

            await db.commit()
            log.info(
                "analytics.rollup_daily completed",
                extra={"date": str(yesterday), "upserted": upserted},
            )
    finally:
        await engine.dispose()

    return {"date": str(yesterday), "upserted": upserted}
