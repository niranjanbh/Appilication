"""Integration tests for video join endpoints and recording consent.

Covers:
  - GET /v1/clinic/patient/consultations/{id}/join
  - POST /v1/clinic/patient/consultations/{id}/recording-consent
  - GET /v1/doctor/consultations/{id}/join

Security properties verified:
  - Cross-user 404 (patient cannot get another patient's join token)
  - Cross-doctor 404 (doctor cannot get another doctor's join token)
  - Audit log written for allowed and denied authorization decisions
  - Room is provisioned on demand at join time when not pre-warmed (200 + token)
  - 503 only when the video provider genuinely fails to create the room
  - Token is returned in stub mode when room is provisioned
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus
from app.models.audit import AuditLog
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from tests.conftest import (
    create_coordinator_user,
    create_doctor_user,
    create_patient_user,
    make_auth_headers,
)

# ── Shared fixtures ────────────────────────────────────────────────────────────


async def _next_kyros_id(db: AsyncSession) -> str:
    from sqlalchemy import text
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-VID-{seq:05d}"


async def _create_doctor_profile(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    nmc = f"NMC-V-{uuid.uuid4().hex[:8].upper()}"
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=nmc,
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Video test doctor",
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


async def _grant_telemedicine_consent(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Grant an active TELEMEDICINE consent — satisfies the TPG hard gate on doctor join."""
    import hashlib

    from app.db.enums import ConsentType
    from app.models.consent import ConsentRecord

    db.add(
        ConsentRecord(
            user_id=user_id,
            consent_type=ConsentType.TELEMEDICINE,
            version="1.0",
            granted=True,
            granted_at=datetime.now(UTC),
            consent_text_hash=hashlib.sha256(b"telemedicine-consent-test").hexdigest(),
        )
    )
    await db.flush()


async def _create_consultation(
    db: AsyncSession,
    *,
    patient: Patient,
    doctor: Doctor,
    video_room_id: str | None = "stub-room-test-123",
    status: ConsultationStatus = ConsultationStatus.CONFIRMED,
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

    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(hours=2),
        scheduled_end_at=now + timedelta(hours=2, minutes=20),
        consultation_fee_paise=60000,
        status=status,
        video_room_id=video_room_id,
    )
    db.add(consultation)
    await db.flush()
    return consultation


# ── Patient join endpoint ──────────────────────────────────────────────────────


async def test_patient_join_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/consultations/{uuid.uuid4()}/join")
    assert resp.status_code == 401


async def test_patient_join_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 403


async def test_patient_join_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord_user = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(coord_user),
    )
    assert resp.status_code == 403


async def test_patient_join_nonexistent_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 404


async def test_patient_join_provisions_room_on_demand(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A confirmed consult with no pre-warmed room is provisioned on join, not 503'd."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id=None
    )

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}/join",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Stub mode returns a deterministic room id derived from the consultation id.
    assert data["room_id"] == f"stub-room-{consultation.id}"
    assert "token" in data

    # The provisioned room id is now persisted on the consultation.
    await db_session.refresh(consultation)
    assert consultation.video_room_id == f"stub-room-{consultation.id}"


async def test_patient_join_room_provisioning_failure_returns_503(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A genuine provider failure during on-demand provisioning still yields 503."""
    import app.integrations.livekit_video as livekit_video
    from app.models.identity import User as UserModel

    async def _boom(*, consultation_id: str) -> str:
        raise RuntimeError("video provider unavailable")

    monkeypatch.setattr(livekit_video, "create_room", _boom)

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id=None
    )

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}/join",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "video_room_not_ready"


async def test_patient_join_provisioned_returns_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    room_id = f"stub-room-{uuid.uuid4()}"
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id=room_id
    )

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}/join",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["room_id"] == room_id
    assert "token" in data
    assert "endpoint" in data


async def test_patient_join_cross_user_returns_404_and_audit_logs_denial(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Cross-user 404: patient A cannot get patient B's join token."""
    from app.models.identity import User as UserModel

    patient_a_user = await create_patient_user(db_session)
    patient_b_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_a_user, UserModel)
    assert isinstance(patient_b_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_b = await _create_patient_profile(db_session, patient_b_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    # Consultation belongs to patient B
    consultation = await _create_consultation(
        db_session, patient=patient_b, doctor=doctor, video_room_id="stub-room-abc"
    )

    # Patient A tries to join
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}/join",
        headers=make_auth_headers(patient_a_user),
    )
    assert resp.status_code == 404

    # Audit log must record the denial
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_a_user.id,
            AuditLog.action == "join_consultation",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


# ── Recording consent endpoint ─────────────────────────────────────────────────


async def test_recording_consent_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/recording-consent"
    )
    assert resp.status_code == 401


async def test_recording_consent_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/recording-consent",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 403


async def test_recording_consent_sets_flag_and_creates_consent_record(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.db.enums import ConsentType
    from app.models.consent import ConsentRecord
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id="stub-room-xyz"
    )
    assert not consultation.recording_consent

    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consultation.id}/recording-consent",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["recording_consent"] is True

    # Consent record written to ad_consent_records
    record = await db_session.scalar(
        select(ConsentRecord).where(
            ConsentRecord.user_id == patient_user.id,
            ConsentRecord.consent_type == ConsentType.RECORDING,
        )
    )
    assert record is not None
    assert record.granted is True


