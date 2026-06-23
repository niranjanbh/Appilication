"""Typed access to admin-controlled platform settings.

Settings are non-secret operational toggles stored in ad_platform_settings.
Getters default defensively so a missing/absent key never breaks a flow; setters
are audited (every state-changing admin action writes ad_audit_log).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext, write_audit
from app.db.enums import OtpResetChannel
from app.repositories import platform_settings as settings_repo

# Setting keys (kept in one place so the admin UI and services agree).
RESET_OTP_CHANNEL_DEFAULT = "reset_otp_channel_default"
GOOGLE_OAUTH_ENABLED = "google_oauth_enabled"
SIGNUP_OTP_ENABLED = "signup_otp_enabled"


async def get_default_reset_channel(db: AsyncSession) -> OtpResetChannel:
    raw = await settings_repo.get(db, RESET_OTP_CHANNEL_DEFAULT)
    if isinstance(raw, str):
        try:
            return OtpResetChannel(raw)
        except ValueError:
            pass
    return OtpResetChannel.SMS


async def is_google_oauth_enabled(db: AsyncSession) -> bool:
    return bool(await settings_repo.get(db, GOOGLE_OAUTH_ENABLED))


async def set_default_reset_channel(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    channel: OtpResetChannel,
    updated_by: uuid.UUID,
) -> None:
    await settings_repo.upsert(
        db, key=RESET_OTP_CHANNEL_DEFAULT, value=channel.value, updated_by=updated_by
    )
    await write_audit(
        db,
        ctx,
        action="platform_setting_update",
        resource_type="platform_setting",
        allowed=True,
        log_metadata={"key": RESET_OTP_CHANNEL_DEFAULT, "value": channel.value},
    )


async def is_signup_otp_enabled(db: AsyncSession) -> bool:
    val = await settings_repo.get(db, SIGNUP_OTP_ENABLED)
    if val is None:
        return True
    return bool(val)


async def set_signup_otp_enabled(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    enabled: bool,
    updated_by: uuid.UUID,
) -> None:
    await settings_repo.upsert(
        db, key=SIGNUP_OTP_ENABLED, value=enabled, updated_by=updated_by
    )
    await write_audit(
        db,
        ctx,
        action="platform_setting_update",
        resource_type="platform_setting",
        allowed=True,
        log_metadata={"key": SIGNUP_OTP_ENABLED, "value": enabled},
    )


async def set_google_oauth_enabled(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    enabled: bool,
    updated_by: uuid.UUID,
) -> None:
    await settings_repo.upsert(
        db, key=GOOGLE_OAUTH_ENABLED, value=enabled, updated_by=updated_by
    )
    await write_audit(
        db,
        ctx,
        action="platform_setting_update",
        resource_type="platform_setting",
        allowed=True,
        log_metadata={"key": GOOGLE_OAUTH_ENABLED, "value": enabled},
    )
