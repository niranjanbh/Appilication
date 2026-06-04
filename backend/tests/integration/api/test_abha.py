"""Integration tests for ABHA M1 endpoints.

All tests run in stub mode (no KYROS_ABHA_CLIENT_ID set) so no real ABDM
sandbox calls are made. PHI discipline: no real Aadhaar or ABHA numbers
appear anywhere in this file — only clearly synthetic values.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_doctor_user,
    create_patient_user,
    make_auth_headers,
)

STUB_ABHA = "91000000000000"
SYNTH_AADHAAR = "123456789012"
STUB_OTP = "000000"
BAD_OTP = "999999"


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_patient_with_profile(db: AsyncSession) -> tuple[object, object]:
    from app.models.clinic import Patient
    from app.models.identity import User as UserModel

    user = await create_patient_user(db)
    assert isinstance(user, UserModel)
    patient = Patient(
        user_id=user.id,
        kyros_patient_id=f"KP-TEST-{uuid.uuid4().hex[:6].upper()}",
        primary_conditions=[],
    )
    db.add(patient)
    await db.flush()
    return user, patient


# ── GET /abha — status ────────────────────────────────────────────────────────


async def test_get_abha_status_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/abha")
    assert resp.status_code == 401


async def test_get_abha_status_no_patient_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Patient user with no kc_patients row gets 404."""
    user = await create_patient_user(db_session)
    headers = make_auth_headers(user)
    resp = await client.get("/v1/clinic/patient/abha", headers=headers)
    assert resp.status_code == 404


