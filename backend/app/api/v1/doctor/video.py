"""Doctor-facing video join endpoint.

GET /v1/doctor/consultations/{id}/join — returns a doctor-role LiveKit token.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole

router = APIRouter(tags=["doctor-video"])


def _livekit_ws_url() -> str:
    from app.core.config import settings

    return settings.livekit_host


class DoctorJoinResponse(BaseModel):
    room_id: str
    token: str
    # LiveKit WebSocket URL the client connects to (ws://… / wss://…).
    endpoint: str = Field(default_factory=_livekit_ws_url)


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
    from app.integrations import livekit_video
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
        # Provision on demand: the beat task pre-warms rooms, but a consult that
        # was never provisioned (created late, or beat down) must still be joinable
        # rather than a permanent dead-end 503. A genuine provider failure below is
        # the only thing that still yields a (retryable) 503.
        try:
            room_id = await consultation_service.ensure_video_room(
                db, consultation_id=consultation.id
            )
        except Exception as exc:
            await write_audit(
                db, ctx, action="join_consultation",
                resource_type="consultation", resource_id=consultation_id,
                allowed=False, reason="room_provisioning_failed",
            )
            await db.commit()
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="video_room_not_ready",
            ) from exc
        consultation.video_room_id = room_id

    token = livekit_video.generate_doctor_token(
        room_id=consultation.video_room_id,
        user_id=str(user.id),
    )

    # If the patient consented to recording, start S3 egress now that the doctor
    # is joining. The egress_id is persisted on the consultation so the recording
    # can be explicitly stopped when the consult completes (security rule #20).
    # Skip if an egress is already recorded (doctor reconnect — don't double-start).
    if consultation.recording_consent and consultation.recording_egress_id is None:
        try:
            egress_id = await livekit_video.start_recording(
                room_name=consultation.video_room_id
            )
            if egress_id is not None:
                await consultations_repo.update_consultation(
                    db, consultation_id=consultation.id, recording_egress_id=egress_id
                )
                # No PHI: room name + opaque egress id only.
                import structlog

                structlog.get_logger(__name__).info(
                    "doctor_video.recording_started",
                    room=consultation.video_room_id,
                    egress_id=egress_id,
                )
        except Exception:
            # Recording failure must not block the doctor from joining the call.
            import structlog

            structlog.get_logger(__name__).warning(
                "doctor_video.recording_start_failed",
                room=consultation.video_room_id,
            )

    await write_audit(
        db, ctx, action="join_consultation",
        resource_type="consultation", resource_id=consultation_id, allowed=True
    )
    return DoctorJoinResponse(room_id=consultation.video_room_id, token=token)
