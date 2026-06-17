"""Integration tests for the content review/publish state machine (P37).

State transitions tested:
  DRAFT → submit-for-review → PENDING_REVIEW
  PENDING_REVIEW → doctor review (approve) → APPROVED
  PENDING_REVIEW → doctor review (reject)  → REJECTED
  APPROVED → admin publish → PUBLISHED
  wrong-state transitions → 409
  no doctor profile → 404
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_admin_user,
    create_doctor_with_profile,
    create_patient_user,
    create_super_admin_user,
    make_auth_headers,
)


# ── Fixture helpers ────────────────────────────────────────────────────────────


async def _create_draft_content(db: AsyncSession) -> uuid.UUID:
    """Insert a DRAFT content row directly and return its id."""
    from faker import Faker

    from app.db.enums import ContentStatus, ContentType
    from app.models.education import EducationContent

    fake = Faker()
    content = EducationContent(
        title=fake.sentence(nb_words=4),
        slug=f"test-{uuid.uuid4().hex[:8]}",
        content_type=ContentType.ARTICLE,
        condition_categories=["thyroid"],
        body_md="Some test body content.",
        status=ContentStatus.DRAFT,
        ai_disclosure=False,
    )
    db.add(content)
    await db.flush()
    return content.id


async def _create_pending_review_content(db: AsyncSession) -> uuid.UUID:
    """Insert a PENDING_REVIEW content row directly."""
    from faker import Faker

    from app.db.enums import ContentStatus, ContentType
    from app.models.education import EducationContent

    fake = Faker()
    content = EducationContent(
        title=fake.sentence(nb_words=4),
        slug=f"test-{uuid.uuid4().hex[:8]}",
        content_type=ContentType.ARTICLE,
        condition_categories=["pcos"],
        body_md="Pending review body.",
        status=ContentStatus.PENDING_REVIEW,
        ai_disclosure=False,
    )
    db.add(content)
    await db.flush()
    return content.id


async def _create_approved_content(db: AsyncSession, doctor_id: uuid.UUID) -> uuid.UUID:
    """Insert an APPROVED content row directly."""
    from datetime import UTC, datetime

    from faker import Faker

    from app.db.enums import ContentStatus, ContentType
    from app.models.education import EducationContent

    fake = Faker()
    content = EducationContent(
        title=fake.sentence(nb_words=4),
        slug=f"test-{uuid.uuid4().hex[:8]}",
        content_type=ContentType.ARTICLE,
        condition_categories=["weight"],
        body_md="Approved body.",
        status=ContentStatus.APPROVED,
        reviewed_by_doctor_id=doctor_id,
        reviewed_at=datetime.now(UTC),
        ai_disclosure=False,
    )
    db.add(content)
    await db.flush()
    return content.id


# ── submit-for-review ──────────────────────────────────────────────────────────


async def test_submit_for_review_transitions_draft_to_pending(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    content_id = await _create_draft_content(db_session)

    resp = await client.post(
        f"/v1/admin/content/{content_id}/submit-for-review",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_review"


async def test_submit_for_review_wrong_state_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    content_id = await _create_pending_review_content(db_session)

    resp = await client.post(
        f"/v1/admin/content/{content_id}/submit-for-review",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 409


async def test_submit_for_review_no_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(f"/v1/admin/content/{uuid.uuid4()}/submit-for-review")
    assert resp.status_code == 401


async def test_submit_for_review_patient_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await create_patient_user(db_session)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/submit-for-review",
        headers=make_auth_headers(patient),
    )
    assert resp.status_code == 403


# ── doctor review — approve ────────────────────────────────────────────────────


async def test_doctor_approve_transitions_to_approved(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    content_id = await _create_pending_review_content(db_session)

    resp = await client.post(
        f"/v1/doctor/content/{content_id}/review",
        json={"action": "approved", "notes": "Looks good."},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


async def test_doctor_approve_creates_sign_off_record(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.sign_off import SignOffRecord

    doctor = await create_doctor_with_profile(db_session)
    content_id = await _create_pending_review_content(db_session)

    resp = await client.post(
        f"/v1/doctor/content/{content_id}/review",
        json={"action": "approved"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        select(SignOffRecord).where(SignOffRecord.content_id == content_id)
    )
    record = result.scalar_one_or_none()
    assert record is not None
    assert record.action == "approved"
    assert len(record.artifact_hash) == 64


async def test_doctor_reject_transitions_to_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    content_id = await _create_pending_review_content(db_session)

    resp = await client.post(
        f"/v1/doctor/content/{content_id}/review",
        json={"action": "rejected", "notes": "Needs revision."},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


async def test_doctor_review_creates_sign_off_record_for_rejection(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.sign_off import SignOffRecord

    doctor = await create_doctor_with_profile(db_session)
    content_id = await _create_pending_review_content(db_session)

    await client.post(
        f"/v1/doctor/content/{content_id}/review",
        json={"action": "rejected", "notes": "Fix required."},
        headers=make_auth_headers(doctor),
    )

    result = await db_session.execute(
        select(SignOffRecord).where(SignOffRecord.content_id == content_id)
    )
    record = result.scalar_one_or_none()
    assert record is not None
    assert record.action == "rejected"
    assert record.notes == "Fix required."


async def test_doctor_review_wrong_state_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.db.enums import DoctorStatus
    from app.models.doctor import Doctor

    doctor_user = await create_doctor_with_profile(db_session)

    # Content in DRAFT state — not PENDING_REVIEW
    content_id = await _create_draft_content(db_session)

    resp = await client.post(
        f"/v1/doctor/content/{content_id}/review",
        json={"action": "approved"},
        headers=make_auth_headers(doctor_user),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "content_not_pending_review"


async def test_doctor_review_without_profile_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from tests.conftest import create_doctor_user

    doctor_no_profile = await create_doctor_user(db_session)
    content_id = await _create_pending_review_content(db_session)

    resp = await client.post(
        f"/v1/doctor/content/{content_id}/review",
        json={"action": "approved"},
        headers=make_auth_headers(doctor_no_profile),
    )
    assert resp.status_code == 404


# ── admin publish ──────────────────────────────────────────────────────────────


async def test_admin_publish_transitions_to_published(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    doctor = await create_doctor_with_profile(db_session)

    # Need a doctor_id for the approved content fixture
    from app.models.identity import User as UserModel
    assert isinstance(doctor, UserModel)
    from sqlalchemy import select as sa_select
    from app.models.doctor import Doctor
    result = await db_session.execute(sa_select(Doctor).where(Doctor.user_id == doctor.id))
    doctor_row = result.scalar_one()

    content_id = await _create_approved_content(db_session, doctor_row.id)

    resp = await client.post(
        f"/v1/admin/content/{content_id}/publish",
        headers=make_auth_headers(super_admin),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


async def test_admin_publish_wrong_state_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    super_admin = await create_super_admin_user(db_session)
    content_id = await _create_pending_review_content(db_session)

    resp = await client.post(
        f"/v1/admin/content/{content_id}/publish",
        headers=make_auth_headers(super_admin),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "content_not_found_or_not_approved"


async def test_admin_publish_read_only_admin_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    resp = await client.post(
        f"/v1/admin/content/{uuid.uuid4()}/publish",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 403


# ── full happy path ────────────────────────────────────────────────────────────


async def test_full_review_publish_happy_path(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_admin_user(db_session)
    super_admin = await create_super_admin_user(db_session)
    doctor = await create_doctor_with_profile(db_session)
    content_id = await _create_draft_content(db_session)

    # 1. Submit for review
    resp = await client.post(
        f"/v1/admin/content/{content_id}/submit-for-review",
        headers=make_auth_headers(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_review"

    # 2. Doctor approves
    resp = await client.post(
        f"/v1/doctor/content/{content_id}/review",
        json={"action": "approved"},
        headers=make_auth_headers(doctor),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # 3. Admin publishes
    resp = await client.post(
        f"/v1/admin/content/{content_id}/publish",
        headers=make_auth_headers(super_admin),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


# ── doctor content list ────────────────────────────────────────────────────────


async def test_doctor_can_list_pending_review_content(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await create_doctor_with_profile(db_session)
    await _create_pending_review_content(db_session)

    resp = await client.get("/v1/doctor/content", headers=make_auth_headers(doctor))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1
