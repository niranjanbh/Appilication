"""Integration tests for the doctor credentialing REST API (P38).

Tests: advance pipeline, invalid transitions, suspend, reactivate, credential verify.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_admin_user,
    create_doctor_user,
    create_super_admin_user,
    make_auth_headers,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


async def _create_doctor_with_status(db: AsyncSession, status: str) -> uuid.UUID:
    """Create a doctor profile at the given DoctorStatus. Returns doctor_id."""
    from app.db.enums import DoctorStatus
    from app.models.doctor import Doctor

    user = await create_doctor_user(db)
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    doctor = Doctor(
        user_id=user.id,
        nmc_registration_number=f"NMC{uuid.uuid4().hex[:8]}",
        status=DoctorStatus(status),
    )
    db.add(doctor)
    await db.flush()
    return doctor.id  # type: ignore[return-value]


async def _create_credential(db: AsyncSession, doctor_id: uuid.UUID) -> uuid.UUID:
    """Insert a Credential row for the given doctor."""
    from app.db.enums import CredentialType
    from app.models.doctor import Credential

    credential = Credential(
        doctor_id=doctor_id,
        credential_type=CredentialType.MBBS,
        institution="Test Medical College",
        year=2015,
    )
    db.add(credential)
    await db.flush()
    return credential.id  # type: ignore[return-value]


# ── Tests ──────────────────────────────────────────────────────────────────────


async def test_list_doctors(client: AsyncClient, db_session: AsyncSession) -> None:
    super_admin = await create_super_admin_user(db_session)
    response = await client.get(
        "/v1/admin/doctors", headers=make_auth_headers(super_admin)
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


async def test_advance_status_applied_to_documents_submitted(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    doctor_id = await _create_doctor_with_status(db_session, "applied")

    response = await client.post(
        f"/v1/admin/doctors/{doctor_id}/advance",
        json={"target_status": "documents_submitted"},
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "documents_submitted"


async def test_advance_full_pipeline(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    doctor_id = await _create_doctor_with_status(db_session, "applied")
    headers = make_auth_headers(super_admin)

    for target in ("documents_submitted", "verified", "onboarding", "active"):
        r = await client.post(
            f"/v1/admin/doctors/{doctor_id}/advance",
            json={"target_status": target},
            headers=headers,
        )
        assert r.status_code == 200, f"Failed at {target}: {r.json()}"
        assert r.json()["status"] == target


async def test_advance_invalid_transition_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    # Skip two steps — APPLIED → VERIFIED is invalid
    doctor_id = await _create_doctor_with_status(db_session, "applied")

    response = await client.post(
        f"/v1/admin/doctors/{doctor_id}/advance",
        json={"target_status": "verified"},
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "invalid_transition"


async def test_suspend_active_doctor(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    doctor_id = await _create_doctor_with_status(db_session, "active")

    response = await client.post(
        f"/v1/admin/doctors/{doctor_id}/suspend",
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "suspended"


async def test_suspend_from_invalid_status_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    # SUSPENDED → SUSPENDED is not allowed
    doctor_id = await _create_doctor_with_status(db_session, "suspended")

    response = await client.post(
        f"/v1/admin/doctors/{doctor_id}/suspend",
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 409


async def test_reactivate_suspended_doctor(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    doctor_id = await _create_doctor_with_status(db_session, "suspended")

    response = await client.post(
        f"/v1/admin/doctors/{doctor_id}/reactivate",
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"


async def test_credential_verify(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    from app.models.identity import User as UserModel

    assert isinstance(super_admin, UserModel)
    doctor_id = await _create_doctor_with_status(db_session, "verified")
    credential_id = await _create_credential(db_session, doctor_id)

    response = await client.post(
        f"/v1/admin/doctors/{doctor_id}/credentials/{credential_id}/verify",
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verified_by_admin_id"] == str(super_admin.id)


async def test_advance_requires_staff_manage(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Read-only admin (ADMIN role) cannot advance doctor status."""
    admin = await create_admin_user(db_session)
    doctor_id = await _create_doctor_with_status(db_session, "applied")

    response = await client.post(
        f"/v1/admin/doctors/{doctor_id}/advance",
        json={"target_status": "documents_submitted"},
        headers=make_auth_headers(admin),
    )
    assert response.status_code == 403


async def test_advance_nonexistent_doctor_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    fake_id = uuid.uuid4()

    response = await client.post(
        f"/v1/admin/doctors/{fake_id}/advance",
        json={"target_status": "documents_submitted"},
        headers=make_auth_headers(super_admin),
    )
    assert response.status_code == 404
