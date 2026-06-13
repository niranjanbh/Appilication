"""Doctor-facing prescription endpoints.

GET   /v1/doctor/consultations/{consultation_id}/prescriptions — list (drafts incl.)
POST  /v1/doctor/consultations/{consultation_id}/prescription  — create draft
PATCH /v1/doctor/prescriptions/{id}                            — edit draft
POST  /v1/doctor/prescriptions/{id}/sign                       — sign + enqueue PDF
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from app.models.clinic import Prescription

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.services import prescription_service

router = APIRouter(tags=["doctor-prescriptions"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────


class PrescriptionItemCreate(BaseModel):
    drug_generic_name: str
    drug_form: str
    dosage: str
    frequency: str
    duration_days: int | None = None
    instructions: str | None = None
    refill_allowed: bool = False

    @field_validator("drug_form")
    @classmethod
    def _validate_drug_form(cls, v: str) -> str:
        from app.db.enums import DrugForm
        valid = {e.value for e in DrugForm}
        if v not in valid:
            raise ValueError(f"drug_form must be one of: {', '.join(sorted(valid))}")
        return v


class CreatePrescriptionRequest(BaseModel):
    diagnosis_note: str | None = None
    general_instructions: str | None = None
    items: list[PrescriptionItemCreate]

    @field_validator("items")
    @classmethod
    def _validate_items(cls, v: list[PrescriptionItemCreate]) -> list[PrescriptionItemCreate]:
        if not v:
            raise ValueError("at least one medication item is required")
        return v


class UpdatePrescriptionRequest(BaseModel):
    """Draft edit. items omitted/None keeps existing lines; a list replaces them."""

    diagnosis_note: str | None = None
    general_instructions: str | None = None
    items: list[PrescriptionItemCreate] | None = None

    @field_validator("items")
    @classmethod
    def _validate_items(
        cls, v: list[PrescriptionItemCreate] | None
    ) -> list[PrescriptionItemCreate] | None:
        if v is not None and not v:
            raise ValueError("items must contain at least one medication when provided")
        return v


class PrescriptionItemRead(BaseModel):
    id: uuid.UUID
    drug_generic_name: str
    drug_form: str
    dosage: str
    frequency: str
    duration_days: int | None
    instructions: str | None
    refill_allowed: bool
    order_index: int


class PrescriptionRead(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    status: str
    signed_at: datetime | None
    pdf_url: str | None
    version: int
    diagnosis_note: str | None
    general_instructions: str | None
    items: list[PrescriptionItemRead] = []


# ── Helpers ────────────────────────────────────────────────────────────────────


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


async def _read_with_items(db: DbSession, rx: Prescription) -> PrescriptionRead:
    from app.repositories import prescriptions as rx_repo

    items = await rx_repo.list_items(db, prescription_id=rx.id)
    return PrescriptionRead(
        id=rx.id,
        consultation_id=rx.consultation_id,
        doctor_id=rx.doctor_id,
        patient_id=rx.patient_id,
        status=rx.status.value,
        signed_at=rx.signed_at,
        pdf_url=rx.pdf_url,
        version=rx.version,
        diagnosis_note=rx.diagnosis_note,
        general_instructions=rx.general_instructions,
        items=[
            PrescriptionItemRead(
                id=item.id,
                drug_generic_name=item.drug_generic_name,
                drug_form=item.drug_form.value,
                dosage=item.dosage,
                frequency=item.frequency,
                duration_days=item.duration_days,
                instructions=item.instructions,
                refill_allowed=item.refill_allowed,
                order_index=item.order_index,
            )
            for item in items
        ],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/consultations/{consultation_id}/prescriptions",
    response_model=list[PrescriptionRead],
)
async def list_consultation_prescriptions(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> list[PrescriptionRead]:
    """All prescriptions this doctor wrote for the consultation, drafts included.

    Doctor-scoped at the SQL layer: another doctor's consultation yields [].
    """
    from sqlalchemy import select

    from app.models.doctor import Doctor
    from app.models.identity import User as UserModel
    from app.repositories import prescriptions as rx_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    result = await db.execute(select(Doctor).where(Doctor.user_id == user.id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        await write_audit(
            db, ctx,
            action="list_prescriptions",
            resource_type="consultation",
            resource_id=consultation_id,
            allowed=False,
            reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    prescriptions = await rx_repo.list_for_consultation_for_doctor(
        db, consultation_id=consultation_id, doctor_id=doctor.id
    )
    await write_audit(
        db, ctx,
        action="list_prescriptions",
        resource_type="consultation",
        resource_id=consultation_id,
        allowed=True,
    )
    return [await _read_with_items(db, rx) for rx in prescriptions]


@router.post(
    "/consultations/{consultation_id}/prescription",
    response_model=PrescriptionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_prescription(
    consultation_id: uuid.UUID,
    body: CreatePrescriptionRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> PrescriptionRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        rx = await prescription_service.create_draft(
            db,
            doctor_user_id=user.id,
            consultation_id=consultation_id,
            diagnosis_note=body.diagnosis_note,
            general_instructions=body.general_instructions,
            items=[item.model_dump() for item in body.items],
        )
    except prescription_service.PrescriptionError as exc:
        reason = str(exc)
        await write_audit(
            db, ctx,
            action="create_prescription",
            resource_type="consultation",
            resource_id=consultation_id,
            allowed=False,
            reason=reason,
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found") from exc

    await write_audit(
        db, ctx,
        action="create_prescription",
        resource_type="prescription",
        resource_id=rx.id,
        allowed=True,
    )

    result = await _read_with_items(db, rx)
    return result


@router.patch(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionRead,
)
async def update_prescription(
    prescription_id: uuid.UUID,
    body: UpdatePrescriptionRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> PrescriptionRead:
    """Edit a draft prescription. Signed prescriptions are immutable — 404."""
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        rx = await prescription_service.update_draft(
            db,
            doctor_user_id=user.id,
            prescription_id=prescription_id,
            diagnosis_note=body.diagnosis_note,
            general_instructions=body.general_instructions,
            items=(
                [item.model_dump() for item in body.items]
                if body.items is not None
                else None
            ),
        )
    except prescription_service.PrescriptionError as exc:
        await write_audit(
            db, ctx,
            action="update_prescription",
            resource_type="prescription",
            resource_id=prescription_id,
            allowed=False,
            reason=str(exc),
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found") from exc

    await write_audit(
        db, ctx,
        action="update_prescription",
        resource_type="prescription",
        resource_id=prescription_id,
        allowed=True,
    )

    return await _read_with_items(db, rx)


@router.post(
    "/prescriptions/{prescription_id}/sign",
    response_model=PrescriptionRead,
)
async def sign_prescription(
    prescription_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> PrescriptionRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        rx = await prescription_service.sign_prescription(
            db,
            doctor_user_id=user.id,
            prescription_id=prescription_id,
        )
    except prescription_service.PrescriptionError as exc:
        reason = str(exc)
        await write_audit(
            db, ctx,
            action="sign_prescription",
            resource_type="prescription",
            resource_id=prescription_id,
            allowed=False,
            reason=reason,
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found") from exc

    await write_audit(
        db, ctx,
        action="sign_prescription",
        resource_type="prescription",
        resource_id=prescription_id,
        allowed=True,
    )

    # Fire-and-forget: generate PDF asynchronously
    from app.tasks.prescription_tasks import generate_prescription_pdf
    generate_prescription_pdf.apply_async(
        args=[str(prescription_id)],
        queue="reports",
    )

    return await _read_with_items(db, rx)
