from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import OtpResetChannel, UserRole
from app.models.identity import User


async def create(
    db: AsyncSession,
    *,
    name: str,
    role: UserRole,
    phone: str | None = None,
    email: str | None = None,
    password_hash: str | None = None,
) -> User:
    user = User(
        name=name,
        role=role,
        phone=phone,
        email=email,
        password_hash=password_hash,
    )
    db.add(user)
    await db.flush()
    return user


async def get_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    include_deleted: bool = False,
) -> User | None:
    stmt = select(User).where(User.id == user_id)
    if not include_deleted:
        stmt = stmt.where(User.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(
        select(User).where(User.phone == phone, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_by_email_or_phone(db: AsyncSession, email_or_phone: str) -> User | None:
    """Try email lookup first, then phone. Used by admin login."""
    from sqlalchemy import or_
    result = await db.execute(
        select(User).where(
            or_(User.email == email_or_phone, User.phone == email_or_phone),
            User.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def update_for_re_registration(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str,
    email: str,
    password_hash: str,
) -> None:
    """Refresh an abandoned unverified account so the user can retry registration."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(name=name, email=email, password_hash=password_hash, updated_at=datetime.now(UTC))
    )


async def update_phone_verified(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(phone_verified=True, updated_at=datetime.now(UTC))
    )


async def set_phone_verified(
    db: AsyncSession, user_id: uuid.UUID, phone: str
) -> None:
    """Attach a phone to an account and mark it verified in one update.

    Used when a number is captured after the fact (e.g. Google sign-in, which
    carries no phone). The caller is responsible for the uniqueness check.
    """
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(phone=phone, phone_verified=True, updated_at=datetime.now(UTC))
    )


async def get_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    result = await db.execute(
        select(User).where(User.google_sub == google_sub, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def set_google_sub(
    db: AsyncSession, user_id: uuid.UUID, google_sub: str
) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(google_sub=google_sub, updated_at=datetime.now(UTC))
    )


async def update_password(
    db: AsyncSession, user_id: uuid.UUID, password_hash: str
) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=password_hash, updated_at=datetime.now(UTC))
    )


async def update_reset_otp_channel(
    db: AsyncSession, user_id: uuid.UUID, channel: OtpResetChannel | None
) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(reset_otp_channel=channel, updated_at=datetime.now(UTC))
    )


async def mark_email_verified(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(email_verified=True, updated_at=datetime.now(UTC))
    )


async def update_last_login(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            last_login_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
