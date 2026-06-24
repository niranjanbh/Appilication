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
    BusinessRuleError,
    ConflictError,
    OtpCooldownError,
    OtpMaxAttemptsError,
    PhoneNotVerifiedError,
)
from app.core.security import (
    audience_for_role,
    create_access_token,
    decrypt_mfa_secret,
    encrypt_mfa_secret,
    generate_otp,
    generate_recovery_codes,
    generate_token,
    generate_totp_secret,
    hash_otp,
    hash_refresh_token,
    totp_provisioning_uri,
    verify_password,
    verify_totp_code,
)
from app.db.enums import ActorRole, OtpResetChannel, UserRole
from app.db.redis import RedisClient
from app.integrations import authkey
from app.models.admin import StaffMfa
from app.models.identity import User
from app.repositories import auth as auth_repo
from app.repositories import patients as patients_repo
from app.repositories import staff_mfa as staff_mfa_repo
from app.repositories import users as users_repo

logger = structlog.get_logger(__name__)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass
class MfaChallenge:
    """Returned from login() in place of tokens when staff MFA is enabled.

    No session exists yet — the challenge must be redeemed via /mfa/verify before
    any refresh token is minted (staff-rbac-spec §1).
    """

    challenge_token: str
    expires_in: int


@dataclass
class SignupResult:
    user_id: uuid.UUID
    phone: str
    tokens: TokenPair | None = None


# Namespaces keep OTP flows isolated: a code issued for the public booking flow
# ("booking") can never be replayed against /v1/auth/verify-otp ("phone"), which
# would mark the phone verified and mint a session.
def _otp_key(phone: str, namespace: str = "phone") -> str:
    return f"otp:{namespace}:{phone}"


def _otp_cooldown_key(phone: str, namespace: str = "phone") -> str:
    return f"otp:{namespace}:{phone}:cooldown"


def _otp_attempts_key(phone: str, namespace: str = "phone") -> str:
    return f"otp:{namespace}:{phone}:attempts"


def _otp_debug_key(phone: str, namespace: str = "phone") -> str:
    return f"otp:{namespace}:{phone}:debug"


