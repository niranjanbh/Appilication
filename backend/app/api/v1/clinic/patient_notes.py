"""Patient health-notes endpoints.

POST   /v1/clinic/patient/notes           — create a note
GET    /v1/clinic/patient/notes           — list own notes (newest first)
PATCH  /v1/clinic/patient/notes/{note_id} — edit own note
DELETE /v1/clinic/patient/notes/{note_id} — soft-delete own note
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import patient_notes as notes_repo

router = APIRouter(tags=["patient-notes"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class PatientNoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=1000)


class PatientNoteUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=1000)


class PatientNoteRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    body: str
    created_at: str
    updated_at: str


class PatientNoteListResponse(BaseModel):
    items: list[PatientNoteRead]
    total: int
    page: int
    page_size: int


# ── Helpers ───────────────────────────────────────────────────────────────────


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


def _note_to_read(note: object) -> PatientNoteRead:
    from app.models.clinic import PatientNote

    assert isinstance(note, PatientNote)
    return PatientNoteRead(
        id=note.id,
        body=note.body,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


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
        db, ctx, action="create_patient_note",
        resource_type="patient_note", resource_id=note.id, allowed=True,
    )
    return _note_to_read(note)


@router.get("/notes", response_model=PatientNoteListResponse)
async def list_notes(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PatientNoteListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    offset = (page - 1) * page_size
    notes, total = await notes_repo.list_notes_for_patient(
        db, patient_user_id=user.id, limit=page_size, offset=offset
    )

    await write_audit(
        db, ctx, action="list_patient_notes",
        resource_type="patient_note", allowed=True,
    )
    return PatientNoteListResponse(
        items=[_note_to_read(n) for n in notes],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/notes/{note_id}", response_model=PatientNoteRead)
async def update_note(
    note_id: uuid.UUID,
    payload: PatientNoteUpdate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> PatientNoteRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    note = await notes_repo.update_note(
        db, note_id=note_id, patient_user_id=user.id, body=payload.body
    )
    if note is None:
        await write_audit(
            db, ctx, action="update_patient_note",
            resource_type="patient_note", resource_id=note_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="update_patient_note",
        resource_type="patient_note", resource_id=note.id, allowed=True,
    )
    return _note_to_read(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_note(
    note_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> None:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    deleted = await notes_repo.soft_delete_note(
        db, note_id=note_id, patient_user_id=user.id
    )
    if not deleted:
        await write_audit(
            db, ctx, action="delete_patient_note",
            resource_type="patient_note", resource_id=note_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="delete_patient_note",
        resource_type="patient_note", resource_id=note_id, allowed=True,
    )
