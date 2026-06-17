"""Doctor read-only access to patient health notes.

GET /v1/doctor/patients/{patient_user_id}/notes

Scoped: doctor must have at least one consultation with the patient.
Audit-logged on every read.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import doctor_portal as dr_repo
from app.repositories import patient_notes as notes_repo

router = APIRouter(tags=["doctor-patient-notes"])


class PatientNoteRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    body: str
    created_at: str
    updated_at: str


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


@router.get("/patients/{patient_user_id}/notes", response_model=list[PatientNoteRead])
async def get_patient_notes(
    patient_user_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> list[PatientNoteRead]:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dr_row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if dr_row is None:
        await write_audit(
            db, ctx, action="view_patient_notes",
            resource_type="patient_note", resource_id=patient_user_id,
            allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, _ = dr_row
    notes = await notes_repo.list_notes_for_doctor(
        db, patient_user_id=patient_user_id, doctor_id=doctor.id
    )
    if notes is None:
        await write_audit(
            db, ctx, action="view_patient_notes",
            resource_type="patient_note", resource_id=patient_user_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="view_patient_notes",
        resource_type="patient_note", resource_id=patient_user_id, allowed=True,
    )
    return [
        PatientNoteRead(
            id=n.id,
            body=n.body,
            created_at=n.created_at.isoformat(),
            updated_at=n.updated_at.isoformat(),
        )
        for n in notes
    ]
