"""P1 smoke: verify the app can be imported and settings load without error."""
from __future__ import annotations

import os

os.environ.setdefault("KYROS_JWT_SECRET", "test_secret_minimum_32_characters_long_xxxx")
os.environ.setdefault("KYROS_OTP_SECRET", "test_otp_secret_minimum_32_chars_yyyy")


def test_settings_load() -> None:
    from app.core.config import settings

    assert settings.app_env == "development"
    assert len(settings.jwt_secret) >= 32


def test_create_app() -> None:
    from app.main import create_app

    app = create_app()
    assert app.title == "Kyros API"
