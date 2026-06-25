"""Tests for staff-initiated on-demand video consultations.

Covers consultation_service.create_on_demand_consultation:
  - Lands CONFIRMED, zero-fee, with a video room provisioned immediately.
  - The per-consultation participant cap is stored and passed to the provider,
    clamped to [2, settings.video_max_participants_cap].
  - An inactive doctor is refused.

The coordinator/admin portal endpoints are thin wrappers over this service plus
RBAC scoping (the coordinator path additionally checks patient assignment via
coord_repo.get_assigned_patient, exercised in the coordinator-routing tests).
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ConsultationStatus, DoctorStatus
from app.repositories import consultations as consultations_repo
from app.repositories import patients as patients_repo
from app.services import consultation_service
from tests.conftest import create_doctor_with_profile, create_patient_user


async def _patient_and_doctor(db: AsyncSession) -> tuple[object, object]:
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db)
    assert isinstance(patient_user, UserModel)
    patient = await patients_repo.get_or_create_for_user(db, user_id=patient_user.id)

    doctor_user = await create_doctor_with_profile(db)
    assert isinstance(doctor_user, UserModel)
    doctor = await consultations_repo.get_doctor_record(db, user_id=doctor_user.id)
    assert doctor is not None
    return patient, doctor


async def test_create_on_demand_confirmed_free_with_room(db_session: AsyncSession) -> None:
    patient, doctor = await _patient_and_doctor(db_session)

    consult = await consultation_service.create_on_demand_consultation(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        max_participants=6,
    )

    assert consult.status == ConsultationStatus.CONFIRMED
    assert consult.consultation_fee_paise == 0
    assert consult.scheduled_start_at is not None
    assert consult.video_max_participants == 6

    # The room was provisioned on creation (Core update — refresh to read it back).
    await db_session.refresh(consult)
    assert consult.video_room_id == f"stub-room-{consult.id}"


async def test_on_demand_room_sized_to_requested_cap(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An over-large request is clamped to the cap and passed to the provider."""
    import app.integrations.livekit_video as livekit_video

    captured: dict[str, int | None] = {}

    async def _capture(*, consultation_id: str, max_participants: int | None = None) -> str:
        captured["max"] = max_participants
        return f"stub-room-{consultation_id}"

    monkeypatch.setattr(livekit_video, "create_room", _capture)

    patient, doctor = await _patient_and_doctor(db_session)
    consult = await consultation_service.create_on_demand_consultation(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="weight",
        max_participants=50,
    )

    # Clamped to settings.video_max_participants_cap (12) and used for the room.
    assert consult.video_max_participants == 12
    assert captured["max"] == 12


async def test_on_demand_clamps_below_minimum(db_session: AsyncSession) -> None:
    patient, doctor = await _patient_and_doctor(db_session)
    consult = await consultation_service.create_on_demand_consultation(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="pcos",
        max_participants=1,
    )
    assert consult.video_max_participants == 2


async def test_on_demand_inactive_doctor_refused(db_session: AsyncSession) -> None:
    patient, doctor = await _patient_and_doctor(db_session)
    doctor.status = DoctorStatus.INACTIVE  # type: ignore[attr-defined]
    await db_session.flush()

    with pytest.raises(consultation_service.ConsultationError) as exc_info:
        await consultation_service.create_on_demand_consultation(
            db_session,
            patient_id=patient.id,
            doctor_id=doctor.id,
            condition_category="thyroid",
        )
    assert exc_info.value.code == "doctor_not_available"


def test_generate_staff_token_uses_visible_role_identity() -> None:
    """Staff support tokens carry the role as identity (never covert) — stub mode."""
    from app.integrations import livekit_video

    token = livekit_video.generate_staff_token(
        room_id="room-x", user_id="u1", role="coordinator"
    )
    assert token == "stub-coordinator-token-room-x-u1"
