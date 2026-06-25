"""Integration tests for consultation booking, cancellation, and RBAC."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.enums import AvailabilityStatus, ConsultationStatus, DoctorStatus, PaymentStatus
from app.models.admin import Coordinator
from app.models.audit import AuditLog
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.repositories import payments as payments_repo
from app.services import consultation_service
from tests.conftest import (
    create_coordinator_user,
    create_doctor_user,
    create_patient_user,
    make_auth_headers,
)

_STUB_ORDER_ID = "order_TESTSTUB_CONSULT1"
_STUB_PAYMENT_ID = "pay_TESTSTUB_CONSULT1"
# Server-authoritative fee (initial consult). The booking endpoint resolves this
# from config; the client cannot influence it.
_FEE_PAISE = settings.consultation_fee_initial_paise


# ── Shared helpers ─────────────────────────────────────────────────────────────


async def _next_kyros_id(db: AsyncSession) -> str:
    seq = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
    return f"KYR-TST-{seq:05d}"


async def _create_doctor_profile(db: AsyncSession, user_id: uuid.UUID) -> Doctor:
    nmc = f"NMC-C-{uuid.uuid4().hex[:8].upper()}"
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


async def _create_slot(
    db: AsyncSession,
    doctor: Doctor,
    *,
    hours_from_now: int = 48,
) -> Availability:
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    slot_start = now + timedelta(hours=hours_from_now)
    slot_end = slot_start + timedelta(minutes=doctor.consultation_duration_minutes_default)
    slot = Availability(
        doctor_id=doctor.id,
        slot_start=slot_start,
        slot_end=slot_end,
        status=AvailabilityStatus.AVAILABLE,
    )
    db.add(slot)
    await db.flush()
    return slot


def _sig(order_id: str, payment_id: str, secret: str = "rzp_test_key_secret") -> str:
    msg = f"{order_id}|{payment_id}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


async def _create_coordinator_for_patient(
    db: AsyncSession, patient_profile_id: uuid.UUID
) -> Coordinator:
    """Create a coordinator with the given patient assigned to them."""
    coord_user = await create_coordinator_user(db)
    coord = Coordinator(
        user_id=coord_user.id,
        assigned_patient_ids=[str(patient_profile_id)],
    )
    db.add(coord)
    await db.flush()
    return coord


async def _request_consultation_api(client: AsyncClient, patient_user: object) -> str:
    """Patient submits a request via the API; returns the consultation_id."""
    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={
            "condition_category": "thyroid",
            "requirement_notes": "Tired and gaining weight.",
            "preferred_time_window": "weekday_morning",
        },
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["consultation_id"]


async def _request_and_assign(
    client: AsyncClient,
    db: AsyncSession,
    patient_user: object,
    patient_profile: Patient,
    doctor: Doctor,
    slot: Availability,
) -> tuple[str, str]:
    """Drive the full request → coordinator-assign flow.

    Returns (consultation_id, payment_id). The consultation ends up SCHEDULED
    with a Razorpay order awaiting payment.
    """
    consult_id = await _request_consultation_api(client, patient_user)
    coord = await _create_coordinator_for_patient(db, patient_profile.id)

    with patch(
        "app.integrations.razorpay.create_order",
        new_callable=AsyncMock,
        return_value={"id": _STUB_ORDER_ID, "amount": _FEE_PAISE, "currency": "INR"},
    ):
        _consultation, payment = await consultation_service.assign_consultation(
            db,
            consultation_id=uuid.UUID(consult_id),
            coordinator_id=coord.id,
            slot_id=slot.id,
        )
    await db.flush()
    return consult_id, str(payment.id)


# ── RBAC matrix — unauthenticated / wrong-role ────────────────────────────────


async def test_list_consultations_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/v1/clinic/patient/consultations")
    assert resp.status_code == 401


async def test_list_consultations_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/consultations",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 403


async def test_get_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(f"/v1/clinic/patient/consultations/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_get_consultation_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}",
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 403


async def test_request_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={"condition_category": "thyroid"},
    )
    assert resp.status_code == 401


async def test_request_consultation_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={"condition_category": "thyroid"},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 403


async def test_cancel_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/cancel",
        json={"reason": "changed mind"},
    )
    assert resp.status_code == 401


async def test_confirm_payment_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}/confirm-payment",
        json={
            "razorpay_payment_id": "pay_xxx",
            "razorpay_order_id": "order_xxx",
            "razorpay_signature": "sig_xxx",
        },
    )
    assert resp.status_code == 401


async def test_list_slots_no_auth_returns_401(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    resp = await client.get(
        "/v1/clinic/patient/consultations/slots",
        params={
            "doctor_id": str(uuid.uuid4()),
            "date_from": now.isoformat(),
            "date_to": (now + timedelta(days=7)).isoformat(),
        },
    )
    assert resp.status_code == 401


# ── Request flow (patient submits, no doctor/slot/payment) ─────────────────────


async def test_request_consultation_happy_path(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    await _create_patient_profile(db_session, patient_user.id)

    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={
            "condition_category": "thyroid",
            "requirement_notes": "Tired and gaining weight.",
            "preferred_time_window": "weekday_morning",
        },
        headers=make_auth_headers(patient_user),
    )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    # A request has no doctor, slot, fee, or payment yet.
    assert data["status"] == "requested"
    assert data["condition_category"] == "thyroid"
    assert data["requirement_notes"] == "Tired and gaining weight."
    assert data["preferred_time_window"] == "weekday_morning"
    assert "payment" not in data

    # The row is persisted with no doctor assigned.
    consultation = await db_session.get(Consultation, uuid.UUID(data["consultation_id"]))
    assert consultation is not None
    assert consultation.doctor_id is None
    assert consultation.scheduled_start_at is None
    assert consultation.consultation_fee_paise is None
    assert consultation.status == ConsultationStatus.REQUESTED


async def test_request_consultation_ignores_doctor_selection(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A patient cannot choose a doctor — any doctor_id in the body is ignored."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)
    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)

    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={
            "condition_category": "thyroid",
            # Attempt to pick a specific doctor — must have no effect.
            "doctor_id": str(doctor.id),
        },
        headers=make_auth_headers(patient_user),
    )

    assert resp.status_code == 201, resp.text
    consultation = await db_session.get(
        Consultation, uuid.UUID(resp.json()["consultation_id"])
    )
    assert consultation is not None
    assert consultation.doctor_id is None


async def test_request_consultation_invalid_time_window_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    await _create_patient_profile(db_session, patient_user.id)

    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={"condition_category": "thyroid", "preferred_time_window": "whenever"},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 422


async def test_request_consultation_without_patient_profile_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Patient user without a kc_patients row cannot submit a request."""
    patient_user = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    # Intentionally skip _create_patient_profile

    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={"condition_category": "thyroid"},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 422


