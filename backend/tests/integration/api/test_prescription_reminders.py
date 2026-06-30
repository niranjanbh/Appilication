"""Integration tests for prescription-linked reminder generation on sign.

Signing a prescription transcribes its daily-cadence drug lines into patient
reminders (PR1 of the doctor→patient→adherence loop).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.models.identity import User as UserModel
from app.models.wellness import Reminder
from tests.conftest import create_doctor_user, create_patient_user, make_auth_headers


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text

    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-RXR-{seq:05d}"


async def _doctor_profile(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=f"NMC-RXR-{uuid.uuid4().hex[:8].upper()}",
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Reminder generation test doctor",
        consultation_duration_minutes_default=20,
    )
    db.add(doctor)
    await db.flush()
    return doctor


async def _patient_profile(db: AsyncSession, user_id: uuid.UUID) -> Patient:
    patient = Patient(
        user_id=user_id,
        kyros_patient_id=await _next_kyros_id(db),
        primary_conditions=["thyroid"],
    )
    db.add(patient)
    await db.flush()
    return patient


async def _consultation(db: AsyncSession, *, patient: Patient, doctor: Doctor) -> Consultation:
    now = datetime.now(UTC)
    db.add(
        Availability(
            doctor_id=doctor.id,
            slot_start=now + timedelta(hours=2),
            slot_end=now + timedelta(hours=2, minutes=20),
            status=AvailabilityStatus.BOOKED,
        )
    )
    await db.flush()
    c = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(hours=2),
        scheduled_end_at=now + timedelta(hours=2, minutes=20),
        consultation_fee_paise=60000,
        status=ConsultationStatus.IN_PROGRESS,
        video_room_id=f"stub-{uuid.uuid4().hex[:8]}",
        actual_start_at=now,
    )
    db.add(c)
    await db.flush()
    return c


def _structured_item(*, frequency_code: str, timing_slots: list[str], name: str = "levothyroxine") -> dict:
    return {
        "drug_generic_name": name,
        "drug_form": "tablet",
        "dosage": "50mcg",
        "frequency_code": frequency_code,
        "timing_slots": timing_slots,
        "food_relation": "after_food",
        "duration_days": 30,
    }


async def _draft_and_sign(
    client: AsyncClient,
    db_session: AsyncSession,
    *,
    items: list[dict],
) -> tuple[UserModel, UserModel, str]:
    """Create patient+doctor+consultation, a prescription draft, then sign it.
    Returns (doctor_user, patient_user, prescription_id)."""
    doctor_user = await create_doctor_user(db_session)
    patient_user = await create_patient_user(db_session)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(patient_user, UserModel)
    doctor = await _doctor_profile(db_session, doctor_user.id)
    patient = await _patient_profile(db_session, patient_user.id)
    consultation = await _consultation(db_session, patient=patient, doctor=doctor)

    create = await client.post(
        f"/v1/doctor/consultations/{consultation.id}/prescription",
        json={"items": items},
        headers=make_auth_headers(doctor_user),
    )
    assert create.status_code == 201, create.text
    rx_id = create.json()["id"]

    sign = await client.post(
        f"/v1/doctor/prescriptions/{rx_id}/sign",
        headers=make_auth_headers(doctor_user),
    )
    assert sign.status_code == 200, sign.text
    return doctor_user, patient_user, rx_id


async def test_signing_bd_prescription_generates_two_reminders(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, patient_user, rx_id = await _draft_and_sign(
        client,
        db_session,
        items=[_structured_item(frequency_code="BD", timing_slots=["morning", "night"])],
    )

    resp = await client.get("/v1/wellness/reminders", headers=make_auth_headers(patient_user))
    assert resp.status_code == 200, resp.text
    reminders = resp.json()["reminders"]
    med = [r for r in reminders if r["source_type"] == "prescription"]
    assert len(med) == 2
    assert {r["schedule_cron"] for r in med} == {"0 8 * * *", "0 21 * * *"}
    for r in med:
        assert r["type"] == "medication"
        assert r["generated_by"] == "doctor"
        assert r["ends_at"] is not None
        assert r["metadata"]["prescription_id"] == rx_id
        # Server-delivered (empty channels), so the dispatcher does not skip it.
        assert r["notification_channels"] == []


async def test_signing_weekly_prescription_generates_no_reminder(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A non-daily cadence is not deterministically schedulable → no reminder."""
    _, patient_user, _ = await _draft_and_sign(
        client,
        db_session,
        items=[_structured_item(frequency_code="WEEKLY", timing_slots=["morning"])],
    )

    resp = await client.get("/v1/wellness/reminders", headers=make_auth_headers(patient_user))
    assert resp.status_code == 200, resp.text
    assert [r for r in resp.json()["reminders"] if r["source_type"] == "prescription"] == []


