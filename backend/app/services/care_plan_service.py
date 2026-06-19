"""Care plan service — create draft, update, activate, complete."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import CarePlan
from app.repositories import care_plans as care_plans_repo


class CarePlanError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_OWNERSHIP_CODES: frozenset[str] = frozenset(
    {
        "consultation_not_found_or_not_owned",
        "doctor_profile_not_found",
        "care_plan_not_found_or_not_draft",
        "care_plan_not_found_or_not_activatable",
        "care_plan_not_found_or_not_completable",
    }
)


async def _resolve_doctor(db: AsyncSession, doctor_user_id: uuid.UUID) -> Any:
    from sqlalchemy import select

    from app.models.doctor import Doctor

    result = await db.execute(select(Doctor).where(Doctor.user_id == doctor_user_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise CarePlanError("doctor_profile_not_found")
    return doctor


async def _resolve_consultation(
    db: AsyncSession, consultation_id: uuid.UUID, doctor_id: uuid.UUID
) -> Any:
    from sqlalchemy import select

    from app.models.clinic import Consultation

    result = await db.execute(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.doctor_id == doctor_id,
        )
    )
    consultation = result.scalar_one_or_none()
    if consultation is None:
        raise CarePlanError("consultation_not_found_or_not_owned")
    return consultation


async def create_draft(
    db: AsyncSession,
    *,
    doctor_user_id: uuid.UUID,
    consultation_id: uuid.UUID,
    title: str,
    condition_category: str | None,
    goals: str | None,
    notes: str | None,
    items: list[dict[str, Any]],
) -> CarePlan:
    doctor = await _resolve_doctor(db, doctor_user_id)
    consultation = await _resolve_consultation(db, consultation_id, doctor.id)

    return await care_plans_repo.create_draft(
        db,
        consultation_id=consultation_id,
        doctor_id=doctor.id,
        patient_id=consultation.patient_id,
        title=title,
        condition_category=condition_category,
        goals=goals,
        notes=notes,
        items=items,
    )


async def update_draft(
    db: AsyncSession,
    *,
    doctor_user_id: uuid.UUID,
    care_plan_id: uuid.UUID,
    title: str | None,
    condition_category: str | None,
    goals: str | None,
    notes: str | None,
    items: list[dict[str, Any]] | None,
) -> CarePlan:
    doctor = await _resolve_doctor(db, doctor_user_id)

    cp = await care_plans_repo.update_draft(
        db,
        care_plan_id=care_plan_id,
        doctor_id=doctor.id,
        title=title,
        condition_category=condition_category,
        goals=goals,
        notes=notes,
        items=items,
    )
    if cp is None:
        raise CarePlanError("care_plan_not_found_or_not_draft")
    return cp


async def activate_care_plan(
    db: AsyncSession,
    *,
    doctor_user_id: uuid.UUID,
    care_plan_id: uuid.UUID,
) -> CarePlan:
    doctor = await _resolve_doctor(db, doctor_user_id)

    cp = await care_plans_repo.activate(
        db, care_plan_id=care_plan_id, doctor_id=doctor.id
    )
    if cp is None:
        raise CarePlanError("care_plan_not_found_or_not_activatable")
    return cp


async def complete_care_plan(
    db: AsyncSession,
    *,
    doctor_user_id: uuid.UUID,
    care_plan_id: uuid.UUID,
) -> CarePlan:
    doctor = await _resolve_doctor(db, doctor_user_id)

    cp = await care_plans_repo.complete(
        db, care_plan_id=care_plan_id, doctor_id=doctor.id
    )
    if cp is None:
        raise CarePlanError("care_plan_not_found_or_not_completable")
    return cp
