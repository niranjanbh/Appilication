from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KYROS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://kyros:kyros@localhost:5432/kyros"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security — validated to be >=32 chars at startup
    jwt_secret: str = "CHANGEME_minimum_32_chars_xxxxxxxxxxxxxxxx"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30
    otp_secret: str = "CHANGEME_minimum_32_chars_yyyyyyyyyyyyyyyy"

    # CORS
    cors_allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # AWS
    aws_region: str = "ap-south-1"
    s3_bucket: str = "kyros-dev-uploads"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Sentry
    sentry_dsn: str = ""

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # OpenAPI (disabled in production)
    @property
    def openapi_url(self) -> str | None:
        return None if self.app_env == "production" else "/openapi.json"

    @property
    def docs_url(self) -> str | None:
        return None if self.app_env == "production" else "/docs"

    @field_validator("jwt_secret", "otp_secret")
    @classmethod
    def _require_32_chars(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("Secret must be at least 32 characters")
        return v


settings = Settings()