async def test_regeneration_is_idempotent_per_prescription(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Re-running generation for a prescription deactivates the prior batch
    instead of stacking duplicates (the future supersede seam)."""
    from app.repositories import prescriptions as prescriptions_repo
    from app.services import reminder_generation

    _, patient_user, rx_id = await _draft_and_sign(
        client,
        db_session,
        items=[_structured_item(frequency_code="BD", timing_slots=["morning", "night"])],
    )
    rx_uuid = uuid.UUID(rx_id)

    rx = await prescriptions_repo.get_by_id(db_session, prescription_id=rx_uuid)
    assert rx is not None
    items = await prescriptions_repo.list_items(db_session, prescription_id=rx_uuid)
    await reminder_generation.generate_for_prescription(
        db_session, prescription=rx, items=items, patient_user_id=patient_user.id
    )

    total = await db_session.scalar(
        select(func.count()).select_from(Reminder).where(Reminder.user_id == patient_user.id)
    )
    active = await db_session.scalar(
        select(func.count())
        .select_from(Reminder)
        .where(Reminder.user_id == patient_user.id, Reminder.active.is_(True))
    )
    assert total == 4   # 2 from sign (now inactive) + 2 fresh
    assert active == 2   # only the latest batch fires


async def _patient_id_for(db_session: AsyncSession, patient_user: UserModel) -> uuid.UUID:
    pid = await db_session.scalar(select(Patient.id).where(Patient.user_id == patient_user.id))
    assert pid is not None
    return pid


async def test_doctor_reads_patient_adherence_summary(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user, patient_user, _ = await _draft_and_sign(
        client,
        db_session,
        items=[_structured_item(frequency_code="BD", timing_slots=["morning", "night"])],
    )

    # Patient takes both of today's doses.
    rems = (
        await client.get("/v1/wellness/reminders", headers=make_auth_headers(patient_user))
    ).json()["reminders"]
    med = [r for r in rems if r["source_type"] == "prescription"]
    assert len(med) == 2
    slot = datetime.now(UTC).replace(microsecond=0).isoformat()
    for r in med:
        resp = await client.post(
            f"/v1/wellness/reminders/{r['id']}/log",
            headers=make_auth_headers(patient_user),
            json={"scheduled_at": slot, "action": "taken"},
        )
        assert resp.status_code == 201, resp.text

    patient_id = await _patient_id_for(db_session, patient_user)
    resp = await client.get(
        f"/v1/doctor/patients/{patient_id}/adherence",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["active_prescription_reminders"] == 2
    assert body["adherence_rate_30d"] == 1.0
    assert body["current_streak"] == 1
    assert body["longest_streak"] == 1
    assert body["last_missed_at"] is None


async def test_doctor_cannot_read_other_doctors_patient_adherence(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, patient_user, _ = await _draft_and_sign(
        client,
        db_session,
        items=[_structured_item(frequency_code="OD", timing_slots=["morning"])],
    )
    patient_id = await _patient_id_for(db_session, patient_user)

    other_doctor = await create_doctor_user(db_session)
    assert isinstance(other_doctor, UserModel)
    await _doctor_profile(db_session, other_doctor.id)

    resp = await client.get(
        f"/v1/doctor/patients/{patient_id}/adherence",
        headers=make_auth_headers(other_doctor),
    )
    assert resp.status_code == 404
