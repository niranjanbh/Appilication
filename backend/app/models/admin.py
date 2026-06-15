from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import CoordinatorStatus, UserRole, enum_values
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Coordinator(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "ad_coordinators"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    status: Mapped[CoordinatorStatus] = mapped_column(
        SAEnum(
            CoordinatorStatus,
            name="coordinator_status",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default=text("'active'"),
    )
    assigned_patient_ids: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    employee_id: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Followup(Base, UUIDMixin, TimestampMixin):
    """Coordinator follow-up task for an assigned patient.

    The note is operational ("call to check on consult #2 booking"), never
    clinical. Lab values, prescription contents, and doctor-note content must
    not be written here — coordinators are schema-blocked from those fields.
    """

    __tablename__ = "ad_followups"

    coordinator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_coordinators.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(String(500), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_ad_followups_coord_status_due", "coordinator_id", "status", "due_at"),
    )


class PatientInteraction(Base, UUIDMixin, TimestampMixin):
    """Operational log of a coordinator's contact with a patient.

    Replaces ad-hoc WhatsApp/Excel notes (a PHI-leak vector). Summary is
    operational, never clinical.
    """

    __tablename__ = "ad_patient_interactions"

    coordinator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_coordinators.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)

    __table_args__ = (
        Index("ix_ad_patient_interactions_patient", "patient_id", "created_at"),
    )


class StaffRole(Base, UUIDMixin, TimestampMixin):
    """Additional staff role held by a user beyond their primary ``users.role``.

    Roles are permission bundles, not identities (staff-rbac-spec §1): a founder or
    first doctor may hold several. Permissions resolve as the union of the primary
    role plus every row here. Patients are never multi-role — only staff.
    """

    __tablename__ = "ad_staff_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_type=False, values_callable=enum_values),
        nullable=False,
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_ad_staff_roles_user_role"),
    )


class StaffMfa(Base, UUIDMixin, TimestampMixin):
    """TOTP-based MFA enrollment for a staff account (staff-rbac-spec §1).

    ``enabled_at IS NULL`` means a secret has been generated but not yet confirmed with a
    valid code — pending enrollment, freely regenerable. Once confirmed, re-enrollment
    requires an MFA-verified session (see ``mfa_setup`` in ``app.services.auth``).
    """

    __tablename__ = "ad_staff_mfa"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    totp_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_codes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlatformSetting(Base, TimestampMixin):
    """Key/value store for admin-controlled platform configuration.

    Holds non-secret operational toggles only — e.g. the default password-reset
    OTP channel and whether Google Sign-In is activated. Secrets (OAuth client
    secret) live in Secrets Manager / env, never here. Value is a JSONB scalar
    (bool or string) so each key stays self-describing.
    """

    __tablename__ = "ad_platform_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(
        JSONB, nullable=False, server_default=text("'null'::jsonb")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class DailyMetric(Base, UUIDMixin, TimestampMixin):
    """Pre-aggregated daily analytics rollup, populated by kyros.analytics.rollup_daily."""

    __tablename__ = "ad_daily_metrics"

    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[str] = mapped_column(
        String(128), nullable=False, server_default=text("''")
    )
    value: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )

    __table_args__ = (
        UniqueConstraint(
            "metric_date", "metric_key", "dimension", name="uq_ad_daily_metrics"
        ),
        Index("ix_ad_daily_metrics_date_key", "metric_date", "metric_key"),
    )
