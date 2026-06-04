"""Doctor-facing pre-consultation report endpoints.

GET   /v1/doctor/consultations/{consultation_id}/pre-consult-report         — full view
PATCH /v1/doctor/consultations/{consultation_id}/pre-consult-report         — edit prep notes
POST  /v1/doctor/consultations/{consultation_id}/pre-consult-report/generate — on-demand trigger
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import consultations as consultations_repo
from app.repositories import pre_consult_reports as reports_repo

router = APIRouter(tags=["doctor-pre-consult-report"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class DoctorPreConsultReportRead(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID | None
    generated_at: datetime
    lab_summary: dict[str, Any] | None
    adherence_summary: dict[str, Any] | None
    wearable_summary: dict[str, Any] | None
    patient_flags: dict[str, Any] | None
    intake_responses: dict[str, Any] | None
    pdf_url: str | None
    doctor_notes_pre_consult: str | None
    doctor_reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class DoctorPreConsultReportUpdate(BaseModel):
    doctor_notes_pre_consult: str


class GenerateReportResponse(BaseModel):
    task_id: str
    status: str = "queued"


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


async def _resolve_doctor_id(db: DbSession, user: object) -> uuid.UUID:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    doctor = await consultations_repo.get_doctor_record(db, user_id=user.id)
    if doctor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
    return doctor.id


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get(
    "/consultations/{consultation_id}/pre-consult-report",
    response_model=DoctorPreConsultReportRead,
)
async def get_pre_consult_report(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> DoctorPreConsultReportRead:
    ctx = _audit_ctx(request, user)
    doctor_id = await _resolve_doctor_id(db, user)

    report = await reports_repo.get_for_doctor(
        db, consultation_id=consultation_id, doctor_id=doctor_id
    )

    if report is None:
        await write_audit(
            db, ctx,
            action="get_pre_consult_report",
            resource_type="pre_consult_report",
            resource_id=consultation_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="get_pre_consult_report",
        resource_type="pre_consult_report",
        resource_id=report.id,
        allowed=True,
    )
    return DoctorPreConsultReportRead.model_validate(report)


@router.patch(
    "/consultations/{consultation_id}/pre-consult-report",
    response_model=DoctorPreConsultReportRead,
)
async def update_doctor_prep_notes(
    consultation_id: uuid.UUID,
    body: DoctorPreConsultReportUpdate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> DoctorPreConsultReportRead:
    ctx = _audit_ctx(request, user)
    doctor_id = await _resolve_doctor_id(db, user)

    report = await reports_repo.get_for_doctor(
        db, consultation_id=consultation_id, doctor_id=doctor_id
    )

    if report is None:
        await write_audit(
            db, ctx,
            action="update_pre_consult_notes",
            resource_type="pre_consult_report",
            resource_id=consultation_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    updated = await reports_repo.update_doctor_notes(
        db, report_id=report.id, notes=body.doctor_notes_pre_consult
    )
    await write_audit(
        db, ctx,
        action="update_pre_consult_notes",
        resource_type="pre_consult_report",
        resource_id=report.id,
        allowed=True,
    )

    assert updated is not None
    return DoctorPreConsultReportRead.model_validate(updated)


@router.post(
    "/consultations/{consultation_id}/pre-consult-report/generate",
    response_model=GenerateReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_report_generation(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> GenerateReportResponse:
    """Enqueue an on-demand report generation task.  Returns immediately with task_id."""
    from app.tasks.report_tasks import generate_pre_consultation_report

    ctx = _audit_ctx(request, user)
    doctor_id = await _resolve_doctor_id(db, user)

    # Verify the consultation belongs to this doctor before enqueuing
    consultation = await consultations_repo.get_consultation_for_doctor(
        db, consultation_id=consultation_id, doctor_id=doctor_id
    )

    if consultation is None:
        await write_audit(
            db, ctx,
            action="trigger_pre_consult_report",
            resource_type="consultation",
            resource_id=consultation_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    task = generate_pre_consultation_report.apply_async(
        args=[str(consultation_id)],
        queue="reports",
    )

    await write_audit(
        db, ctx,
        action="trigger_pre_consult_report",
        resource_type="consultation",
        resource_id=consultation_id,
        allowed=True,
    )

    return GenerateReportResponse(task_id=task.id)
