"""A patient-submitted consultation request must reach a coordinator's queue.

Regression: a patient created before coordinator auto-assignment (or while no
active coordinator existed) had ``assigned_coordinator_id=None``. Their request
was created with ``coordinator_id=None`` and never appeared in any coordinator
portal queue, which scopes strictly by ``assigned_patient_ids``. The request
flow now assigns a coordinator on the fly when one is missing.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CoordinatorStatus
from app.models.admin import Coordinator
from app.repositories import coordinator_portal as coord_repo
from app.repositories import patients as patients_repo
from app.services import consultation_service
from tests.conftest import create_coordinator_user, create_patient_user


async def test_request_assigns_coordinator_when_patient_unassigned(
    db_session: AsyncSession,
) -> None:
    # Patient created first, before any coordinator exists -> stays unassigned.
    patient_user = await create_patient_user(db_session)
    await db_session.flush()
    patient = await patients_repo.get_or_create_for_user(
        db_session, user_id=patient_user.id
    )
    assert patient.assigned_coordinator_id is None

    # A coordinator now exists.
    coord_user = await create_coordinator_user(db_session)
    coord = Coordinator(
        user_id=coord_user.id,
        status=CoordinatorStatus.ACTIVE,
        assigned_patient_ids=[],
    )
    db_session.add(coord)
    await db_session.flush()

    # Submitting the request routes the patient to the coordinator on the fly.
    consultation = await consultation_service.request_consultation(
        db_session,
        patient_user_id=patient_user.id,
        condition_category="thyroid",
        consultation_type="initial",
    )
    await db_session.flush()

    # Both sides of the link are set, and the consultation carries the coordinator.
    assert patient.assigned_coordinator_id == coord.id
    assert consultation.coordinator_id == coord.id
    await db_session.refresh(coord)
    assert str(patient.id) in coord.assigned_patient_ids

    # And it shows up in that coordinator's requested-consultation queue.
    queue = await coord_repo.list_requested_consultations(
        db_session, coordinator_id=coord.id
    )
    assert consultation.id in [c.id for c, _patient_user in queue]


async def test_new_consultation_routes_to_least_loaded_coordinator(
    db_session: AsyncSession,
) -> None:
    import uuid

    busy_user = await create_coordinator_user(db_session)
    free_user = await create_coordinator_user(db_session)
    busy = Coordinator(
        user_id=busy_user.id,
        status=CoordinatorStatus.ACTIVE,
        assigned_patient_ids=[str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())],
    )
    free = Coordinator(
        user_id=free_user.id,
        status=CoordinatorStatus.ACTIVE,
        assigned_patient_ids=[],
    )
    db_session.add_all([busy, free])
    await db_session.flush()

    patient_user = await create_patient_user(db_session)
    await db_session.flush()
    await patients_repo.get_or_create_for_user(db_session, user_id=patient_user.id)

    consultation = await consultation_service.request_consultation(
        db_session,
        patient_user_id=patient_user.id,
        condition_category="thyroid",
        consultation_type="initial",
    )
    await db_session.flush()

    assert consultation.coordinator_id == free.id


async def test_consultation_rebalances_away_from_primary_coordinator(
    db_session: AsyncSession,
) -> None:
    """A patient whose primary coordinator is busier than another gets the new
    consultation routed to the least-loaded one, and the queue is scoped to that
    coordinator (consultation.coordinator_id), not the patient's primary."""
    import uuid

    a_user = await create_coordinator_user(db_session)
    b_user = await create_coordinator_user(db_session)
    coord_a = Coordinator(
        user_id=a_user.id, status=CoordinatorStatus.ACTIVE, assigned_patient_ids=[]
    )
    coord_b = Coordinator(
        user_id=b_user.id, status=CoordinatorStatus.ACTIVE, assigned_patient_ids=[]
    )
    db_session.add_all([coord_a, coord_b])
    await db_session.flush()

    patient_user = await create_patient_user(db_session)
    await db_session.flush()
    patient = await patients_repo.get_or_create_for_user(
        db_session, user_id=patient_user.id
    )

    # Force the scenario: A is the patient's primary and is the busier of the two.
    coord_a.assigned_patient_ids = [
        str(patient.id),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
    ]
    coord_b.assigned_patient_ids = []
    patient.assigned_coordinator_id = coord_a.id
    await db_session.flush()

    consultation = await consultation_service.request_consultation(
        db_session,
        patient_user_id=patient_user.id,
        condition_category="pcos",
        consultation_type="initial",
    )
    await db_session.flush()

    # Routed to B (the least loaded), not the patient's primary A.
    assert consultation.coordinator_id == coord_b.id
    await db_session.refresh(coord_b)
    assert str(patient.id) in coord_b.assigned_patient_ids

    # Queue is consultation-scoped: B sees it, A does not.
    b_queue = await coord_repo.list_requested_consultations(
        db_session, coordinator_id=coord_b.id
    )
    assert consultation.id in [c.id for c, _pu in b_queue]
    a_queue = await coord_repo.list_requested_consultations(
        db_session, coordinator_id=coord_a.id
    )
    assert consultation.id not in [c.id for c, _pu in a_queue]