async def test_get_abha_status_unlinked(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, _patient = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.get("/v1/clinic/patient/abha", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["linked"] is False
    assert body["abha_number_masked"] is None


async def test_get_abha_status_linked(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import update as sa_update

    from app.models.clinic import Patient
    from app.models.identity import User as UserModel

    user, patient = await _create_patient_with_profile(db_session)
    assert isinstance(user, UserModel)
    await db_session.execute(
        sa_update(Patient).where(Patient.id == patient.id).values(abha_number=STUB_ABHA)  # type: ignore[attr-defined]
    )
    await db_session.flush()

    headers = make_auth_headers(user)
    resp = await client.get("/v1/clinic/patient/abha", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["linked"] is True
    # Masked: last 4 digits of STUB_ABHA are "0000"
    assert body["abha_number_masked"] is not None
    assert "0000" in body["abha_number_masked"]


async def test_get_abha_status_doctor_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    headers = make_auth_headers(doctor)
    resp = await client.get("/v1/clinic/patient/abha", headers=headers)
    assert resp.status_code == 403


# ── POST /abha/link ───────────────────────────────────────────────────────────


async def test_link_abha_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post("/v1/clinic/patient/abha/link", json={"abha_number": STUB_ABHA})
    assert resp.status_code == 401


async def test_link_abha_invalid_format_short(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": "1234567890"},  # only 10 digits
        headers=headers,
    )
    assert resp.status_code == 422


async def test_link_abha_invalid_format_letters(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": "ABCDEFGHIJKLMN"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_link_abha_success_plain(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """14-digit plain number is accepted in stub mode."""
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": STUB_ABHA},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["linked"] is True
    assert body["abha_number_masked"] is not None


async def test_link_abha_success_dashed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Dashed format (XX-XXXX-XXXX-XXXX) is also accepted."""
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": "91-0000-0000-0000"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["linked"] is True


async def test_link_abha_persisted_to_db(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.models.clinic import Patient

    user, patient = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": STUB_ABHA},
        headers=headers,
    )
    await db_session.refresh(patient)  # type: ignore[arg-type]
    row = await db_session.scalar(select(Patient).where(Patient.id == patient.id))  # type: ignore[attr-defined]
    assert row is not None
    assert row.abha_number == STUB_ABHA


async def test_link_abha_audit_logged(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.models.audit import AuditLog
    from app.models.identity import User as UserModel

    user, _ = await _create_patient_with_profile(db_session)
    assert isinstance(user, UserModel)
    headers = make_auth_headers(user)
    await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": STUB_ABHA},
        headers=headers,
    )
    log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == user.id,
            AuditLog.action == "link_abha",
            AuditLog.allowed.is_(True),
        )
    )
    assert log is not None


async def test_link_abha_doctor_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    headers = make_auth_headers(doctor)
    resp = await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": STUB_ABHA},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_link_abha_no_profile_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Patient with no kc_patients row gets 404, not 403."""
    user = await create_patient_user(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/link",
        json={"abha_number": STUB_ABHA},
        headers=headers,
    )
    assert resp.status_code == 404


# ── POST /abha/create/init ────────────────────────────────────────────────────


async def test_create_abha_init_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/abha/create/init",
        json={"aadhaar_number": SYNTH_AADHAAR},
    )
    assert resp.status_code == 401


async def test_create_abha_init_invalid_aadhaar_short(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/create/init",
        json={"aadhaar_number": "12345678"},  # only 8 digits
        headers=headers,
    )
    assert resp.status_code == 422


async def test_create_abha_init_invalid_aadhaar_letters(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/create/init",
        json={"aadhaar_number": "ABCD12345678"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_create_abha_init_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/create/init",
        json={"aadhaar_number": SYNTH_AADHAAR},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "txn_id" in body
    assert body["txn_id"]  # non-empty
    assert "message" in body


async def test_create_abha_init_doctor_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    headers = make_auth_headers(doctor)
    resp = await client.post(
        "/v1/clinic/patient/abha/create/init",
        json={"aadhaar_number": SYNTH_AADHAAR},
        headers=headers,
    )
    assert resp.status_code == 403


# ── POST /abha/create/confirm ─────────────────────────────────────────────────


async def test_create_abha_confirm_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/abha/create/confirm",
        json={"txn_id": "some-txn", "otp": "000000"},
    )
    assert resp.status_code == 401


async def test_create_abha_confirm_invalid_txn(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """txn_id not stored in Redis → 400 expired/invalid."""
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/clinic/patient/abha/create/confirm",
        json={"txn_id": "nonexistent-txn", "otp": STUB_OTP},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_create_abha_confirm_wrong_otp(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Correct txn_id but wrong OTP → 400 in stub mode."""
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)

    # Init first to store txn_id in Redis
    init_resp = await client.post(
        "/v1/clinic/patient/abha/create/init",
        json={"aadhaar_number": SYNTH_AADHAAR},
        headers=headers,
    )
    assert init_resp.status_code == 200
    txn_id = init_resp.json()["txn_id"]

    resp = await client.post(
        "/v1/clinic/patient/abha/create/confirm",
        json={"txn_id": txn_id, "otp": BAD_OTP},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_create_abha_confirm_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Full init → confirm flow with stub OTP succeeds."""
    user, _ = await _create_patient_with_profile(db_session)
    headers = make_auth_headers(user)

    init_resp = await client.post(
        "/v1/clinic/patient/abha/create/init",
        json={"aadhaar_number": SYNTH_AADHAAR},
        headers=headers,
    )
    assert init_resp.status_code == 200
    txn_id = init_resp.json()["txn_id"]

    confirm_resp = await client.post(
        "/v1/clinic/patient/abha/create/confirm",
        json={"txn_id": txn_id, "otp": STUB_OTP},
        headers=headers,
    )
    assert confirm_resp.status_code == 200
    body = confirm_resp.json()
    assert body["linked"] is True
    assert body["abha_number_masked"] is not None


async def test_create_abha_confirm_doctor_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    headers = make_auth_headers(doctor)
    resp = await client.post(
        "/v1/clinic/patient/abha/create/confirm",
        json={"txn_id": "some-txn", "otp": STUB_OTP},
        headers=headers,
    )
    assert resp.status_code == 403
