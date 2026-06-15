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
from app.models.audit import AuditLog
from app.models.clinic import Consultation, Patient
from app.models.doctor import Availability, Doctor
from app.repositories import payments as payments_repo
from tests.conftest import (
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


async def test_book_consultation_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={
            "doctor_id": str(uuid.uuid4()),
            "slot_id": str(uuid.uuid4()),
            "condition_category": "thyroid",
            "consultation_fee_paise": _FEE_PAISE,
        },
    )
    assert resp.status_code == 401


async def test_book_consultation_doctor_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor_user = await create_doctor_user(db_session)
    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={
            "doctor_id": str(uuid.uuid4()),
            "slot_id": str(uuid.uuid4()),
            "condition_category": "thyroid",
            "consultation_fee_paise": _FEE_PAISE,
        },
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


# ── Happy-path booking flow ────────────────────────────────────────────────────


async def test_book_consultation_happy_path(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Setup
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    with patch(
        "app.integrations.razorpay.create_order",
        new_callable=AsyncMock,
        return_value={"id": _STUB_ORDER_ID, "amount": _FEE_PAISE, "currency": "INR"},
    ):
        resp = await client.post(
            "/v1/clinic/patient/consultations",
            json={
                "doctor_id": str(doctor.id),
                "slot_id": str(slot.id),
                "condition_category": "thyroid",
                # Client attempts to set a bogus fee — must be ignored server-side.
                "consultation_fee_paise": 1,
            },
            headers=make_auth_headers(patient_user),
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["condition_category"] == "thyroid"
    # Fee is the server-authoritative value, not the client's "1".
    assert data["consultation_fee_paise"] == _FEE_PAISE
    assert data["payment"]["razorpay_order_id"] == _STUB_ORDER_ID

    # Slot must now be booked
    loaded_slot = await db_session.get(Availability, slot.id)
    assert loaded_slot is not None
    assert loaded_slot.status == AvailabilityStatus.BOOKED


async def test_book_consultation_unavailable_slot_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    # Pre-mark the slot as booked
    slot.status = AvailabilityStatus.BOOKED
    await db_session.flush()

    with patch(
        "app.integrations.razorpay.create_order",
        new_callable=AsyncMock,
        return_value={"id": _STUB_ORDER_ID, "amount": _FEE_PAISE, "currency": "INR"},
    ):
        resp = await client.post(
            "/v1/clinic/patient/consultations",
            json={
                "doctor_id": str(doctor.id),
                "slot_id": str(slot.id),
                "condition_category": "thyroid",
                "consultation_fee_paise": _FEE_PAISE,
            },
            headers=make_auth_headers(patient_user),
        )

    assert resp.status_code == 409


async def test_book_consultation_inactive_doctor_returns_409_doctor_not_available(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """An unverified/inactive doctor cannot be assigned a consult — state precondition."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    doctor.status = DoctorStatus.INACTIVE
    await db_session.flush()
    slot = await _create_slot(db_session, doctor)

    resp = await client.post(
        "/v1/clinic/patient/consultations",
        json={
            "doctor_id": str(doctor.id),
            "slot_id": str(slot.id),
            "condition_category": "thyroid",
            "consultation_fee_paise": _FEE_PAISE,
        },
        headers=make_auth_headers(patient_user),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "doctor_not_available"


async def test_book_consultation_without_patient_profile_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Patient user without a kc_patients row cannot book."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    # Intentionally skip _create_patient_profile
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    with patch(
        "app.integrations.razorpay.create_order",
        new_callable=AsyncMock,
        return_value={"id": _STUB_ORDER_ID, "amount": _FEE_PAISE, "currency": "INR"},
    ):
        resp = await client.post(
            "/v1/clinic/patient/consultations",
            json={
                "doctor_id": str(doctor.id),
                "slot_id": str(slot.id),
                "condition_category": "thyroid",
                "consultation_fee_paise": _FEE_PAISE,
            },
            headers=make_auth_headers(patient_user),
        )

    assert resp.status_code == 422


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

    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    # Book first
    with patch(
        "app.integrations.razorpay.create_order",
        new_callable=AsyncMock,
        return_value={"id": _STUB_ORDER_ID, "amount": _FEE_PAISE, "currency": "INR"},
    ):
        book_resp = await client.post(
            "/v1/clinic/patient/consultations",
            json={
                "doctor_id": str(doctor.id),
                "slot_id": str(slot.id),
                "condition_category": "thyroid",
                "consultation_fee_paise": _FEE_PAISE,
            },
            headers=make_auth_headers(patient_user),
        )
    assert book_resp.status_code == 201
    consult_id = book_resp.json()["consultation_id"]

    # Mark payment as paid in DB to bypass Razorpay verification
    payment_id = book_resp.json()["payment"]["payment_id"]
    from app.repositories import payments as payments_repo

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


async def _book_consultation(
    client: AsyncClient,
    db_session: AsyncSession,
    patient_user: object,
    doctor: Doctor,
    slot: Availability,
) -> tuple[str, str]:
    """Helper: books a consultation and returns (consult_id, payment_id)."""
    with patch(
        "app.integrations.razorpay.create_order",
        new_callable=AsyncMock,
        return_value={"id": _STUB_ORDER_ID, "amount": _FEE_PAISE, "currency": "INR"},
    ):
        resp = await client.post(
            "/v1/clinic/patient/consultations",
            json={
                "doctor_id": str(doctor.id),
                "slot_id": str(slot.id),
                "condition_category": "thyroid",
                "consultation_fee_paise": _FEE_PAISE,
            },
            headers=make_auth_headers(patient_user),
        )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["consultation_id"], data["payment"]["payment_id"]


async def test_cancel_consultation_with_refund(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Cancellation > 24 h before slot triggers a refund."""
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor, hours_from_now=48)  # > 24 h away

    consult_id, payment_id = await _book_consultation(
        client, db_session, patient_user, doctor, slot
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

    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor, hours_from_now=12)  # ≤ 24 h away

    consult_id, payment_id = await _book_consultation(
        client, db_session, patient_user, doctor, slot
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

    await _create_patient_profile(db_session, patient_user.id)
    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot = await _create_slot(db_session, doctor)

    consult_id, _ = await _book_consultation(client, db_session, patient_user, doctor, slot)

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


# ── Slot listing ───────────────────────────────────────────────────────────────


async def test_list_available_slots_returns_open_slots(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient_user = await create_patient_user(db_session)
    doctor_user = await create_doctor_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(patient_user, UserModel)
    assert isinstance(doctor_user, UserModel)

    doctor = await _create_doctor_profile(db_session, doctor_user.id)
    slot1 = await _create_slot(db_session, doctor, hours_from_now=24)
    slot2 = await _create_slot(db_session, doctor, hours_from_now=25)
    # slot2 is marked booked — should not appear
    slot2.status = AvailabilityStatus.BOOKED
    await db_session.flush()

    now = datetime.now(UTC)
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


