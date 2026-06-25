from __future__ import annotations

import json

from pydantic import field_validator, model_validator
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
    # Staff plane (doctor/coordinator/admin/super_admin): shorter access-token TTL and an
    # idle timeout enforced on /refresh (staff-rbac-spec §1).
    jwt_staff_access_token_expire_minutes: int = 15
    jwt_staff_idle_timeout_minutes: int = 60
    otp_secret: str = "CHANGEME_minimum_32_chars_yyyyyyyyyyyyyyyy"
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5
    # Deliver the OTP to the user's registered email when WhatsApp fails
    # (delivery chain: WhatsApp → email → SMS)
    otp_email_fallback_enabled: bool = True
    # Require phone OTP verification on the public website booking form.
    # Off by default; the website must set NEXT_PUBLIC_BOOKING_OTP_ENABLED to match.
    booking_otp_enabled: bool = False

    # Staff MFA (TOTP) — secret used to encrypt enrolled TOTP secrets at rest.
    mfa_encryption_key: str = "CHANGEME_minimum_32_chars_zzzzzzzzzzzzzzzz"
    mfa_challenge_ttl_seconds: int = 300
    mfa_recovery_codes_count: int = 8

    # Consultation pricing (paise, server-authoritative — never client-supplied).
    # Spec ranges: 500-700 initial, 400-600 follow-up (rupees). Config-driven so pricing
    # is never hardcoded at the call site. Full per-vertical pricing lands later.
    consultation_fee_initial_paise: int = 70000
    consultation_fee_followup_paise: int = 50000

    # Abuse protection — per-IP fixed-window limits on auth endpoints
    rate_limit_enabled: bool = True

    # Ops kill-switch for PHIAuditMiddleware's denial-side audit writes (P33)
    phi_audit_middleware_enabled: bool = True

    # Startup safety — refuse to serve traffic against an outdated schema
    startup_schema_check: bool = True

    # authkey.io — OTP (WhatsApp + SMS) and WhatsApp utility templates
    authkey_api_key: str = ""
    authkey_otp_template_name: str = "kyros_otp"   # approved WhatsApp OTP template name
    authkey_sender_id: str = "KYROS"                # DLT-registered SMS sender ID
    authkey_sms_template_id: str = ""               # DLT SMS template ID (OTP fallback)

    # CORS — list[str] | str: the Union makes pydantic-settings pass parse failures
    # through to the field_validator below, which handles comma-separated .env values.
    cors_allowed_origins: list[str] | str = "http://localhost:3000,http://localhost:5173,http://localhost:8081"

    # AWS
    aws_region: str = "ap-south-1"
    s3_bucket: str = "kyros-dev-uploads"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_endpoint_url: str = ""  # empty → real AWS; set to LocalStack URL for offline dev
    # Client-reachable S3 endpoint for presigned URLs. When the backend signs against a
    # docker-network host (e.g. http://localstack:4566) but the patient's device/browser
    # reaches S3 at a different host (e.g. http://localhost:4566), set this so the host in
    # returned presigned URLs is rewritten. Empty → return URLs as signed (real AWS).
    s3_public_endpoint_url: str = ""
    # KMS key for SSE-KMS on PHI objects. Empty → S3 uses the account default
    # aws/s3 KMS key (still SSE-KMS, satisfies security rule 6).
    s3_kms_key_id: str = ""

    # Google Document AI
    # Name of the AWS Secrets Manager secret holding the GCP service account JSON.
    # Empty → stub mode (returns synthetic OCR output for dev/test).
    google_document_ai_secret_name: str = ""
    google_document_ai_processor_id: str = ""  # full resource name: projects/.../processors/...
    google_document_ai_location: str = "asia-south1"

    # Google Sign-In (patient role) — accepted OAuth client IDs (audiences) for
    # ID-token verification, comma-separated (one per platform: web/iOS/Android).
    # Activation is gated by the admin toggle in ad_platform_settings; configuring
    # IDs here does nothing until an admin enables it. No client secret is needed
    # for ID-token verification, so none is stored.
    google_oauth_client_ids: str = ""

    # Sentry
    sentry_dsn: str = ""

    # 100ms (HMS) video — legacy, replaced by LiveKit
    hms_access_key: str = ""
    hms_secret: str = ""
    hms_template_id: str = ""

    # LiveKit video
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_host: str = "ws://localhost:7880"
    livekit_recordings_bucket: str = ""
    # Video room participant sizing. The default covers a standard 1:1 consult plus
    # support seats. Staff may raise it per-consultation (up to the cap) when
    # creating an on-demand multi-specialist consultation.
    video_default_max_participants: int = 6
    video_max_participants_cap: int = 12

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    gst_number: str = ""

    # WhatsApp utility templates are sent via authkey.io (see authkey_* keys above)

    # Email (SMTP — mailhog in dev, real SMTP in prod)
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "contact@kyrosclinic.com"
    admin_alert_email: str = "admin@kyrosclinic.com"
    # Single ops inbox for new booking inquiries / help queries from the public
    # website. Empty → falls back to admin_alert_email.
    ops_notify_email: str = ""

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

    @property
    def google_oauth_client_id_list(self) -> list[str]:
        return [c.strip() for c in self.google_oauth_client_ids.split(",") if c.strip()]

    @field_validator("jwt_secret", "otp_secret", "mfa_encryption_key")
    @classmethod
    def _require_32_chars(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("Secret must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def _refuse_unsafe_production_config(self) -> Settings:
        """Security rule 8: production refuses to start with placeholder values."""
        if self.app_env != "production":
            return self
        problems: list[str] = []
        if self.jwt_secret.startswith("CHANGEME"):
            problems.append("KYROS_JWT_SECRET is still the placeholder value")
        if self.otp_secret.startswith("CHANGEME"):
            problems.append("KYROS_OTP_SECRET is still the placeholder value")
        if self.mfa_encryption_key.startswith("CHANGEME"):
            problems.append("KYROS_MFA_ENCRYPTION_KEY is still the placeholder value")
        # Razorpay secrets must be present in production: a blank key secret makes
        # verify_payment_signature accept all signatures (H3), and a blank webhook
        # secret rejects all webhooks. Both are unsafe to boot with in production.
        if not self.razorpay_key_secret:
            problems.append("KYROS_RAZORPAY_KEY_SECRET must be set in production")
        if not self.razorpay_webhook_secret:
            problems.append("KYROS_RAZORPAY_WEBHOOK_SECRET must be set in production")
        if self.debug:
            problems.append("KYROS_DEBUG must be false in production")
        origins = self.cors_allowed_origins
        if isinstance(origins, list) and any(
            "localhost" in o or "127.0.0.1" in o for o in origins
        ):
            problems.append("KYROS_CORS_ALLOWED_ORIGINS contains localhost origins")
        if problems:
            raise ValueError(
                "Refusing to start in production: " + "; ".join(problems)
            )
        return self


settings = Settings()