# ── Coordinator assignment (doctor + slot) ─────────────────────────────────────


async def test_coordinator_assign_consultation_happy_path(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    consult_id, _payment_id = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot
    )

    # The request is now scheduled with the assigned doctor, slot, and server fee.
    consultation = await db_session.get(Consultation, uuid.UUID(consult_id))
    assert consultation is not None
    assert consultation.status == ConsultationStatus.SCHEDULED
    assert consultation.doctor_id == doctor.id
    assert consultation.scheduled_start_at == slot.slot_start
    assert consultation.consultation_fee_paise == _FEE_PAISE
    assert consultation.payment_id is not None

    # Slot is now booked.
    loaded_slot = await db_session.get(Availability, slot.id)
    assert loaded_slot is not None
    assert loaded_slot.status == AvailabilityStatus.BOOKED

    # The patient sees the Razorpay order to pay on the detail endpoint.
    detail = await client.get(
        f"/v1/clinic/patient/consultations/{consult_id}",
        headers=make_auth_headers(patient_user),
    )
    assert detail.status_code == 200
    assert detail.json()["payment"]["razorpay_order_id"] == _STUB_ORDER_ID


async def test_assign_consultation_unassigned_patient_raises(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A coordinator cannot assign a request for a patient who isn't theirs."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    consult_id = await _request_consultation_api(client, patient_user)
    # Coordinator with NO patients assigned.
    coord_user = await create_coordinator_user(db_session)
    coord = Coordinator(user_id=coord_user.id, assigned_patient_ids=[])
    db_session.add(coord)
    await db_session.flush()

    import pytest

    with pytest.raises(consultation_service.ConsultationError) as exc:
        await consultation_service.assign_consultation(
            db_session,
            consultation_id=uuid.UUID(consult_id),
            coordinator_id=coord.id,
            slot_id=slot.id,
        )
    assert exc.value.code == "patient_not_assigned"


async def test_assign_consultation_inactive_doctor_raises(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    doctor.status = DoctorStatus.INACTIVE
    await db_session.flush()
    slot = await _create_slot(db_session, doctor)

    consult_id = await _request_consultation_api(client, patient_user)
    coord = await _create_coordinator_for_patient(db_session, patient_profile.id)

    import pytest

    with pytest.raises(consultation_service.ConsultationError) as exc:
        await consultation_service.assign_consultation(
            db_session,
            consultation_id=uuid.UUID(consult_id),
            coordinator_id=coord.id,
            slot_id=slot.id,
        )
    assert exc.value.code == "doctor_not_available"


# ── List consultations ─────────────────────────────────────────────────────────


async def test_list_consultations_empty_for_new_patient(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    resp = await client.get(
        "/v1/clinic/patient/consultations",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


# ── GET detail + cross-user 404 ────────────────────────────────────────────────


async def test_get_consultation_not_found_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    resp = await client.get(
        f"/v1/clinic/patient/consultations/{uuid.uuid4()}",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 404


async def test_cross_user_consultation_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Patient A cannot see Patient B's consultation — same 404 as non-existent."""
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_a, UserModel)
    assert isinstance(patient_b, UserModel)
    assert isinstance(doctor_user, UserModel)

    profile_b = await _create_patient_profile(db_session, patient_b.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)
    slot.status = AvailabilityStatus.BOOKED

    now = datetime.now(UTC)
    consultation = Consultation(
        patient_id=profile_b.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(hours=48),
        scheduled_end_at=now + timedelta(hours=48, minutes=20),
        consultation_fee_paise=_FEE_PAISE,
        status=ConsultationStatus.SCHEDULED,
    )
    db_session.add(consultation)
    await db_session.flush()

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}",
        headers=make_auth_headers(patient_a),
    )
    assert resp.status_code == 404

    # Denial must be audit-logged
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_a.id,
            AuditLog.action == "view_consultation",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"


# ── Confirm payment ────────────────────────────────────────────────────────────


async def test_confirm_payment_marks_consultation_confirmed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    # Request → coordinator assigns doctor + slot (creates the payment order).
    consult_id, payment_id = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot
    )

    # Mark payment as paid in DB to bypass Razorpay verification
    await payments_repo.update_payment(
        db_session, payment_id=uuid.UUID(payment_id), status=PaymentStatus.PAID
    )

    # Confirm with any signature (verify_payment_signature is skipped since payment already PAID)
    confirm_resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/confirm-payment",
        json={
            "razorpay_payment_id": _STUB_PAYMENT_ID,
            "razorpay_order_id": _STUB_ORDER_ID,
            "razorpay_signature": "irrelevant_already_paid",
        },
        headers=make_auth_headers(patient_user),
    )
    assert confirm_resp.status_code == 200, confirm_resp.text
    assert confirm_resp.json()["status"] == "confirmed"


