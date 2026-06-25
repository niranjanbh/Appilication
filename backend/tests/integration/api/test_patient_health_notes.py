"""Integration tests for patient health notes endpoints.

Patient routes: POST/GET/PATCH/DELETE /v1/clinic/patient/notes
Doctor route:   GET /v1/doctor/patients/{patient_user_id}/notes
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_coordinator_user,
    create_doctor_user,
    create_doctor_with_profile,
    create_patient_user,
    create_super_admin_user,
    make_auth_headers,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def patient(db_session: AsyncSession) -> object:
    return await create_patient_user(db_session)


@pytest.fixture
async def patient_headers(patient: object) -> dict[str, str]:
    return make_auth_headers(patient)


@pytest.fixture
async def other_patient(db_session: AsyncSession) -> object:
    return await create_patient_user(db_session)


@pytest.fixture
async def other_patient_headers(other_patient: object) -> dict[str, str]:
    return make_auth_headers(other_patient)


@pytest.fixture
async def doctor(db_session: AsyncSession) -> object:
    return await create_doctor_user(db_session)


@pytest.fixture
async def doctor_headers(doctor: object) -> dict[str, str]:
    return make_auth_headers(doctor)


@pytest.fixture
async def coordinator(db_session: AsyncSession) -> object:
    return await create_coordinator_user(db_session)


@pytest.fixture
async def coordinator_headers(coordinator: object) -> dict[str, str]:
    return make_auth_headers(coordinator)


@pytest.fixture
async def admin(db_session: AsyncSession) -> object:
    return await create_super_admin_user(db_session)


@pytest.fixture
async def admin_headers(admin: object) -> dict[str, str]:
    return make_auth_headers(admin)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_note(
    client: AsyncClient,
    headers: dict[str, str],
    body: str = "Ask about TSH results",
) -> dict:
    resp = await client.post(
        "/v1/clinic/patient/notes",
        headers=headers,
        json={"body": body},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_doctor_with_consultation(
    db_session: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
) -> object:
    """Create a doctor with full profile and a consultation linked to the patient."""
    from datetime import UTC, datetime, timedelta

    from app.db.enums import ConsultationStatus, ConsultationType
    from app.models.clinic import Consultation, Patient
    from app.models.doctor import Doctor
    from app.models.identity import User as UserModel

    doctor_user = await create_doctor_with_profile(db_session)
    assert isinstance(doctor_user, UserModel)

    dr_result = await db_session.execute(
        __import__("sqlalchemy", fromlist=["select"]).select(Doctor).where(
            Doctor.user_id == doctor_user.id
        )
    )
    doctor = dr_result.scalar_one()

    pt_result = await db_session.execute(
        __import__("sqlalchemy", fromlist=["select"]).select(Patient).where(
            Patient.user_id == patient_user_id
        )
    )
    patient_profile = pt_result.scalar_one_or_none()

    if patient_profile is None:
        from app.models.clinic import Patient as PatientModel

        patient_profile = PatientModel(
            user_id=patient_user_id,
            kyros_patient_id=f"KYR{str(patient_user_id)[:8].upper()}",
        )
        db_session.add(patient_profile)
        await db_session.flush()

    now = datetime.now(UTC)
    consult = Consultation(
        patient_id=patient_profile.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type=ConsultationType.INITIAL,
        scheduled_start_at=now + timedelta(hours=1),
        scheduled_end_at=now + timedelta(hours=2),
        status=ConsultationStatus.SCHEDULED,
        consultation_fee_paise=50000,
    )
    db_session.add(consult)
    await db_session.flush()

    return doctor_user


# ── Auth / role enforcement ───────────────────────────────────────────────────


async def test_create_note_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/v1/clinic/patient/notes", json={"body": "test"})
    assert resp.status_code == 401


async def test_list_notes_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/notes")
    assert resp.status_code == 401


async def test_create_note_doctor_returns_403(
    client: AsyncClient, doctor_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/clinic/patient/notes", headers=doctor_headers, json={"body": "test"}
    )
    assert resp.status_code == 403


async def test_create_note_coordinator_returns_403(
    client: AsyncClient, coordinator_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/clinic/patient/notes", headers=coordinator_headers, json={"body": "test"}
    )
    assert resp.status_code == 403


# ── Patient CRUD ──────────────────────────────────────────────────────────────


async def test_create_note_returns_201(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/clinic/patient/notes",
        headers=patient_headers,
        json={"body": "Ask doctor about fatigue levels"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["body"] == "Ask doctor about fatigue levels"
    assert "id" in data
    assert "created_at" in data


async def test_create_note_empty_body_returns_422(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/clinic/patient/notes", headers=patient_headers, json={"body": ""}
    )
    assert resp.status_code == 422


async def test_create_note_too_long_returns_422(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/v1/clinic/patient/notes",
        headers=patient_headers,
        json={"body": "x" * 1001},
    )
    assert resp.status_code == 422


async def test_list_notes_returns_own_notes(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    await _create_note(client, patient_headers, body="First note")
    await _create_note(client, patient_headers, body="Second note")

    resp = await client.get("/v1/clinic/patient/notes", headers=patient_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    bodies = [item["body"] for item in data["items"]]
    assert "First note" in bodies
    assert "Second note" in bodies


async def test_list_notes_newest_first(
    client: AsyncClient, patient_headers: dict[str, str], db_session: AsyncSession
) -> None:
    import sqlalchemy as sa

    note1 = await _create_note(client, patient_headers, body="Older note")
    # Within the test's outer transaction NOW() is frozen, so force note1 to be older.
    await db_session.execute(
        sa.text(
            "UPDATE kc_patient_notes SET created_at = created_at - INTERVAL '60 seconds'"
            " WHERE id = :id"
        ),
        {"id": note1["id"]},
    )
    await db_session.flush()

    note2 = await _create_note(client, patient_headers, body="Newer note")

    resp = await client.get("/v1/clinic/patient/notes", headers=patient_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    ids = [i["id"] for i in items]
    assert ids.index(note2["id"]) < ids.index(note1["id"])


async def test_update_note_returns_200(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    note = await _create_note(client, patient_headers, body="Original body")

    resp = await client.patch(
        f"/v1/clinic/patient/notes/{note['id']}",
        headers=patient_headers,
        json={"body": "Updated body"},
    )
    assert resp.status_code == 200
    assert resp.json()["body"] == "Updated body"


async def test_delete_note_returns_204(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    note = await _create_note(client, patient_headers)

    resp = await client.delete(
        f"/v1/clinic/patient/notes/{note['id']}", headers=patient_headers
    )
    assert resp.status_code == 204

    # Note should no longer appear in list
    list_resp = await client.get("/v1/clinic/patient/notes", headers=patient_headers)
    ids = [i["id"] for i in list_resp.json()["items"]]
    assert note["id"] not in ids


# ── Cross-user isolation ──────────────────────────────────────────────────────


async def test_patient_cannot_update_other_patients_note(
    client: AsyncClient,
    patient_headers: dict[str, str],
    other_patient_headers: dict[str, str],
) -> None:
    note = await _create_note(client, other_patient_headers, body="Other patient note")

    resp = await client.patch(
        f"/v1/clinic/patient/notes/{note['id']}",
        headers=patient_headers,
        json={"body": "Tampered"},
    )
    assert resp.status_code == 404


async def test_patient_cannot_delete_other_patients_note(
    client: AsyncClient,
    patient_headers: dict[str, str],
    other_patient_headers: dict[str, str],
) -> None:
    note = await _create_note(client, other_patient_headers, body="Other patient note")

    resp = await client.delete(
        f"/v1/clinic/patient/notes/{note['id']}", headers=patient_headers
    )
    assert resp.status_code == 404


# ── Doctor access ─────────────────────────────────────────────────────────────


async def test_doctor_without_consultation_gets_404(
    client: AsyncClient,
    db_session: AsyncSession,
    patient: object,
) -> None:
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)

    doctor_user = await create_doctor_with_profile(db_session)
    headers = make_auth_headers(doctor_user)

    resp = await client.get(
        f"/v1/doctor/patients/{patient.id}/notes", headers=headers
    )
    assert resp.status_code == 404


async def test_doctor_with_consultation_can_read_notes(
    client: AsyncClient,
    db_session: AsyncSession,
    patient: object,
    patient_headers: dict[str, str],
) -> None:
    from app.models.identity import User as UserModel

    assert isinstance(patient, UserModel)

    await _create_note(client, patient_headers, body="Question about my thyroid")

    doctor_user = await _create_doctor_with_consultation(
        db_session, patient_user_id=patient.id
    )
    doctor_headers = make_auth_headers(doctor_user)

    resp = await client.get(
        f"/v1/doctor/patients/{patient.id}/notes", headers=doctor_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(n["body"] == "Question about my thyroid" for n in data)


async def test_doctor_endpoint_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/patients/{uuid.uuid4()}/notes")
    assert resp.status_code == 401


async def test_patient_cannot_access_doctor_notes_endpoint(
    client: AsyncClient, patient_headers: dict[str, str]
) -> None:
    resp = await client.get(
        f"/v1/doctor/patients/{uuid.uuid4()}/notes", headers=patient_headers
    )
    assert resp.status_code == 403
