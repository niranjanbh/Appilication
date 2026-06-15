"""Doctor-facing video join endpoint.

GET /v1/doctor/consultations/{id}/join — returns a doctor-role HMS token.
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

router = APIRouter(tags=["doctor-video"])


class DoctorJoinResponse(BaseModel):
    room_id: str
    token: str
    endpoint: str = "https://prod-in2.100ms.live/hmscore"


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


@router.get("/consultations/{consultation_id}/join", response_model=DoctorJoinResponse)
async def doctor_join_consultation(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> DoctorJoinResponse:
    from app.integrations import hms
    from app.models.identity import User as UserModel
    from app.repositories import consultations as consultations_repo
    from app.services import consultation_service

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    doctor = await consultations_repo.get_doctor_record(db, user_id=user.id)
    if doctor is None:
        await write_audit(
            db, ctx, action="join_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    consultation = await consultations_repo.get_consultation_for_doctor(
        db, consultation_id=consultation_id, doctor_id=doctor.id
    )
    if consultation is None:
        await write_audit(
            db, ctx, action="join_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    # TPG hard gate: the doctor cannot "open" the consult without a verified
    # patient identity and active telemedicine consent. Takes precedence over
    # video-room readiness.
    try:
        consultation = await consultation_service.open_consultation(
            db, consultation_id=consultation_id, doctor_id=doctor.id
        )
    except consultation_service.ConsultationError as exc:
        await write_audit(
            db, ctx, action="join_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason=exc.code,
        )
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.code) from exc

    if consultation.video_room_id is None:
        await write_audit(
            db, ctx, action="join_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="room_not_provisioned",
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="video_room_not_ready",
        )

    token = hms.generate_doctor_token(
        room_id=consultation.video_room_id,
        user_id=str(user.id),
    )
    await write_audit(
        db, ctx, action="join_consultation",
        resource_type="consultation", resource_id=consultation_id, allowed=True
    )
    return DoctorJoinResponse(room_id=consultation.video_room_id, token=token)
