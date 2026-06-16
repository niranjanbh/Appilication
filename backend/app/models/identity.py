from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import OtpResetChannel, UserGender, UserRole, enum_values
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    phone_verified: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Admin-controlled per-user channel for password-reset OTP delivery.
    # NULL → fall back to the platform default (ad_platform_settings).
    reset_otp_channel: Mapped[OtpResetChannel | None] = mapped_column(
        SAEnum(
            OtpResetChannel,
            name="otp_reset_channel",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=True,
    )
    # Google subject id for accounts linked via Sign in with Google (patients only).
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[UserGender | None] = mapped_column(
        SAEnum(UserGender, name="user_gender", create_type=False, values_callable=enum_values),
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language_preference: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(50), server_default=text("'Asia/Kolkata'"), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expo_push_token: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notification_preferences: Mapped[dict[str, bool]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text('\'{"push": true, "whatsapp": true, "email": true}\'::jsonb'),
    )
    # Set when DPDP erasure task anonymizes PII. Separate from deleted_at (soft-delete).
    erased_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Carried forward across /refresh rotations within a session: True once the staff user has
    # completed an MFA challenge for this session (staff-rbac-spec §1).
    mfa_verified: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")
