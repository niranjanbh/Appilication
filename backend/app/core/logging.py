from __future__ import annotations

import logging
import re
from typing import Any

import structlog

_PHI_KEYS = frozenset({
    "phone", "phone_number", "mobile", "email", "email_address",
    "name", "patient_name", "doctor_name", "full_name",
    "date_of_birth", "dob", "address", "abha_number",
    "lab_value", "lab_values", "prescription_content",
    "diagnosis", "diagnosis_note", "password", "password_hash",
    "token", "token_hash", "otp", "otp_code",
})

_PHONE_RE = re.compile(r"\+?\d{10,15}")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def _scrub_phi(
    _logger: Any, _method: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    """Strip known PHI fields and redact phone/email patterns in values."""
    for key in list(event_dict):
        if key in _PHI_KEYS:
            event_dict[key] = "[REDACTED]"
        elif isinstance(event_dict[key], str):
            val = event_dict[key]
            val = _PHONE_RE.sub("[REDACTED_PHONE]", val)
            val = _EMAIL_RE.sub("[REDACTED_EMAIL]", val)
            event_dict[key] = val
    return event_dict


def configure_logging(*, debug: bool = False) -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _scrub_phi,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=not debug,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
