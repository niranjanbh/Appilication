"""Doctor-facing patient notes endpoint.

GET /v1/doctor/patients/{patient_id}/notes — read a panel patient's notes (read-only)

`patient_id` is the kc_patients.id (Patient record), not the users.id.
The doctor must have at least one consultation with this patient (panel membership check).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import doctor_portal as dr_repo
from app.repositories import patient_notes as notes_repo

router = APIRouter(tags=["doctor-patient-notes"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class DoctorPatientNoteRead(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime
    updated_at: datetime


class DoctorPatientNotesListResponse(BaseModel):
    items: list[DoctorPatientNoteRead]
    total: int
    page: int
    page_size: int
    pages: int


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


# ── Endpoint ───────────────────────────────────────────────────────────────────


@router.get("/patients/{patient_id}/notes", response_model=DoctorPatientNotesListResponse)
async def list_patient_notes_for_doctor(
    patient_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DoctorPatientNotesListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx,
            action="list_patient_notes",
            resource_type="patient_note",
            allowed=False,
            reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row

    panel_row = await dr_repo.get_panel_patient(db, doctor_id=doctor.id, patient_id=patient_id)
    if panel_row is None:
        await write_audit(
            db, ctx,
            action="list_patient_notes",
            resource_type="patient_note",
            allowed=False,
            reason="patient_not_on_panel_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    _, patient_user = panel_row

    notes, total = await notes_repo.list_for_doctor(
        db,
        patient_user_id=patient_user.id,
        page=page,
        page_size=page_size,
    )

    await write_audit(
        db, ctx,
        action="list_patient_notes",
        resource_type="patient_note",
        allowed=True,
    )

    pages = max(1, -(-total // page_size))
    return DoctorPatientNotesListResponse(
        items=[
            DoctorPatientNoteRead(id=n.id, body=n.body, created_at=n.created_at, updated_at=n.updated_at)
            for n in notes
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
