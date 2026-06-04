"""Patient-facing pre-consultation report endpoint.

GET /v1/clinic/patient/consultations/{consultation_id}/pre-consult-report

Information symmetry: patient sees identical content to doctor (lab summary,
adherence, wearable summary, patient flags).  The only doctor-only field is
doctor_notes_pre_consult — it is intentionally absent from this schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import pre_consult_reports as reports_repo

router = APIRouter(tags=["pre-consult-report"])


class PatientPreConsultReportRead(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID | None
    generated_at: datetime
    lab_summary: dict[str, Any] | None
    adherence_summary: dict[str, Any] | None
    wearable_summary: dict[str, Any] | None
    patient_flags: dict[str, Any] | None
    intake_responses: dict[str, Any] | None
    pdf_url: str | None

    model_config = {"from_attributes": True}


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


@router.get(
    "/consultations/{consultation_id}/pre-consult-report",
    response_model=PatientPreConsultReportRead,
)
async def get_pre_consult_report(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PatientPreConsultReportRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    report = await reports_repo.get_for_patient(
        db,
        consultation_id=consultation_id,
        patient_user_id=user.id,
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
    return PatientPreConsultReportRead.model_validate(report)
