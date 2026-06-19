from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import DbSession
from app.api.v1.users.schemas import (
    ActivityItem,
    ActivityListResponse,
    ConsentListResponse,
    ConsentRead,
    ConsentRequest,
    ConsentWithdrawRequest,
    DataExportListResponse,
    DataExportResponse,
    DataExportStatusRead,
    DataExportSummary,
    EmergencyContactRead,
    EmergencyContactWrite,
    ErasureResponse,
    SessionListResponse,
    SessionRead,
    SessionRevokeResponse,
    UserMeRead,
)
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.repositories import audit as audit_repo
from app.repositories import auth as auth_repo
from app.services import consent as consent_service


class PushTokenRequest(BaseModel):
    push_token: str


class PushTokenResponse(BaseModel):
    status: str = "registered"

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserMeRead)
async def get_me(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> UserMeRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    await write_audit(
        db,
        ctx,
        action="view_own_profile",
        resource_type="user",
        resource_id=user.id,
        allowed=True,
    )
    return UserMeRead.model_validate(user)


@router.post("/me/consent", response_model=ConsentRead, status_code=201)
async def capture_consent(
    body: ConsentRequest,
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> ConsentRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    record = await consent_service.capture_consent(
        db,
        user_id=user.id,
        consent_type=body.consent_type,
        version=body.version,
        granted=body.granted,
        ip_address=request.client.host if request.client else None,
        consent_text=body.consent_text,
    )
    await write_audit(
        db,
        ctx,
        action="capture_consent",
        resource_type="consent_record",
        resource_id=record.id,
        allowed=True,
        log_metadata={"consent_type": body.consent_type.value, "granted": body.granted},
    )
    return ConsentRead.model_validate(record)


@router.get("/me/consents", response_model=ConsentListResponse)
async def list_consents(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> ConsentListResponse:
    from app.models.identity import User as UserModel
    from app.repositories import consent as consent_repo

    assert isinstance(user, UserModel)
    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    records = await consent_repo.list_consents_for_user(db, user_id=user.id)
    await write_audit(
        db,
        ctx,
        action="list_consents",
        resource_type="consent_record",
        resource_id=user.id,
        allowed=True,
    )
    return ConsentListResponse(consents=[ConsentRead.model_validate(r) for r in records])


@router.post("/me/consent/withdraw", response_model=ConsentRead)
async def withdraw_consent(
    body: ConsentWithdrawRequest,
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> ConsentRead:
    """Withdraw an active consent (DPDP right to withdraw). 404 if none active."""
    from app.core.exceptions import NotFoundError
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        record = await consent_service.revoke_consent(
            db, user_id=user.id, consent_type=body.consent_type
        )
    except NotFoundError as exc:
        await write_audit(
            db, ctx, action="withdraw_consent", resource_type="consent_record",
            allowed=False, reason="active_consent_not_found",
            log_metadata={"consent_type": body.consent_type.value},
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="active_consent_not_found"
        ) from exc

    await write_audit(
        db, ctx, action="withdraw_consent", resource_type="consent_record",
        resource_id=record.id, allowed=True,
        log_metadata={"consent_type": body.consent_type.value},
    )
    return ConsentRead.model_validate(record)


@router.post("/me/data-export", response_model=DataExportResponse, status_code=202)
async def request_data_export(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> DataExportResponse:
    from app.models.identity import User as UserModel
    from app.tasks.data_subject_request import process_data_export

    assert isinstance(user, UserModel)
    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    dsr = await consent_service.request_data_export(db, user_id=user.id, audit_ctx=ctx)
    process_data_export.delay(str(user.id), str(dsr.id))
    return DataExportResponse(
        message="Data export request received. You will be notified when it is ready.",
        request_id=dsr.id,
    )


@router.get("/me/data-exports", response_model=DataExportListResponse)
async def list_data_exports(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> DataExportListResponse:
    from app.db.enums import DataSubjectRequestType
    from app.models.identity import User as UserModel
    from app.repositories import consent as consent_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    rows = await consent_repo.list_data_subject_requests_for_user(
        db, user_id=user.id, request_type=DataSubjectRequestType.ACCESS
    )
    await write_audit(
        db, ctx, action="list_data_exports", resource_type="data_subject_request",
        allowed=True,
    )
    return DataExportListResponse(
        items=[
            DataExportSummary(
                id=r.id,
                status=r.status,
                requested_at=r.received_at,
                completed_at=r.completed_at,
            )
            for r in rows
        ]
    )


@router.get("/me/data-exports/{request_id}", response_model=DataExportStatusRead)
async def get_data_export(
    request_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> DataExportStatusRead:
    from app.db.enums import DataSubjectRequestStatus, DataSubjectRequestType
    from app.integrations import s3
    from app.models.identity import User as UserModel
    from app.repositories import consent as consent_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    dsr = await consent_repo.get_data_subject_request_for_user(
        db, request_id=request_id, user_id=user.id
    )
    # Treat erasure requests as non-existent on this export-only surface.
    if dsr is None or dsr.request_type != DataSubjectRequestType.ACCESS:
        await write_audit(
            db, ctx, action="view_data_export", resource_type="data_subject_request",
            resource_id=request_id, allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    download_url: str | None = None
    expires_in: int | None = None
    if dsr.status == DataSubjectRequestStatus.COMPLETED:
        download_url = s3.generate_download_url(
            s3_key=s3.data_export_s3_key(user.id, dsr.id)
        )
        expires_in = 600  # matches generate_download_url TTL

    await write_audit(
        db, ctx, action="view_data_export", resource_type="data_subject_request",
        resource_id=request_id, allowed=True,
    )
    return DataExportStatusRead(
        id=dsr.id,
        status=dsr.status,
        requested_at=dsr.received_at,
        completed_at=dsr.completed_at,
        download_url=download_url,
        download_expires_in_seconds=expires_in,
    )


_EMERGENCY_FIELDS = ("name", "relationship", "phone", "email")


@router.get("/me/emergency-contact", response_model=EmergencyContactRead)
async def get_emergency_contact(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> EmergencyContactRead:
    from app.models.identity import User as UserModel
    from app.repositories import patients as patients_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    patient = await patients_repo.get_patient_for_user(db, user_id=user.id)
    if patient is None:
        await write_audit(
            db, ctx, action="view_emergency_contact", resource_type="patient",
            allowed=False, reason="patient_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="patient_profile_not_found")

    ec = patient.emergency_contact or {}
    await write_audit(
        db, ctx, action="view_emergency_contact", resource_type="patient",
        resource_id=patient.id, allowed=True,
    )
    return EmergencyContactRead(**{k: ec.get(k) for k in _EMERGENCY_FIELDS})


@router.put("/me/emergency-contact", response_model=EmergencyContactRead)
async def set_emergency_contact(
    body: EmergencyContactWrite,
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> EmergencyContactRead:
    from app.models.identity import User as UserModel
    from app.repositories import patients as patients_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    patient = await patients_repo.get_patient_for_user(db, user_id=user.id)
    if patient is None:
        await write_audit(
            db, ctx, action="set_emergency_contact", resource_type="patient",
            allowed=False, reason="patient_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="patient_profile_not_found")

    await patients_repo.update_emergency_contact(
        db, patient_id=patient.id, emergency_contact=body.model_dump()
    )
    await write_audit(
        db, ctx, action="set_emergency_contact", resource_type="patient",
        resource_id=patient.id, allowed=True,
    )
    return EmergencyContactRead(**body.model_dump())


@router.put("/me/push-token", response_model=PushTokenResponse)
async def register_push_token(
    body: PushTokenRequest,
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> PushTokenResponse:
    """Register or update the Expo push token for push notification delivery."""
    from sqlalchemy import update

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    await db.execute(
        update(UserModel)
        .where(UserModel.id == user.id)
        .values(expo_push_token=body.push_token)
    )
    await write_audit(
        db, ctx,
        action="register_push_token",
        resource_type="user",
        resource_id=user.id,
        allowed=True,
    )
    return PushTokenResponse()


@router.post("/me/delete", response_model=ErasureResponse, status_code=202)
async def request_erasure(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> ErasureResponse:
    from app.models.identity import User as UserModel
    from app.tasks.data_subject_request import process_erasure

    assert isinstance(user, UserModel)
    ctx = AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    dsr = await consent_service.request_erasure(db, user_id=user.id, audit_ctx=ctx)
    process_erasure.delay(str(user.id), str(dsr.id))
    return ErasureResponse(
        message=(
            "Account deletion request received. "
            "Your account will be deleted within 30 days."
        ),
        request_id=dsr.id,
    )


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


@router.get("/me/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> SessionListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    current_session = getattr(request.state, "session_id", None)
    rows = await auth_repo.list_active_sessions_for_user(db, user_id=user.id)
    await write_audit(
        db, ctx, action="list_sessions", resource_type="session", allowed=True
    )
    return SessionListResponse(
        items=[
            SessionRead(
                session_id=r["session_id"],  # type: ignore[arg-type]
                ip_address=r["ip_address"],  # type: ignore[arg-type]
                user_agent=r["user_agent"],  # type: ignore[arg-type]
                created_at=r["created_at"],  # type: ignore[arg-type]
                last_used_at=r["last_used_at"],  # type: ignore[arg-type]
                expires_at=r["expires_at"],  # type: ignore[arg-type]
                is_current=str(r["session_id"]) == str(current_session),
            )
            for r in rows
        ]
    )


@router.delete("/me/sessions/{session_id}", response_model=SessionRevokeResponse)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> SessionRevokeResponse:
    """Revoke (sign out) a session family. Cross-user/unknown sessions return 404."""
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    owns = await auth_repo.session_belongs_to_user(
        db, session_id=session_id, user_id=user.id
    )
    if not owns:
        await write_audit(
            db, ctx, action="revoke_session", resource_type="session",
            resource_id=session_id, allowed=False, reason="not_own_or_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    revoked = await auth_repo.revoke_session_family(db, session_id)
    await write_audit(
        db, ctx, action="revoke_session", resource_type="session",
        resource_id=session_id, allowed=True,
    )
    return SessionRevokeResponse(revoked=revoked)


# Friendly labels for the patient-facing activity feed. Unmapped actions fall
# back to a humanized form of the action string.
_ACTIVITY_DESCRIPTIONS: dict[str, str] = {
    "capture_consent": "Consent granted",
    "withdraw_consent": "Consent withdrawn",
    "capture_recording_consent": "Recording consent captured",
    "request_data_export": "Requested a data export",
    "request_erasure": "Requested account deletion",
    "register_push_token": "Registered this device for notifications",
    "revoke_session": "Signed out a device",
    "set_emergency_contact": "Updated emergency contact",
    "log_vitals": "Logged vitals",
    "health_sync": "Synced health data",
    "book_consultation": "Booked a consultation",
    "request_consultation": "Requested a consultation",
    "cancel_consultation": "Cancelled a consultation",
    "reschedule_consultation": "Rescheduled a consultation",
    "confirm_payment": "Confirmed a payment",
    "create_payment_order": "Started a payment",
    "abha_link": "Linked an ABHA number",
    "abha_create_confirm": "Created an ABHA number",
    "finalize_lab_report": "Uploaded a lab report",
}


def _describe_activity(action: str) -> str:
    mapped = _ACTIVITY_DESCRIPTIONS.get(action)
    if mapped is not None:
        return mapped
    return action.replace("_", " ").capitalize()


@router.get("/me/activity", response_model=ActivityListResponse)
async def list_activity(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ActivityListResponse:
    """The patient's own account activity history, derived from the audit log."""
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    rows, total = await audit_repo.list_activity_for_user(
        db, user_id=user.id, page=page, page_size=page_size
    )
    await write_audit(
        db, ctx, action="view_activity", resource_type="audit_log", allowed=True
    )
    pages = (total + page_size - 1) // page_size
    return ActivityListResponse(
        items=[
            ActivityItem(
                action=r.action,
                description=_describe_activity(r.action),
                resource_type=r.resource_type,
                allowed=r.allowed,
                ip_address=str(r.ip_address) if r.ip_address is not None else None,
                timestamp=r.timestamp,
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
