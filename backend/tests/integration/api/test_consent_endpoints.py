"""Integration tests for POST /v1/users/me/consent and GET /v1/users/me/consents."""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers

_DPDP_TEXT = (
    "Kyros Clinic collects and processes your health data under the Digital Personal "
    "Data Protection Act 2023. You may withdraw consent at any time from Profile → My consents."
)
_TELE_TEXT = (
    "I consent to receive telemedicine consultations via the Kyros platform in accordance "
    "with NMC Telemedicine Practice Guidelines 2020."
)
_HEALTH_TEXT = (
    "I consent to Kyros reading health data (steps, heart rate, sleep, weight) from "
    "Apple Health / Health Connect to support my care plan."
)


async def test_capture_dpdp_consent_returns_201(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/users/me/consent",
        json={
            "consent_type": "data_processing",
            "version": "1.0",
            "granted": True,
            "consent_text": _DPDP_TEXT,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["consent_type"] == "data_processing"
    assert data["granted"] is True
    assert data["version"] == "1.0"
    assert data["revoked_at"] is None
    assert "id" in data
    assert "granted_at" in data


async def test_capture_telemedicine_consent_returns_201(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/users/me/consent",
        json={
            "consent_type": "telemedicine",
            "version": "1.0",
            "granted": True,
            "consent_text": _TELE_TEXT,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["consent_type"] == "telemedicine"


async def test_capture_health_sync_consent_returns_201(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    headers = make_auth_headers(user)
    resp = await client.post(
        "/v1/users/me/consent",
        json={
            "consent_type": "health_sync",
            "version": "1.0",
            "granted": True,
            "consent_text": _HEALTH_TEXT,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["consent_type"] == "health_sync"


async def test_list_consents_returns_all_types(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    headers = make_auth_headers(user)

    for ct, text in [
        ("data_processing", _DPDP_TEXT),
        ("telemedicine", _TELE_TEXT),
        ("health_sync", _HEALTH_TEXT),
    ]:
        await client.post(
            "/v1/users/me/consent",
            json={"consent_type": ct, "version": "1.0", "granted": True, "consent_text": text},
            headers=headers,
        )

    resp = await client.get("/v1/users/me/consents", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "consents" in data
    types = {c["consent_type"] for c in data["consents"]}
    assert types == {"data_processing", "telemedicine", "health_sync"}


async def test_list_consents_empty_for_new_patient(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    headers = make_auth_headers(user)
    resp = await client.get("/v1/users/me/consents", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["consents"] == []


async def test_capture_consent_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    headers = make_auth_headers(doctor)
    resp = await client.post(
        "/v1/users/me/consent",
        json={"consent_type": "data_processing", "version": "1.0", "granted": True, "consent_text": _DPDP_TEXT},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_list_consents_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.get("/v1/users/me/consents", headers=make_auth_headers(doctor))
    assert resp.status_code == 403


async def test_capture_consent_invalid_type_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_patient_user(db_session)
    resp = await client.post(
        "/v1/users/me/consent",
        json={"consent_type": "not_a_real_type", "version": "1.0", "granted": True, "consent_text": "x"},
        headers=make_auth_headers(user),
    )
    assert resp.status_code == 422


async def test_patient_cannot_see_another_patients_consents(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Each patient only sees their own consent records."""
    alice = await create_patient_user(db_session)
    bob = await create_patient_user(db_session)

    # bob records a consent
    await client.post(
        "/v1/users/me/consent",
        json={"consent_type": "data_processing", "version": "1.0", "granted": True, "consent_text": _DPDP_TEXT},
        headers=make_auth_headers(bob),
    )

    # alice lists her own consents — should be empty
    resp = await client.get("/v1/users/me/consents", headers=make_auth_headers(alice))
    assert resp.status_code == 200
    assert resp.json()["consents"] == []
