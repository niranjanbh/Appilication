"""Unit tests for maintenance_tasks: publish_metrics and verify_audit_integrity."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── publish_metrics ────────────────────────────────────────────────────────────


class TestPublishMetrics:
    def test_skips_when_no_aws_credentials(self) -> None:
        from app.tasks.maintenance_tasks import publish_metrics

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.aws_access_key_id = ""
            result = publish_metrics()

        assert result == {"skipped": True}

    def test_publishes_queue_depths_to_cloudwatch(self) -> None:
        from app.tasks.maintenance_tasks import publish_metrics

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 5

        mock_cloudwatch = MagicMock()
        mock_boto3_client = MagicMock(return_value=mock_cloudwatch)

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("redis.Redis.from_url", return_value=mock_redis),
            patch("boto3.client", mock_boto3_client),
        ):
            mock_settings.aws_access_key_id = "AKIATEST"
            mock_settings.aws_secret_access_key = "secret"
            mock_settings.aws_region = "ap-south-1"
            mock_settings.redis_url = "redis://localhost:6379/1"
            mock_settings.cloudwatch_namespace = "Kyros/Backend"

            result = publish_metrics()

        assert result["published"] == 6  # 6 queues
        assert result["depths"]["ocr"] == 5

        # Verify PutMetricData was called
        mock_cloudwatch.put_metric_data.assert_called_once()
        call_kwargs = mock_cloudwatch.put_metric_data.call_args[1]
        assert call_kwargs["Namespace"] == "Kyros/Backend"
        metric_names = {m["MetricName"] for m in call_kwargs["MetricData"]}
        assert metric_names == {"CeleryQueueDepth"}

        queue_dims = {
            m["Dimensions"][0]["Value"] for m in call_kwargs["MetricData"]
        }
        assert "ocr" in queue_dims
        assert "notifications" in queue_dims
        assert "payments" in queue_dims

    def test_closes_redis_connection_on_success(self) -> None:
        from app.tasks.maintenance_tasks import publish_metrics

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 0

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("redis.Redis.from_url", return_value=mock_redis),
            patch("boto3.client", return_value=MagicMock()),
        ):
            mock_settings.aws_access_key_id = "AKIATEST"
            mock_settings.aws_secret_access_key = "secret"
            mock_settings.aws_region = "ap-south-1"
            mock_settings.redis_url = "redis://localhost:6379/1"
            mock_settings.cloudwatch_namespace = "Kyros/Backend"

            publish_metrics()

        mock_redis.close.assert_called_once()


# ── verify_audit_integrity ─────────────────────────────────────────────────────


class TestVerifyAuditIntegrity:
    @pytest.mark.asyncio
    async def test_stores_hash_on_first_run(self) -> None:
        from app.tasks.maintenance_tasks import _verify_audit_integrity_async

        row_ids = ["uuid-a", "uuid-b", "uuid-c"]
        expected_hash = hashlib.sha256(",".join(row_ids).encode()).hexdigest()

        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(r,) for r in row_ids]
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_engine_ctx = AsyncMock()
        mock_engine_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_engine_ctx
        mock_engine.dispose = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # first run — no stored hash

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("redis.Redis.from_url", return_value=mock_redis),
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test/test"
            mock_settings.redis_url = "redis://localhost"

            result = await _verify_audit_integrity_async()

        assert result["status"] == "stored"
        assert result["rows"] == 3

        # Verify hash was stored in Redis
        mock_redis.setex.assert_called_once()
        _, _, stored_hash = mock_redis.setex.call_args[0]
        assert stored_hash == expected_hash

    @pytest.mark.asyncio
    async def test_ok_when_hashes_match(self) -> None:
        from app.tasks.maintenance_tasks import _verify_audit_integrity_async

        row_ids = ["uuid-x", "uuid-y"]
        stored_hash = hashlib.sha256(",".join(row_ids).encode()).hexdigest()

        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(r,) for r in row_ids]
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_engine_ctx = AsyncMock()
        mock_engine_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_engine_ctx
        mock_engine.dispose = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.get.return_value = stored_hash  # hash already stored

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("redis.Redis.from_url", return_value=mock_redis),
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test/test"
            mock_settings.redis_url = "redis://localhost"

            result = await _verify_audit_integrity_async()

        assert result["status"] == "ok"
        assert result["rows"] == 2

    @pytest.mark.asyncio
    async def test_alerts_on_hash_drift(self) -> None:
        from app.tasks.maintenance_tasks import _verify_audit_integrity_async

        row_ids = ["uuid-1", "uuid-2"]
        current_hash = hashlib.sha256(",".join(row_ids).encode()).hexdigest()
        stale_hash = "aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffff0000000011111111"
        assert current_hash != stale_hash

        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(r,) for r in row_ids]
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_engine_ctx = AsyncMock()
        mock_engine_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_engine_ctx
        mock_engine.dispose = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.get.return_value = stale_hash  # tampered!

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("redis.Redis.from_url", return_value=mock_redis),
            patch("app.core.config.settings") as mock_settings,
            patch("sentry_sdk.capture_message") as mock_capture,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test/test"
            mock_settings.redis_url = "redis://localhost"

            result = await _verify_audit_integrity_async()

        assert result["status"] == "DRIFT_DETECTED"
        mock_capture.assert_called_once()
        alert_msg: str = mock_capture.call_args[0][0]
        assert "AUDIT INTEGRITY DRIFT" in alert_msg
