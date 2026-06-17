"""Sign-off service — content review/publish state machine (P37).

Separation of duties:
  Doctor (CONTENT_APPROVE) → doctor_review()  — PENDING_REVIEW → APPROVED / REJECTED
  Admin  (CONTENT_PUBLISH)  → publish_content() — APPROVED → PUBLISHED
  Admin  (any admin level)  → submit_for_review() — DRAFT → PENDING_REVIEW
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education import EducationContent
from app.repositories import education as edu_repo
from app.repositories import sign_off as sign_off_repo


class SignOffError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_OWNERSHIP_CODES: frozenset[str] = frozenset(
    {"content_not_found", "doctor_profile_not_found"}
)


def _artifact_hash(content: EducationContent) -> str:
    """Pure — SHA-256 hex of the content snapshot at review time.

    Stored in ad_sign_off_records so the reviewer's attestation is tied to
    a specific version of the article, not just its UUID.
    """
    raw = f"{content.title}|{content.body_md or ''}|{content.content_url or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def submit_for_review(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
) -> EducationContent:
    """Transition DRAFT → PENDING_REVIEW.

    Returns the updated content. Raises SignOffError("content_not_found") if
    the content does not exist or is not in DRAFT status (ambiguous by design —
    prevents state enumeration).
    """
    content = await edu_repo.submit_for_review(db, content_id=content_id)
    if content is None:
        raise SignOffError("content_not_found")
    return content


async def doctor_review(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
    doctor_user_id: uuid.UUID,
    action: Literal["approved", "rejected"],
    notes: str | None,
) -> EducationContent:
    """Transition PENDING_REVIEW → APPROVED or REJECTED, creating an immutable sign-off record.

    Raises:
      SignOffError("content_not_found")          — content does not exist
      SignOffError("doctor_profile_not_found")   — caller has no dr_doctors row
      SignOffError("content_not_pending_review") — wrong state for this transition
    """
    from sqlalchemy import select

    from app.models.doctor import Doctor

    # 1. Fetch content snapshot BEFORE state change (hash captures what was reviewed)
    content = await edu_repo.get_content_by_id(db, content_id=content_id, published_only=False)
    if content is None:
        raise SignOffError("content_not_found")

    # 2. Resolve doctor row for NMC registration number
    result = await db.execute(select(Doctor).where(Doctor.user_id == doctor_user_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise SignOffError("doctor_profile_not_found")

    artifact = _artifact_hash(content)

    # 3. Transition state
    if action == "approved":
        updated = await edu_repo.doctor_approve_content(
            db, content_id=content_id, doctor_id=doctor.id
        )
    else:
        updated = await edu_repo.reject_content(db, content_id=content_id)

    if updated is None:
        raise SignOffError("content_not_pending_review")

    # 4. Write immutable sign-off record
    await sign_off_repo.create_sign_off(
        db,
        content_id=content_id,
        doctor_id=doctor.id,
        nmc_registration_number=doctor.nmc_registration_number,
        artifact_hash=artifact,
        action=action,
        notes=notes,
    )

    return updated


async def publish_content(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
) -> EducationContent:
    """Transition APPROVED → PUBLISHED.

    Raises SignOffError("content_not_found_or_not_approved") if the content does
    not exist or has not been doctor-approved yet.
    """
    content = await edu_repo.publish_content(db, content_id=content_id)
    if content is None:
        raise SignOffError("content_not_found_or_not_approved")
    return content
