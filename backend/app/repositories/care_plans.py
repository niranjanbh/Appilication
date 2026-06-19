"""Care plan repository.

All patient-scoped queries filter status IN ('active', 'completed') at the SQL
layer — draft care plans are NEVER visible to patients regardless of any
application-layer check.

Doctor-scoped queries are scoped by doctor_id (the dr_doctors.id, not users.id).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CarePlanItemCategory, CarePlanItemPriority, CarePlanStatus
from app.models.clinic import (
    CarePlan,
    CarePlanItem,
    Patient,
)

# ── Patient visibility set ─────────────────────────────────────────────────────

_PATIENT_VISIBLE = (CarePlanStatus.ACTIVE, CarePlanStatus.COMPLETED)


# ── Write helpers ──────────────────────────────────────────────────────────────


async def create_draft(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
    title: str,
    condition_category: str | None,
    goals: str | None,
    notes: str | None,
    items: list[dict[str, Any]],
) -> CarePlan:
    cp = CarePlan(
        consultation_id=consultation_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        title=title,
        status=CarePlanStatus.DRAFT,
        condition_category=condition_category,
        goals=goals,
        notes=notes,
        version=1,
    )
    db.add(cp)
    await db.flush()

    for idx, item in enumerate(items):
        db.add(_build_item(item, care_plan_id=cp.id, order_index=idx))

    await db.flush()
    return cp


def _build_item(
    item: dict[str, Any], *, care_plan_id: uuid.UUID, order_index: int
) -> CarePlanItem:
    return CarePlanItem(
        care_plan_id=care_plan_id,
        category=CarePlanItemCategory(item["category"]),
        title=item["title"],
        description=item.get("description"),
        frequency=item.get("frequency"),
        duration=item.get("duration"),
        priority=CarePlanItemPriority(item.get("priority") or "normal"),
        order_index=order_index,
    )


# ── Doctor-scoped reads ───────────────────────────────────────────────────────


async def get_for_doctor(
    db: AsyncSession,
    *,
    care_plan_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> CarePlan | None:
    result = await db.execute(
        select(CarePlan).where(
            CarePlan.id == care_plan_id,
            CarePlan.doctor_id == doctor_id,
        )
    )
    return result.scalar_one_or_none()


async def list_for_consultation_for_doctor(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> list[CarePlan]:
    result = await db.execute(
        select(CarePlan)
        .where(
            CarePlan.consultation_id == consultation_id,
            CarePlan.doctor_id == doctor_id,
        )
        .order_by(CarePlan.created_at.desc())
    )
    return list(result.scalars().all())


# ── Patient-scoped reads ──────────────────────────────────────────────────────


async def get_for_patient(
    db: AsyncSession,
    *,
    care_plan_id: uuid.UUID,
    patient_user_id: uuid.UUID,
) -> CarePlan | None:
    result = await db.execute(
        select(CarePlan)
        .join(Patient, Patient.id == CarePlan.patient_id)
        .where(
            CarePlan.id == care_plan_id,
            Patient.user_id == patient_user_id,
            CarePlan.status.in_(_PATIENT_VISIBLE),
        )
    )
    return result.scalar_one_or_none()


async def list_for_patient(
    db: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CarePlan], int]:
    base = (
        select(CarePlan)
        .join(Patient, Patient.id == CarePlan.patient_id)
        .where(
            Patient.user_id == patient_user_id,
            CarePlan.status.in_(_PATIENT_VISIBLE),
        )
        .order_by(CarePlan.activated_at.desc().nulls_last(), CarePlan.created_at.desc())
    )
    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.scalar(count_q)) or 0

    offset = (page - 1) * page_size
    rows_result = await db.execute(base.offset(offset).limit(page_size))
    return list(rows_result.scalars().all()), total


# ── Items ─────────────────────────────────────────────────────────────────────


async def list_items(
    db: AsyncSession,
    *,
    care_plan_id: uuid.UUID,
) -> list[CarePlanItem]:
    result = await db.execute(
        select(CarePlanItem)
        .where(CarePlanItem.care_plan_id == care_plan_id)
        .order_by(CarePlanItem.order_index)
    )
    return list(result.scalars().all())


# ── Draft mutations ───────────────────────────────────────────────────────────


async def update_draft(
    db: AsyncSession,
    *,
    care_plan_id: uuid.UUID,
    doctor_id: uuid.UUID,
    title: str | None,
    condition_category: str | None,
    goals: str | None,
    notes: str | None,
    items: list[dict[str, Any]] | None,
) -> CarePlan | None:
    cp = await get_for_doctor(db, care_plan_id=care_plan_id, doctor_id=doctor_id)
    if cp is None or cp.status != CarePlanStatus.DRAFT:
        return None

    if title is not None:
        cp.title = title
    if condition_category is not None:
        cp.condition_category = condition_category
    if goals is not None:
        cp.goals = goals
    if notes is not None:
        cp.notes = notes
    cp.updated_at = datetime.now(UTC)

    if items is not None:
        await db.execute(
            delete(CarePlanItem).where(CarePlanItem.care_plan_id == care_plan_id)
        )
        for idx, item in enumerate(items):
            db.add(_build_item(item, care_plan_id=cp.id, order_index=idx))

    await db.flush()
    return cp


# ── Status transitions ────────────────────────────────────────────────────────


async def activate(
    db: AsyncSession,
    *,
    care_plan_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> CarePlan | None:
    cp = await get_for_doctor(db, care_plan_id=care_plan_id, doctor_id=doctor_id)
    if cp is None or cp.status != CarePlanStatus.DRAFT:
        return None
    now = datetime.now(UTC)
    cp.status = CarePlanStatus.ACTIVE
    cp.activated_at = now
    if cp.valid_from is None:
        cp.valid_from = date.today()
    cp.updated_at = now
    await db.flush()
    return cp


async def complete(
    db: AsyncSession,
    *,
    care_plan_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> CarePlan | None:
    cp = await get_for_doctor(db, care_plan_id=care_plan_id, doctor_id=doctor_id)
    if cp is None or cp.status != CarePlanStatus.ACTIVE:
        return None
    now = datetime.now(UTC)
    cp.status = CarePlanStatus.COMPLETED
    cp.completed_at = now
    cp.updated_at = now
    await db.flush()
    return cp
