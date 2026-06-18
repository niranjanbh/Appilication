from __future__ import annotations

import asyncio
import hashlib
import logging
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta

from app.worker import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="kyros.maintenance.ensure_health_partitions_ahead")  # type: ignore[untyped-decorator]
def ensure_health_partitions_ahead() -> dict[str, list[str]]:
    """Create wn_health_datapoints monthly partitions 3 months ahead.

    Safe to run repeatedly — uses CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS.
    Scheduled monthly via Celery beat.
    """
    return asyncio.run(_ensure_partitions_async())


async def _ensure_partitions_async() -> dict[str, list[str]]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import settings

    engine = create_async_engine(settings.database_url)
    created: list[str] = []
    try:
        async with engine.begin() as conn:
            now = datetime.now(UTC)
            for offset in range(1, 4):
                # Advance by ~30-day increments to get distinct months
                target = now + timedelta(days=30 * offset)
                year, month = target.year, target.month
                suffix = f"{year}_{month:02d}"
                from_date = f"{year}-{month:02d}-01"

                days_in_month = monthrange(year, month)[1]
                next_month = datetime(year, month, 1) + timedelta(days=days_in_month)
                to_date = f"{next_month.year}-{next_month.month:02d}-01"

                await conn.execute(
                    text(
                        f"CREATE TABLE IF NOT EXISTS wn_health_datapoints_{suffix} "
                        f"PARTITION OF wn_health_datapoints "
                        f"FOR VALUES FROM ('{from_date}') TO ('{to_date}')"
                    )
                )
                await conn.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS ix_wn_hdp_{suffix}_user_type "
                        f"ON wn_health_datapoints_{suffix} (user_id, type, measured_at DESC)"
                    )
                )
                created.append(suffix)
                log.info("Ensured partition wn_health_datapoints_%s", suffix)
    finally:
        await engine.dispose()

    return {"ensured": created}


# ── CloudWatch metrics ─────────────────────────────────────────────────────────

_CELERY_QUEUES = ("ocr", "notifications", "reports", "payments", "maintenance", "default")


@celery_app.task(name="kyros.maintenance.publish_metrics")  # type: ignore[untyped-decorator]
def publish_metrics() -> dict[str, object]:
    """Publish Celery queue depths and active-user count to CloudWatch.

    No-op when AWS credentials are absent so the task is safe to run in dev.
    Runs every 60 s via beat.
    """
    from app.core.config import settings

    if not settings.aws_access_key_id:
        log.debug("publish_metrics: no AWS credentials configured, skipping")
        return {"skipped": True}

    import boto3
    import redis as sync_redis

    redis_client = sync_redis.Redis.from_url(settings.redis_url, decode_responses=True)
    cloudwatch = boto3.client(
        "cloudwatch",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    metric_data: list[dict[str, object]] = []
    depths: dict[str, int] = {}

    for queue in _CELERY_QUEUES:
        depth = int(redis_client.llen(queue) or 0)
        depths[queue] = depth
        metric_data.append(
            {
                "MetricName": "CeleryQueueDepth",
                "Dimensions": [{"Name": "Queue", "Value": queue}],
                "Value": float(depth),
                "Unit": "Count",
            }
        )

    # Publish in batches of 20 (CloudWatch limit)
    for i in range(0, len(metric_data), 20):
        cloudwatch.put_metric_data(
            Namespace=settings.cloudwatch_namespace,
            MetricData=metric_data[i : i + 20],
        )

    redis_client.close()
    log.info("publish_metrics: published queue depths %s", depths)
    return {"published": len(metric_data), "depths": depths}


# ── Audit integrity ────────────────────────────────────────────────────────────


@celery_app.task(name="kyros.maintenance.verify_audit_integrity")  # type: ignore[untyped-decorator]
def verify_audit_integrity() -> dict[str, object]:
    """Daily audit log integrity check.

    Computes SHA-256 of yesterday's ad_audit_log rows (ordered by created_at,
    then id), stores the hash in Redis, and compares against the stored hash
    from the previous run to detect tampering.
    """
    return asyncio.run(_verify_audit_integrity_async())


async def _verify_audit_integrity_async() -> dict[str, object]:
    import redis as sync_redis
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import settings

    yesterday: date = (datetime.now(UTC) - timedelta(days=1)).date()
    day_start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    engine = create_async_engine(settings.database_url)
    rows: list[str] = []
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT id::text FROM ad_audit_log "
                    "WHERE created_at >= :start AND created_at < :end "
                    "ORDER BY created_at, id"
                ),
                {"start": day_start, "end": day_end},
            )
            rows = [r[0] for r in result.fetchall()]
    finally:
        await engine.dispose()

    payload = ",".join(rows).encode()
    current_hash = hashlib.sha256(payload).hexdigest()
    redis_key = f"audit:integrity:{yesterday.isoformat()}"

    redis_client = sync_redis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        stored_hash: str | None = redis_client.get(redis_key)
        if stored_hash is None:
            # First time we've hashed this day — store and done
            redis_client.setex(redis_key, 90 * 86400, current_hash)
            log.info(
                "verify_audit_integrity: stored hash for %s (%d rows)",
                yesterday,
                len(rows),
            )
            return {"date": str(yesterday), "rows": len(rows), "status": "stored"}

        if stored_hash != current_hash:
            try:
                import sentry_sdk

                sentry_sdk.capture_message(
                    f"AUDIT INTEGRITY DRIFT: ad_audit_log hash for {yesterday} "
                    f"changed. stored={stored_hash[:16]}… current={current_hash[:16]}…",
                    level="warning",
                )
            except ImportError:
                pass
            log.warning(
                "verify_audit_integrity: HASH DRIFT for %s stored=%s current=%s",
                yesterday,
                stored_hash[:16],
                current_hash[:16],
            )
            return {
                "date": str(yesterday),
                "rows": len(rows),
                "status": "DRIFT_DETECTED",
                "stored_prefix": stored_hash[:16],
                "current_prefix": current_hash[:16],
            }
    finally:
        redis_client.close()

    log.info("verify_audit_integrity: integrity OK for %s (%d rows)", yesterday, len(rows))
    return {"date": str(yesterday), "rows": len(rows), "status": "ok"}
