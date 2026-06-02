from __future__ import annotations

import os

import pytest

# Override secrets for tests so Settings validation passes without a real .env
os.environ.setdefault("KYROS_JWT_SECRET", "test_secret_minimum_32_characters_long_xxxx")
os.environ.setdefault("KYROS_OTP_SECRET", "test_otp_secret_minimum_32_chars_yyyy")
os.environ.setdefault("KYROS_DATABASE_URL", "postgresql+asyncpg://kyros:test@localhost:55432/kyros_test")
os.environ.setdefault("KYROS_REDIS_URL", "redis://localhost:56379/0")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
