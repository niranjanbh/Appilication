"""Integration tests for the schedule-aware drug module (P36).

Covers:
  - GET /v1/doctor/drugs (catalogue search)
  - Schedule X / H1 / prohibited drug rejection on create_draft
  - GLP-1 vertical restriction enforcement
  - Schedule H drug allowed; drug_schedule stored on prescription item
  - Unknown (out-of-catalogue) drug allowed with drug_schedule=None
  - Refill gate: blocked on first consultation, allowed after prior completed one
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.models.identity import User as UserModel
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


# ── Fixtures helpers ─────────────────────────────────────────────────────────


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text

    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-RX-{seq:05d}"


async def _create_doctor_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    conditions_treated: list[str] | None = None,
) -> Doctor:
    nmc = f"NMC-RX-{uuid.uuid4().hex[:8].upper()}"
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=nmc,
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=conditions_treated or ["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Prescription schedule test doctor",
        consultation_duration_minutes_default=20,
    )
    db.add(doctor)
    await db.flush()
    return doctor


async def _create_patient_profile(db: AsyncSession, user_id: uuid.UUID) -> Patient:
    kid = await _next_kyros_id(db)
    patient = Patient(
        user_id=user_id,
        kyros_patient_id=kid,
        primary_conditions=["thyroid"],
    )
    db.add(patient)
    await db.flush()
    return patient


async def _create_consultation(
    db: AsyncSession,
    *,
    patient: Patient,
    doctor: Doctor,
    status: ConsultationStatus = ConsultationStatus.IN_PROGRESS,
    video_room_id: str = "stub-room-rx",
) -> Consultation:
    now = datetime.now(UTC)
    slot = Availability(
        doctor_id=doctor.id,
        slot_start=now + timedelta(hours=2),
        slot_end=now + timedelta(hours=2, minutes=20),
        status=AvailabilityStatus.BOOKED,
    )
    db.add(slot)
    await db.flush()
    c = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(hours=2),
        scheduled_end_at=now + timedelta(hours=2, minutes=20),
        consultation_fee_paise=60000,
        status=status,
        video_room_id=video_room_id,
        actual_start_at=now,
    )
    db.add(c)
    await db.flush()
    return c


def _rx_item(
    name: str = "levothyroxine",
    drug_form: str = "tablet",
    refill: bool = False,
) -> dict:
    return {
        "drug_generic_name": name,
        "drug_form": drug_form,
        "dosage": "50mcg",
        "frequency": "once daily",
        "duration_days": 30,
        "refill_allowed": refill,
    }


# ── Drug catalogue search ────────────────────────────────────────────────────


async def test_search_drugs_returns_schedule_h_matches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/doctor/drugs",
        params={"q": "levothyroxine"},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert any(d["drug_generic_name"] == "levothyroxine" for d in items)
    levo = next(d for d in items if d["drug_generic_name"] == "levothyroxine")
    assert levo["drug_schedule"] == "H"
    assert levo["is_prohibited"] is False


async def test_search_drugs_excludes_schedule_x(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/doctor/drugs",
        params={"q": "alprazolam"},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200
    # Schedule X drugs are excluded from autocomplete results
    assert resp.json() == []


# ── Schedule enforcement on create ──────────────────────────────────────────


async def test_schedule_x_drug_rejected_on_create(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": [_rx_item("alprazolam")]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "schedule_x_not_prescribable"


async def test_schedule_h1_drug_rejected_on_create(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id, conditions_treated=["skin_hair"])
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": [_rx_item("isotretinoin")]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "schedule_h1_not_prescribable_via_telemedicine"


async def test_prohibited_drug_rejected_on_create(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id, conditions_treated=["weight"])
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": [_rx_item("sibutramine")]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "drug_prohibited"


async def test_glp1_without_weight_vertical_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    # Doctor treats thyroid only — not 'weight'
    doctor = await _create_doctor_profile(db_session, doctor_user.id, conditions_treated=["thyroid"])
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": [_rx_item("semaglutide")]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "drug_requires_specialist_vertical"


async def test_glp1_with_weight_vertical_allowed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id, conditions_treated=["weight"])
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": [_rx_item("semaglutide")]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()["items"][0]
    assert item["drug_schedule"] == "H"


async def test_schedule_h_drug_allowed_and_schedule_stored(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": [_rx_item("levothyroxine")]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()["items"][0]
    assert item["drug_schedule"] == "H"


async def test_unknown_drug_allowed_with_null_schedule(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": [_rx_item("custom compounded vitamin b12")]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()["items"][0]
    assert item["drug_schedule"] is None


# ── Refill gate ──────────────────────────────────────────────────────────────


async def test_refill_blocked_on_first_consultation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)
    # First (and only) consultation — no prior completed one
    consultation = await _create_consultation(db_session, patient=patient, doctor=doctor)

    resp = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": [_rx_item("levothyroxine", refill=True)]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "refill_requires_prior_consultation"


async def test_refill_allowed_after_prior_completed_consultation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    patient = await _create_patient_profile(db_session, patient_user.id)

    # Create a prior COMPLETED consultation for this patient
    await _create_consultation(
        db_session,
        patient=patient,
        doctor=doctor,
        status=ConsultationStatus.COMPLETED,
        video_room_id="stub-prior-completed",
    )

    # Current in-progress consultation
    current = await _create_consultation(
        db_session,
        patient=patient,
        doctor=doctor,
        video_room_id="stub-current-rx",
    )

    resp = await client.post(
        f"/v1/doctor/consultations/{current.id}/prescription",
        json={"items": [_rx_item("levothyroxine", refill=True)]},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()["items"][0]
    assert item["refill_allowed"] is True
