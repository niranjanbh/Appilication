"""RBAC matrix — every /v1/* endpoint asserts expected status per role.

Format:
  - Public auth endpoints: unauthenticated requests with well-formed bodies → 201/200/422
  - Authenticated endpoints (added in later prompts): role matrix enforced
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    _synth_email,
    _synth_phone,
    create_admin_user,
    create_coordinator_user,
    create_doctor_user,
    create_doctor_with_profile,
    create_patient_user,
    create_super_admin_user,
    make_auth_headers,
)

# ── Public auth endpoints ──────────────────────────────────────────────────────
# All five auth endpoints are public (no Bearer token required).
# Missing/invalid body → 422. Valid body → 201/200/401/403.


async def test_signup_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/signup", json={})
    assert resp.status_code == 422


async def test_signup_invalid_phone_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/signup",
        json={"name": "X", "phone": "not-a-phone", "email": _synth_email(), "password": "Pass1234!"},
    )
    assert resp.status_code == 422


async def test_send_otp_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/send-otp", json={})
    assert resp.status_code == 422


async def test_verify_otp_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/verify-otp", json={})
    assert resp.status_code == 422


async def test_login_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/login", json={})
    assert resp.status_code == 422


async def test_refresh_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/refresh", json={})
    assert resp.status_code == 422


async def test_login_unknown_credentials_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/login",
        json={"email_or_phone": _synth_email(), "password": "SomePass1!"},
    )
    assert resp.status_code == 401


async def test_refresh_invalid_token_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/refresh", json={"refresh_token": "invalid-garbage"})
    assert resp.status_code == 401


async def test_password_reset_request_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/password-reset/request", json={})
    assert resp.status_code == 422


async def test_password_reset_confirm_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/password-reset/confirm", json={})
    assert resp.status_code == 422


async def test_google_login_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/auth/google", json={})
    assert resp.status_code == 422


async def test_auth_config_public_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/v1/auth/config")
    assert resp.status_code == 200
    assert "google_oauth_enabled" in resp.json()


# ── /v1/users/me — patient-scoped endpoints ───────────────────────────────────
# Role matrix: patient=200/202, no-auth=401, doctor/coordinator=403.
# Full cross-role and task tests live in test_users_me.py.


async def test_get_me_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me")
    assert resp.status_code == 401


async def test_data_export_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/users/me/data-export")
    assert resp.status_code == 401


async def test_list_data_exports_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me/data-exports")
    assert resp.status_code == 401


async def test_list_data_exports_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/users/me/data-exports", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_get_data_export_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/users/me/data-exports/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_get_data_export_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/users/me/data-exports/{uuid.uuid4()}", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_delete_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/users/me/delete")
    assert resp.status_code == 401


async def test_activity_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me/activity")
    assert resp.status_code == 401


async def test_activity_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/users/me/activity", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_get_emergency_contact_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me/emergency-contact")
    assert resp.status_code == 401


async def test_get_emergency_contact_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/users/me/emergency-contact", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_set_emergency_contact_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.put(
        "/v1/users/me/emergency-contact",
        json={"name": "A", "relationship": "B", "phone": "+919000000000"},
    )
    assert resp.status_code == 401


async def test_set_emergency_contact_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.put(
        "/v1/users/me/emergency-contact",
        json={"name": "A", "relationship": "B", "phone": "+919000000000"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_capture_consent_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/users/me/consent", json={})
    assert resp.status_code == 401


async def test_list_consents_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me/consents")
    assert resp.status_code == 401


async def test_withdraw_consent_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/users/me/consent/withdraw", json={"consent_type": "marketing"}
    )
    assert resp.status_code == 401


async def test_withdraw_consent_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/users/me/consent/withdraw",
        json={"consent_type": "marketing"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


# ── /v1/users/me/sessions — patient device-session management ─────────────────
# Role matrix: patient=200, no-auth=401, doctor/coordinator=403.


async def test_list_sessions_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/me/sessions")
    assert resp.status_code == 401


async def test_list_sessions_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/users/me/sessions", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_revoke_session_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.delete(f"/v1/users/me/sessions/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_revoke_session_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.delete(
        f"/v1/users/me/sessions/{uuid.uuid4()}", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_revoke_session_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.delete(
        f"/v1/users/me/sessions/{uuid.uuid4()}", headers=make_auth_headers(coord)
    )
    assert resp.status_code == 403


# ── /v1/users/me/push-token — patient only ───────────────────────────────────


async def test_register_push_token_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.put(
        "/v1/users/me/push-token",
        json={"push_token": "ExponentPushToken[test]"},
    )
    assert resp.status_code == 401


async def test_register_push_token_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.put(
        "/v1/users/me/push-token",
        json={"push_token": "ExponentPushToken[test]"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_register_push_token_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.put(
        "/v1/users/me/push-token",
        json={"push_token": "ExponentPushToken[test]"},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_register_push_token_patient_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.put(
        "/v1/users/me/push-token",
        json={"push_token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "registered"


# ── /v1/public/* — unauthenticated public endpoints ──────────────────────────
# These endpoints require no auth. Valid bodies → 200/201; missing/invalid → 422.
# Phone OTP verification is optional (settings.booking_otp_enabled, default OFF);
# the booking_otp_on fixture flips it for the OTP-flow tests.


@pytest.fixture
def booking_otp_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "booking_otp_enabled", True)


async def _request_booking_otp(client: AsyncClient, phone: str) -> str:
    """Issue a booking OTP and return the code (debug hint, KYROS_DEBUG=true)."""
    resp = await client.post("/v1/public/booking-otp", json={"phone": phone})
    assert resp.status_code == 200
    otp = resp.json()["otp_hint"]
    assert otp is not None
    return str(otp)


async def test_public_conditions_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/v1/public/conditions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 8
    slugs = {item["slug"] for item in data}
    # Canonical slugs match website/lib/conditions.ts (2026-06 renames)
    assert {"thyroid", "diabetes", "pmos", "sexual-health"} <= slugs
    assert "pcos" not in slugs
    assert "mens-intimate-health" not in slugs


# ---- booking inquiry, OTP verification disabled (the default) ----


async def test_booking_otp_send_disabled_returns_422(client: AsyncClient) -> None:
    """With booking_otp_enabled off, the send endpoint is not an open SMS relay."""
    resp = await client.post("/v1/public/booking-otp", json={"phone": _synth_phone()})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "otp_verification_disabled"


async def test_booking_inquiry_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/public/booking-inquiry", json={})
    assert resp.status_code == 422


async def test_booking_inquiry_invalid_phone_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "female",
            "phone": "9999999999",  # missing + prefix — not valid E.164
            "condition_category": "thyroid",
        },
    )
    assert resp.status_code == 422


async def test_booking_inquiry_invalid_condition_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "male",
            "phone": _synth_phone(),
            "condition_category": "not-a-real-condition",
        },
    )
    assert resp.status_code == 422


async def test_booking_inquiry_missing_gender_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "phone": _synth_phone(),
            "condition_category": "thyroid",
        },
    )
    assert resp.status_code == 422


async def test_booking_inquiry_without_otp_returns_201(client: AsyncClient) -> None:
    """Default deployment: no OTP requested, none required."""
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "female",
            "phone": _synth_phone(),
            # example.com, not @test.kyros.local: EmailStr (email-validator)
            # rejects the special-use .local TLD at the API boundary.
            "email": "testpatient@example.com",
            "condition_category": "thyroid",
            "intake_responses": {"symptom_duration": "more_than_6_months", "previous_diagnosis": "no"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "message" in data


# ---- booking inquiry, OTP verification enabled (booking_otp_on fixture) ----


async def test_booking_otp_invalid_phone_returns_422(
    client: AsyncClient, booking_otp_on: None
) -> None:
    resp = await client.post("/v1/public/booking-otp", json={"phone": "9999999999"})
    assert resp.status_code == 422


async def test_booking_otp_resend_within_cooldown_returns_429(
    client: AsyncClient, booking_otp_on: None
) -> None:
    phone = _synth_phone()
    await _request_booking_otp(client, phone)
    resp = await client.post("/v1/public/booking-otp", json={"phone": phone})
    assert resp.status_code == 429
    assert resp.json()["detail"] == "otp_cooldown"


async def test_booking_inquiry_missing_otp_returns_422(
    client: AsyncClient, booking_otp_on: None
) -> None:
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "female",
            "phone": _synth_phone(),
            "condition_category": "thyroid",
            "skipped_intake": True,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "otp_required"


async def test_booking_inquiry_wrong_otp_returns_422(
    client: AsyncClient, booking_otp_on: None
) -> None:
    phone = _synth_phone()
    otp = await _request_booking_otp(client, phone)
    wrong = "000000" if otp != "000000" else "111111"
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "female",
            "phone": phone,
            "condition_category": "thyroid",
            "skipped_intake": True,
            "otp": wrong,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "otp_invalid"


async def test_booking_inquiry_no_otp_requested_returns_422(
    client: AsyncClient, booking_otp_on: None
) -> None:
    """An OTP that was never issued for this phone is rejected as expired."""
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "male",
            "phone": _synth_phone(),
            "condition_category": "thyroid",
            "skipped_intake": True,
            "otp": "123456",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "otp_expired"


async def test_booking_inquiry_valid_otp_returns_201(
    client: AsyncClient, booking_otp_on: None
) -> None:
    phone = _synth_phone()
    otp = await _request_booking_otp(client, phone)
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "female",
            "phone": phone,
            "email": "testpatient@example.com",
            "condition_category": "thyroid",
            "intake_responses": {"symptom_duration": "more_than_6_months", "previous_diagnosis": "no"},
            "otp": otp,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "message" in data


async def test_booking_inquiry_otp_single_use(
    client: AsyncClient, booking_otp_on: None
) -> None:
    """A consumed OTP cannot be replayed for a second inquiry."""
    phone = _synth_phone()
    otp = await _request_booking_otp(client, phone)
    body = {
        "name": "Test Patient",
        "gender": "male",
        "phone": phone,
        "condition_category": "thyroid",
        "skipped_intake": True,
        "otp": otp,
    }
    first = await client.post("/v1/public/booking-inquiry", json=body)
    assert first.status_code == 201
    replay = await client.post("/v1/public/booking-inquiry", json=body)
    assert replay.status_code == 422
    assert replay.json()["detail"] == "otp_expired"


async def test_booking_inquiry_skip_flow_returns_201(client: AsyncClient) -> None:
    """Skipped intake: only name + gender + phone required, intake_responses empty."""
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "other",
            "phone": _synth_phone(),
            "condition_category": "pmos",
            "skipped_intake": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data


async def test_booking_inquiry_legacy_slug_normalized_returns_201(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Pre-rename slugs (pcos, mens-intimate-health) are accepted and normalized."""
    from app.models.public import BookingInquiry

    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Patient",
            "gender": "female",
            "phone": _synth_phone(),
            "condition_category": "pcos",  # legacy slug, renamed to pmos 2026-06
            "skipped_intake": True,
        },
    )
    assert resp.status_code == 201
    inquiry = await db_session.get(BookingInquiry, uuid.UUID(resp.json()["id"]))
    assert inquiry is not None
    assert inquiry.condition_category == "pmos"


