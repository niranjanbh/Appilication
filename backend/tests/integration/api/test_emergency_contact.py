"""Integration tests for patient emergency-contact endpoints."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Patient
from app.models.identity import User as UserModel
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


async def _create_patient_profile(db: AsyncSession, user_id: uuid.UUID) -> Patient:
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    patient = Patient(
        user_id=user_id,
        kyros_patient_id=f"KYR-TST-{seq:05d}",
        primary_conditions=["thyroid"],
    )
    db.add(patient)
    await db.flush()
    return patient


_CONTACT = {
    "name": "Asha Rao",
    "relationship": "Sister",
    "phone": "+919000000123",
    "email": "asha@test.kyros.local",
}


# ── Get / set ─────────────────────────────────────────────────────────────────────


async def test_get_emergency_contact_empty_when_unset(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    await _create_patient_profile(db_session, patient.id)

    resp = await client.get(
        "/v1/users/me/emergency-contact", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 200
    assert resp.json() == {"name": None, "relationship": None, "phone": None, "email": None}


async def test_set_then_get_emergency_contact(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    await _create_patient_profile(db_session, patient.id)
    headers = make_auth_headers(patient)

    put = await client.put("/v1/users/me/emergency-contact", json=_CONTACT, headers=headers)
    assert put.status_code == 200, put.text
    assert put.json() == _CONTACT

    got = await client.get("/v1/users/me/emergency-contact", headers=headers)
    assert got.status_code == 200
    assert got.json() == _CONTACT


async def test_set_emergency_contact_updates_existing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    await _create_patient_profile(db_session, patient.id)
    headers = make_auth_headers(patient)

    await client.put("/v1/users/me/emergency-contact", json=_CONTACT, headers=headers)
    updated = {**_CONTACT, "phone": "+919000000999", "email": None}
    put = await client.put("/v1/users/me/emergency-contact", json=updated, headers=headers)
    assert put.status_code == 200
    assert put.json()["phone"] == "+919000000999"
    assert put.json()["email"] is None


async def test_set_emergency_contact_missing_field_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    assert isinstance(patient, UserModel)
    await _create_patient_profile(db_session, patient.id)

    resp = await client.put(
        "/v1/users/me/emergency-contact",
        json={"name": "X", "relationship": "Friend"},  # no phone
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 422


async def test_emergency_contact_without_profile_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)  # no Patient profile row
    resp = await client.get(
        "/v1/users/me/emergency-contact", headers=make_auth_headers(patient)
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "patient_profile_not_found"


# ── RBAC ──────────────────────────────────────────────────────────────────────────


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
    resp = await client.put("/v1/users/me/emergency-contact", json=_CONTACT)
    assert resp.status_code == 401


async def test_set_emergency_contact_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_user(db_session)
    resp = await client.put(
        "/v1/users/me/emergency-contact", json=_CONTACT, headers=make_auth_headers(doctor)
    )
    assert resp.status_code == 403