# ── Cancellation ───────────────────────────────────────────────────────────────


async def test_cancel_consultation_with_refund(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Cancellation > 24 h before slot triggers a refund."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor, hours_from_now=48)  # > 24 h away

    consult_id, payment_id = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot
    )

    # Mark payment as paid so refund path is exercised
    await payments_repo.update_payment(
        db_session, payment_id=uuid.UUID(payment_id), status=PaymentStatus.PAID,
        razorpay_payment_id=_STUB_PAYMENT_ID,
    )

    with patch(
        "app.integrations.razorpay.initiate_refund",
        new_callable=AsyncMock,
        return_value={"id": "rfnd_STUB001", "status": "processed"},
    ):
        cancel_resp = await client.post(
            f"/v1/clinic/patient/consultations/{consult_id}/cancel",
            json={"reason": "schedule conflict"},
            headers=make_auth_headers(patient_user),
        )

    assert cancel_resp.status_code == 200, cancel_resp.text
    data = cancel_resp.json()
    assert data["status"] == "cancelled"
    assert data["refund_issued"] is True

    # Slot should be released
    loaded_slot = await db_session.get(Availability, slot.id)
    assert loaded_slot is not None
    assert loaded_slot.status == AvailabilityStatus.AVAILABLE


async def test_cancel_consultation_no_refund_within_window(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Cancellation ≤ 24 h before slot: cancels without refund."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor, hours_from_now=12)  # ≤ 24 h away

    consult_id, payment_id = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot
    )

    await payments_repo.update_payment(
        db_session, payment_id=uuid.UUID(payment_id), status=PaymentStatus.PAID,
        razorpay_payment_id=_STUB_PAYMENT_ID,
    )

    # Razorpay refund should NOT be called
    with patch(
        "app.integrations.razorpay.initiate_refund",
        new_callable=AsyncMock,
    ) as mock_refund:
        cancel_resp = await client.post(
            f"/v1/clinic/patient/consultations/{consult_id}/cancel",
            json={"reason": "emergency"},
            headers=make_auth_headers(patient_user),
        )
        mock_refund.assert_not_called()

    assert cancel_resp.status_code == 200, cancel_resp.text
    data = cancel_resp.json()
    assert data["status"] == "cancelled"
    assert data["refund_issued"] is False


