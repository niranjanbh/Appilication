from __future__ import annotations

import asyncio
import os

import pytest

# Override env before any app imports so Settings picks up test values.
os.environ.setdefault("KYROS_JWT_SECRET", "test_secret_minimum_32_characters_long_xxxx")
os.environ.setdefault("KYROS_OTP_SECRET", "test_otp_secret_minimum_32_chars_yyyy")
os.environ.setdefault("KYROS_RAZORPAY_WEBHOOK_SECRET", "test_razorpay_webhook_secret_xxxxx")
os.environ.setdefault("KYROS_RAZORPAY_KEY_ID", "rzp_test_key_id")
os.environ.setdefault("KYROS_RAZORPAY_KEY_SECRET", "rzp_test_key_secret")
os.environ.setdefault(
    "KYROS_DATABASE_URL", "postgresql+asyncpg://kyros:test@localhost:55432/kyros_test"
)
os.environ.setdefault("KYROS_REDIS_URL", "redis://localhost:56379/0")
os.environ.setdefault("KYROS_DEBUG", "true")

import uuid
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.db.enums import UserRole
from app.db.session import get_db

fake = Faker("en_IN")


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop shared by all tests and fixtures in the session.

    Prevents asyncpg "Future attached to a different loop" errors that occur
    when function-scoped async fixtures (db_session) and test functions use
    separate per-test event loops.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # NullPool: every connect() creates a fresh asyncpg connection in the
    # current event loop.  No pooled connections → no "different loop" errors.
    # join_transaction_mode="create_savepoint" lets service-layer commit()
    # calls release a SAVEPOINT rather than the outer transaction.
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.begin()
            session = AsyncSession(
                bind=conn,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            try:
                yield session
            finally:
                await session.close()
                await conn.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
async def redis_client() -> AsyncGenerator[aioredis.Redis[str], None]:
    client: aioredis.Redis[str] = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[assignment]
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.main import create_app

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    application = create_app()
    application.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=application)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    application.dependency_overrides.clear()


# ── Synthetic data helpers ─────────────────────────────────────────────────────

def _synth_phone() -> str:
    """Clearly synthetic E.164 phone in +9190000XXXXX range."""
    suffix = str(fake.random_int(min=10000, max=99999))
    return f"+919000{suffix}"


def _synth_email() -> str:
    return f"test_{uuid.uuid4().hex[:8]}@test.kyros.local"


# ── User factories ─────────────────────────────────────────────────────────────

async def create_patient_user(
    db: AsyncSession,
    *,
    phone: str | None = None,
    email: str | None = None,
    name: str | None = None,
    phone_verified: bool = True,
) -> object:
    from app.core.security import hash_password
    from app.repositories import users as users_repo

    user = await users_repo.create(
        db,
        name=name or fake.name(),
        role=UserRole.PATIENT,
        phone=phone or _synth_phone(),
        email=email or _synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    if phone_verified:
        await users_repo.update_phone_verified(db, user.id)  # type: ignore[union-attr]
    return user


async def create_doctor_user(
    db: AsyncSession,
    *,
    phone: str | None = None,
    email: str | None = None,
    name: str | None = None,
) -> object:
    from app.core.security import hash_password
    from app.repositories import users as users_repo

    return await users_repo.create(
        db,
        name=name or fake.name(),
        role=UserRole.DOCTOR,
        phone=phone or _synth_phone(),
        email=email or _synth_email(),
        password_hash=hash_password("TestPass123!"),
    )


async def create_coordinator_user(
    db: AsyncSession,
    *,
    phone: str | None = None,
    email: str | None = None,
) -> object:
    from app.core.security import hash_password
    from app.repositories import users as users_repo

    return await users_repo.create(
        db,
        name=fake.name(),
        role=UserRole.COORDINATOR,
        phone=phone or _synth_phone(),
        email=email or _synth_email(),
        password_hash=hash_password("TestPass123!"),
    )


async def create_super_admin_user(
    db: AsyncSession,
    *,
    phone: str | None = None,
    email: str | None = None,
) -> object:
    from app.core.security import hash_password
    from app.repositories import users as users_repo

    return await users_repo.create(
        db,
        name=fake.name(),
        role=UserRole.SUPER_ADMIN,
        phone=phone or _synth_phone(),
        email=email or _synth_email(),
        password_hash=hash_password("TestPass123!"),
    )


async def create_doctor_with_profile(
    db: AsyncSession,
    *,
    phone: str | None = None,
    email: str | None = None,
    name: str | None = None,
) -> object:
    """Create a User with role=doctor AND a matching dr_doctors profile row."""
    from datetime import UTC, datetime

    from app.db.enums import DoctorStatus
    from app.models.doctor import Doctor

    user = await create_doctor_user(db, phone=phone, email=email, name=name)

    from app.models.identity import User as UserModel
    assert isinstance(user, UserModel)

    doctor = Doctor(
        user_id=user.id,
        nmc_registration_number=f"NMC{fake.random_int(min=10000, max=99999)}",
        nmc_state_council="Test Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["thyroid"],
        conditions_treated=["hypothyroidism"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Test doctor",
        onboarding_stage="complete",
    )
    db.add(doctor)
    await db.flush()
    return user


def make_auth_headers(user: object) -> dict[str, str]:
    """Return Bearer auth headers for the given user."""
    from app.core.security import create_access_token
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    token = create_access_token(user.id, user.role, uuid.uuid4())
    return {"Authorization": f"Bearer {token}"}