async def _send_otp_email(email: str, code: str) -> bool:
    """Deliver the OTP to the user's registered email. Non-raising.

    Sends directly (not via the Celery email task) — OTP is time-sensitive and
    the task's dedup key would swallow legitimate resends. The subject carries
    no code; the OTP appears only in the body.
    """
    from app.integrations.email import send_email_async
    from app.services.notifications import render_email

    return await send_email_async(
        to_email=email,
        subject="Your Kyros verification code",
        html_body=render_email(
            "otp_code", otp=code, ttl_minutes=str(settings.otp_ttl_seconds // 60)
        ),
    )


_OTP_CHANNEL_ORDER = ("whatsapp", "email", "sms")


async def _deliver_otp(
    phone: str, code: str, *, email: str | None, preferred: str | None
) -> str | None:
    """Try delivery channels in order, preferred one first. Returns the channel
    that delivered, or None if every channel failed.
    """
    order = list(_OTP_CHANNEL_ORDER)
    if preferred in order:
        order.remove(preferred)
        order.insert(0, preferred)

    for channel in order:
        if channel == "whatsapp":
            delivered = await authkey.send_otp_whatsapp(phone, code)
        elif channel == "email":
            if not email or not settings.otp_email_fallback_enabled:
                continue
            delivered = await _send_otp_email(email, code)
        else:
            delivered = await authkey.send_otp_sms(phone, code)
        if delivered:
            return channel
    return None


async def _deliver_reset_otp(user: User, code: str, channel: OtpResetChannel) -> bool:
    """Deliver a password-reset OTP on exactly the admin-chosen channel.

    Unlike signup OTP (multi-channel chain), a reset OTP goes to the single
    channel the admin configured for this user (or the platform default): email
    or the registered mobile number (SMS). No cross-channel fallback — the admin
    decision is authoritative.
    """
    if channel == OtpResetChannel.EMAIL:
        if not user.email:
            return False
        return await _send_otp_email(user.email, code)
    # OtpResetChannel.SMS → registered mobile number
    if not user.phone:
        return False
    return await authkey.send_otp_sms(user.phone, code)


async def _issue_reset_otp(
    redis: RedisClient, *, user: User, channel: OtpResetChannel
) -> None:
    """Generate, store, and deliver a password-reset OTP, keyed by user id.

    Keyed by user id (not phone) so the same flow works whether the user resets
    by email or phone, and across every role.
    """
    key_id = str(user.id)
    if await redis.exists(_otp_cooldown_key(key_id, "pwd_reset")):
        raise OtpCooldownError()

    code = generate_otp(6)
    hashed = hash_otp(code)

    async with redis.pipeline(transaction=False) as pipe:
        pipe.set(_otp_key(key_id, "pwd_reset"), hashed, ex=settings.otp_ttl_seconds)
        pipe.set(
            _otp_cooldown_key(key_id, "pwd_reset"),
            "1",
            ex=settings.otp_resend_cooldown_seconds,
        )
        pipe.delete(_otp_attempts_key(key_id, "pwd_reset"))
        if settings.debug:
            pipe.set(
                _otp_debug_key(key_id, "pwd_reset"), code, ex=settings.otp_ttl_seconds
            )
        await pipe.execute()

    delivered = await _deliver_reset_otp(user, code, channel)
    if delivered:
        logger.info("reset_otp_delivered", channel=channel.value)
    else:
        logger.warning("reset_otp_delivery_failed", channel=channel.value)


async def _issue_otp(
    redis: RedisClient,
    phone: str,
    *,
    email: str | None = None,
    preferred_channel: str | None = None,
    namespace: str = "phone",
) -> str:
    """Generate OTP, store HMAC hash in Redis, and deliver it.

    Default delivery chain: WhatsApp → email (if registered) → SMS. A preferred
    channel moves to the front; the rest remain as fallback. All channels carry
    the same code, so verification is identical regardless of how it arrived.
    """
    if preferred_channel == "email" and (
        not email or not settings.otp_email_fallback_enabled
    ):
        from app.core.exceptions import BusinessRuleError

        raise BusinessRuleError("email_channel_unavailable")

    if await redis.exists(_otp_cooldown_key(phone, namespace)):
        raise OtpCooldownError()

    code = generate_otp(6)
    hashed = hash_otp(code)

    async with redis.pipeline(transaction=False) as pipe:
        pipe.set(_otp_key(phone, namespace), hashed, ex=settings.otp_ttl_seconds)
        pipe.set(
            _otp_cooldown_key(phone, namespace),
            "1",
            ex=settings.otp_resend_cooldown_seconds,
        )
        pipe.delete(_otp_attempts_key(phone, namespace))
        if settings.debug:
            pipe.set(_otp_debug_key(phone, namespace), code, ex=settings.otp_ttl_seconds)
        await pipe.execute()

    channel = await _deliver_otp(phone, code, email=email, preferred=preferred_channel)
    if channel is not None:
        logger.info("otp_delivered", channel=channel)
    else:
        logger.warning("otp_delivery_failed_all_channels")

    return code


async def _verify_otp_code(
    redis: RedisClient, phone: str, code: str, namespace: str = "phone"
) -> None:
    """Validate OTP from Redis. Raises on invalid/expired/too-many-attempts."""
    attempts = await redis.incr(_otp_attempts_key(phone, namespace))
    if attempts == 1:
        await redis.expire(_otp_attempts_key(phone, namespace), 900)

    if attempts > settings.otp_max_attempts:
        await redis.delete(_otp_key(phone, namespace))
        raise OtpMaxAttemptsError()

    stored = await redis.get(_otp_key(phone, namespace))
    if stored is None:
        from app.core.exceptions import BusinessRuleError

        raise BusinessRuleError("otp_expired")

    import hmac as _hmac

    expected = hash_otp(code)
    if not _hmac.compare_digest(stored, expected):
        from app.core.exceptions import BusinessRuleError

        raise BusinessRuleError("otp_invalid")

    await redis.delete(_otp_key(phone, namespace), _otp_attempts_key(phone, namespace))


async def _create_token_pair(
    db: AsyncSession,
    user: User,
    ip_address: str,
    user_agent: str,
    parent_id: uuid.UUID | None = None,
    *,
    mfa_verified: bool = False,
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
        mfa_verified=mfa_verified,
    )

    access_token = create_access_token(user.id, user.role, session_id, mfa_verified=mfa_verified)
    aud = audience_for_role(user.role)
    ttl_minutes = (
        settings.jwt_staff_access_token_expire_minutes
        if aud == "staff"
        else settings.jwt_access_token_expire_minutes
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=ttl_minutes * 60,
    )


async def _staff_mfa_enabled(db: AsyncSession, user_id: uuid.UUID) -> StaffMfa | None:
    """Return the user's confirmed StaffMfa row, or None if MFA isn't enabled.

    A row with ``enabled_at IS NULL`` is a pending (unconfirmed) enrollment and
    does not gate login.
    """
    entry = await staff_mfa_repo.get_for_user(db, user_id)
    if entry is None or entry.enabled_at is None:
        return None
    return entry


async def _issue_mfa_challenge(redis: RedisClient, user_id: uuid.UUID) -> MfaChallenge:
    token = generate_token(32)
    await redis.set(
        f"mfa_challenge:{token}", str(user_id), ex=settings.mfa_challenge_ttl_seconds
    )
    return MfaChallenge(challenge_token=token, expires_in=settings.mfa_challenge_ttl_seconds)


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
    channel: str | None = None,
    skip_otp: bool = False,
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

    # Every patient needs a 1:1 clinic profile; create it now so consultations,
    # lab reports, and ABHA work from the first request.
    await patients_repo.get_or_create_for_user(db, user_id=user.id)

    if skip_otp:
        await users_repo.update_phone_verified(db, user.id)
        tokens = await _create_token_pair(db, user, ip_address, user_agent)
        await users_repo.update_last_login(db, user.id)
        await write_audit(db, ctx, action="login", resource_type="user", resource_id=user.id, allowed=True)
        return SignupResult(user_id=user.id, phone=phone, tokens=tokens)

    try:
        await _issue_otp(redis, phone, email=user.email, preferred_channel=channel)
    except OtpCooldownError:
        pass
    return SignupResult(user_id=user.id, phone=phone)


async def send_otp(
    db: AsyncSession,
    redis: RedisClient,
    *,
    phone: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
    channel: str | None = None,
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
    await _issue_otp(redis, phone, email=user.email, preferred_channel=channel)


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


@dataclass
class PhoneCaptureResult:
    phone: str
    # Mirrors signup: when signup OTP is admin-enabled the number must be
    # confirmed via /me/phone/confirm (otp_required=True). When disabled the
    # number is stored verified immediately and no confirm step is needed.
    otp_required: bool


async def request_phone_capture(
    db: AsyncSession,
    redis: RedisClient,
    *,
    user: User,
    phone: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
    channel: str | None = None,
) -> PhoneCaptureResult:
    """Attach a mobile number to the signed-in account.

    Used after Google sign-in (which carries no phone) to force-collect a
    reachable number for communication. Honours the admin signup-OTP toggle:
    when OTP is enabled the number is held pending an OTP confirm; when disabled
    it is stored verified immediately.
    """
    from app.services import platform_settings_service

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    # A number already verified by a *different* account cannot be claimed.
    existing = await users_repo.get_by_phone(db, phone)
    if existing is not None and existing.id != user.id and existing.phone_verified:
        await write_audit(
            db, ctx, action="phone_capture_request", resource_type="user",
            resource_id=user.id, allowed=False, reason="phone_already_registered",
        )
        await db.commit()
        raise ConflictError("phone_already_registered")

    if not await platform_settings_service.is_signup_otp_enabled(db):
        # OTP disabled by admin: store the number verified straight away.
        await users_repo.set_phone_verified(db, user.id, phone)
        await write_audit(
            db, ctx, action="phone_verified", resource_type="user",
            resource_id=user.id, allowed=True, reason="signup_otp_disabled",
        )
        return PhoneCaptureResult(phone=phone, otp_required=False)

    await write_audit(
        db, ctx, action="phone_capture_request", resource_type="user",
        resource_id=user.id, allowed=True,
    )
    try:
        await _issue_otp(redis, phone, email=user.email, preferred_channel=channel)
    except OtpCooldownError:
        pass  # A code is already in flight; the user can use the previous one.
    return PhoneCaptureResult(phone=phone, otp_required=True)


async def confirm_phone_capture(
    db: AsyncSession,
    redis: RedisClient,
    *,
    user: User,
    phone: str,
    otp: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> None:
    """Confirm the OTP for a captured number and mark it verified on the account."""
    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    # Re-check the race: someone may have verified this number meanwhile.
    existing = await users_repo.get_by_phone(db, phone)
    if existing is not None and existing.id != user.id and existing.phone_verified:
        await write_audit(
            db, ctx, action="phone_capture_confirm", resource_type="user",
            resource_id=user.id, allowed=False, reason="phone_already_registered",
        )
        await db.commit()
        raise ConflictError("phone_already_registered")

    await _verify_otp_code(redis, phone, otp)

    await users_repo.set_phone_verified(db, user.id, phone)
    await write_audit(
        db, ctx, action="phone_verified", resource_type="user",
        resource_id=user.id, allowed=True,
    )


async def login(
    db: AsyncSession,
    redis: RedisClient,
    *,
    email_or_phone: str,
    password: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> TokenPair | MfaChallenge:
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
            await _issue_otp(redis, user.phone or "", email=user.email)
        except OtpCooldownError:
            pass  # OTP already in flight; caller still needs to verify, not re-request
        await write_audit(
            db, ctx, action="login", resource_type="user", resource_id=user.id,
            allowed=False, reason="phone_not_verified",
        )
        await db.commit()
        raise PhoneNotVerifiedError(phone=user.phone)

    if await _staff_mfa_enabled(db, user.id) is not None:
        challenge = await _issue_mfa_challenge(redis, user.id)
        await write_audit(
            db, ctx, action="login", resource_type="user", resource_id=user.id,
            allowed=True, log_metadata={"mfa_challenge": True},
        )
        return challenge

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

    if audience_for_role(user.role) == "staff":
        # A not-yet-rotated token's updated_at equals its mint time (TimestampMixin's
        # onupdate=func.now() only fires on UPDATE). Idle staff sessions are killed
        # outright rather than silently extended (staff-rbac-spec §1).
        idle_for = datetime.now(UTC) - stored.updated_at
        if idle_for > timedelta(minutes=settings.jwt_staff_idle_timeout_minutes):
            revoked = await auth_repo.revoke_session_family(db, stored.session_id)
            logger.warning(
                "staff_session_idle_timeout",
                session_id=str(stored.session_id),
                tokens_revoked=revoked,
            )
            await write_audit(
                db, ctx, action="token_refresh", resource_type="session",
                resource_id=stored.id, allowed=False, reason="session_idle_timeout",
            )
            await db.commit()
            raise AuthenticationError("session_idle_timeout")

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
    tokens = await _create_token_pair(
        db, user, ip_address, user_agent, parent_id=stored.id, mfa_verified=stored.mfa_verified
    )
    await write_audit(
        db, ctx, action="token_refresh", resource_type="session", resource_id=stored.id, allowed=True
    )
    return tokens


async def mfa_setup(
    db: AsyncSession,
    user: User,
    ctx: AuditContext,
    *,
    mfa_verified: bool,
) -> tuple[str, str]:
    """Generate (or regenerate) a pending TOTP secret for a staff user.

    Returns ``(secret, provisioning_uri)``. Nothing is enforced until /mfa/confirm
    succeeds. Re-enrolling an account that already has MFA enabled requires an
    MFA-verified session — the same bar as /mfa/disable — so a stolen access token
    alone cannot swap out a victim's authenticator.
    """
    existing = await staff_mfa_repo.get_for_user(db, user.id)
    if existing is not None and existing.enabled_at is not None and not mfa_verified:
        raise AuthenticationError("mfa_required")

    secret = generate_totp_secret()
    await staff_mfa_repo.upsert_pending(db, user.id, encrypt_mfa_secret(secret))
    account_name = user.email or user.phone or str(user.id)
    uri = totp_provisioning_uri(secret, account_name)
    await write_audit(
        db, ctx, action="mfa_setup_initiated", resource_type="user",
        resource_id=user.id, allowed=True,
    )
    return secret, uri


async def mfa_confirm(
    db: AsyncSession,
    user: User,
    ctx: AuditContext,
    *,
    code: str,
) -> list[str]:
    """Confirm a pending TOTP enrollment and return one-time recovery codes.

    Recovery codes are returned in plaintext exactly once — only their HMAC hashes
    are persisted.
    """
    entry = await staff_mfa_repo.get_for_user(db, user.id)
    if entry is None:
        raise BusinessRuleError("mfa_not_set_up")

    secret = decrypt_mfa_secret(entry.totp_secret_encrypted)
    if not verify_totp_code(secret, code):
        await write_audit(
            db, ctx, action="mfa_enabled", resource_type="user",
            resource_id=user.id, allowed=False, reason="mfa_invalid_code",
        )
        await db.commit()
        raise BusinessRuleError("mfa_invalid_code")

    recovery_codes = generate_recovery_codes(settings.mfa_recovery_codes_count)
    await staff_mfa_repo.confirm(db, user.id, [hash_otp(c) for c in recovery_codes])
    await write_audit(
        db, ctx, action="mfa_enabled", resource_type="user", resource_id=user.id, allowed=True
    )
    return recovery_codes


async def mfa_disable(
    db: AsyncSession,
    user: User,
    ctx: AuditContext,
    *,
    password: str,
) -> None:
    if user.password_hash is None or not verify_password(password, user.password_hash):
        await write_audit(
            db, ctx, action="mfa_disabled", resource_type="user",
            resource_id=user.id, allowed=False, reason="invalid_credentials",
        )
        await db.commit()
        raise AuthenticationError("invalid_credentials")

    await staff_mfa_repo.disable(db, user.id)
    await write_audit(
        db, ctx, action="mfa_disabled", resource_type="user", resource_id=user.id, allowed=True
    )


async def mfa_verify(
    db: AsyncSession,
    redis: RedisClient,
    *,
    challenge_token: str,
    code: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> TokenPair:
    """Redeem an MFA challenge (from login()) for a real token pair.

    ``code`` may be a TOTP code or a recovery code; recovery codes are single-use.
    """
    challenge_key = f"mfa_challenge:{challenge_token}"
    user_id_raw = await redis.get(challenge_key)
    if user_id_raw is None:
        raise AuthenticationError("mfa_challenge_expired")

    user = await users_repo.get_by_id(db, uuid.UUID(user_id_raw))
    if user is None:
        raise AuthenticationError("user_not_found")

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    entry = await staff_mfa_repo.get_for_user(db, user.id)
    valid = False
    via_recovery = False
    if entry is not None and entry.enabled_at is not None:
        secret = decrypt_mfa_secret(entry.totp_secret_encrypted)
        if verify_totp_code(secret, code):
            valid = True
        elif await staff_mfa_repo.consume_recovery_code(db, user.id, hash_otp(code)):
            valid = True
            via_recovery = True

    if not valid:
        await write_audit(
            db, ctx, action="login", resource_type="user", resource_id=user.id,
            allowed=False, reason="mfa_invalid_code",
        )
        await db.commit()
        raise AuthenticationError("mfa_invalid_code")

    await redis.delete(challenge_key)
    tokens = await _create_token_pair(db, user, ip_address, user_agent, mfa_verified=True)
    await users_repo.update_last_login(db, user.id)
    await write_audit(
        db, ctx, action="login", resource_type="user", resource_id=user.id,
        allowed=True, log_metadata={"recovery_code": via_recovery, "mfa": True},
    )
    return tokens


async def request_password_reset(
    db: AsyncSession,
    redis: RedisClient,
    *,
    identifier: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> uuid.UUID | None:
    """Issue a password-reset OTP for any role.

    Channel is admin-controlled: the user's reset_otp_channel, falling back to
    the platform default. Never reveals whether the identifier exists (no
    enumeration) — an unknown identifier returns success-shaped silence.

    Returns the user id (used only for the dev-mode debug OTP hint) or None.
    The caller's response message is identical regardless.
    """
    from app.services import platform_settings_service

    user = await users_repo.get_by_email_or_phone(db, identifier)
    if user is None:
        logger.info("password_reset_requested_unknown_identifier")
        return None

    channel = user.reset_otp_channel or await platform_settings_service.get_default_reset_channel(db)

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
    try:
        await _issue_reset_otp(redis, user=user, channel=channel)
    except OtpCooldownError:
        # OTP already in flight; the user can use the previously sent code.
        # Treat as success so timing doesn't leak account existence.
        return user.id
    await write_audit(
        db, ctx, action="password_reset_request", resource_type="user",
        resource_id=user.id, allowed=True, log_metadata={"channel": channel.value},
    )
    return user.id


async def confirm_password_reset(
    db: AsyncSession,
    redis: RedisClient,
    *,
    identifier: str,
    otp: str,
    new_password: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> None:
    """Verify the reset OTP and set a new password.

    On success every live session for the user is revoked, forcing re-auth
    everywhere. Unknown identifier raises the same generic OTP error as a wrong
    code — no enumeration.
    """
    from app.core.exceptions import BusinessRuleError
    from app.core.security import hash_password

    user = await users_repo.get_by_email_or_phone(db, identifier)
    if user is None:
        raise BusinessRuleError("otp_invalid")

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    await _verify_otp_code(redis, str(user.id), otp, "pwd_reset")

    await users_repo.update_password(db, user.id, hash_password(new_password))
    revoked = await auth_repo.revoke_all_for_user(db, user.id)
    await write_audit(
        db, ctx, action="password_reset_confirm", resource_type="user",
        resource_id=user.id, allowed=True, log_metadata={"sessions_revoked": revoked},
    )


async def google_login(
    db: AsyncSession,
    *,
    id_token: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> TokenPair:
    """Sign in a patient with a verified Google ID token.

    Gated by the admin toggle (google_oauth_enabled). Matches by google_sub, then
    by verified email (linking the Google account), otherwise creates a new
    patient. Only the patient role may use Google sign-in; matching a staff
    account is refused.
    """
    from app.core.exceptions import AuthenticationError
    from app.integrations import google_oauth
    from app.services import platform_settings_service

    if not await platform_settings_service.is_google_oauth_enabled(db):
        raise AuthenticationError("google_signin_disabled")

    identity = await google_oauth.verify_id_token(id_token)
    if identity is None:
        raise AuthenticationError("invalid_google_token")

    system_ctx = AuditContext(
        actor_user_id=None,
        actor_role=ActorRole.SYSTEM,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    user = await users_repo.get_by_google_sub(db, identity.sub)

    if user is None and identity.email and identity.email_verified:
        existing = await users_repo.get_by_email(db, identity.email)
        if existing is not None:
            if existing.role != UserRole.PATIENT:
                await write_audit(
                    db, system_ctx, action="google_login", resource_type="user",
                    resource_id=existing.id, allowed=False, reason="not_patient_role",
                )
                await db.commit()
                raise AuthenticationError("google_signin_not_allowed")
            await users_repo.set_google_sub(db, existing.id, identity.sub)
            user = existing

    if user is None:
        if not (identity.email and identity.email_verified):
            raise AuthenticationError("google_email_unverified")
        user = await users_repo.create(
            db,
            name=identity.name or identity.email.split("@")[0],
            role=UserRole.PATIENT,
            email=identity.email,
            password_hash=None,
        )
        await users_repo.set_google_sub(db, user.id, identity.sub)
        await users_repo.mark_email_verified(db, user.id)

    # Belt-and-suspenders: never mint a non-patient session via Google.
    if user.role != UserRole.PATIENT:
        await write_audit(
            db, system_ctx, action="google_login", resource_type="user",
            resource_id=user.id, allowed=False, reason="not_patient_role",
        )
        await db.commit()
        raise AuthenticationError("google_signin_not_allowed")

    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole.PATIENT,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
    # Google patients (new, linked, or returning) all need a clinic profile.
    await patients_repo.get_or_create_for_user(db, user_id=user.id)
    tokens = await _create_token_pair(db, user, ip_address, user_agent)
    await users_repo.update_last_login(db, user.id)
    await write_audit(
        db, ctx, action="google_login", resource_type="user",
        resource_id=user.id, allowed=True,
    )
    return tokens
