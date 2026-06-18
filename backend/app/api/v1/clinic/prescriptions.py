"""Patient-facing prescription endpoints.

GET /v1/clinic/patient/prescriptions            — list (signed/dispensed only)
GET /v1/clinic/patient/prescriptions/{id}       — detail (cross-user → 404)
GET /v1/clinic/patient/prescriptions/{id}/pdf   — presigned S3 URL (signed only)

Draft prescriptions are NEVER visible: filtered at the repository SQL layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from app.models.clinic import Prescription

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import prescriptions as prescriptions_repo

router = APIRouter(tags=["patient-prescriptions"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────


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


class PatientPrescriptionRead(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    status: str
    signed_at: datetime | None
    version: int
    diagnosis_note: str | None
    general_instructions: str | None
    items: list[PrescriptionItemRead] = []


class PatientPrescriptionListResponse(BaseModel):
    items: list[PatientPrescriptionRead]
    total: int
    page: int
    page_size: int
    pages: int


class PrescriptionPdfResponse(BaseModel):
    download_url: str
    expires_in_seconds: int = 900


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


async def _to_read(db: DbSession, rx: Prescription) -> PatientPrescriptionRead:
    items = await prescriptions_repo.list_items(db, prescription_id=rx.id)
    return PatientPrescriptionRead(
        id=rx.id,
        consultation_id=rx.consultation_id,
        status=rx.status.value,
        signed_at=rx.signed_at,
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


@router.get("/prescriptions", response_model=PatientPrescriptionListResponse)
async def list_prescriptions(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PatientPrescriptionListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    prescriptions, total = await prescriptions_repo.list_for_patient(
        db,
        patient_user_id=user.id,
        page=page,
        page_size=page_size,
    )

    await write_audit(db, ctx, action="list_prescriptions", allowed=True)

    items = []
    for rx in prescriptions:
        items.append(await _to_read(db, rx))

    return PatientPrescriptionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if page_size else 0,
    )


@router.get("/prescriptions/{prescription_id}", response_model=PatientPrescriptionRead)
async def get_prescription(
    prescription_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PatientPrescriptionRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    rx = await prescriptions_repo.get_for_patient(
        db,
        prescription_id=prescription_id,
        patient_user_id=user.id,
    )

    if rx is None:
        await write_audit(
            db, ctx,
            action="view_prescription",
            resource_type="prescription",
            resource_id=prescription_id,
            allowed=False,
            reason="not_own_or_not_found_or_draft",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="view_prescription",
        resource_type="prescription",
        resource_id=prescription_id,
        allowed=True,
    )

    return await _to_read(db, rx)


@router.get(
    "/prescriptions/{prescription_id}/pdf",
    response_model=PrescriptionPdfResponse,
)
async def get_prescription_pdf_url(
    prescription_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PrescriptionPdfResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    rx = await prescriptions_repo.get_for_patient(
        db,
        prescription_id=prescription_id,
        patient_user_id=user.id,
    )

    if rx is None:
        await write_audit(
            db, ctx,
            action="download_prescription_pdf",
            resource_type="prescription",
            resource_id=prescription_id,
            allowed=False,
            reason="not_own_or_not_found_or_draft",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    if not rx.pdf_url:
        await write_audit(
            db, ctx,
            action="download_prescription_pdf",
            resource_type="prescription",
            resource_id=prescription_id,
            allowed=False,
            reason="pdf_not_yet_generated",
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="PDF not yet generated. Please try again shortly.",
        )

    await write_audit(
        db, ctx,
        action="download_prescription_pdf",
        resource_type="prescription",
        resource_id=prescription_id,
        allowed=True,
    )

    # Generate pre-signed URL from the S3 key stored in pdf_url
    presigned = _generate_presigned_url(rx.pdf_url)
    return PrescriptionPdfResponse(download_url=presigned)


def _generate_presigned_url(pdf_url: str) -> str:
    """Convert s3://bucket/key to a presigned HTTPS URL (sync boto3)."""
    from app.core.config import settings
    from app.integrations.s3 import _s3_client

    if pdf_url.startswith("s3://"):
        parts = pdf_url[5:].split("/", 1)
        key = parts[1] if len(parts) > 1 else ""
    else:
        key = pdf_url

    client = _s3_client()
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=900,
    )
    return url
