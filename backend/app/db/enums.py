from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    COORDINATOR = "coordinator"
    SUPER_ADMIN = "super_admin"


class AppEnv(str, enum.Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
