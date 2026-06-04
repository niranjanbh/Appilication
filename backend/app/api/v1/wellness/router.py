from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import DbSession
from app.api.v1.wellness.schemas import (
    AdherenceLogRead,
    AdherenceLogRequest,
    HealthSyncRequest,
    HealthSyncResponse,
    ReminderCreate,
    ReminderListResponse,
    ReminderRead,
    ReminderUpdate,
)
from app.core.audit import AuditContext, write_audit
from app.core.rbac import cross_user_404, get_patient_user
from app.db.enums import ActorRole
from app.repositories import reminders as reminders_repo
from app.services import health_sync as health_sync_service
from app.services import reminders as reminders_service

router = APIRouter(tags=["wellness"])


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


@router.get("/reminders", response_model=ReminderListResponse)
async def list_reminders(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ReminderListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    reminders = await reminders_repo.list_reminders_for_user(db, user_id=user.id)
    await write_audit(
        db, ctx, action="list_reminders", resource_type="reminder", allowed=True
    )
    items: list[ReminderRead] = []
    for r in reminders:
        rate = await reminders_repo.get_adherence_rate(db, reminder_id=r.id, user_id=user.id)
        read = ReminderRead.model_validate(r)
        read.adherence_rate = rate
        items.append(read)
    return ReminderListResponse(reminders=items, total=len(items))


@router.post("/reminders", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderCreate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ReminderRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    reminder = await reminders_service.create_reminder(
        db,
        user_id=user.id,
        type=body.type,
        label=body.label,
        schedule_cron=body.schedule_cron,
        schedule_interval_minutes=body.schedule_interval_minutes,
        notification_channels=body.notification_channels,
        extra_metadata=body.metadata,
    )
    await write_audit(
        db,
        ctx,
        action="create_reminder",
        resource_type="reminder",
        resource_id=reminder.id,
        allowed=True,
        log_metadata={"type": body.type.value},
    )
    return ReminderRead.model_validate(reminder)


@router.patch("/reminders/{reminder_id}", response_model=ReminderRead)
async def update_reminder(
    reminder_id: uuid.UUID,
    body: ReminderUpdate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ReminderRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    reminder = await reminders_repo.get_reminder_for_user(
        db, reminder_id=reminder_id, user_id=user.id
    )
    reminder = await cross_user_404(
        db,
        reminder,
        ctx,
        action="update_reminder",
        resource_type="reminder",
        resource_id=reminder_id,
    )
    update_kwargs = body.model_dump(exclude_unset=True)
    # Remap client-facing "metadata" key to ORM attribute name
    if "metadata" in update_kwargs:
        update_kwargs["extra_metadata"] = update_kwargs.pop("metadata")
    updated = await reminders_repo.update_reminder(
        db, reminder_id=reminder_id, user_id=user.id, **update_kwargs
    )
    await write_audit(
        db,
        ctx,
        action="update_reminder",
        resource_type="reminder",
        resource_id=reminder_id,
        allowed=True,
    )
    assert updated is not None
    rate = await reminders_repo.get_adherence_rate(db, reminder_id=updated.id, user_id=user.id)
    read = ReminderRead.model_validate(updated)
    read.adherence_rate = rate
    return read


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_reminder(
    reminder_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> None:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    reminder = await reminders_repo.get_reminder_for_user(
        db, reminder_id=reminder_id, user_id=user.id
    )
    await cross_user_404(
        db,
        reminder,
        ctx,
        action="delete_reminder",
        resource_type="reminder",
        resource_id=reminder_id,
    )
    await reminders_repo.soft_delete_reminder(db, reminder_id=reminder_id, user_id=user.id)
    await write_audit(
        db,
        ctx,
        action="delete_reminder",
        resource_type="reminder",
        resource_id=reminder_id,
        allowed=True,
    )


@router.post("/health-sync", response_model=HealthSyncResponse, status_code=status.HTTP_200_OK)
async def health_sync(
    body: HealthSyncRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> HealthSyncResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        result = await health_sync_service.process_health_sync(
            db,
            user_id=user.id,
            source=body.source,
            data_range_start=body.data_range_start,
            data_range_end=body.data_range_end,
            datapoints=[
                health_sync_service.DatapointInput(
                    type=dp.type,
                    source_record_id=dp.source_record_id,
                    measured_at=dp.measured_at,
                    value=dp.value,
                )
                for dp in body.datapoints
            ],
        )
    except PermissionError:
        await write_audit(
            db,
            ctx,
            action="health_sync",
            resource_type="health_sync_session",
            allowed=False,
            reason="consent_revoked_or_absent",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="health_sync_consent_required",
        ) from None

    await write_audit(
        db,
        ctx,
        action="health_sync",
        resource_type="health_sync_session",
        resource_id=result.session.id,
        allowed=True,
        log_metadata={
            "source": body.source.value,
            "inserted": result.inserted_count,
            "skipped": result.skipped_count,
        },
    )

    return HealthSyncResponse(
        session_id=result.session.id,
        inserted_count=result.inserted_count,
        skipped_count=result.skipped_count,
        status=result.status,
    )


@router.post(
    "/reminders/{reminder_id}/log",
    response_model=AdherenceLogRead,
    status_code=status.HTTP_201_CREATED,
)
async def log_adherence(
    reminder_id: uuid.UUID,
    body: AdherenceLogRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> AdherenceLogRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    reminder = await reminders_repo.get_reminder_for_user(
        db, reminder_id=reminder_id, user_id=user.id
    )
    await cross_user_404(
        db,
        reminder,
        ctx,
        action="log_adherence",
        resource_type="reminder",
        resource_id=reminder_id,
    )
    log = await reminders_service.log_adherence(
        db,
        reminder_id=reminder_id,
        user_id=user.id,
        scheduled_at=body.scheduled_at,
        action=body.action,
        notes=body.notes,
    )
    await write_audit(
        db,
        ctx,
        action="log_adherence",
        resource_type="reminder_log",
        resource_id=log.id,
        allowed=True,
        log_metadata={"action": body.action.value},
    )
    return AdherenceLogRead.model_validate(log)
