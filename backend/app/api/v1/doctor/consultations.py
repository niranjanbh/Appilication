"""Doctor consultation list, detail, notes, and lab-order endpoints.

GET  /v1/doctor/consultations           — list with ?filter=today|upcoming|history
GET  /v1/doctor/consultations/{id}      — detail (cross-doctor 404)
POST /v1/doctor/consultations/{id}/notes     — append-only note (version-tracked)
POST /v1/doctor/consultations/{id}/lab-order — create lab order
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole, NoteType
from app.repositories import doctor_portal as dr_repo


def _ev(v: object) -> str:
    """Return enum value as string, tolerating already-string storage."""
    return v.value if hasattr(v, "value") else str(v)

router = APIRouter(tags=["doctor-consultations"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class DoctorConsultationSummary(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    kyros_patient_id: str
    condition_category: str
    consultation_type: str
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    status: str
    video_room_id: str | None


class DoctorConsultationDetail(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    kyros_patient_id: str
    condition_category: str
    consultation_type: str
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    status: str
    video_room_id: str | None
    consultation_fee_paise: int
    cancellation_reason: str | None
    recording_consent: bool
    created_at: datetime


class DoctorConsultationListResponse(BaseModel):
    items: list[DoctorConsultationSummary]
    total: int
    page: int
    page_size: int
    pages: int


class ConsultationCompleteResponse(BaseModel):
    id: uuid.UUID
    status: str
    actual_end_at: datetime | None


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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/consultations", response_model=DoctorConsultationListResponse)
async def list_my_consultations(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    filter: Literal["today", "upcoming", "history"] = Query(default="upcoming"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DoctorConsultationListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="list_own_consultations",
            resource_type="consultation", allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    triples, total = await dr_repo.list_doctor_consultations(
        db, doctor_id=doctor.id, filter_type=filter, page=page, page_size=page_size
    )

    await write_audit(
        db, ctx, action="list_own_consultations",
        resource_type="consultation", allowed=True,
    )

    pages = max(1, -(-total // page_size))
    return DoctorConsultationListResponse(
        items=[
            DoctorConsultationSummary(
                id=c.id,
                patient_id=pt.id,
                patient_name=u.name,
                kyros_patient_id=pt.kyros_patient_id,
                condition_category=c.condition_category,
                consultation_type=_ev(c.consultation_type),
                scheduled_start_at=c.scheduled_start_at,
                scheduled_end_at=c.scheduled_end_at,
                status=_ev(c.status),
                video_room_id=c.video_room_id,
            )
            for c, pt, u in triples
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/consultations/{consultation_id}", response_model=DoctorConsultationDetail)
async def get_my_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> DoctorConsultationDetail:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="view_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    row = await dr_repo.get_doctor_consultation_detail(
        db, doctor_id=doctor.id, consultation_id=consultation_id
    )
    if row is None:
        await write_audit(
            db, ctx, action="view_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    c, pt, u = row
    await write_audit(
        db, ctx, action="view_consultation",
        resource_type="consultation", resource_id=consultation_id, allowed=True,
    )
    return DoctorConsultationDetail(
        id=c.id,
        patient_id=pt.id,
        patient_name=u.name,
        kyros_patient_id=pt.kyros_patient_id,
        condition_category=c.condition_category,
        consultation_type=_ev(c.consultation_type),
        scheduled_start_at=c.scheduled_start_at,
        scheduled_end_at=c.scheduled_end_at,
        actual_start_at=c.actual_start_at,
        actual_end_at=c.actual_end_at,
        status=c.status.value,
        video_room_id=c.video_room_id,
        consultation_fee_paise=c.consultation_fee_paise,
        cancellation_reason=c.cancellation_reason,
        recording_consent=c.recording_consent,
        created_at=c.created_at,
    )


@router.post(
    "/consultations/{consultation_id}/complete",
    response_model=ConsultationCompleteResponse,
)
async def complete_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> ConsultationCompleteResponse:
    from app.models.identity import User as UserModel
    from app.services import consultation_service

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="complete_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row

    try:
        consultation = await consultation_service.complete_consultation(
            db, consultation_id=consultation_id, doctor_id=doctor.id
        )
    except consultation_service.ConsultationError as exc:
        if exc.code == "consultation_not_found":
            await write_audit(
                db, ctx, action="complete_consultation",
                resource_type="consultation", resource_id=consultation_id,
                allowed=False, reason="not_own_or_not_found",
            )
            await db.commit()
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found") from exc
        await write_audit(
            db, ctx, action="complete_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason=exc.code,
        )
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.code) from exc

    await write_audit(
        db, ctx, action="complete_consultation",
        resource_type="consultation", resource_id=consultation.id, allowed=True,
    )
    return ConsultationCompleteResponse(
        id=consultation.id,
        status=consultation.status.value,
        actual_end_at=consultation.actual_end_at,
    )


# ── Notes ──────────────────────────────────────────────────────────────────────


class NoteCreate(BaseModel):
    note_type: NoteType = NoteType.CLINICAL
    content: str = Field(..., min_length=1, max_length=10_000)


class NoteRead(BaseModel):
    id: uuid.UUID
    note_type: str
    version: int
    created_at: datetime


@router.get("/consultations/{consultation_id}/notes", response_model=list[NoteRead])
async def list_consultation_notes(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> list[NoteRead]:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="list_doctor_notes",
            resource_type="doctor_note", allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    row = await dr_repo.get_doctor_consultation_detail(
        db, doctor_id=doctor.id, consultation_id=consultation_id
    )
    if row is None:
        await write_audit(
            db, ctx, action="list_doctor_notes",
            resource_type="doctor_note", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    notes = await dr_repo.get_notes_for_consultation(
        db, doctor_id=doctor.id, consultation_id=consultation_id
    )
    await write_audit(
        db, ctx, action="list_doctor_notes",
        resource_type="doctor_note", resource_id=consultation_id, allowed=True,
    )
    return [
        NoteRead(
            id=n.id,
            note_type=n.note_type.value,
            version=n.version,
            created_at=n.created_at,
        )
        for n in notes
    ]


@router.post(
    "/consultations/{consultation_id}/notes",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_consultation_note(
    consultation_id: uuid.UUID,
    body: NoteCreate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> NoteRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="create_doctor_note",
            resource_type="doctor_note", allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    row = await dr_repo.get_doctor_consultation_detail(
        db, doctor_id=doctor.id, consultation_id=consultation_id
    )
    if row is None:
        await write_audit(
            db, ctx, action="create_doctor_note",
            resource_type="doctor_note", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    c, pt, _ = row
    note = await dr_repo.append_doctor_note(
        db,
        doctor_id=doctor.id,
        consultation_id=c.id,
        patient_id=pt.id,
        note_type=body.note_type,
        content=body.content,
    )
    await write_audit(
        db, ctx, action="create_doctor_note",
        resource_type="doctor_note", resource_id=note.id, allowed=True,
    )
    return NoteRead(
        id=note.id,
        note_type=note.note_type.value,
        version=note.version,
        created_at=note.created_at,
    )


# ── Lab orders ─────────────────────────────────────────────────────────────────


class LabOrderCreate(BaseModel):
    tests: list[str] = Field(..., min_length=1)
    lab_name: str | None = Field(default=None, max_length=255)


class LabOrderRead(BaseModel):
    id: uuid.UUID
    status: str
    tests: list[str]
    lab_name: str | None
    created_at: datetime


@router.post(
    "/consultations/{consultation_id}/lab-order",
    response_model=LabOrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_consultation_lab_order(
    consultation_id: uuid.UUID,
    body: LabOrderCreate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> LabOrderRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="create_lab_order",
            resource_type="lab_order", allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    row = await dr_repo.get_doctor_consultation_detail(
        db, doctor_id=doctor.id, consultation_id=consultation_id
    )
    if row is None:
        await write_audit(
            db, ctx, action="create_lab_order",
            resource_type="lab_order", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    c, pt, _ = row
    order = await dr_repo.create_lab_order_for_consultation(
        db,
        doctor_id=doctor.id,
        consultation_id=c.id,
        patient_id=pt.id,
        tests=body.tests,
        lab_name=body.lab_name,
    )
    await write_audit(
        db, ctx, action="create_lab_order",
        resource_type="lab_order", resource_id=order.id, allowed=True,
    )
    return LabOrderRead(
        id=order.id,
        status=order.status.value,
        tests=order.tests,
        lab_name=order.lab_name,
        created_at=order.created_at,
    )


# ── POST /v1/doctor/consultations/{id}/education — assign content to patient ──


class EducationAssignRequest(BaseModel):
    content_id: uuid.UUID
    notes: str | None = None


class EducationAssignRead(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    patient_id: uuid.UUID
    consultation_id: uuid.UUID | None
    notes: str | None

    model_config = {"from_attributes": True}


@router.post(
    "/consultations/{consultation_id}/education",
    response_model=EducationAssignRead,
    status_code=status.HTTP_201_CREATED,
)
async def assign_education_content(
    consultation_id: uuid.UUID,
    body: EducationAssignRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> EducationAssignRead:
    from app.models.identity import User as UserModel
    from app.repositories import education as edu_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="assign_education",
            resource_type="education_assignment", allowed=False,
            reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    row = await dr_repo.get_doctor_consultation_detail(
        db, doctor_id=doctor.id, consultation_id=consultation_id
    )
    if row is None:
        await write_audit(
            db, ctx, action="assign_education",
            resource_type="education_assignment", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    c, pt, _ = row

    # Verify content exists and is published
    content = await edu_repo.get_content_by_id(db, content_id=body.content_id, published_only=True)
    if content is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="content_not_found_or_unpublished")

    assignment = await edu_repo.create_assignment(
        db,
        content_id=body.content_id,
        patient_id=pt.id,
        doctor_id=doctor.id,
        consultation_id=c.id,
        notes=body.notes,
    )
    await write_audit(
        db, ctx, action="assign_education",
        resource_type="education_assignment", resource_id=assignment.id, allowed=True,
    )
    return EducationAssignRead.model_validate(assignment)