async def test_recording_consent_nonexistent_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/recording-consent",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 404


# ── Doctor join endpoint ───────────────────────────────────────────────────────


async def test_doctor_join_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/doctor/consultations/{uuid.uuid4()}/join")
    assert resp.status_code == 401


async def test_doctor_join_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 403


async def test_doctor_join_coordinator_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    coord_user = await create_coordinator_user(db_session)
    resp = await client.get(
        f"/v1/doctor/consultations/{uuid.uuid4()}/join",
        headers=make_auth_headers(coord_user),
    )
    assert resp.status_code == 403


async def test_doctor_join_provisioned_returns_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    await _grant_telemedicine_consent(db_session, user_id=patient_user.id)
    room_id = f"stub-room-dr-{uuid.uuid4()}"
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id=room_id
    )

    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["room_id"] == room_id
    assert "token" in data
    assert "endpoint" in data


async def test_doctor_join_transitions_confirmed_to_in_progress_and_is_idempotent(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """TPG gate satisfied: CONFIRMED -> IN_PROGRESS with actual_start_at stamped.

    A second join (now IN_PROGRESS) is an idempotent reconnect — 200, no change to
    actual_start_at.
    """
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    await _grant_telemedicine_consent(db_session, user_id=patient_user.id)
    room_id = f"stub-room-dr-{uuid.uuid4()}"
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id=room_id
    )
    assert consultation.actual_start_at is None

    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text

    await db_session.refresh(consultation)
    assert consultation.status == ConsultationStatus.IN_PROGRESS
    assert consultation.actual_start_at is not None
    first_start = consultation.actual_start_at

    # Re-join: idempotent, no duplicate transition or actual_start_at change.
    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text

    await db_session.refresh(consultation)
    assert consultation.status == ConsultationStatus.IN_PROGRESS
    assert consultation.actual_start_at == first_start


async def test_doctor_join_identity_not_verified_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """TPG identity-verification gate: patient with phone_verified=False blocks open."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session, phone_verified=False)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    await _grant_telemedicine_consent(db_session, user_id=patient_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id="stub-room-unverified"
    )

    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "identity_not_verified"

    await db_session.refresh(consultation)
    assert consultation.status == ConsultationStatus.CONFIRMED

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == doctor_user.id,
            AuditLog.action == "join_consultation",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "identity_not_verified"


async def test_doctor_join_missing_telemedicine_consent_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """TPG consent gate: phone verified but no active TELEMEDICINE consent blocks open."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id="stub-room-no-consent"
    )

    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "telemedicine_consent_missing"

    await db_session.refresh(consultation)
    assert consultation.status == ConsultationStatus.CONFIRMED


async def test_doctor_join_scheduled_consult_returns_409_not_open_eligible(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A SCHEDULED (unpaid) consult cannot be opened — wrong lifecycle stage."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    await _grant_telemedicine_consent(db_session, user_id=patient_user.id)
    consultation = await _create_consultation(
        db_session,
        patient=patient,
        doctor=doctor,
        video_room_id="stub-room-scheduled",
        status=ConsultationStatus.SCHEDULED,
    )

    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "consultation_not_open_eligible"


async def test_doctor_join_cross_doctor_returns_404_and_audit_logs_denial(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Cross-doctor 404: doctor A cannot get doctor B's consultation token."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_a_user = await create_doctor_user(db_session)
    doctor_b_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_a_user, UserModel)
    assert isinstance(doctor_b_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    # Consultation belongs to doctor B
    doctor_b = await _create_doctor_profile(db_session, doctor_b_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor_b, video_room_id="stub-room-drb"
    )

    # Doctor A (who has a profile) tries to join
    await _create_doctor_profile(db_session, doctor_a_user.id)

    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_a_user),
    )
    assert resp.status_code == 404

    # Audit log records denial for doctor A
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == doctor_a_user.id,
            AuditLog.action == "join_consultation",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


async def test_doctor_join_provisions_room_on_demand(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A confirmed consult with no pre-warmed room is provisioned on the doctor join."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    await _grant_telemedicine_consent(db_session, user_id=patient_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id=None
    )

    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["room_id"] == f"stub-room-{consultation.id}"
    assert "token" in data

    await db_session.refresh(consultation)
    assert consultation.video_room_id == f"stub-room-{consultation.id}"
    assert consultation.status == ConsultationStatus.IN_PROGRESS


async def test_doctor_join_room_provisioning_failure_returns_503(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A genuine provider failure during on-demand provisioning still yields 503."""
    import app.integrations.livekit_video as livekit_video
    from app.models.identity import User as UserModel

    async def _boom(*, consultation_id: str) -> str:
        raise RuntimeError("video provider unavailable")

    monkeypatch.setattr(livekit_video, "create_room", _boom)

    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    await _grant_telemedicine_consent(db_session, user_id=patient_user.id)
    consultation = await _create_consultation(
        db_session, patient=patient, doctor=doctor, video_room_id=None
    )

    resp = await client.get(
        f"/v1/doctor/consultations/{consultation.id}/join",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "video_room_not_ready"
