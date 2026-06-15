"""Unit tests for platform_settings_service (admin-controlled toggles + audit)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext
from app.db.enums import ActorRole, OtpResetChannel
from app.services import platform_settings_service as svc


def _ctx(actor_id: uuid.UUID) -> AuditContext:
    return AuditContext(
        actor_user_id=actor_id,
        actor_role=ActorRole.SUPER_ADMIN,
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_id="test",
    )


async def test_default_reset_channel_falls_back_to_sms(db_session: AsyncSession) -> None:
    # No row present → defensive default.
    assert await svc.get_default_reset_channel(db_session) == OtpResetChannel.SMS


async def test_google_oauth_disabled_by_default(db_session: AsyncSession) -> None:
    assert await svc.is_google_oauth_enabled(db_session) is False


async def test_set_and_read_default_reset_channel(db_session: AsyncSession) -> None:
    from tests.conftest import create_super_admin_user

    admin = await create_super_admin_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)

    await svc.set_default_reset_channel(
        db_session, _ctx(admin.id), channel=OtpResetChannel.EMAIL, updated_by=admin.id
    )
    await db_session.flush()

    assert await svc.get_default_reset_channel(db_session) == OtpResetChannel.EMAIL


async def test_set_google_oauth_enabled_writes_audit(db_session: AsyncSession) -> None:
    from app.models.audit import AuditLog
    from tests.conftest import create_super_admin_user

    admin = await create_super_admin_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)

    await svc.set_google_oauth_enabled(
        db_session, _ctx(admin.id), enabled=True, updated_by=admin.id
    )
    await db_session.flush()

    assert await svc.is_google_oauth_enabled(db_session) is True

    row = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.actor_user_id == admin.id,
                AuditLog.action == "platform_setting_update",
            )
        )
    ).scalars().first()
    assert row is not None
    assert row.log_metadata is not None
    assert row.log_metadata.get("key") == svc.GOOGLE_OAUTH_ENABLED
