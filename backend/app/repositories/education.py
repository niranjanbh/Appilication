"""Education content repository.

Patient-scoped functions take patient_user_id (users.id) not patient_id
to enforce the cross-user 404 pattern at the SQL layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ContentStatus
from app.models.clinic import Patient
from app.models.education import EducationAssignment, EducationContent

# ── Content library ───────────────────────────────────────────────────────────


async def list_published(
    db: AsyncSession,
    *,
    categories: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EducationContent], int]:
    base = select(EducationContent).where(
        EducationContent.status == ContentStatus.PUBLISHED
    )
    if categories:
        # ?| operator: JSONB array contains any element from a text array
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import ARRAY, TEXT

        base = base.where(
            EducationContent.condition_categories.op("?|")(
                cast(categories, ARRAY(TEXT))
            )
        )
    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total: int = count_result.scalar_one()
    offset = (page - 1) * page_size
    items_result = await db.execute(
        base.order_by(EducationContent.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(items_result.scalars().all()), total


async def get_content_by_id(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
    published_only: bool = True,
) -> EducationContent | None:
    stmt = select(EducationContent).where(EducationContent.id == content_id)
    if published_only:
        stmt = stmt.where(EducationContent.status == ContentStatus.PUBLISHED)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all_content(
    db: AsyncSession,
    *,
    status: ContentStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EducationContent], int]:
    base = select(EducationContent)
    if status is not None:
        base = base.where(EducationContent.status == status)
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()
    offset = (page - 1) * page_size
    items_result = await db.execute(
        base.order_by(EducationContent.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(items_result.scalars().all()), total


async def create_content(
    db: AsyncSession,
    *,
    title: str,
    slug: str,
    content_type: str,
    condition_categories: list[str],
    content_url: str | None,
    body_md: str | None,
    ai_disclosure: bool = False,
) -> EducationContent:
    from app.db.enums import ContentType

    content = EducationContent(
        title=title,
        slug=slug,
        content_type=ContentType(content_type),
        condition_categories=condition_categories,
        content_url=content_url,
        body_md=body_md,
        ai_disclosure=ai_disclosure,
        status=ContentStatus.DRAFT,
    )
    db.add(content)
    await db.flush()
    return content


async def approve_content(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> EducationContent | None:
    """Legacy: sets reviewed_by + status=PUBLISHED in one step. Use doctor_approve_content instead."""
    result = await db.execute(
        update(EducationContent)
        .where(EducationContent.id == content_id)
        .values(
            reviewed_by_doctor_id=doctor_id,
            reviewed_at=datetime.now(UTC),
            status=ContentStatus.PUBLISHED,
            updated_at=datetime.now(UTC),
        )
        .returning(EducationContent)
    )
    return result.scalar_one_or_none()


async def update_content_status(
    db: AsyncSession,
    content_id: uuid.UUID,
    new_status: ContentStatus,
) -> EducationContent | None:
    """Set content status (admin action: publish or archive)."""
    from datetime import UTC, datetime

    result = await db.execute(
        update(EducationContent)
        .where(EducationContent.id == content_id)
        .values(status=new_status, updated_at=datetime.now(UTC))
        .returning(EducationContent)
    )
    return result.scalar_one_or_none()


# ── State-machine transitions (P37) ──────────────────────────────────────────
# All functions filter on both id AND current status. Returning None means either
# "not found" or "wrong state" — caller raises the same 409/404 in both cases.


async def submit_for_review(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
) -> EducationContent | None:
    """DRAFT → PENDING_REVIEW."""
    result = await db.execute(
        update(EducationContent)
        .where(
            EducationContent.id == content_id,
            EducationContent.status == ContentStatus.DRAFT,
        )
        .values(status=ContentStatus.PENDING_REVIEW, updated_at=datetime.now(UTC))
        .returning(EducationContent)
    )
    return result.scalar_one_or_none()


async def doctor_approve_content(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> EducationContent | None:
    """PENDING_REVIEW → APPROVED, stamps reviewed_by_doctor_id for NMC audit trail."""
    result = await db.execute(
        update(EducationContent)
        .where(
            EducationContent.id == content_id,
            EducationContent.status == ContentStatus.PENDING_REVIEW,
        )
        .values(
            reviewed_by_doctor_id=doctor_id,
            reviewed_at=datetime.now(UTC),
            status=ContentStatus.APPROVED,
            updated_at=datetime.now(UTC),
        )
        .returning(EducationContent)
    )
    return result.scalar_one_or_none()


async def reject_content(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
) -> EducationContent | None:
    """PENDING_REVIEW → REJECTED."""
    result = await db.execute(
        update(EducationContent)
        .where(
            EducationContent.id == content_id,
            EducationContent.status == ContentStatus.PENDING_REVIEW,
        )
        .values(status=ContentStatus.REJECTED, updated_at=datetime.now(UTC))
        .returning(EducationContent)
    )
    return result.scalar_one_or_none()


async def publish_content(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
) -> EducationContent | None:
    """APPROVED → PUBLISHED."""
    result = await db.execute(
        update(EducationContent)
        .where(
            EducationContent.id == content_id,
            EducationContent.status == ContentStatus.APPROVED,
        )
        .values(status=ContentStatus.PUBLISHED, updated_at=datetime.now(UTC))
        .returning(EducationContent)
    )
    return result.scalar_one_or_none()


async def list_pending_review(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EducationContent], int]:
    """List all PENDING_REVIEW content, oldest first (review queue order)."""
    base = select(EducationContent).where(
        EducationContent.status == ContentStatus.PENDING_REVIEW
    )
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()
    offset = (page - 1) * page_size
    items_result = await db.execute(
        base.order_by(EducationContent.created_at.asc()).offset(offset).limit(page_size)
    )
    return list(items_result.scalars().all()), total


# ── Assignments ───────────────────────────────────────────────────────────────


async def list_assignments_for_patient(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
) -> list[tuple[EducationAssignment, EducationContent]]:
    """Return (assignment, content) pairs, ordered newest first."""
    result = await db.execute(
        select(EducationAssignment, EducationContent)
        .join(EducationContent, EducationContent.id == EducationAssignment.content_id)
        .join(Patient, Patient.id == EducationAssignment.patient_id)
        .where(Patient.user_id == patient_user_id)
        .order_by(EducationAssignment.created_at.desc())
    )
    rows = result.all()
    return [(row[0], row[1]) for row in rows]


async def get_assignment_for_patient(
    db: AsyncSession,
    *,
    assignment_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> EducationAssignment | None:
    """Cross-user safe."""
    result = await db.execute(
        select(EducationAssignment)
        .join(Patient, Patient.id == EducationAssignment.patient_id)
        .where(
            EducationAssignment.id == assignment_id,
            Patient.user_id == patient_user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_assignment(
    db: AsyncSession,
    *,
    content_id: uuid.UUID,
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    consultation_id: uuid.UUID | None,
    notes: str | None,
) -> EducationAssignment:
    assignment = EducationAssignment(
        content_id=content_id,
        patient_id=patient_id,
        assigned_by_doctor_id=doctor_id,
        consultation_id=consultation_id,
        notes=notes,
    )
    db.add(assignment)
    await db.flush()
    return assignment


async def mark_assignment_read(
    db: AsyncSession,
    *,
    assignment_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> EducationAssignment | None:
    """Sets read_at only if owned by this patient and not already read."""
    assignment = await get_assignment_for_patient(
        db, assignment_id=assignment_id, patient_user_id=patient_user_id
    )
    if assignment is None:
        return None
    if assignment.read_at is None:
        assignment.read_at = datetime.now(UTC)
        assignment.updated_at = datetime.now(UTC)
        await db.flush()
    return assignment
