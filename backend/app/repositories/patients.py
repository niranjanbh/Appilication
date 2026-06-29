from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CoordinatorStatus
from app.models.admin import Coordinator
from app.models.clinic import Patient


async def get_patient_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> Patient | None:
    """Return the Patient profile row for a given user. Returns None if not found."""
    result = await db.execute(
        select(Patient).where(Patient.user_id == user_id, Patient.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_or_create_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> Patient:
    """Return the patient's profile, creating a minimal one if it is missing.

    The Patient profile is 1:1 with a ``role=patient`` user and is required by
    every clinic flow (consultations, lab reports, ABHA). It is created at
    registration; this helper makes that idempotent and self-healing for any
    pre-existing user that never got one. ``kyros_patient_id`` is drawn from the
    ``kc_patient_id_seq`` sequence (same source the seed uses).
    """
    existing = await get_patient_for_user(db, user_id=user_id)
    if existing is not None:
        return existing

    seq_val = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    kyros_patient_id = f"KYR-{datetime.now(UTC).year}-{seq_val:05d}"
    patient = Patient(user_id=user_id, kyros_patient_id=kyros_patient_id)
    db.add(patient)
    await db.flush()
    await ensure_coordinator_assigned(db, patient)
    return patient


async def _least_loaded_active_coordinator(db: AsyncSession) -> Coordinator | None:
    """The active coordinator currently handling the fewest patients.

    Load is the count of distinct assigned patients (``assigned_patient_ids``).
    Returns None when no active coordinator exists.
    """
    coordinators = (
        await db.scalars(
            select(Coordinator).where(
                Coordinator.status == CoordinatorStatus.ACTIVE,
                Coordinator.deleted_at.is_(None),
            )
        )
    ).all()
    if not coordinators:
        return None
    return min(coordinators, key=lambda c: len(c.assigned_patient_ids))


def _link_patient_to_coordinator(coordinator: Coordinator, patient: Patient) -> None:
    """Keep both sides of the link in sync: add the patient to the coordinator's
    ``assigned_patient_ids`` (so the coordinator can view and act on them) and
    set the patient's primary coordinator. Mirrors the admin manual-assignment
    writer. Idempotent on the list."""
    pid = str(patient.id)
    if pid not in coordinator.assigned_patient_ids:
        coordinator.assigned_patient_ids = [*coordinator.assigned_patient_ids, pid]
    patient.assigned_coordinator_id = coordinator.id


async def ensure_coordinator_assigned(db: AsyncSession, patient: Patient) -> None:
    """Give a patient a primary coordinator at creation time, if they have none.

    Idempotent: a patient that already has a coordinator is left untouched. This
    guarantees a patient is reachable via the patient-scoped coordinator views
    even before they submit a consultation. If no active coordinator exists, the
    patient is left unassigned (admin can assign later).
    """
    if patient.assigned_coordinator_id is not None:
        return
    target = await _least_loaded_active_coordinator(db)
    if target is None:
        return
    _link_patient_to_coordinator(target, patient)
    await db.flush()


async def ensure_patient_linked_to_coordinator(
    db: AsyncSession,
    *,
    patient: Patient,
    coordinator_id: uuid.UUID,
) -> None:
    """Ensure a patient appears in the given coordinator's assigned_patient_ids.

    Used when routing a follow-up to the original coordinator — the patient may
    already be linked (common case), but if the coordinator was changed since the
    original consultation this keeps the queue visible.  Idempotent.
    """
    coordinator = await db.get(Coordinator, coordinator_id)
    if coordinator is None:
        return
    pid = str(patient.id)
    if pid not in coordinator.assigned_patient_ids:
        coordinator.assigned_patient_ids = [*coordinator.assigned_patient_ids, pid]
    await db.flush()


async def route_consultation_to_coordinator(
    db: AsyncSession, patient: Patient
) -> uuid.UUID | None:
    """Per-consultation load balancing: route a new consultation to whichever
    active coordinator currently has the fewest patients.

    Unlike ``ensure_coordinator_assigned``, this runs for every new consultation
    even if the patient already has a coordinator — so a patient's consultations
    may land on different coordinators as load shifts. The patient is added to
    the chosen coordinator's ``assigned_patient_ids`` so that coordinator can
    both see the request (the requested queue is scoped by
    ``consultation.coordinator_id``) and assign a doctor (assignment is scoped by
    ``assigned_patient_ids``). Returns the chosen coordinator id, or None if no
    active coordinator exists (the consultation is then created unassigned).
    """
    target = await _least_loaded_active_coordinator(db)
    if target is None:
        return None
    _link_patient_to_coordinator(target, patient)
    await db.flush()
    return target.id


async def update_abha_number(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    abha_number: str,
) -> Patient:
    """Persist an ABHA number to the patient record. Flushes but does not commit."""
    await db.execute(
        update(Patient).where(Patient.id == patient_id).values(abha_number=abha_number)
    )
    await db.flush()
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one()
    return patient


async def update_emergency_contact(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    emergency_contact: dict[str, object] | None,
) -> Patient:
    """Set (or clear, with None) the patient's emergency contact. Flushes, no commit."""
    await db.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(emergency_contact=emergency_contact)
    )
    await db.flush()
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    return result.scalar_one()
