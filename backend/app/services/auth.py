from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext, write_audit
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    OtpCooldownError,
    OtpMaxAttemptsError,
    PhoneNotVerifiedError,
)
from app.core.security import (
    create_access_token,
    generate_otp,
    generate_token,
    hash_otp,
    hash_refresh_token,
    verify_password,
)
from app.db.enums import ActorRole, UserRole
from app.db.redis import RedisClient
from app.integrations import msg91
from app.models.identity import User
from app.repositories import auth as auth_repo
from app.repositories import users as users_repo

logger = structlog.get_logger(__name__)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass
class SignupResult:
    user_id: uuid.UUID
    phone: str


def _otp_key(phone: str) -> str:
    return f"otp:phone:{phone}"


def _otp_cooldown_key(phone: str) -> str:
    return f"otp:phone:{phone}:cooldown"


def _otp_attempts_key(phone: str) -> str:
    return f"otp:phone:{phone}:attempts"


def _otp_debug_key(phone: str) -> str:
    return f"otp:phone:{phone}:debug"


async def _issue_otp(redis: RedisClient, phone: str) -> str:
    """Generate OTP, store HMAC hash in Redis, send via MSG91."""
    if await redis.exists(_otp_cooldown_key(phone)):
        raise OtpCooldownError()

    code = generate_otp(6)
    hashed = hash_otp(code)

    async with redis.pipeline(transaction=False) as pipe:
        pipe.set(_otp_key(phone), hashed, ex=settings.otp_ttl_seconds)
        pipe.set(_otp_cooldown_key(phone), "1", ex=settings.otp_resend_cooldown_seconds)
        pipe.delete(_otp_attempts_key(phone))
        if settings.debug:
            pipe.set(_otp_debug_key(phone), code, ex=settings.otp_ttl_seconds)
        await pipe.execute()

    await msg91.send_otp_sms(phone, code)
    return code


async def _verify_otp_code(redis: RedisClient, phone: str, code: str) -> None:
    """Validate OTP from Redis. Raises on invalid/expired/too-many-attempts."""
    attempts = await redis.incr(_otp_attempts_key(phone))
    if attempts == 1:
        await redis.expire(_otp_attempts_key(phone), 900)

    if attempts > settings.otp_max_attempts:
        await redis.delete(_otp_key(phone))
        raise OtpMaxAttemptsError()

    stored = await redis.get(_otp_key(phone))
    if stored is None:
        from app.core.exceptions import BusinessRuleError

        raise BusinessRuleError("otp_expired")

    expected = hash_otp(code)
    if not stored == expected:
        from app.core.exceptions import BusinessRuleError

        raise BusinessRuleError("otp_invalid")

    await redis.delete(_otp_key(phone), _otp_attempts_key(phone))


async def _create_token_pair(
    db: AsyncSession,
    user: User,
    ip_address: str,
    user_agent: str,
    parent_id: uuid.UUID | None = None,
) -> TokenPair:
    session_id = uuid.uuid4()
    raw_refresh = generate_token(32)
    token_hash = hash_refresh_token(raw_refresh)
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)

    await auth_repo.create_refresh_token(
        db,
        user_id=user.id,
        session_id=session_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address or None,
        user_agent=user_agent or None,
        parent_id=parent_id,
    )

    access_token = create_access_token(user.id, user.role, session_id)
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


