"""Doctor lab-report review endpoints.

GET   /v1/doctor/patients/{patient_id}/lab-reports              — list reports
GET   /v1/doctor/patients/{patient_id}/lab-reports/{report_id}  — single report
PATCH /v1/doctor/lab-reports/{report_id}/annotate               — annotate + flag

All endpoints scope to the requesting doctor's panel patients (cross-doctor 404).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import doctor_portal as dr_repo

router = APIRouter(tags=["doctor-lab-review"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class LabReportDoctorRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    lab_name: str | None
    report_date: date | None
    status: str
    original_filename: str
    parsed_json: dict[str, Any] | None
    ocr_confidence_avg: float | None
    doctor_reviewed_by_id: uuid.UUID | None
    doctor_commentary: dict[str, Any] | None
    patient_attention_flags: list[Any] | None
    created_at: datetime


class AnnotateRequest(BaseModel):
    commentary: dict[str, str] | None = None
    patient_attention_flags: list[str] | None = None


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


async def _resolve_doctor(db: DbSession, user: object) -> object:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")
    return row[0]


def _to_read(report: object) -> LabReportDoctorRead:
    from app.models.clinic import LabReport

    assert isinstance(report, LabReport)
    return LabReportDoctorRead(
        id=report.id,
        patient_id=report.patient_id,
        lab_name=report.lab_name,
        report_date=report.report_date,
        status=report.status.value if hasattr(report.status, "value") else str(report.status),
        original_filename=report.original_filename,
        parsed_json=report.parsed_json,
        ocr_confidence_avg=float(report.ocr_confidence_avg) if report.ocr_confidence_avg is not None else None,
        doctor_reviewed_by_id=report.doctor_reviewed_by_id,
        doctor_commentary=report.doctor_commentary,
        patient_attention_flags=list(report.patient_attention_flags) if report.patient_attention_flags else None,
        created_at=report.created_at,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get(
    "/patients/{patient_id}/lab-reports",
    response_model=list[LabReportDoctorRead],
)
async def list_patient_lab_reports(
    patient_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> list[LabReportDoctorRead]:
    from app.models.doctor import Doctor as DoctorModel

    ctx = _audit_ctx(request, user)
    doctor = await _resolve_doctor(db, user)
    assert isinstance(doctor, DoctorModel)

    reports = await dr_repo.list_patient_lab_reports(
        db, doctor_id=doctor.id, patient_id=patient_id
    )
    if not reports:
        # Could be empty panel or no reports — either way write a denied entry
        # only when the patient isn't on panel at all; omit for empty-but-valid.
        # We return an empty list rather than 404 for "no reports yet."
        pass

    await write_audit(
        db, ctx, action="list_patient_lab_reports",
        resource_type="lab_report", allowed=True,
        log_metadata={"patient_id": str(patient_id), "count": len(reports)},
    )
    return [_to_read(r) for r in reports]


@router.get(
    "/patients/{patient_id}/lab-reports/{report_id}",
    response_model=LabReportDoctorRead,
)
async def get_patient_lab_report(
    patient_id: uuid.UUID,
    report_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> LabReportDoctorRead:
    from app.models.doctor import Doctor as DoctorModel

    ctx = _audit_ctx(request, user)
    doctor = await _resolve_doctor(db, user)
    assert isinstance(doctor, DoctorModel)

    report = await dr_repo.get_patient_lab_report(
        db, doctor_id=doctor.id, patient_id=patient_id, report_id=report_id
    )
    if report is None:
        await write_audit(
            db, ctx, action="view_patient_lab_report",
            resource_type="lab_report", resource_id=report_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="view_patient_lab_report",
        resource_type="lab_report", resource_id=report_id, allowed=True,
    )
    return _to_read(report)


@router.patch(
    "/lab-reports/{report_id}/annotate",
    response_model=LabReportDoctorRead,
)
async def annotate_lab_report(
    report_id: uuid.UUID,
    body: AnnotateRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> LabReportDoctorRead:
    """Annotate a patient's lab report with commentary and/or attention flags.

    The report must belong to a patient on the doctor's panel.
    Body may contain `commentary` (dict biomarker→text) and/or
    `patient_attention_flags` (list of biomarker names).
    At least one field must be provided.
    """
    from app.models.doctor import Doctor as DoctorModel

    if body.commentary is None and body.patient_attention_flags is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of commentary or patient_attention_flags must be provided",
        )

    ctx = _audit_ctx(request, user)
    doctor = await _resolve_doctor(db, user)
    assert isinstance(doctor, DoctorModel)

    # We need patient_id for the scope check; fetch the report first.
    from sqlalchemy import select

    from app.models.clinic import LabReport
    raw = await db.execute(select(LabReport).where(LabReport.id == report_id))
    raw_report = raw.scalar_one_or_none()
    if raw_report is None:
        await write_audit(
            db, ctx, action="annotate_lab_report",
            resource_type="lab_report", resource_id=report_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    assert isinstance(raw_report, LabReport)
    updated = await dr_repo.annotate_lab_report(
        db,
        doctor_id=doctor.id,
        report_id=report_id,
        patient_id=raw_report.patient_id,
        commentary=body.commentary,
        flags=body.patient_attention_flags,
    )
    if updated is None:
        await write_audit(
            db, ctx, action="annotate_lab_report",
            resource_type="lab_report", resource_id=report_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="annotate_lab_report",
        resource_type="lab_report", resource_id=report_id, allowed=True,
    )
    return _to_read(updated)
