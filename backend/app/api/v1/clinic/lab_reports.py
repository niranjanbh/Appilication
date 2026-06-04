"""Lab report endpoints — patient-scoped upload, download, and correction.

Upload flow:
  POST /initiate-upload  → presigned S3 PUT URL
  (client uploads directly to S3)
  POST /{id}/finalize    → HEAD-verify, set ocr_pending, dispatch Celery
  GET  /{id}/download    → 10-min presigned GET URL

Mutation:
  PATCH /{id}            → patient correction of OCR output

Queries:
  GET  /                 → paginated list (newest first)
  GET  /{id}             → single report (cross-user 404)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.integrations.s3 import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE_BYTES
from app.repositories import lab_reports as lab_reports_repo
from app.services import lab_report_service

router = APIRouter(tags=["lab-reports"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────


class InitiateUploadRequest(BaseModel):
    original_filename: str
    content_type: str
    file_size_bytes: int

    @field_validator("content_type")
    @classmethod
    def _validate_content_type(cls, v: str) -> str:
        if v not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}")
        return v

    @field_validator("file_size_bytes")
    @classmethod
    def _validate_size(cls, v: int) -> int:
        if v <= 0 or v > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"file_size_bytes must be between 1 and {MAX_FILE_SIZE_BYTES}")
        return v


class InitiateUploadResponse(BaseModel):
    lab_report_id: uuid.UUID
    upload_url: str
    fields: dict[str, str]
    s3_key: str
    content_type: str


class FinalizeUploadResponse(BaseModel):
    lab_report_id: uuid.UUID
    status: str
    ocr_task_id: str | None


class LabReportRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    source: str
    lab_name: str | None
    report_date: date | None
    original_filename: str
    content_type: str
    file_size_bytes: int
    status: str
    ocr_confidence_avg: float | None
    low_confidence_fields: list[str] | None
    patient_corrected: bool
    parsed_json: dict[str, Any] | None
    doctor_commentary: dict[str, Any] | None
    patient_attention_flags: list[Any] | None
    created_at: datetime
    updated_at: datetime


class LabReportListResponse(BaseModel):
    items: list[LabReportRead]
    total: int
    page: int
    page_size: int


class PatientCorrectionRequest(BaseModel):
    parsed_json: dict[str, Any]


class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in_seconds: int = 600


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


async def _get_patient_profile(db: DbSession, user_id: uuid.UUID) -> Any:
    """Return the kc_patients row for a given users.id."""
    from sqlalchemy import select

    from app.models.clinic import Patient

    result = await db.execute(select(Patient).where(Patient.user_id == user_id))
    return result.scalar_one_or_none()


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/lab-reports/initiate-upload",
    response_model=InitiateUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def initiate_upload(
    body: InitiateUploadRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> InitiateUploadResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    patient = await _get_patient_profile(db, user.id)
    if patient is None:
        await write_audit(
            db, ctx,
            action="initiate_lab_report_upload",
            allowed=False,
            reason="patient_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    result = await lab_report_service.initiate_upload(
        db,
        patient_user_id=user.id,
        patient_id=patient.id,
        original_filename=body.original_filename,
        content_type=body.content_type,
        file_size_bytes=body.file_size_bytes,
    )

    await write_audit(
        db, ctx,
        action="initiate_lab_report_upload",
        resource_type="lab_report",
        resource_id=result["lab_report_id"],
        allowed=True,
    )

    return InitiateUploadResponse(
        lab_report_id=result["lab_report_id"],
        upload_url=result["upload_url"],
        fields=result["fields"],
        s3_key=result["s3_key"],
        content_type=result["content_type"],
    )


@router.post(
    "/lab-reports/{lab_report_id}/finalize",
    response_model=FinalizeUploadResponse,
)
async def finalize_upload(
    lab_report_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> FinalizeUploadResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        result = await lab_report_service.finalize_upload(
            db,
            lab_report_id=lab_report_id,
            patient_user_id=user.id,
        )
    except lab_report_service.LabReportValidationError as exc:
        await write_audit(
            db, ctx,
            action="finalize_lab_report_upload",
            resource_type="lab_report",
            resource_id=lab_report_id,
            allowed=False,
            reason=str(exc),
        )
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if result.get("not_found"):
        await write_audit(
            db, ctx,
            action="finalize_lab_report_upload",
            resource_type="lab_report",
            resource_id=lab_report_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="finalize_lab_report_upload",
        resource_type="lab_report",
        resource_id=lab_report_id,
        allowed=True,
    )

    return FinalizeUploadResponse(
        lab_report_id=result["lab_report_id"],
        status=str(result["status"]),
        ocr_task_id=result.get("ocr_task_id"),
    )


@router.get("/lab-reports", response_model=LabReportListResponse)
async def list_lab_reports(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> LabReportListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    reports, total = await lab_reports_repo.list_for_patient(
        db,
        patient_user_id=user.id,
        page=page,
        page_size=page_size,
    )

    await write_audit(
        db, ctx,
        action="list_lab_reports",
        allowed=True,
    )

    return LabReportListResponse(
        items=[_to_read(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/lab-reports/{lab_report_id}", response_model=LabReportRead)
async def get_lab_report(
    lab_report_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> LabReportRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    report = await lab_reports_repo.get_for_patient(
        db,
        lab_report_id=lab_report_id,
        patient_user_id=user.id,
    )

    if report is None:
        await write_audit(
            db, ctx,
            action="view_lab_report",
            resource_type="lab_report",
            resource_id=lab_report_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="view_lab_report",
        resource_type="lab_report",
        resource_id=lab_report_id,
        allowed=True,
    )

    return _to_read(report)


@router.patch("/lab-reports/{lab_report_id}", response_model=LabReportRead)
async def correct_lab_report(
    lab_report_id: uuid.UUID,
    body: PatientCorrectionRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> LabReportRead:
    """Allow patient to correct OCR-parsed biomarker data."""
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    report = await lab_reports_repo.apply_patient_correction(
        db,
        lab_report_id=lab_report_id,
        patient_user_id=user.id,
        parsed_json=body.parsed_json,
    )

    if report is None:
        await write_audit(
            db, ctx,
            action="correct_lab_report",
            resource_type="lab_report",
            resource_id=lab_report_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="correct_lab_report",
        resource_type="lab_report",
        resource_id=lab_report_id,
        allowed=True,
    )

    return _to_read(report)


@router.get("/lab-reports/{lab_report_id}/download", response_model=DownloadUrlResponse)
async def download_lab_report(
    lab_report_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> DownloadUrlResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    url = await lab_report_service.get_download_url(
        db,
        lab_report_id=lab_report_id,
        patient_user_id=user.id,
    )

    if url is None:
        await write_audit(
            db, ctx,
            action="generate_download_url",
            resource_type="lab_report",
            resource_id=lab_report_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="generate_download_url",
        resource_type="lab_report",
        resource_id=lab_report_id,
        allowed=True,
    )

    return DownloadUrlResponse(download_url=url)


# ── Conversion helper ──────────────────────────────────────────────────────────


def _to_read(report: Any) -> LabReportRead:
    return LabReportRead(
        id=report.id,
        patient_id=report.patient_id,
        source=report.source,
        lab_name=report.lab_name,
        report_date=report.report_date,
        original_filename=report.original_filename,
        content_type=report.content_type,
        file_size_bytes=report.file_size_bytes,
        status=report.status,
        ocr_confidence_avg=float(report.ocr_confidence_avg) if report.ocr_confidence_avg is not None else None,
        low_confidence_fields=report.low_confidence_fields,
        patient_corrected=report.patient_corrected,
        parsed_json=report.parsed_json,
        doctor_commentary=report.doctor_commentary,
        patient_attention_flags=list(report.patient_attention_flags) if report.patient_attention_flags else None,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )
