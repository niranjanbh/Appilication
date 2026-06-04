from __future__ import annotations

from app.core.config import settings

_PHI_FIELDS = frozenset(
    {
        "phone", "phone_number", "email", "name", "full_name",
        "dob", "date_of_birth", "address", "diagnosis", "prescription",
        "lab_value", "notes", "doctor_notes", "otp", "password",
    }
)


def _scrub_phi(event: dict[str, object], hint: object) -> dict[str, object] | None:
    """Strip PHI from Sentry events before they leave the process."""
    _scrub_dict(event)
    return event


def _scrub_dict(obj: object) -> None:
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if isinstance(key, str) and key.lower() in _PHI_FIELDS:
                obj[key] = "[REDACTED]"
            else:
                _scrub_dict(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            _scrub_dict(item)


def init_sentry() -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            release=settings.app_version,
            before_send=_scrub_phi,  # type: ignore[arg-type]
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
    except ImportError:
        pass
