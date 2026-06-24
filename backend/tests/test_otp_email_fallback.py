"""Email OTP fallback: delivery chain WhatsApp → email → SMS.

The OTP value, Redis storage, and verification path are shared across all
channels — these tests assert only the delivery routing and that a code
delivered by email verifies through the normal /v1/auth/verify-otp flow.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

import pytest

from app.core.config import settings
from app.integrations import authkey
from app.integrations import email as email_integration
from app.services import auth as auth_service

fake_phone_counter = 0


def _phone() -> str:
    return f"+91901{uuid.uuid4().int % 10_000_000:07d}"


class DeliveryRecorder:
    """Patches all three OTP channels and records which were attempted."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        whatsapp_ok: bool,
        email_ok: bool,
        sms_ok: bool,
    ) -> None:
        self.calls: list[str] = []
        self.email_kwargs: dict[str, Any] = {}

        async def fake_whatsapp(phone: str, otp: str) -> bool:
            self.calls.append("whatsapp")
            return whatsapp_ok

        async def fake_sms(phone: str, otp: str) -> bool:
            self.calls.append("sms")
            return sms_ok

        async def fake_email(**kwargs: Any) -> bool:
            self.calls.append("email")
            self.email_kwargs = kwargs
            return email_ok

        monkeypatch.setattr(authkey, "send_otp_whatsapp", fake_whatsapp)
        monkeypatch.setattr(authkey, "send_otp_sms", fake_sms)
        monkeypatch.setattr(email_integration, "send_email_async", fake_email)


async def test_email_attempted_before_sms_when_whatsapp_fails(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=False, email_ok=True, sms_ok=True)
    code = await auth_service._issue_otp(
        redis_client, _phone(), email="patient@test.kyros.local"
    )
    assert rec.calls == ["whatsapp", "email"]
    assert rec.email_kwargs["to_email"] == "patient@test.kyros.local"
    assert code in rec.email_kwargs["html_body"]
    # OTP never in the subject line
    assert code not in rec.email_kwargs["subject"]


async def test_sms_used_when_email_also_fails(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=False, email_ok=False, sms_ok=True)
    await auth_service._issue_otp(redis_client, _phone(), email="patient@test.kyros.local")
    assert rec.calls == ["whatsapp", "email", "sms"]


async def test_no_fallback_when_whatsapp_succeeds(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=True, email_ok=True, sms_ok=True)
    await auth_service._issue_otp(redis_client, _phone(), email="patient@test.kyros.local")
    assert rec.calls == ["whatsapp"]


async def test_email_skipped_without_registered_email(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=False, email_ok=True, sms_ok=True)
    await auth_service._issue_otp(redis_client, _phone(), email=None)
    assert rec.calls == ["whatsapp", "sms"]


async def test_email_skipped_when_flag_disabled(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "otp_email_fallback_enabled", False)
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=False, email_ok=True, sms_ok=True)
    await auth_service._issue_otp(redis_client, _phone(), email="patient@test.kyros.local")
    assert rec.calls == ["whatsapp", "sms"]


async def test_otp_still_issued_when_all_channels_fail(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    DeliveryRecorder(monkeypatch, whatsapp_ok=False, email_ok=False, sms_ok=False)
    phone = _phone()
    code = await auth_service._issue_otp(redis_client, phone, email="p@test.kyros.local")
    assert len(code) == 6
    # The hash is stored, so a code obtained out-of-band still verifies
    await auth_service._verify_otp_code(redis_client, phone, code)


async def test_preferred_email_channel_tried_first(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=True, email_ok=True, sms_ok=True)
    await auth_service._issue_otp(
        redis_client,
        _phone(),
        email="patient@test.kyros.local",
        preferred_channel="email",
    )
    assert rec.calls == ["email"]


async def test_preferred_sms_channel_tried_first(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=True, email_ok=True, sms_ok=True)
    await auth_service._issue_otp(
        redis_client,
        _phone(),
        email="patient@test.kyros.local",
        preferred_channel="sms",
    )
    assert rec.calls == ["sms"]


async def test_preferred_channel_still_falls_back(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=True, email_ok=False, sms_ok=True)
    await auth_service._issue_otp(
        redis_client,
        _phone(),
        email="patient@test.kyros.local",
        preferred_channel="email",
    )
    assert rec.calls == ["email", "whatsapp"]


async def test_preferred_email_rejected_without_registered_email(
    redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.exceptions import BusinessRuleError

    DeliveryRecorder(monkeypatch, whatsapp_ok=True, email_ok=True, sms_ok=True)
    with pytest.raises(BusinessRuleError, match="email_channel_unavailable"):
        await auth_service._issue_otp(
            redis_client, _phone(), email=None, preferred_channel="email"
        )


async def test_send_otp_api_accepts_channel(
    client: Any, db_session: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.conftest import create_patient_user

    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=True, email_ok=True, sms_ok=True)
    user = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/auth/send-otp", json={"phone": user.phone, "channel": "email"}
    )
    assert resp.status_code == 200, resp.text
    assert rec.calls == ["email"]
    assert rec.email_kwargs["to_email"] == user.email


async def test_send_otp_api_rejects_unknown_channel(client: Any) -> None:
    resp = await client.post(
        "/v1/auth/send-otp", json={"phone": "+919000099999", "channel": "carrier_pigeon"}
    )
    assert resp.status_code == 422


async def test_emailed_code_verifies_via_api(
    client: Any, redis_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: signup → OTP delivered by email → /v1/auth/verify-otp."""
    rec = DeliveryRecorder(monkeypatch, whatsapp_ok=False, email_ok=True, sms_ok=False)
    phone = _phone()
    resp = await client.post(
        "/v1/auth/signup",
        json={
            "phone": phone,
            "email": f"otp_{uuid.uuid4().hex[:8]}@test.kyros.local",
            "name": "Synthetic Testuser",
            "password": "TestPass123!",
        },
    )
    assert resp.status_code == 201, resp.text
    assert rec.calls == ["whatsapp", "email"]

    match = re.search(r">(\d{6})<", rec.email_kwargs["html_body"])
    assert match is not None, "OTP code not found in email body"
    code = match.group(1)

    verify = await client.post("/v1/auth/verify-otp", json={"phone": phone, "otp": code})
    assert verify.status_code == 200, verify.text
    data = verify.json()
    assert data["access_token"] and data["refresh_token"]