async def signup(
    db: AsyncSession,
    redis: RedisClient,
    *,
    phone: str,
    email: str,
    name: str,
    password: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> SignupResult:
    from app.core.security import hash_password

    existing_by_phone = await users_repo.get_by_phone(db, phone)

    if existing_by_phone is not None:
        if existing_by_phone.phone_verified:
            raise ConflictError("phone_already_registered")
        # Unverified ghost account — allow re-registration.
        # Guard against the new email colliding with a different account.
        if existing_by_phone.email != email:
            collision = await users_repo.get_by_email(db, email)
            if collision is not None and collision.id != existing_by_phone.id:
                raise ConflictError("email_already_registered")
        await users_repo.update_for_re_registration(
            db, existing_by_phone.id,
            name=name, email=email, password_hash=hash_password(password),
        )
        user = existing_by_phone
    else:
        if await users_repo.get_by_email(db, email) is not None:
            raise ConflictError("email_already_registered")
        user = await users_repo.create(
            db,
            name=name,
            role=UserRole.PATIENT,
            phone=phone,
            email=email,
            password_hash=hash_password(password),
        )

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole.PATIENT,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
    await write_audit(db, ctx, action="signup", resource_type="user", resource_id=user.id, allowed=True)

    try:
        await _issue_otp(redis, phone)
    except OtpCooldownError:
        pass  # OTP already in flight from a prior attempt; user can use the previously sent code
    return SignupResult(user_id=user.id, phone=phone)


async def send_otp(
    db: AsyncSession,
    redis: RedisClient,
    *,
    phone: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> None:
    user = await users_repo.get_by_phone(db, phone)
    if user is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("phone_not_registered")

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
    await write_audit(db, ctx, action="send_otp", resource_type="user", resource_id=user.id, allowed=True)
    await _issue_otp(redis, phone)


async def verify_otp(
    db: AsyncSession,
    redis: RedisClient,
    *,
    phone: str,
    otp: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> TokenPair:
    user = await users_repo.get_by_phone(db, phone)
    if user is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError()

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    await _verify_otp_code(redis, phone, otp)

    await users_repo.update_phone_verified(db, user.id)
    await write_audit(db, ctx, action="phone_verified", resource_type="user", resource_id=user.id, allowed=True)

    tokens = await _create_token_pair(db, user, ip_address, user_agent)
    await users_repo.update_last_login(db, user.id)
    await write_audit(db, ctx, action="login", resource_type="user", resource_id=user.id, allowed=True)
    return tokens


async def login(
    db: AsyncSession,
    redis: RedisClient,
    *,
    email_or_phone: str,
    password: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> TokenPair:
    if "@" in email_or_phone:
        user = await users_repo.get_by_email(db, email_or_phone)
    else:
        user = await users_repo.get_by_phone(db, email_or_phone)

    if user is None or user.password_hash is None:
        raise AuthenticationError("invalid_credentials")

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    if not verify_password(password, user.password_hash):
        await write_audit(
            db, ctx, action="login", resource_type="user", resource_id=user.id,
            allowed=False, reason="invalid_credentials",
        )
        await db.commit()
        raise AuthenticationError("invalid_credentials")

    if not user.phone_verified:
        try:
            await _issue_otp(redis, user.phone or "")
        except OtpCooldownError:
            pass  # OTP already in flight; caller still needs to verify, not re-request
        await write_audit(
            db, ctx, action="login", resource_type="user", resource_id=user.id,
            allowed=False, reason="phone_not_verified",
        )
        await db.commit()
        raise PhoneNotVerifiedError(phone=user.phone)

    tokens = await _create_token_pair(db, user, ip_address, user_agent)
    await users_repo.update_last_login(db, user.id)
    await write_audit(db, ctx, action="login", resource_type="user", resource_id=user.id, allowed=True)
    return tokens


async def refresh(
    db: AsyncSession,
    *,
    raw_token: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> TokenPair:
    token_hash = hash_refresh_token(raw_token)
    stored = await auth_repo.get_by_hash(db, token_hash)

    if stored is None:
        raise AuthenticationError("invalid_refresh_token")

    user = await users_repo.get_by_id(db, stored.user_id)
    if user is None:
        raise AuthenticationError("user_not_found")

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    if stored.revoked_at is not None:
        # Reuse detected — revoke entire session family
        revoked = await auth_repo.revoke_session_family(db, stored.session_id)
        logger.warning(
            "refresh_token_reuse_detected",
            session_id=str(stored.session_id),
            tokens_revoked=revoked,
        )
        await write_audit(
            db, ctx, action="token_refresh", resource_type="session",
            resource_id=stored.id, allowed=False, reason="token_reuse_detected",
        )
        await db.commit()
        raise AuthenticationError("session_revoked")

    if stored.expires_at < datetime.now(UTC):
        raise AuthenticationError("refresh_token_expired")

    await auth_repo.revoke_token(db, stored.id)
    tokens = await _create_token_pair(db, user, ip_address, user_agent, parent_id=stored.id)
    await write_audit(
        db, ctx, action="token_refresh", resource_type="session", resource_id=stored.id, allowed=True
    )
    return tokens
