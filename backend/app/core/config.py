from __future__ import annotations

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KYROS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,  # empty env vars fall back to field defaults
        extra="ignore",  # .env files often contain more fields than the model
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
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30
    otp_secret: str = "CHANGEME_minimum_32_chars_yyyyyyyyyyyyyyyy"
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5

    # MSG91
    msg91_auth_key: str = ""
    msg91_sender_id: str = "KYROS"
    msg91_template_id: str = ""

    # CORS — list[str] | str: the Union makes pydantic-settings pass parse failures
    # through to the field_validator below, which handles comma-separated .env values.
    cors_allowed_origins: list[str] | str = "http://localhost:3000,http://localhost:5173,http://localhost:8081"

    # AWS
    aws_region: str = "ap-south-1"
    s3_bucket: str = "kyros-dev-uploads"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_endpoint_url: str = ""  # empty → real AWS; set to LocalStack URL for offline dev

    # Google Document AI
    # Name of the AWS Secrets Manager secret holding the GCP service account JSON.
    # Empty → stub mode (returns synthetic OCR output for dev/test).
    google_document_ai_secret_name: str = ""
    google_document_ai_processor_id: str = ""  # full resource name: projects/.../processors/...
    google_document_ai_location: str = "asia-south1"

    # Sentry
    sentry_dsn: str = ""

    # 100ms (HMS) video
    hms_access_key: str = ""
    hms_secret: str = ""
    hms_template_id: str = ""

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    gst_number: str = ""

    # WhatsApp (AiSensy)
    aisensy_api_key: str = ""
    aisensy_campaign_name: str = "kyros_utility"

    # Email (SMTP — mailhog in dev, real SMTP in prod)
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@kyros.clinic"
    admin_alert_email: str = "admin@kyros.clinic"

    # ABDM / ABHA sandbox
    abha_client_id: str = ""
    abha_client_secret: str = ""
    abha_sandbox_url: str = "https://sandbox.abdm.gov.in"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Observability
    cloudwatch_namespace: str = "Kyros/Backend"

    # OpenAPI (disabled in production)
    @property
    def openapi_url(self) -> str | None:
        return None if self.app_env == "production" else "/openapi.json"

    @property
    def docs_url(self) -> str | None:
        return None if self.app_env == "production" else "/docs"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, list):
            return [str(o) for o in v]
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["http://localhost:3000", "http://localhost:5173", "http://localhost:8081"]
            try:
                result = json.loads(v)
                if isinstance(result, list):
                    return [str(o) for o in result]
            except (ValueError, TypeError):
                pass
            return [o.strip() for o in v.split(",") if o.strip()]
        return ["http://localhost:3000", "http://localhost:5173", "http://localhost:8081"]

    @field_validator("jwt_secret", "otp_secret")
    @classmethod
    def _require_32_chars(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("Secret must be at least 32 characters")
        return v


settings = Settings()
