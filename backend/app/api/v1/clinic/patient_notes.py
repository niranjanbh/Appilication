"""Patient-facing notes endpoints.

GET    /v1/clinic/patient/notes           — list own notes (newest first)
POST   /v1/clinic/patient/notes           — create a note
DELETE /v1/clinic/patient/notes/{note_id} — soft-delete own note (cross-user → 404)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import patient_notes as notes_repo

router = APIRouter(tags=["patient-notes"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class PatientNoteCreate(BaseModel):
    body: str

    @field_validator("body")
    @classmethod
    def _body_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("body must not be blank")
        return v.strip()


class PatientNoteRead(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime
    updated_at: datetime


class PatientNotesListResponse(BaseModel):
    items: list[PatientNoteRead]
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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/notes", response_model=PatientNotesListResponse)
async def list_notes(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PatientNotesListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    notes, total = await notes_repo.list_for_patient(
        db,
        patient_user_id=user.id,
        page=page,
        page_size=page_size,
    )

    await write_audit(db, ctx, action="list_patient_notes", allowed=True)

    pages = max(1, -(-total // page_size))
    return PatientNotesListResponse(
        items=[
            PatientNoteRead(id=n.id, body=n.body, created_at=n.created_at, updated_at=n.updated_at)
            for n in notes
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/notes", response_model=PatientNoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: PatientNoteCreate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PatientNoteRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    note = await notes_repo.create_note(db, patient_user_id=user.id, body=payload.body)

    await write_audit(
        db, ctx,
        action="create_patient_note",
        resource_type="patient_note",
        resource_id=note.id,
        allowed=True,
    )

    return PatientNoteRead(id=note.id, body=note.body, created_at=note.created_at, updated_at=note.updated_at)


@router.patch("/notes/{note_id}", response_model=PatientNoteRead)
async def update_note(
    note_id: uuid.UUID,
    payload: PatientNoteCreate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PatientNoteRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    note = await notes_repo.update_for_patient(
        db,
        note_id=note_id,
        patient_user_id=user.id,
        body=payload.body,
    )

    if note is None:
        await write_audit(
            db, ctx,
            action="update_patient_note",
            resource_type="patient_note",
            resource_id=note_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="update_patient_note",
        resource_type="patient_note",
        resource_id=note_id,
        allowed=True,
    )

    return PatientNoteRead(id=note.id, body=note.body, created_at=note.created_at, updated_at=note.updated_at)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> None:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    deleted = await notes_repo.soft_delete_for_patient(
        db,
        note_id=note_id,
        patient_user_id=user.id,
    )

    if not deleted:
        await write_audit(
            db, ctx,
            action="delete_patient_note",
            resource_type="patient_note",
            resource_id=note_id,
            allowed=False,
            reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="delete_patient_note",
        resource_type="patient_note",
        resource_id=note_id,
        allowed=True,
    )
