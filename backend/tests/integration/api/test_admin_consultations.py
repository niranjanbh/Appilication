"""Admin consultation listing must include patient-submitted requests.

A `requested` consultation has no doctor yet (doctor_id is NULL until a
coordinator assigns one). The admin list query must left-join the doctor so
these unassigned requests still appear — an inner join silently dropped every
one of them, leaving the admin console empty of new requests.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import admin_portal as admin_repo
from app.repositories import consultations as consultations_repo
from app.repositories import patients as patients_repo
from tests.conftest import create_patient_user


async def test_admin_list_includes_requested_consultation_without_doctor(
    db_session: AsyncSession,
) -> None:
    user = await create_patient_user(db_session)
    await db_session.flush()
    patient = await patients_repo.get_or_create_for_user(db_session, user_id=user.id)

    consult = await consultations_repo.create_consultation_request(
        db_session,
        patient_id=patient.id,
        condition_category="thyroid",
        consultation_type="initial",
    )
    await db_session.flush()

    triples, total = await admin_repo.list_all_consultations(db_session)

    match = next((t for t in triples if t[0].id == consult.id), None)
    assert match is not None, "requested consultation missing from admin list"
    # No doctor assigned yet — the doctor_user slot is None, not a crash.
    assert match[2] is None
    assert total >= 1


async def test_admin_list_status_filter_includes_requested(
    db_session: AsyncSession,
) -> None:
    user = await create_patient_user(db_session)
    await db_session.flush()
    patient = await patients_repo.get_or_create_for_user(db_session, user_id=user.id)

    consult = await consultations_repo.create_consultation_request(
        db_session,
        patient_id=patient.id,
        condition_category="pcos",
        consultation_type="initial",
    )
    await db_session.flush()

    triples, total = await admin_repo.list_all_consultations(
        db_session, status_filter="requested"
    )

    ids = [c.id for (c, _patient_user, _doctor_user) in triples]
    assert consult.id in ids
    assert total >= 1


async def test_admin_cancel_writes_patient_notification(
    db_session: AsyncSession,
) -> None:
    """Admin cancellation tells the patient via a 'consultation_cancelled' inbox
    notification (P3 fix)."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.db.enums import ConsultationStatus
    from app.models.clinic import Consultation
    from app.models.notifications import Notification
    from app.services import consultation_service

    user = await create_patient_user(db_session)
    await db_session.flush()
    patient = await patients_repo.get_or_create_for_user(db_session, user_id=user.id)

    now = datetime.now(UTC)
    consultation = Consultation(
        patient_id=patient.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(hours=4),
        scheduled_end_at=now + timedelta(hours=4, minutes=20),
        consultation_fee_paise=60000,
        status=ConsultationStatus.SCHEDULED,
    )
    db_session.add(consultation)
    await db_session.flush()

    updated, refund_issued = await consultation_service.admin_cancel_consultation(
        db_session, consultation_id=consultation.id, reason="doctor unavailable"
    )
    await db_session.flush()

    assert updated.status == ConsultationStatus.CANCELLED
    assert refund_issued is False  # no payment linked

    notification = await db_session.scalar(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.template_name == "consultation_cancelled",
        )
    )
    assert notification is not None
    assert notification.data.get("resource_id") == str(consultation.id)