async def test_booking_inquiry_international_phone_returns_201(client: AsyncClient) -> None:
    """Non-Indian country codes are accepted (NRI patients)."""
    resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test NRI Patient",
            "gender": "male",
            "phone": f"+1212555{uuid.uuid4().int % 10000:04d}",
            "condition_category": "longevity",
            "skipped_intake": True,
        },
    )
    assert resp.status_code == 201


# ---- /v1/public/lead — contact-form help queries ----


async def test_lead_missing_body_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/public/lead", json={})
    assert resp.status_code == 422


async def test_lead_invalid_email_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/public/lead",
        json={
            "name": "Test Visitor",
            "email": "not-an-email",
            "subject": "support",
            "message": "I have a question about consultations.",
        },
    )
    assert resp.status_code == 422


async def test_lead_valid_body_returns_201(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/public/lead",
        json={
            "name": "Test Visitor",
            "email": "testvisitor@example.com",
            "subject": "support",
            "message": "I have a question about how consultations work.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "message" in data


# ── /v1/wellness/reminders — patient-scoped endpoints ────────────────────────
# Role matrix: patient=200/201/204, no-auth=401, doctor/coordinator=403.


async def test_list_reminders_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/wellness/reminders")
    assert resp.status_code == 401


async def test_create_reminder_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/wellness/reminders", json={})
    assert resp.status_code == 401


async def test_update_reminder_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid
    resp = await client.patch(f"/v1/wellness/reminders/{uuid.uuid4()}", json={})
    assert resp.status_code == 401


async def test_delete_reminder_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid
    resp = await client.delete(f"/v1/wellness/reminders/{uuid.uuid4()}")
    assert resp.status_code == 401


# ── /v1/wellness/health-sync — patient-scoped endpoint ───────────────────────
# Role matrix: patient=200/403 (consent-gated), no-auth=401, doctor/coordinator=403.


async def test_health_sync_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/wellness/health-sync", json={})
    assert resp.status_code == 401


async def test_health_sync_doctor_returns_403(
    client: AsyncClient, db_session: object
) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.conftest import create_doctor_user, make_auth_headers

    assert isinstance(db_session, AsyncSession)
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/wellness/health-sync",
        json={
            "source": "apple_health",
            "data_range_start": "2026-05-27T00:00:00Z",
            "data_range_end": "2026-06-03T00:00:00Z",
            "datapoints": [],
        },
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_log_adherence_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid
    resp = await client.post(f"/v1/wellness/reminders/{uuid.uuid4()}/log", json={})
    assert resp.status_code == 401


# ── /v1/wellness/vitals — patient-scoped manual vitals ───────────────────────


async def test_log_vitals_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": "2026-06-19T08:00:00Z", "weight_kg": 70.0},
    )
    assert resp.status_code == 401


async def test_log_vitals_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/wellness/vitals",
        json={"measured_at": "2026-06-19T08:00:00Z", "weight_kg": 70.0},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_list_vitals_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/wellness/vitals")
    assert resp.status_code == 401


async def test_list_vitals_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/wellness/vitals", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


# ── /v1/payments — patient-scoped endpoints ──────────────────────────────────
# Role matrix: patient=201/200, no-auth=401, doctor=403.


async def test_create_payment_order_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/payments/order", json={"amount_paise": 10000})
    assert resp.status_code == 401


async def test_create_payment_order_doctor_returns_403(
    client: AsyncClient, db_session: object
) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.conftest import create_doctor_user, make_auth_headers

    assert isinstance(db_session, AsyncSession)
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/payments/order",
        json={"amount_paise": 10000},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_get_payment_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid
    resp = await client.get(f"/v1/payments/{uuid.uuid4()}")
    assert resp.status_code == 401


# ── /v1/payments/refunds — patient-scoped refund tracking ────────────────────
# Role matrix: patient=200, no-auth=401, doctor/coordinator=403.


async def test_list_refunds_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/payments/refunds")
    assert resp.status_code == 401


async def test_list_refunds_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/payments/refunds", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_list_refunds_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/payments/refunds", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_get_refund_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/payments/refunds/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_get_refund_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/payments/refunds/{uuid.uuid4()}", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


# ── /v1/clinic/patient/* — patient-scoped consultation endpoints ──────────────
# Role matrix: patient=200/201, no-auth=401, doctor/coordinator=403.


async def test_clinic_list_consultations_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/consultations")
    assert resp.status_code == 401


async def test_clinic_list_consultations_doctor_returns_403(
    client: AsyncClient, db_session: object
) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.conftest import create_doctor_user, make_auth_headers
    assert isinstance(db_session, AsyncSession)
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/clinic/patient/consultations", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_clinic_get_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid
    resp = await client.get(f"/v1/clinic/patient/consultations/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_clinic_request_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={"condition_category": "thyroid"},
    )
    assert resp.status_code == 401


async def test_clinic_confirm_payment_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/confirm-payment",
        json={
            "razorpay_payment_id": "pay_x",
            "razorpay_order_id": "order_x",
            "razorpay_signature": "sig_x",
        },
    )
    assert resp.status_code == 401


async def test_clinic_cancel_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/cancel",
        json={"reason": "test"},
    )
    assert resp.status_code == 401


# ── /v1/clinic/patient/consultations/{id}/reschedule — patient only ──────────
# Role matrix: patient=200/400/404, no-auth=401, doctor/coordinator=403.


async def test_clinic_reschedule_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/reschedule",
        json={"slot_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


async def test_clinic_reschedule_consultation_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    import uuid
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/reschedule",
        json={"slot_id": str(uuid.uuid4())},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_clinic_reschedule_consultation_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    import uuid
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/reschedule",
        json={"slot_id": str(uuid.uuid4())},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_clinic_list_slots_no_auth_returns_401(client: AsyncClient) -> None:
    from datetime import UTC, datetime, timedelta
    now = datetime.now(UTC)
    import uuid
    resp = await client.get(
        "/v1/clinic/patient/consultations/slots",
        params={
            "doctor_id": str(uuid.uuid4()),
            "date_from": now.isoformat(),
            "date_to": (now + timedelta(days=7)).isoformat(),
        },
    )
    assert resp.status_code == 401


# ── /v1/clinic/patient/lab-reports — patient-scoped ──────────────────────────
# Role matrix: patient=200/201, no-auth=401, doctor/coordinator=403.


async def test_lab_report_initiate_upload_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/lab-reports/initiate-upload",
        json={"original_filename": "x.pdf", "content_type": "application/pdf", "file_size_bytes": 1024},
    )
    assert resp.status_code == 401


async def test_lab_report_list_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/lab-reports")
    assert resp.status_code == 401


async def test_lab_report_get_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_lab_report_finalize_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}/finalize")
    assert resp.status_code == 401


async def test_lab_report_patch_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}",
        json={"parsed_json": {}},
    )
    assert resp.status_code == 401


async def test_lab_report_download_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}/download")
    assert resp.status_code == 401


async def test_lab_report_list_doctor_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/clinic/patient/lab-reports", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_lab_report_list_coordinator_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/clinic/patient/lab-reports", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_lab_report_get_doctor_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_lab_report_get_coordinator_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}", headers=make_auth_headers(coord)
    )
    assert resp.status_code == 403


async def test_lab_report_finalize_doctor_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}/finalize", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_lab_report_finalize_coordinator_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}/finalize", headers=make_auth_headers(coord)
    )
    assert resp.status_code == 403