async def test_cancel_already_cancelled_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    consult_id, _ = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot
    )

    # First cancellation
    await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/cancel",
        json={"reason": "first cancel"},
        headers=make_auth_headers(patient_user),
    )

    # Second cancellation on an already-cancelled consultation
    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/cancel",
        json={"reason": "again"},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 400


async def test_patient_can_withdraw_requested_consultation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A patient may cancel (withdraw) a not-yet-assigned request — no refund path."""
    patient_user = await create_patient_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    await _create_patient_profile(db_session, patient_user.id)

    consult_id = await _request_consultation_api(client, patient_user)

    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/cancel",
        json={"reason": "no longer needed"},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["refund_issued"] is False


# ── Rescheduling ───────────────────────────────────────────────────────────────


async def test_reschedule_consultation_happy_path(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Reschedule > 24 h out to another open slot with the same doctor."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot_a = await _create_slot(db_session, doctor, hours_from_now=48)
    slot_b = await _create_slot(db_session, doctor, hours_from_now=72)

    consult_id, _ = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot_a
    )

    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/reschedule",
        json={"slot_id": str(slot_b.id)},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["consultation_id"] == consult_id
    assert data["scheduled_start_at"][:19] == slot_b.slot_start.isoformat()[:19]

    # Old slot released, new slot claimed
    loaded_a = await db_session.get(Availability, slot_a.id)
    loaded_b = await db_session.get(Availability, slot_b.id)
    assert loaded_a is not None and loaded_a.status == AvailabilityStatus.AVAILABLE
    assert loaded_b is not None and loaded_b.status == AvailabilityStatus.BOOKED


async def test_reschedule_cross_user_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Patient A cannot reschedule Patient B's consultation — 404, denial audited."""
    patient_a = await create_patient_user(db_session)
    patient_b = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_a, UserModel)
    assert isinstance(patient_b, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile_b = await _create_patient_profile(db_session, patient_b.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot_a = await _create_slot(db_session, doctor, hours_from_now=48)
    slot_b = await _create_slot(db_session, doctor, hours_from_now=72)

    consult_id, _ = await _request_and_assign(
        client, db_session, patient_b, patient_profile_b, doctor, slot_a
    )

    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/reschedule",
        json={"slot_id": str(slot_b.id)},
        headers=make_auth_headers(patient_a),
    )
    assert resp.status_code == 404

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_a.id,
            AuditLog.action == "reschedule_consultation",
            AuditLog.allowed == False,  # noqa: E712
        )
    )
    assert audit is not None
    assert audit.reason == "consultation_not_found"


async def test_reschedule_within_window_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Reschedule ≤ 24 h before slot is rejected."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot_a = await _create_slot(db_session, doctor, hours_from_now=12)  # ≤ 24 h away
    slot_b = await _create_slot(db_session, doctor, hours_from_now=72)

    consult_id, _ = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot_a
    )

    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/reschedule",
        json={"slot_id": str(slot_b.id)},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "reschedule_window_closed"


