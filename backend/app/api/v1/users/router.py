from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.deps import DbSession
from app.api.v1.users.schemas import (
    ConsentListResponse,
    ConsentRead,
    ConsentRequest,
    DataExportResponse,
    ErasureResponse,
    UserMeRead,
)
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
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
