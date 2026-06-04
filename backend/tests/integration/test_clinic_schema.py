"""Integration tests for the P10 clinic domain schema.

Verifies that:
- Doctor, Patient, Coordinator records can be created and retrieved
- Patient ↔ user 1:1 UNIQUE constraint is enforced
- Doctor NMC registration number UNIQUE constraint is enforced
- Cross-table FK relationships resolve correctly
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    AvailabilityStatus,
    CoordinatorStatus,
    CredentialType,
    DoctorStatus,
    UserRole,
)
from app.models.admin import Coordinator
from app.models.clinic import Patient
from app.models.doctor import Availability, Credential, Doctor
from tests.conftest import (
    _synth_email,
    _synth_phone,
    create_doctor_user,
    create_patient_user,
)


async def _create_doctor_profile(db: AsyncSession, user_id: uuid.UUID, nmc: str) -> Doctor:
    doctor = Doctor(
        user_id=user_id,
        nmc_registration_number=nmc,
        nmc_state_council="Karnataka Medical Council",
        verified_at=datetime.now(UTC),
        specialty=["endocrinologist"],
        conditions_treated=["thyroid"],
        consultation_languages=["en"],
        status=DoctorStatus.ACTIVE,
        bio_short="Test doctor",
        onboarding_stage="complete",
    )
    db.add(doctor)
    await db.flush()
    return doctor


async def _next_kyros_id(db: AsyncSession) -> str:
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-TEST-{seq:05d}"


async def _create_patient_profile(
    db: AsyncSession, user_id: uuid.UUID, kyros_id: str | None = None
) -> Patient:
    kid = kyros_id or await _next_kyros_id(db)
    patient = Patient(
        user_id=user_id,
        kyros_patient_id=kid,
        primary_conditions=["thyroid"],
    )
    db.add(patient)
    await db.flush()
    return patient


# ── Doctor model ───────────────────────────────────────────────────────────────


async def test_create_doctor_profile(db_session: AsyncSession) -> None:
    user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)

    nmc = f"NMC-TEST-{uuid.uuid4().hex[:8].upper()}"
    doctor = await _create_doctor_profile(db_session, user.id, nmc)

    loaded = await db_session.scalar(select(Doctor).where(Doctor.id == doctor.id))
    assert loaded is not None
    assert loaded.nmc_registration_number == nmc
    assert loaded.status == DoctorStatus.ACTIVE
    assert loaded.conditions_treated == ["thyroid"]


async def test_doctor_nmc_uniqueness_enforced(db_session: AsyncSession) -> None:
    """Two doctors cannot share the same NMC registration number."""
    user1 = await create_doctor_user(db_session)
    user2 = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(user1, UserModel)
    assert isinstance(user2, UserModel)

    nmc = f"NMC-DUP-{uuid.uuid4().hex[:8].upper()}"
    await _create_doctor_profile(db_session, user1.id, nmc)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            dup = Doctor(
                user_id=user2.id,
                nmc_registration_number=nmc,  # duplicate
                specialty=[],
                conditions_treated=[],
                consultation_languages=["en"],
                status=DoctorStatus.APPLIED,
            )
            db_session.add(dup)
            await db_session.flush()


async def test_doctor_user_uniqueness_enforced(db_session: AsyncSession) -> None:
    """One user cannot have two Doctor profiles."""
    user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)

    nmc1 = f"NMC-U1-{uuid.uuid4().hex[:6].upper()}"
    nmc2 = f"NMC-U2-{uuid.uuid4().hex[:6].upper()}"
    await _create_doctor_profile(db_session, user.id, nmc1)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            dup = Doctor(
                user_id=user.id,  # same user
                nmc_registration_number=nmc2,
                specialty=[],
                conditions_treated=[],
                consultation_languages=["en"],
                status=DoctorStatus.APPLIED,
            )
            db_session.add(dup)
            await db_session.flush()


# ── Patient model ──────────────────────────────────────────────────────────────


async def test_create_patient_profile(db_session: AsyncSession) -> None:
    user = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)

    patient = await _create_patient_profile(db_session, user.id)

    loaded = await db_session.scalar(select(Patient).where(Patient.id == patient.id))
    assert loaded is not None
    assert loaded.user_id == user.id
    assert loaded.kyros_patient_id.startswith("KYR-")


async def test_patient_user_one_to_one_enforced(db_session: AsyncSession) -> None:
    """Same user_id cannot have two Patient rows."""
    user = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)

    await _create_patient_profile(db_session, user.id)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            dup = Patient(
                user_id=user.id,  # same user
                kyros_patient_id=f"KYR-DUP-{uuid.uuid4().hex[:5].upper()}",
                primary_conditions=[],
            )
            db_session.add(dup)
            await db_session.flush()


async def test_patient_kyros_id_uniqueness_enforced(db_session: AsyncSession) -> None:
    """kyros_patient_id must be unique across patients."""
    user1 = await create_patient_user(db_session)
    user2 = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(user1, UserModel)
    assert isinstance(user2, UserModel)

    shared_id = f"KYR-UNIQ-{uuid.uuid4().hex[:5].upper()}"
    await _create_patient_profile(db_session, user1.id, kyros_id=shared_id)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            dup = Patient(
                user_id=user2.id,
                kyros_patient_id=shared_id,  # duplicate
                primary_conditions=[],
            )
            db_session.add(dup)
            await db_session.flush()


# ── Coordinator model ─────────────────────────────────────────────────────────


async def test_create_coordinator(db_session: AsyncSession) -> None:
    from app.core.security import hash_password
    from app.models.identity import User as UserModel
    from app.repositories import users as users_repo

    coord_user = await users_repo.create(
        db_session,
        name="Test Coordinator",
        role=UserRole.COORDINATOR,
        phone=_synth_phone(),
        email=_synth_email(),
        password_hash=hash_password("TestPass123!"),
    )
    assert isinstance(coord_user, UserModel)

    coord = Coordinator(
        user_id=coord_user.id,
        status=CoordinatorStatus.ACTIVE,
        employee_id="COORD-TEST-001",
    )
    db_session.add(coord)
    await db_session.flush()

    loaded = await db_session.scalar(select(Coordinator).where(Coordinator.id == coord.id))
    assert loaded is not None
    assert loaded.employee_id == "COORD-TEST-001"
    assert loaded.assigned_patient_ids == []


# ── Cross-domain FK relationships ─────────────────────────────────────────────


async def test_patient_preferred_doctor_fk(db_session: AsyncSession) -> None:
    """Patient.preferred_doctor_id resolves to a Doctor row."""
    doc_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(doc_user, UserModel)

    nmc = f"NMC-PREF-{uuid.uuid4().hex[:8].upper()}"
    doctor = await _create_doctor_profile(db_session, doc_user.id, nmc)

    pat_user = await create_patient_user(db_session)
    assert isinstance(pat_user, UserModel)

    kid = await _next_kyros_id(db_session)
    patient = Patient(
        user_id=pat_user.id,
        kyros_patient_id=kid,
        primary_conditions=["thyroid"],
        preferred_doctor_id=doctor.id,
    )
    db_session.add(patient)
    await db_session.flush()

    loaded = await db_session.scalar(select(Patient).where(Patient.id == patient.id))
    assert loaded is not None
    assert loaded.preferred_doctor_id == doctor.id


# ── Credential model ──────────────────────────────────────────────────────────


async def test_create_credential_for_doctor(db_session: AsyncSession) -> None:
    doc_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(doc_user, UserModel)

    nmc = f"NMC-CRED-{uuid.uuid4().hex[:8].upper()}"
    doctor = await _create_doctor_profile(db_session, doc_user.id, nmc)

    cred = Credential(
        doctor_id=doctor.id,
        credential_type=CredentialType.MBBS,
        institution="AIIMS Delhi",
        year=2015,
    )
    db_session.add(cred)
    await db_session.flush()

    loaded = await db_session.scalar(select(Credential).where(Credential.doctor_id == doctor.id))
    assert loaded is not None
    assert loaded.institution == "AIIMS Delhi"


# ── Availability model ────────────────────────────────────────────────────────


async def test_create_availability_slot(db_session: AsyncSession) -> None:
    from datetime import timedelta

    doc_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(doc_user, UserModel)

    nmc = f"NMC-AVAIL-{uuid.uuid4().hex[:6].upper()}"
    doctor = await _create_doctor_profile(db_session, doc_user.id, nmc)

    slot_start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    slot_end = slot_start + timedelta(minutes=20)

    slot = Availability(
        doctor_id=doctor.id,
        slot_start=slot_start,
        slot_end=slot_end,
        status=AvailabilityStatus.AVAILABLE,
    )
    db_session.add(slot)
    await db_session.flush()

    loaded = await db_session.scalar(
        select(Availability).where(Availability.doctor_id == doctor.id)
    )
    assert loaded is not None
    assert loaded.status == AvailabilityStatus.AVAILABLE


async def test_availability_duplicate_slot_rejected(db_session: AsyncSession) -> None:
    """Cannot create two slots for the same doctor at the same slot_start."""
    from datetime import timedelta

    doc_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(doc_user, UserModel)

    nmc = f"NMC-DUPSL-{uuid.uuid4().hex[:6].upper()}"
    doctor = await _create_doctor_profile(db_session, doc_user.id, nmc)

    slot_start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)
    slot_end = slot_start + timedelta(minutes=20)

    db_session.add(
        Availability(
            doctor_id=doctor.id, slot_start=slot_start, slot_end=slot_end,
            status=AvailabilityStatus.AVAILABLE,
        )
    )
    await db_session.flush()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                Availability(
                    doctor_id=doctor.id, slot_start=slot_start, slot_end=slot_end,
                    status=AvailabilityStatus.BLOCKED,
                )
            )
            await db_session.flush()