async def test_reschedule_to_other_doctor_slot_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The target slot must belong to the consultation's existing doctor."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    other_doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)
    assert isinstance(other_doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    other_doctor = await _create_doctor_profile(db_session, other_doctor_user.id)
    slot_a = await _create_slot(db_session, doctor, hours_from_now=48)
    foreign_slot = await _create_slot(db_session, other_doctor, hours_from_now=72)

    consult_id, _ = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot_a
    )

    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/reschedule",
        json={"slot_id": str(foreign_slot.id)},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "slot_wrong_doctor"


async def test_reschedule_to_taken_slot_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A slot already booked cannot be claimed by a reschedule."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot_a = await _create_slot(db_session, doctor, hours_from_now=48)
    slot_b = await _create_slot(db_session, doctor, hours_from_now=72)
    slot_b.status = AvailabilityStatus.BOOKED
    await db_session.flush()

    consult_id, _ = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot_a
    )

    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/reschedule",
        json={"slot_id": str(slot_b.id)},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "slot_not_available"


async def test_reschedule_cancelled_consultation_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A cancelled consultation can no longer be rescheduled."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient_profile = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot_a = await _create_slot(db_session, doctor, hours_from_now=48)
    slot_b = await _create_slot(db_session, doctor, hours_from_now=72)

    consult_id, _ = await _request_and_assign(
        client, db_session, patient_user, patient_profile, doctor, slot_a
    )
    await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/cancel",
        json={"reason": "cancel first"},
        headers=make_auth_headers(patient_user),
    )

    resp = await client.post(
        f"/v1/clinic/patient/consultations/{consult_id}/reschedule",
        json={"slot_id": str(slot_b.id)},
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "consultation_not_reschedulable"


# ── Slot listing ───────────────────────────────────────────────────────────────


async def test_list_available_slots_returns_open_slots(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    patient = await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot1 = await _create_slot(db_session, doctor, hours_from_now=24)
    slot2 = await _create_slot(db_session, doctor, hours_from_now=25)
    # slot2 is marked booked — should not appear
    slot2.status = AvailabilityStatus.BOOKED
    # Slot listing is gated on the patient having a non-terminal consultation with
    # this doctor (no open doctor-shopping). Link them via a scheduled consult.
    now = datetime.now(UTC)
    db_session.add(
        Consultation(
            patient_id=patient.id,
            doctor_id=doctor.id,
            condition_category="thyroid",
            consultation_type="initial",
            scheduled_start_at=now + timedelta(days=2),
            scheduled_end_at=now + timedelta(days=2, minutes=20),
            consultation_fee_paise=_FEE_PAISE,
            status=ConsultationStatus.SCHEDULED,
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/v1/clinic/patient/consultations/slots",
        params={
            "doctor_id": str(doctor.id),
            "date_from": now.isoformat(),
            "date_to": (now + timedelta(days=7)).isoformat(),
        },
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert str(slot1.id) in ids
    assert str(slot2.id) not in ids




async def test_get_consultation_includes_assigned_doctor_name(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Once a coordinator assigns a doctor, the patient sees the doctor's name
    and specialty — not just an opaque doctor_id."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    patient = await _create_patient_profile(db_session, patient_user.id)

    doctor_user = await create_doctor_user(db_session)
    assert isinstance(doctor_user, UserModel)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)

    now = datetime.now(UTC)
    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        condition_category="thyroid",
        consultation_type="initial",
        scheduled_start_at=now + timedelta(days=2),
        scheduled_end_at=now + timedelta(days=2, minutes=20),
        consultation_fee_paise=_FEE_PAISE,
        status=ConsultationStatus.SCHEDULED,
    )
    db_session.add(consultation)
    await db_session.flush()

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["doctor_name"] == doctor_user.name
    assert data["doctor_specialty"] == ["endocrinologist"]


async def test_requested_consultation_has_no_doctor_name(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A request with no doctor yet exposes null doctor display fields."""
    from app.models.identity import User as UserModel

    patient_user = await create_patient_user(db_session)
    assert isinstance(patient_user, UserModel)
    patient = await _create_patient_profile(db_session, patient_user.id)

    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=None,
        condition_category="thyroid",
        consultation_type="initial",
        status=ConsultationStatus.REQUESTED,
    )
    db_session.add(consultation)
    await db_session.flush()

    resp = await client.get(
        f"/v1/clinic/patient/consultations/{consultation.id}",
        headers=make_auth_headers(patient_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["doctor_name"] is None
    assert data["doctor_specialty"] is None