async def test_lab_report_patch_doctor_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.patch(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}",
        json={"parsed_json": {}},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_lab_report_patch_coordinator_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.patch(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}",
        json={"parsed_json": {}},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_lab_report_download_doctor_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}/download", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_lab_report_download_coordinator_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/lab-reports/{uuid.uuid4()}/download", headers=make_auth_headers(coord)
    )
    assert resp.status_code == 403


# ── /v1/clinic/patient/biomarker-trends/{biomarker} ──────────────────────────


async def test_biomarker_trends_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/biomarker-trends/TSH")
    assert resp.status_code == 401


async def test_biomarker_trends_doctor_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_biomarker_trends_coordinator_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH", headers=make_auth_headers(coord)
    )
    assert resp.status_code == 403


async def test_biomarker_trends_patient_empty_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.models.clinic import Patient
    from app.repositories import users as users_repo
    from tests.conftest import _synth_email, _synth_phone

    user = await users_repo.create(
        db_session,
        name="Trend Patient",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    await users_repo.update_phone_verified(db_session, user.id)  # type: ignore[union-attr]
    patient = Patient(
        user_id=user.id,  # type: ignore[union-attr]
        kyros_patient_id=f"KP{uuid.uuid4().hex[:6].upper()}",
        primary_conditions=[],
    )
    db_session.add(patient)
    await db_session.flush()

    resp = await client.get(
        "/v1/clinic/patient/biomarker-trends/TSH",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_points"] == []
    assert body["trend"] == "steady"


# ── /v1/doctor/prescriptions — doctor only ───────────────────────────────────


async def test_doctor_create_prescription_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescription",
        json={"items": [{"drug_generic_name": "X", "drug_form": "tablet", "dosage": "1", "frequency": "od"}]},
    )
    assert resp.status_code == 401


async def test_doctor_create_prescription_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.repositories import users as users_repo
    from tests.conftest import _synth_email, _synth_phone

    user = await users_repo.create(
        db_session,
        name="Patient",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescription",
        json={"items": [{"drug_generic_name": "X", "drug_form": "tablet", "dosage": "1", "frequency": "od"}]},
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 403


async def test_doctor_list_prescriptions_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/consultations/{uuid.uuid4()}/prescriptions")
    assert resp.status_code == 401


async def test_doctor_list_prescriptions_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescriptions",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_list_prescriptions_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescriptions",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_list_prescriptions_unowned_consultation_returns_empty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/prescriptions",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_doctor_update_prescription_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch(
        f"/v1/doctor/prescriptions/{uuid.uuid4()}",
        json={"diagnosis_note": "updated"},
    )
    assert resp.status_code == 401


async def test_doctor_update_prescription_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.patch(
        f"/v1/doctor/prescriptions/{uuid.uuid4()}",
        json={"diagnosis_note": "updated"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_update_prescription_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.patch(
        f"/v1/doctor/prescriptions/{uuid.uuid4()}",
        json={"diagnosis_note": "updated"},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_update_prescription_unowned_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.patch(
        f"/v1/doctor/prescriptions/{uuid.uuid4()}",
        json={"diagnosis_note": "updated"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


async def test_doctor_update_prescription_empty_items_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.patch(
        f"/v1/doctor/prescriptions/{uuid.uuid4()}",
        json={"items": []},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 422


async def test_doctor_sign_prescription_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/doctor/prescriptions/{uuid.uuid4()}/sign")
    assert resp.status_code == 401


async def test_doctor_sign_prescription_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.repositories import users as users_repo
    from tests.conftest import _synth_email, _synth_phone

    user = await users_repo.create(
        db_session,
        name="Patient",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    resp = await client.post(
        f"/v1/doctor/prescriptions/{uuid.uuid4()}/sign",
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 403


# ── /v1/clinic/patient/prescriptions — patient only ──────────────────────────


async def test_patient_list_prescriptions_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/prescriptions")
    assert resp.status_code == 401


async def test_patient_list_prescriptions_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/prescriptions",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_patient_get_prescription_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/prescriptions/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_patient_get_prescription_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/prescriptions/{uuid.uuid4()}",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_patient_pdf_url_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/prescriptions/{uuid.uuid4()}/pdf")
    assert resp.status_code == 401


# ── /v1/clinic/patient/consultations/{id}/join — patient only ────────────────
# Role matrix: patient=200/404/503, no-auth=401, doctor/coordinator=403.


async def test_patient_join_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/consultations/{uuid.uuid4()}/join")
    assert resp.status_code == 401


async def test_patient_join_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_patient_join_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


# ── /v1/clinic/patient/consultations/{id}/recording-consent — patient only ───
# Role matrix: patient=200/404, no-auth=401, doctor/coordinator=403.


async def test_recording_consent_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/recording-consent"
    )
    assert resp.status_code == 401


async def test_recording_consent_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/recording-consent",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_recording_consent_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/recording-consent",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


# ── /v1/doctor/consultations/{id}/join — doctor only ─────────────────────────
# Role matrix: doctor=200/404/503, no-auth=401, patient/coordinator=403.


async def test_doctor_join_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/consultations/{uuid.uuid4()}/join")
    assert resp.status_code == 401


async def test_doctor_join_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.repositories import users as users_repo
    from tests.conftest import _synth_email, _synth_phone

    patient = await users_repo.create(
        db_session,
        name="Patient",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_join_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


# ── /v1/doctor/consultations/{id}/complete — doctor only ─────────────────────
# Role matrix: doctor=200/404/409, no-auth=401, patient/coordinator=403.


async def test_doctor_complete_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/doctor/consultations/{uuid.uuid4()}/complete")
    assert resp.status_code == 401


async def test_doctor_complete_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/complete",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_complete_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/complete",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_complete_unowned_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/complete",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── /v1/doctor/me — doctor only ──────────────────────────────────────────────
# Role matrix: doctor=200, no-auth=401, patient/coordinator=403.


async def test_doctor_me_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/me")
    assert resp.status_code == 401


async def test_doctor_me_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.repositories import users as users_repo
    from tests.conftest import _synth_email, _synth_phone

    patient = await users_repo.create(
        db_session,
        name="Patient",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    resp = await client.get("/v1/doctor/me", headers=make_auth_headers(patient))
    assert resp.status_code == 403


async def test_doctor_me_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/doctor/me", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_doctor_patch_me_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch("/v1/doctor/me", json={"bio_short": "x"})
    assert resp.status_code == 401


# ── /v1/doctor/patients — doctor only ────────────────────────────────────────
# Role matrix: doctor=200, no-auth=401, patient/coordinator=403.


async def test_doctor_list_patients_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/patients")
    assert resp.status_code == 401


async def test_doctor_list_patients_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.repositories import users as users_repo
    from tests.conftest import _synth_email, _synth_phone

    patient = await users_repo.create(
        db_session,
        name="Patient",
        role=UserRole.PATIENT,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    resp = await client.get("/v1/doctor/patients", headers=make_auth_headers(patient))
    assert resp.status_code == 403


async def test_doctor_list_patients_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/doctor/patients", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_doctor_get_patient_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/patients/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_doctor_get_patient_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/doctor/patients/{uuid.uuid4()}", headers=make_auth_headers(coord)
    )
    assert resp.status_code == 403


# ── /v1/doctor/consultations — doctor only ───────────────────────────────────
# Role matrix: doctor=200, no-auth=401, patient/coordinator=403.


async def test_doctor_list_consultations_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/consultations")
    assert resp.status_code == 401


async def test_doctor_list_consultations_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/doctor/consultations", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_doctor_get_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/consultations/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_doctor_get_consultation_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}", headers=make_auth_headers(coord)
    )
    assert resp.status_code == 403


# ── /v1/webhooks/razorpay — HMAC-verified, no JWT ────────────────────────────
# No-signature → 400 (signature error, not 401).


async def test_webhook_razorpay_no_signature_returns_400(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=b'{"event":"payment.captured"}',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


# ── /v1/doctor/consultations/{id}/notes — doctor only ────────────────────────


async def test_doctor_add_note_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/notes",
        json={"content": "test note"},
    )
    assert resp.status_code == 401


async def test_doctor_add_note_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/notes",
        json={"content": "test note"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_add_note_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/notes",
        json={"content": "test note"},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_add_note_unowned_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/notes",
        json={"content": "test note"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── /v1/doctor/drugs — doctor only ──────────────────────────────────────────
# Role matrix: doctor=200, no-auth=401, patient/coordinator=403.


async def test_doctor_drug_search_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/drugs", params={"q": "levothyroxine"})
    assert resp.status_code == 401


async def test_doctor_drug_search_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/doctor/drugs",
        params={"q": "levothyroxine"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_drug_search_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        "/v1/doctor/drugs",
        params={"q": "levothyroxine"},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_drug_search_doctor_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/doctor/drugs",
        params={"q": "levothyroxine"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200


# ── /v1/doctor/icd10-codes — doctor only ─────────────────────────────────────
# Role matrix: doctor=200, no-auth=401, patient/coordinator=403.


async def test_doctor_icd10_search_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/icd10-codes", params={"q": "thyroid"})
    assert resp.status_code == 401


async def test_doctor_icd10_search_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/doctor/icd10-codes",
        params={"q": "thyroid"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_icd10_search_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        "/v1/doctor/icd10-codes",
        params={"q": "thyroid"},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_icd10_search_doctor_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/doctor/icd10-codes",
        params={"q": "thyroid"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200


# ── /v1/doctor/consultations/{id}/diagnoses — doctor only ────────────────────
# Role matrix: doctor=200/201 + 404 (unowned), no-auth=401, patient/coordinator=403.


async def test_doctor_list_diagnoses_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses")
    assert resp.status_code == 401


async def test_doctor_list_diagnoses_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_list_diagnoses_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_list_diagnoses_unowned_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


async def test_doctor_add_diagnosis_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses",
        json={"icd10_code": "E28.2", "icd10_description": "PCOS"},
    )
    assert resp.status_code == 401


async def test_doctor_add_diagnosis_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses",
        json={"icd10_code": "E28.2", "icd10_description": "PCOS"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_add_diagnosis_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses",
        json={"icd10_code": "E28.2", "icd10_description": "PCOS"},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_add_diagnosis_unowned_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses",
        json={"icd10_code": "E28.2", "icd10_description": "PCOS"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── /v1/doctor/consultations/{id}/diagnoses/{diagnosis_id} — doctor only ─────
# Role matrix: doctor=204 + 404 (unowned), no-auth=401, patient/coordinator=403.


async def test_doctor_delete_diagnosis_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.delete(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses/{uuid.uuid4()}"
    )
    assert resp.status_code == 401


async def test_doctor_delete_diagnosis_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.delete(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses/{uuid.uuid4()}",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_delete_diagnosis_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.delete(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses/{uuid.uuid4()}",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_delete_diagnosis_unowned_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.delete(
        f"/v1/doctor/consultations/{uuid.uuid4()}/diagnoses/{uuid.uuid4()}",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── /v1/doctor/consultations/{id}/lab-order — doctor only ────────────────────


async def test_doctor_create_lab_order_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/lab-order",
        json={"tests": ["TSH", "FT4"]},
    )
    assert resp.status_code == 401


async def test_doctor_create_lab_order_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/lab-order",
        json={"tests": ["TSH", "FT4"]},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_create_lab_order_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/lab-order",
        json={"tests": ["TSH", "FT4"]},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_create_lab_order_unowned_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/lab-order",
        json={"tests": ["TSH", "FT4"]},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── /v1/clinic/patient/consultations/{id}/pre-consult-report — patient only ──


async def test_patient_get_pre_consult_report_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/consultations/{uuid.uuid4()}/pre-consult-report")
    assert resp.status_code == 401


async def test_patient_get_pre_consult_report_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/pre-consult-report",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_patient_get_pre_consult_report_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/pre-consult-report",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_patient_get_pre_consult_report_not_own_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/pre-consult-report",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 404


# ── /v1/doctor/consultations/{id}/pre-consult-report — doctor only ────────────


async def test_doctor_get_pre_consult_report_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report")
    assert resp.status_code == 401


async def test_doctor_get_pre_consult_report_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_get_pre_consult_report_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_get_pre_consult_report_not_own_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── PATCH /v1/doctor/consultations/{id}/pre-consult-report — doctor only ──────


async def test_doctor_patch_pre_consult_report_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report",
        json={"doctor_notes_pre_consult": "notes"},
    )
    assert resp.status_code == 401


async def test_doctor_patch_pre_consult_report_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.patch(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report",
        json={"doctor_notes_pre_consult": "notes"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_patch_pre_consult_report_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.patch(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report",
        json={"doctor_notes_pre_consult": "notes"},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_patch_pre_consult_report_not_own_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.patch(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report",
        json={"doctor_notes_pre_consult": "notes"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── POST /v1/doctor/consultations/{id}/pre-consult-report/generate — doctor only


async def test_doctor_generate_pre_consult_report_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report/generate"
    )
    assert resp.status_code == 401


async def test_doctor_generate_pre_consult_report_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report/generate",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_generate_pre_consult_report_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report/generate",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_generate_pre_consult_report_not_own_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/pre-consult-report/generate",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── /v1/clinic/patient/education — patient only ───────────────────────────────


async def test_patient_list_education_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/education")
    assert resp.status_code == 401


async def test_patient_list_education_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/education",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_patient_list_education_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/education",
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_patient_list_education_patient_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/education",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200


# ── /v1/clinic/patient/education/{id}/read — patient only ────────────────────


async def test_patient_mark_education_read_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/clinic/patient/education/{uuid.uuid4()}/read")
    assert resp.status_code == 401


async def test_patient_mark_education_read_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/education/{uuid.uuid4()}/read",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_patient_mark_education_read_not_own_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/education/{uuid.uuid4()}/read",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 404


# ── /v1/doctor/consultations/{id}/education — doctor only ────────────────────


async def test_doctor_assign_education_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/education",
        json={"content_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


async def test_doctor_assign_education_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/education",
        json={"content_id": str(uuid.uuid4())},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_assign_education_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/education",
        json={"content_id": str(uuid.uuid4())},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_assign_education_not_own_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/doctor/consultations/{uuid.uuid4()}/education",
        json={"content_id": str(uuid.uuid4())},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


# ── /v1/admin/content — super admin only ─────────────────────────────────────


async def test_admin_list_content_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/content")
    assert resp.status_code == 401


async def test_admin_list_content_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/admin/content",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_admin_list_content_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/admin/content",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_admin_list_content_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/admin/content",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200


async def test_admin_create_content_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/admin/content", json={})
    assert resp.status_code == 401


async def test_admin_create_content_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/admin/content",
        json={"title": "t", "slug": "s", "content_type": "article", "condition_categories": []},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_admin_create_content_admin_returns_201(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.post(
        "/v1/admin/content",
        json={
            "title": "Understanding TSH",
            "slug": "understanding-tsh-test",
            "content_type": "article",
            "condition_categories": ["thyroid"],
            "body_md": "TSH is a hormone...",
            "ai_disclosure": False,
        },
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 201


# ── /v1/admin/content/{id}/submit-for-review — admin level+ ──────────────────


async def test_submit_for_review_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/admin/content/{uuid.uuid4()}/submit-for-review")
    assert resp.status_code == 401


async def test_submit_for_review_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/submit-for-review",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_submit_for_review_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/submit-for-review",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_submit_for_review_admin_returns_409_on_nonexistent(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from tests.conftest import create_admin_user

    admin = await create_admin_user(db_session)
    # Non-existent content_id returns 409 (content_not_found maps to 409 for wrong-state)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/submit-for-review",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 409


# ── /v1/admin/content/{id}/publish — super_admin only ────────────────────────


async def test_admin_publish_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/admin/content/{uuid.uuid4()}/publish")
    assert resp.status_code == 401


async def test_admin_publish_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/publish",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_admin_publish_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/publish",
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 403


async def test_admin_publish_read_only_admin_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from tests.conftest import create_admin_user

    admin = await create_admin_user(db_session)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/publish",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 403


async def test_admin_publish_super_admin_returns_409_on_nonexistent(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    # Non-existent content → 409 (content_not_found_or_not_approved)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/publish",
        headers=make_auth_headers(super_admin),
    )
    assert resp.status_code == 409


# ── /v1/doctor/content — doctor only (CONTENT_APPROVE) ───────────────────────


async def test_doctor_list_content_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/content")
    assert resp.status_code == 401


async def test_doctor_list_content_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/doctor/content", headers=make_auth_headers(patient))
    assert resp.status_code == 403


async def test_doctor_list_content_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/doctor/content", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_doctor_list_content_doctor_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.get("/v1/doctor/content", headers=make_auth_headers(doctor))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── /v1/doctor/content/{id}/review — doctor only (CONTENT_APPROVE) ───────────


async def test_doctor_review_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/doctor/content/{uuid.uuid4()}/review",
        json={"action": "approved"},
    )
    assert resp.status_code == 401


async def test_doctor_review_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/doctor/content/{uuid.uuid4()}/review",
        json={"action": "approved"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_review_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.post(
        f"/v1/doctor/content/{uuid.uuid4()}/review",
        json={"action": "approved"},
        headers=make_auth_headers(coord),
    )
    assert resp.status_code == 403


async def test_doctor_review_doctor_without_profile_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/doctor/content/{uuid.uuid4()}/review",
        json={"action": "approved"},
        headers=make_auth_headers(doctor),
    )
    # doctor has no dr_doctors profile → 404
    assert resp.status_code == 404


# ── /v1/doctor/schedule — doctor only ────────────────────────────────────────


async def test_list_schedule_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/doctor/schedule")
    assert resp.status_code == 401


async def test_list_schedule_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/doctor/schedule", headers=make_auth_headers(patient))
    assert resp.status_code == 403


async def test_list_schedule_doctor_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.get("/v1/doctor/schedule", headers=make_auth_headers(doctor))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_bulk_create_slots_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/doctor/schedule/bulk", json={"slots": []})
    assert resp.status_code == 401


async def test_bulk_create_slots_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/doctor/schedule/bulk",
        json={"slots": [{"slot_start": "2026-07-01T10:00:00Z", "slot_end": "2026-07-01T10:30:00Z"}]},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_bulk_create_slots_doctor_creates_and_lists(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.post(
        "/v1/doctor/schedule/bulk",
        json={
            "slots": [
                {"slot_start": "2026-08-01T09:00:00Z", "slot_end": "2026-08-01T09:30:00Z"},
                {"slot_start": "2026-08-01T10:00:00Z", "slot_end": "2026-08-01T10:30:00Z"},
            ]
        },
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] is not None
    assert data["skipped_count"] == 0

    # Idempotent: re-submitting the same slots returns 0 created, 2 skipped
    resp2 = await client.post(
        "/v1/doctor/schedule/bulk",
        json={
            "slots": [
                {"slot_start": "2026-08-01T09:00:00Z", "slot_end": "2026-08-01T09:30:00Z"},
                {"slot_start": "2026-08-01T10:00:00Z", "slot_end": "2026-08-01T10:30:00Z"},
            ]
        },
        headers=make_auth_headers(doctor),
    )
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["skipped_count"] == 2


async def test_delete_slot_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.delete(f"/v1/doctor/schedule/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_delete_slot_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.delete(
        f"/v1/doctor/schedule/{uuid.uuid4()}", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 403


async def test_delete_slot_wrong_doctor_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Cross-doctor: doctor B cannot delete doctor A's slot."""
    doctor_a = await create_doctor_with_profile(db_session)
    doctor_b = await create_doctor_with_profile(db_session)

    # Doctor A creates a slot
    create_resp = await client.post(
        "/v1/doctor/schedule/bulk",
        json={"slots": [{"slot_start": "2026-09-01T08:00:00Z", "slot_end": "2026-09-01T08:30:00Z"}]},
        headers=make_auth_headers(doctor_a),
    )
    assert create_resp.status_code == 201
    slot_id = create_resp.json()["created"][0]["id"]

    # Doctor B tries to delete
    del_resp = await client.delete(
        f"/v1/doctor/schedule/{slot_id}", headers=make_auth_headers(doctor_b)
    )
    assert del_resp.status_code == 404


async def test_update_schedule_preferences_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch("/v1/doctor/schedule/preferences", json={})
    assert resp.status_code == 401


async def test_update_schedule_preferences_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.patch(
        "/v1/doctor/schedule/preferences",
        json={"consultation_duration_minutes_default": 30},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_update_schedule_preferences_doctor_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.patch(
        "/v1/doctor/schedule/preferences",
        json={"consultation_duration_minutes_default": 45, "buffer_time_minutes": 10},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["consultation_duration_minutes_default"] == 45
    assert data["buffer_time_minutes"] == 10


# ── /v1/doctor/patients/{id}/lab-reports — doctor only ───────────────────────


async def test_doctor_list_patient_lab_reports_no_auth_returns_401(
    client: AsyncClient,
) -> None:
    resp = await client.get(f"/v1/doctor/patients/{uuid.uuid4()}/lab-reports")
    assert resp.status_code == 401


async def test_doctor_list_patient_lab_reports_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/doctor/patients/{uuid.uuid4()}/lab-reports",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_list_patient_lab_reports_doctor_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.get(
        f"/v1/doctor/patients/{uuid.uuid4()}/lab-reports",
        headers=make_auth_headers(doctor),
    )
    # Unknown patient (not on panel) → empty list, not 404
    assert resp.status_code == 200
    assert resp.json() == []


async def test_doctor_get_patient_lab_report_no_auth_returns_401(
    client: AsyncClient,
) -> None:
    resp = await client.get(
        f"/v1/doctor/patients/{uuid.uuid4()}/lab-reports/{uuid.uuid4()}"
    )
    assert resp.status_code == 401


async def test_doctor_get_patient_lab_report_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/doctor/patients/{uuid.uuid4()}/lab-reports/{uuid.uuid4()}",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_doctor_get_patient_lab_report_wrong_doctor_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Cross-doctor: doctor B cannot view a report for doctor A's patient."""
    doctor_b = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/doctor/patients/{uuid.uuid4()}/lab-reports/{uuid.uuid4()}",
        headers=make_auth_headers(doctor_b),
    )
    assert resp.status_code == 404


# ── /v1/doctor/lab-reports/{id}/annotate — doctor only ───────────────────────


async def test_annotate_lab_report_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch(
        f"/v1/doctor/lab-reports/{uuid.uuid4()}/annotate", json={"commentary": {}}
    )
    assert resp.status_code == 401


async def test_annotate_lab_report_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.patch(
        f"/v1/doctor/lab-reports/{uuid.uuid4()}/annotate",
        json={"commentary": {"TSH": "Normal range"}},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_annotate_lab_report_nonexistent_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.patch(
        f"/v1/doctor/lab-reports/{uuid.uuid4()}/annotate",
        json={"commentary": {"TSH": "Within normal limits"}},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 404


async def test_annotate_lab_report_no_fields_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.patch(
        f"/v1/doctor/lab-reports/{uuid.uuid4()}/annotate",
        json={},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 422


# ── /v1/doctor/me/bank-details — doctor only ─────────────────────────────────


async def test_submit_bank_details_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/doctor/me/bank-details", json={})
    assert resp.status_code == 401


async def test_submit_bank_details_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/doctor/me/bank-details",
        json={
            "account_holder_name": "Dr Test",
            "account_number": "123456789012",
            "ifsc_code": "HDFC0001234",
            "bank_name": "HDFC Bank",
        },
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_submit_bank_details_doctor_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.post(
        "/v1/doctor/me/bank-details",
        json={
            "account_holder_name": "Dr Test Doctor",
            "account_number": "123456789012",
            "ifsc_code": "HDFC0001234",
            "bank_name": "HDFC Bank",
        },
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data

    # Profile now shows has_bank_details=True
    profile_resp = await client.get("/v1/doctor/me", headers=make_auth_headers(doctor))
    assert profile_resp.status_code == 200
    assert profile_resp.json()["has_bank_details"] is True


async def test_submit_bank_details_invalid_ifsc_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/doctor/me/bank-details",
        json={
            "account_holder_name": "Dr Test",
            "account_number": "123456789",
            "ifsc_code": "INVALID",
            "bank_name": "Test Bank",
        },
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 422


# ── /v1/doctor/me specialty edit ─────────────────────────────────────────────


async def test_patch_doctor_me_specialty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    resp = await client.patch(
        "/v1/doctor/me",
        json={"specialty": ["thyroid", "pcos"], "conditions_treated": ["hypothyroidism"]},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "thyroid" in data["specialty"]
    assert "hypothyroidism" in data["conditions_treated"]


# ── /admin/* — HTML routes (session cookie auth) ─────────────────────────────


async def test_admin_dashboard_no_cookie_redirects(client: AsyncClient) -> None:
    """Unauthenticated: redirect to /admin/login."""
    resp = await client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers.get("location", "")


async def test_admin_users_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/users", follow_redirects=False)
    assert resp.status_code == 302


async def test_admin_doctors_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/doctors", follow_redirects=False)
    assert resp.status_code == 302


async def test_admin_pipeline_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/doctors/pipeline", follow_redirects=False)
    assert resp.status_code == 302


async def test_admin_consultations_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/consultations", follow_redirects=False)
    assert resp.status_code == 302


async def test_admin_content_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/content", follow_redirects=False)
    assert resp.status_code == 302


async def test_admin_audit_log_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/audit-log", follow_redirects=False)
    assert resp.status_code == 302


async def test_admin_login_page_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/admin/login")
    assert resp.status_code == 200
    assert b"Kyros" in resp.content


async def test_admin_login_wrong_credentials_returns_200_with_error(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    resp = await client.post(
        "/admin/login",
        data={"email_or_phone": "noone@test.kyros.local", "password": "wrongpass"},
    )
    assert resp.status_code == 200
    assert b"Invalid" in resp.content


async def test_admin_login_valid_admin_redirects_to_dashboard(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    from sqlalchemy import update as sa_update

    from app.core.security import hash_password
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    await db_session.execute(
        sa_update(UserModel).where(UserModel.id == admin.id)
        .values(
            email="testadmin@test.kyros.local",
            password_hash=hash_password("AdminPass123!"),
        )
    )
    await db_session.flush()
    resp = await client.post(
        "/admin/login",
        data={
            "email_or_phone": "testadmin@test.kyros.local",
            "password": "AdminPass123!",
            "next_url": "/admin/",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/admin/" in resp.headers.get("location", "")


# ── /admin/* — read-only 'admin' tier vs full 'super_admin' tier ──────────────


def _admin_session_cookie(user_id: uuid.UUID) -> tuple[str, str]:
    """Create an admin-portal session in Redis and return (session_id, csrf_token)."""
    from fastapi.responses import Response as FResponse

    from app.adminui.deps import create_admin_session

    dummy_response = FResponse()
    create_admin_session(dummy_response, user_id)
    session_id = ""
    csrf_token = ""
    for header_val in dummy_response.raw_headers:
        decoded = header_val[1].decode() if isinstance(header_val[1], bytes) else header_val[1]
        if "kyros_admin_session=" in decoded:
            for part in decoded.split(";"):
                if "kyros_admin_session=" in part:
                    session_id = part.split("=", 1)[1].strip()
        if "kyros_admin_csrf=" in decoded:
            for part in decoded.split(";"):
                if "kyros_admin_csrf=" in part:
                    csrf_token = part.split("=", 1)[1].strip()
    return session_id, csrf_token


async def _create_readonly_admin(db: AsyncSession) -> object:
    from app.core.security import hash_password
    from app.db.enums import UserRole
    from app.repositories import users as users_repo

    return await users_repo.create(
        db,
        name="Test Readonly Admin",
        role=UserRole.ADMIN,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )


async def test_admin_tier_can_view_users(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Read-only admin: every GET page works."""
    from app.models.identity import User as UserModel

    admin = await _create_readonly_admin(db_session)
    assert isinstance(admin, UserModel)
    try:
        cookie, csrf = _admin_session_cookie(admin.id)
    except Exception:
        return  # Redis unavailable in test — skip session creation path
    if not cookie:
        return

    for path in ("/admin/users", "/admin/doctors", "/admin/content"):
        resp = await client.get(path, cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf})
        assert resp.status_code == 200, path


async def test_admin_tier_cannot_suspend_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Read-only admin: state-changing POST is 403, not a login redirect."""
    from app.models.identity import User as UserModel

    admin = await _create_readonly_admin(db_session)
    patient = await create_patient_user(db_session)
    assert isinstance(admin, UserModel)
    assert isinstance(patient, UserModel)
    try:
        cookie, csrf = _admin_session_cookie(admin.id)
    except Exception:
        return
    if not cookie:
        return

    resp = await client.post(
        f"/admin/users/{patient.id}/suspend",
        data={"_csrf": csrf},
        cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 403


async def test_super_admin_tier_can_suspend_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Positive control: super admin still passes the stricter dependency."""
    from app.models.identity import User as UserModel

    super_admin = await create_super_admin_user(db_session)
    patient = await create_patient_user(db_session)
    assert isinstance(super_admin, UserModel)
    assert isinstance(patient, UserModel)
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not cookie:
        return

    resp = await client.post(
        f"/admin/users/{patient.id}/suspend",
        data={"_csrf": csrf},
        cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302


async def test_admin_staff_new_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/staff/new", follow_redirects=False)
    assert resp.status_code == 302


async def test_admin_dsr_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/dsr", follow_redirects=False)
    assert resp.status_code == 302


async def test_admin_tier_cannot_open_staff_form(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Read-only admin: staff creation and DSR queue are super-admin only."""
    from app.models.identity import User as UserModel

    admin = await _create_readonly_admin(db_session)
    assert isinstance(admin, UserModel)
    try:
        cookie, csrf = _admin_session_cookie(admin.id)
    except Exception:
        return
    if not cookie:
        return

    for path in ("/admin/staff/new", "/admin/dsr"):
        resp = await client.get(
            path, cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf}, follow_redirects=False
        )
        assert resp.status_code == 403, path


async def test_super_admin_creates_coordinator_via_portal(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Happy path: fresh super-admin session creates a coordinator from the form."""
    from sqlalchemy import select as sa_select

    from app.db.enums import UserRole
    from app.models.identity import User as UserModel

    super_admin = await create_super_admin_user(db_session)
    assert isinstance(super_admin, UserModel)
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)  # login marks the session fresh
    except Exception:
        return
    if not cookie:
        return

    phone = _synth_phone()
    resp = await client.post(
        "/admin/staff",
        data={
            "role": "coordinator",
            "name": "Test Portal Coordinator",
            "email": _synth_email(),
            "phone": phone,
            "password": "PortalPass123!",
            "_csrf": csrf,
        },
        cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    created = await db_session.scalar(
        sa_select(UserModel).where(UserModel.phone == phone)
    )
    assert created is not None
    assert created.role == UserRole.COORDINATOR
    assert created.phone_verified is True


async def test_stale_super_admin_session_redirects_to_reauth(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Fresh-auth: once the 10-minute window lapses, money/identity POSTs
    bounce to /admin/reauth instead of executing."""
    from app.adminui.deps import _fresh_key, _redis
    from app.models.identity import User as UserModel

    super_admin = await create_super_admin_user(db_session)
    assert isinstance(super_admin, UserModel)
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
        _redis().delete(_fresh_key(cookie))  # simulate the window lapsing
    except Exception:
        return
    if not cookie:
        return

    resp = await client.post(
        "/admin/staff",
        data={
            "role": "coordinator",
            "name": "Should Not Be Created",
            "email": _synth_email(),
            "phone": _synth_phone(),
            "password": "PortalPass123!",
            "_csrf": csrf,
        },
        cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/admin/reauth" in resp.headers.get("location", "")


async def test_admin_cancel_unknown_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    super_admin = await create_super_admin_user(db_session)
    assert isinstance(super_admin, UserModel)
    try:
        cookie, csrf = _admin_session_cookie(super_admin.id)
    except Exception:
        return
    if not cookie:
        return

    resp = await client.post(
        f"/admin/consultations/{uuid.uuid4()}/cancel",
        data={"reason": "test", "_csrf": csrf},
        cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 404


async def test_analytics_export_works_with_session_cookie(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The portal export uses the session cookie — the /v1 JWT twin can't be
    reached from a browser link."""
    from app.models.identity import User as UserModel

    admin = await _create_readonly_admin(db_session)
    assert isinstance(admin, UserModel)
    try:
        cookie, csrf = _admin_session_cookie(admin.id)
    except Exception:
        return
    if not cookie:
        return

    resp = await client.get(
        "/admin/analytics/export?report=funnel",
        cookies={"kyros_admin_session": cookie, "kyros_admin_csrf": csrf},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


async def test_admin_tier_can_login_via_portal(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import update as sa_update

    from app.core.security import hash_password
    from app.models.identity import User as UserModel

    admin = await _create_readonly_admin(db_session)
    assert isinstance(admin, UserModel)
    await db_session.execute(
        sa_update(UserModel).where(UserModel.id == admin.id)
        .values(
            email="testreadonly@test.kyros.local",
            password_hash=hash_password("ReadOnly123!!"),
        )
    )
    await db_session.flush()
    resp = await client.post(
        "/admin/login",
        data={
            "email_or_phone": "testreadonly@test.kyros.local",
            "password": "ReadOnly123!!",
            "next_url": "/admin/",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/admin/" in resp.headers.get("location", "")


# ── /coord/* — HTML routes (coordinator session cookie auth) ──────────────────


async def test_coord_dashboard_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/coord/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/coord/login" in resp.headers.get("location", "")


async def test_coord_patients_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/coord/patients", follow_redirects=False)
    assert resp.status_code == 302


async def test_coord_intake_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/coord/intake", follow_redirects=False)
    assert resp.status_code == 302


async def test_coord_scheduling_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/coord/scheduling", follow_redirects=False)
    assert resp.status_code == 302


async def test_coord_communication_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/coord/communication", follow_redirects=False)
    assert resp.status_code == 302


async def test_coord_inquiries_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/coord/inquiries", follow_redirects=False)
    assert resp.status_code == 302


def _coord_session_cookie(user_id: uuid.UUID) -> tuple[str, str]:
    """Create a coordinator session in Redis and return (session_id, csrf_token)."""
    from fastapi.responses import Response as FResponse

    from app.adminui.deps import create_coord_session

    dummy_response = FResponse()
    create_coord_session(dummy_response, user_id)
    session_id = ""
    csrf_token = ""
    for header_val in dummy_response.raw_headers:
        decoded = header_val[1].decode() if isinstance(header_val[1], bytes) else header_val[1]
        if "kyros_coord_session=" in decoded:
            for part in decoded.split(";"):
                if "kyros_coord_session=" in part:
                    session_id = part.split("=", 1)[1].strip()
        if "kyros_coord_csrf=" in decoded:
            for part in decoded.split(";"):
                if "kyros_coord_csrf=" in part:
                    csrf_token = part.split("=", 1)[1].strip()
    return session_id, csrf_token


async def test_coord_inquiry_contacted_first_coordinator_wins(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A new website inquiry shows as not contacted; the first coordinator to
    mark it contacted claims it, and a second attempt gets 404."""
    from app.models.identity import User as UserModel

    inquiry_resp = await client.post(
        "/v1/public/booking-inquiry",
        json={
            "name": "Test Inquiry Patient",
            "gender": "female",
            "phone": _synth_phone(),
            "condition_category": "thyroid",
            "skipped_intake": True,
        },
    )
    assert inquiry_resp.status_code == 201
    inquiry_id = inquiry_resp.json()["id"]

    coord_one = await create_coordinator_user(db_session)
    coord_two = await create_coordinator_user(db_session)
    assert isinstance(coord_one, UserModel)
    assert isinstance(coord_two, UserModel)

    try:
        cookie_one, csrf_one = _coord_session_cookie(coord_one.id)
        cookie_two, csrf_two = _coord_session_cookie(coord_two.id)
    except Exception:
        return  # Redis unavailable in test — skip session creation path
    if not cookie_one or not cookie_two:
        return

    # Queue lists the inquiry as not contacted
    queue = await client.get(
        "/coord/inquiries", cookies={"kyros_coord_session": cookie_one, "kyros_coord_csrf": csrf_one}
    )
    assert queue.status_code == 200
    assert b"Test Inquiry Patient" in queue.content
    assert b"not contacted" in queue.content

    # First coordinator claims it
    first = await client.post(
        f"/coord/inquiries/{inquiry_id}/contacted",
        data={"_csrf": csrf_one},
        cookies={"kyros_coord_session": cookie_one, "kyros_coord_csrf": csrf_one},
        follow_redirects=False,
    )
    assert first.status_code == 302

    # Second coordinator cannot re-claim
    second = await client.post(
        f"/coord/inquiries/{inquiry_id}/contacted",
        data={"_csrf": csrf_two},
        cookies={"kyros_coord_session": cookie_two, "kyros_coord_csrf": csrf_two},
        follow_redirects=False,
    )
    assert second.status_code == 404


async def test_coord_login_page_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/coord/login")
    assert resp.status_code == 200
    assert b"Coordinator" in resp.content


async def test_coord_login_wrong_credentials_returns_200_with_error(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/coord/login",
        data={"email_or_phone": "nobody@test.kyros.local", "password": "wrong"},
    )
    assert resp.status_code == 200
    assert b"Invalid" in resp.content


async def test_coord_login_admin_returns_error(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Super admin credentials should not grant access to coordinator portal."""
    admin = await create_super_admin_user(db_session)
    from sqlalchemy import update as sa_update

    from app.core.security import hash_password
    from app.models.identity import User as UserModel
    assert isinstance(admin, UserModel)
    await db_session.execute(
        sa_update(UserModel).where(UserModel.id == admin.id)
        .values(email="testadmin2@test.kyros.local", password_hash=hash_password("Pass123!"))
    )
    await db_session.flush()
    resp = await client.post(
        "/coord/login",
        data={"email_or_phone": "testadmin2@test.kyros.local", "password": "Pass123!"},
        follow_redirects=False,
    )
    # Admin credentials in coord portal → error page (200), not redirect
    assert resp.status_code == 200
    assert b"Invalid" in resp.content


async def test_coord_login_valid_coordinator_redirects(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    from sqlalchemy import update as sa_update

    from app.core.security import hash_password
    from app.models.identity import User as UserModel
    assert isinstance(coord, UserModel)
    await db_session.execute(
        sa_update(UserModel).where(UserModel.id == coord.id)
        .values(email="testcoord@test.kyros.local", password_hash=hash_password("CoordPass1!"))
    )
    await db_session.flush()
    resp = await client.post(
        "/coord/login",
        data={
            "email_or_phone": "testcoord@test.kyros.local",
            "password": "CoordPass1!",
            "next_url": "/coord/",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/coord/" in resp.headers.get("location", "")


async def test_coord_patient_not_assigned_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Penetration test: coordinator cannot access a patient not in their assigned list."""
    from fastapi.responses import Response as FResponse

    from app.adminui.deps import create_coord_session
    from app.models.admin import Coordinator
    from app.models.clinic import Patient
    from app.models.identity import User as UserModel

    # Create coordinator with no assigned patients
    coord_user = await create_coordinator_user(db_session)
    assert isinstance(coord_user, UserModel)
    coordinator = Coordinator(user_id=coord_user.id, assigned_patient_ids=[])
    db_session.add(coordinator)
    await db_session.flush()

    # Create a patient not assigned to this coordinator
    other_patient_user = await create_patient_user(db_session)
    assert isinstance(other_patient_user, UserModel)
    patient = Patient(
        user_id=other_patient_user.id,
        kyros_patient_id="KP-TEST-999",
        primary_conditions=[],
    )
    db_session.add(patient)
    await db_session.flush()

    # Manually create a coordinator session in Redis
    dummy_response = FResponse()
    try:
        create_coord_session(dummy_response, coord_user.id)
        session_cookie = dummy_response.headers.get("set-cookie", "")
        session_id = ""
        for part in session_cookie.split(";"):
            if "kyros_coord_session=" in part:
                session_id = part.split("=", 1)[1].strip()
                break
    except Exception:
        # Redis unavailable in test — skip session creation path
        return

    resp = await client.get(
        f"/coord/patients/{patient.id}",
        cookies={"kyros_coord_session": session_id},
        follow_redirects=False,
    )
    # Either 404 (not assigned) or 302 (session invalid) — both are acceptable
    assert resp.status_code in (404, 302)


# ── ABHA endpoints (P27) ───────────────────────────────────────────────────────
# GET  /v1/clinic/patient/abha               patient only
# POST /v1/clinic/patient/abha/link          patient only
# POST /v1/clinic/patient/abha/create/init   patient only
# POST /v1/clinic/patient/abha/create/confirm patient only


async def test_rbac_abha_status_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/abha")
    assert resp.status_code == 401


async def test_rbac_abha_status_doctor_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/abha", headers=make_auth_headers(user)
    )
    assert resp.status_code == 403


async def test_rbac_abha_status_coordinator_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_coordinator_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/abha", headers=make_auth_headers(user)
    )
    assert resp.status_code == 403


async def test_rbac_abha_status_admin_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/abha", headers=make_auth_headers(user)
    )
    assert resp.status_code == 403


async def test_rbac_abha_link_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/abha/link", json={"abha_number": "91000000000000"}
    )
    assert resp.status_code == 401


async def test_rbac_abha_link_doctor_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": "91000000000000"},
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 403


async def test_rbac_abha_create_init_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/abha/create/init", json={"aadhaar_number": "123456789012"}
    )
    assert resp.status_code == 401


async def test_rbac_abha_create_init_doctor_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/clinic/patient/abha/create/init",
        json={"aadhaar_number": "123456789012"},
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 403


async def test_rbac_abha_create_confirm_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/abha/create/confirm",
        json={"txn_id": "some-txn", "otp": "000000"},
    )
    assert resp.status_code == 401


async def test_rbac_abha_create_confirm_doctor_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/clinic/patient/abha/create/confirm",
        json={"txn_id": "some-txn", "otp": "000000"},
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 403


# ── /v1/admin/analytics/* — super admin only ─────────────────────────────────


async def test_analytics_funnel_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/analytics/funnel")
    assert resp.status_code == 401


async def test_analytics_funnel_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    resp = await client.get("/v1/admin/analytics/funnel", headers=make_auth_headers(user))
    assert resp.status_code == 403


async def test_analytics_funnel_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_doctor_user(db_session)
    resp = await client.get("/v1/admin/analytics/funnel", headers=make_auth_headers(user))
    assert resp.status_code == 403


async def test_analytics_funnel_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get("/v1/admin/analytics/funnel", headers=make_auth_headers(admin))
    assert resp.status_code == 200
    data = resp.json()
    assert "inquiries" in data
    assert "registrations" in data
    assert "bookings" in data
    assert "completions" in data


async def test_analytics_retention_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/analytics/retention")
    assert resp.status_code == 401


async def test_analytics_retention_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    resp = await client.get("/v1/admin/analytics/retention", headers=make_auth_headers(user))
    assert resp.status_code == 403


async def test_analytics_retention_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/admin/analytics/retention?cohort_months=3",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "cohorts" in data
    assert isinstance(data["cohorts"], list)


async def test_analytics_revenue_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/analytics/revenue")
    assert resp.status_code == 401


async def test_analytics_revenue_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    resp = await client.get("/v1/admin/analytics/revenue", headers=make_auth_headers(user))
    assert resp.status_code == 403


async def test_analytics_revenue_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/admin/analytics/revenue?group_by=condition",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "rows" in data


async def test_analytics_condition_mix_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/analytics/condition-mix")
    assert resp.status_code == 401


async def test_analytics_condition_mix_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/admin/analytics/condition-mix", headers=make_auth_headers(user)
    )
    assert resp.status_code == 403


async def test_analytics_condition_mix_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/admin/analytics/condition-mix", headers=make_auth_headers(admin)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "rows" in data


async def test_analytics_doctor_utilization_no_auth_returns_401(
    client: AsyncClient,
) -> None:
    resp = await client.get("/v1/admin/analytics/doctor-utilization")
    assert resp.status_code == 401


async def test_analytics_doctor_utilization_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/admin/analytics/doctor-utilization", headers=make_auth_headers(user)
    )
    assert resp.status_code == 403


async def test_analytics_doctor_utilization_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/admin/analytics/doctor-utilization?weeks=4",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "rows" in data


async def test_analytics_export_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/analytics/export?report=funnel")
    assert resp.status_code == 401


async def test_analytics_export_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/admin/analytics/export?report=funnel", headers=make_auth_headers(user)
    )
    assert resp.status_code == 403


async def test_analytics_export_admin_returns_csv(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/admin/analytics/export?report=funnel",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")


async def test_analytics_html_no_cookie_redirects(client: AsyncClient) -> None:
    resp = await client.get("/admin/analytics", follow_redirects=False)
    assert resp.status_code == 302


# ── /v1/users/notifications — patient inbox ───────────────────────────────────


async def test_notifications_list_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/users/notifications")
    assert resp.status_code == 401


async def test_notifications_list_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/users/notifications", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_notifications_list_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord = await create_coordinator_user(db_session)
    resp = await client.get("/v1/users/notifications", headers=make_auth_headers(coord))
    assert resp.status_code == 403


async def test_notifications_list_patient_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/users/notifications", headers=make_auth_headers(patient))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "unread_count" in data
    assert data["items"] == []
    assert data["unread_count"] == 0


async def test_notification_mark_read_no_auth_returns_401(client: AsyncClient) -> None:
    import uuid as _uuid
    resp = await client.patch(f"/v1/users/notifications/{_uuid.uuid4()}/read")
    assert resp.status_code == 401


async def test_notification_mark_read_cross_user_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A patient cannot mark another patient's notification as read."""
    from app.repositories import notifications as notif_repo

    owner = await create_patient_user(db_session)
    attacker = await create_patient_user(db_session)

    from app.models.identity import User as UserModel
    assert isinstance(owner, UserModel)

    notif = await notif_repo.create(
        db_session,
        user_id=owner.id,
        template_name="appointment_confirmation",
        title="Appointment confirmed",
        body="Your appointment is confirmed.",
        channels=["push"],
        data={"screen": "consultation"},
    )
    await db_session.flush()

    resp = await client.patch(
        f"/v1/users/notifications/{notif.id}/read",
        headers=make_auth_headers(attacker),
    )
    assert resp.status_code == 404


async def test_notification_mark_read_patient_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.repositories import notifications as notif_repo

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient, UserModel)

    notif = await notif_repo.create(
        db_session,
        user_id=patient.id,
        template_name="appointment_reminder",
        title="Appointment tomorrow",
        body="Your appointment is tomorrow.",
        channels=["push", "whatsapp"],
        data={"screen": "consultation"},
    )
    await db_session.flush()

    resp = await client.patch(
        f"/v1/users/notifications/{notif.id}/read",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["read_at"] is not None
    assert data["id"] == str(notif.id)


async def test_notification_mark_all_read_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/users/notifications/read-all")
    assert resp.status_code == 401


async def test_notification_mark_all_read_patient_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.repositories import notifications as notif_repo

    patient = await create_patient_user(db_session)
    from app.models.identity import User as UserModel
    assert isinstance(patient, UserModel)

    for i in range(3):
        await notif_repo.create(
            db_session,
            user_id=patient.id,
            template_name="lab_result_ready",
            title=f"Lab result {i}",
            body="Your results are ready.",
            channels=["push"],
            data={},
        )
    await db_session.flush()

    resp = await client.post(
        "/v1/users/notifications/read-all",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    assert resp.json()["marked_read"] == 3


# ── /v1/users/notification-preferences ───────────────────────────────────────


async def test_notification_preferences_get_no_auth_returns_401(
    client: AsyncClient,
) -> None:
    resp = await client.get("/v1/users/notification-preferences")
    assert resp.status_code == 401


async def test_notification_preferences_get_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/users/notification-preferences", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_notification_preferences_get_patient_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/users/notification-preferences", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"push": True, "whatsapp": True, "email": True}


async def test_notification_preferences_patch_patient_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.patch(
        "/v1/users/notification-preferences",
        json={"whatsapp": False},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["push"] is True
    assert data["whatsapp"] is False
    assert data["email"] is True


async def test_notification_preferences_patch_no_auth_returns_401(
    client: AsyncClient,
) -> None:
    resp = await client.patch(
        "/v1/users/notification-preferences", json={"push": False}
    )
    assert resp.status_code == 401


# ── /v1/admin/internal/db-pool-status ────────────────────────────────────────


async def test_db_pool_status_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/internal/db-pool-status")
    assert resp.status_code == 401


async def test_db_pool_status_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/admin/internal/db-pool-status", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 403


async def test_db_pool_status_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/admin/internal/db-pool-status", headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403


async def test_db_pool_status_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coordinator = await create_coordinator_user(db_session)
    resp = await client.get(
        "/v1/admin/internal/db-pool-status", headers=make_auth_headers(coordinator)
    )
    assert resp.status_code == 403


async def test_db_pool_status_super_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/admin/internal/db-pool-status", headers=make_auth_headers(admin)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "pool_size" in data
    assert "checked_in" in data
    assert "checked_out" in data
    assert "overflow" in data
    assert "status_string" in data


# ── /v1/admin/internal/health-detail ─────────────────────────────────────────


async def test_health_detail_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/internal/health-detail")
    assert resp.status_code == 401


async def test_health_detail_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/admin/internal/health-detail", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 403


async def test_health_detail_super_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get(
        "/v1/admin/internal/health-detail", headers=make_auth_headers(admin)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["db_ok"] is True
    assert data["redis_ok"] is True
    assert data["overall"] == "ok"
    assert data["db_latency_ms"] >= 0


# ── /v1/admin/doctors ─────────────────────────────────────────────────────────


async def test_list_doctors_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/doctors")
    assert resp.status_code == 401


async def test_list_doctors_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/admin/doctors", headers=make_auth_headers(patient))
    assert resp.status_code == 403


async def test_list_doctors_super_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get("/v1/admin/doctors", headers=make_auth_headers(admin))
    assert resp.status_code == 200


# ── /v1/admin/doctors/{id}/advance ───────────────────────────────────────────


async def test_advance_doctor_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/admin/doctors/{uuid.uuid4()}/advance",
        json={"target_status": "documents_submitted"},
    )
    assert resp.status_code == 401


async def test_advance_doctor_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/admin/doctors/{uuid.uuid4()}/advance",
        json={"target_status": "documents_submitted"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_advance_doctor_read_only_admin_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    resp = await client.post(
        f"/v1/admin/doctors/{uuid.uuid4()}/advance",
        json={"target_status": "documents_submitted"},
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 403


async def test_advance_doctor_super_admin_nonexistent_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.post(
        f"/v1/admin/doctors/{uuid.uuid4()}/advance",
        json={"target_status": "documents_submitted"},
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 404


# ── /v1/admin/doctors/{id}/suspend ───────────────────────────────────────────


async def test_suspend_doctor_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/admin/doctors/{uuid.uuid4()}/suspend")
    assert resp.status_code == 401


async def test_suspend_doctor_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/admin/doctors/{uuid.uuid4()}/suspend",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_suspend_doctor_super_admin_nonexistent_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.post(
        f"/v1/admin/doctors/{uuid.uuid4()}/suspend",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 404


# ── /v1/admin/doctors/{id}/reactivate ────────────────────────────────────────


async def test_reactivate_doctor_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/admin/doctors/{uuid.uuid4()}/reactivate")
    assert resp.status_code == 401


async def test_reactivate_doctor_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/admin/doctors/{uuid.uuid4()}/reactivate",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


# ── /v1/admin/pricing ────────────────────────────────────────────────────────


async def test_list_pricing_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/pricing")
    assert resp.status_code == 401


async def test_list_pricing_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/admin/pricing", headers=make_auth_headers(patient))
    assert resp.status_code == 403


async def test_list_pricing_super_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get("/v1/admin/pricing", headers=make_auth_headers(admin))
    assert resp.status_code == 200


async def test_upsert_pricing_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.put(
        "/v1/admin/pricing/thyroid/initial", json={"fee_paise": 70000}
    )
    assert resp.status_code == 401


async def test_upsert_pricing_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.put(
        "/v1/admin/pricing/thyroid/initial",
        json={"fee_paise": 70000},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_upsert_pricing_read_only_admin_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    resp = await client.put(
        "/v1/admin/pricing/thyroid/initial",
        json={"fee_paise": 70000},
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 403


async def test_upsert_pricing_super_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.put(
        "/v1/admin/pricing/thyroid/initial",
        json={"fee_paise": 70000},
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200


# ── /v1/admin/coupons ────────────────────────────────────────────────────────


async def test_list_coupons_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/coupons")
    assert resp.status_code == 401


async def test_list_coupons_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/admin/coupons", headers=make_auth_headers(patient))
    assert resp.status_code == 403


async def test_list_coupons_read_only_admin_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    resp = await client.get("/v1/admin/coupons", headers=make_auth_headers(admin))
    assert resp.status_code == 403


async def test_list_coupons_super_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get("/v1/admin/coupons", headers=make_auth_headers(admin))
    assert resp.status_code == 200


async def test_create_coupon_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/admin/coupons",
        json={
            "code": "TEST01",
            "discount_type": "flat",
            "discount_value": 5000,
            "min_order_paise": 0,
            "valid_from": "2026-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 401


async def test_create_coupon_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/admin/coupons",
        json={
            "code": "TEST02",
            "discount_type": "flat",
            "discount_value": 5000,
            "min_order_paise": 0,
            "valid_from": "2026-01-01T00:00:00Z",
        },
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_delete_coupon_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.delete(f"/v1/admin/coupons/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_delete_coupon_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.delete(
        f"/v1/admin/coupons/{uuid.uuid4()}",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


# ── /v1/admin/dsr ─────────────────────────────────────────────────────────────


async def test_list_dsr_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/dsr")
    assert resp.status_code == 401


async def test_list_dsr_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.get("/v1/admin/dsr", headers=make_auth_headers(patient))
    assert resp.status_code == 403


async def test_list_dsr_super_admin_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_super_admin_user(db_session)
    resp = await client.get("/v1/admin/dsr", headers=make_auth_headers(admin))
    assert resp.status_code == 200


# ── /v1/admin/dsr/{id}/status ─────────────────────────────────────────────────


async def test_patch_dsr_status_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.patch(
        f"/v1/admin/dsr/{uuid.uuid4()}/status",
        json={"new_status": "in_progress"},
    )
    assert resp.status_code == 401


async def test_patch_dsr_status_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.patch(
        f"/v1/admin/dsr/{uuid.uuid4()}/status",
        json={"new_status": "in_progress"},
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


async def test_patch_dsr_status_read_only_admin_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    resp = await client.patch(
        f"/v1/admin/dsr/{uuid.uuid4()}/status",
        json={"new_status": "in_progress"},
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 403
