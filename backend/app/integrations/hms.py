"""100ms (HMS) video integration.

Provides room creation and role-scoped app token generation.
Stub mode is active when KYROS_HMS_ACCESS_KEY is empty — returns synthetic IDs
so local dev and tests work without real 100ms credentials.

100ms REST API docs: https://www.100ms.live/docs/server-side/v2/how-to-guides/rooms/create-via-api
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog
from jose import jwt

from app.core.config import settings

logger = structlog.get_logger(__name__)

_HMS_BASE_URL = "https://api.100ms.live/v2"
_MGMT_TOKEN_TTL_SECONDS = 86400  # 24 h — management tokens are short-lived internal secrets
_APP_TOKEN_TTL_SECONDS = 3600  # 1 h — plenty for a consultation session


# ── Internal JWT helpers ───────────────────────────────────────────────────────


def _management_token() -> str:
    """Generate a signed management JWT for authenticating 100ms REST API calls."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "access_key": settings.hms_access_key,
        "type": "management",
        "version": 2,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=_MGMT_TOKEN_TTL_SECONDS)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.hms_secret, algorithm="HS256")


def _app_token(*, room_id: str, user_id: str, role: str) -> str:
    """Generate a signed app JWT for a participant to join a 100ms room.

    role must match a role name defined in the 100ms template (e.g. 'patient', 'doctor').
    """
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "access_key": settings.hms_access_key,
        "room_id": room_id,
        "user_id": user_id,
        "role": role,
        "type": "app",
        "version": 2,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=_APP_TOKEN_TTL_SECONDS)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.hms_secret, algorithm="HS256")


# ── Public API ─────────────────────────────────────────────────────────────────


def is_stub_mode() -> bool:
    return not settings.hms_access_key


async def create_room(*, consultation_id: str) -> str:
    """Create a 100ms room for the given consultation.

    Returns the room_id string (e.g. 'room_64c...').
    In stub mode returns a deterministic fake room_id without hitting the API.
    """
    if is_stub_mode():
        synthetic_id = f"stub-room-{consultation_id}"
        logger.info("hms.create_room.stub", consultation_id=consultation_id, room_id=synthetic_id)
        return synthetic_id

    token = _management_token()
    payload: dict[str, Any] = {
        "name": f"kyros-consult-{consultation_id}",
        "description": "Kyros telemedicine consultation",
        "region": "in",  # India region
    }
    if settings.hms_template_id:
        payload["template_id"] = settings.hms_template_id

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{_HMS_BASE_URL}/rooms",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()

    room_id: str = data["id"]
    logger.info("hms.create_room.ok", consultation_id=consultation_id, room_id=room_id)
    return room_id


def generate_patient_token(*, room_id: str, user_id: str) -> str:
    """Return a patient-role app token for joining the room."""
    if is_stub_mode():
        return f"stub-patient-token-{room_id}-{user_id}"
    return _app_token(room_id=room_id, user_id=user_id, role="patient")


def generate_doctor_token(*, room_id: str, user_id: str) -> str:
    """Return a doctor-role app token for joining the room."""
    if is_stub_mode():
        return f"stub-doctor-token-{room_id}-{user_id}"
    return _app_token(room_id=room_id, user_id=user_id, role="doctor")
