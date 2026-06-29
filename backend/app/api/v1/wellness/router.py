from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import DbSession
from app.api.v1.wellness.schemas import (
    AdherenceLogRead,
    AdherenceLogRequest,
    DailySummaryResponse,
    HealthSummaryResponse,
    HealthSyncRequest,
    HealthSyncResponse,
    ReminderCreate,
    ReminderImageInitiateRequest,
    ReminderImageInitiateResponse,
    ReminderImageUrlResponse,
    ReminderListResponse,
    ReminderRead,
    ReminderUpdate,
    SymptomCheckInCreate,
    SymptomCheckInRead,
    TodayCheckInResponse,
    VitalReadItem,
    VitalsListResponse,
    VitalsLogRequest,
    VitalsLogResponse,
    WeekDaySummary,
    WeekSummaryResponse,
)
from app.core.audit import AuditContext, write_audit
from app.core.rbac import cross_user_404, get_patient_user
from app.db.enums import ActorRole, HealthDatapointType
from app.repositories import health_sync as health_sync_repo
from app.repositories import reminders as reminders_repo
from app.repositories import symptom_checkin as symptom_checkin_repo
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
    reminders = await reminders_repo.list_reminders_for_user(db, user_id=user.id, include_inactive=True)
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


@router.get("/reminders/daily-summary", response_model=DailySummaryResponse)
async def daily_summary(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    date: str | None = Query(default=None, description="ISO date (YYYY-MM-DD), defaults to today IST"),
) -> DailySummaryResponse:
    from datetime import date as date_cls
    from datetime import datetime as dt
    from zoneinfo import ZoneInfo

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    if date:
        try:
            target = date_cls.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid date format, expected YYYY-MM-DD") from None
    else:
        target = dt.now(ZoneInfo("Asia/Kolkata")).date()

    total, completed = await reminders_repo.get_daily_adherence_summary(
        db, user_id=user.id, target_date=target
    )
    streak = await reminders_repo.get_adherence_streak(db, user_id=user.id)

    await write_audit(
        db, ctx, action="daily_summary", resource_type="reminder", allowed=True
    )

    return DailySummaryResponse(
        date=target.isoformat(),
        total=total,
        completed=completed,
        streak=streak,
    )


@router.get("/reminders/week-summary", response_model=WeekSummaryResponse)
async def week_summary(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    start: str = Query(..., description="ISO date (YYYY-MM-DD) for week start (Sunday)"),
) -> WeekSummaryResponse:
    from datetime import date as date_cls
    from datetime import timedelta

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    try:
        week_start = date_cls.fromisoformat(start)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid date format") from None

    completed_by_day = await reminders_repo.get_week_adherence(
        db, user_id=user.id, week_start=week_start
    )
    completed_map = dict(completed_by_day)

    all_reminders = await reminders_repo.list_reminders_for_user(
        db, user_id=user.id, include_inactive=False
    )
    total = len(all_reminders)

    days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        days.append(WeekDaySummary(
            date=d.isoformat(),
            total=total,
            completed=completed_map.get(d, 0),
        ))

    await write_audit(
        db, ctx, action="week_summary", resource_type="reminder", allowed=True
    )

    return WeekSummaryResponse(days=days)


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


@router.post(
    "/reminders/{reminder_id}/image-initiate",
    response_model=ReminderImageInitiateResponse,
)
async def initiate_reminder_image(
    reminder_id: uuid.UUID,
    body: ReminderImageInitiateRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ReminderImageInitiateResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    reminder = await reminders_repo.get_reminder_for_user(
        db, reminder_id=reminder_id, user_id=user.id
    )
    await cross_user_404(
        db, reminder, ctx,
        action="upload_reminder_image", resource_type="reminder", resource_id=reminder_id,
    )
    assert reminder is not None
    try:
        result = await reminders_service.initiate_image_upload(
            db,
            reminder=reminder,
            filename=body.filename,
            content_type=body.content_type,
            file_size_bytes=body.file_size_bytes,
        )
    except reminders_service.ReminderImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await write_audit(
        db, ctx, action="upload_reminder_image", resource_type="reminder",
        resource_id=reminder_id, allowed=True,
    )
    return ReminderImageInitiateResponse(**result)


@router.post("/reminders/{reminder_id}/image-finalize")
async def finalize_reminder_image(
    reminder_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> dict[str, object]:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    reminder = await reminders_repo.get_reminder_for_user(
        db, reminder_id=reminder_id, user_id=user.id
    )
    await cross_user_404(
        db, reminder, ctx,
        action="finalize_reminder_image", resource_type="reminder", resource_id=reminder_id,
    )
    assert reminder is not None
    try:
        await reminders_service.finalize_image_upload(db, reminder=reminder)
    except reminders_service.ReminderImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await write_audit(
        db, ctx, action="finalize_reminder_image", resource_type="reminder",
        resource_id=reminder_id, allowed=True,
    )
    return {"reminder_id": str(reminder_id), "image_uploaded": True}


@router.get("/reminders/{reminder_id}/image-url", response_model=ReminderImageUrlResponse)
async def get_reminder_image_url(
    reminder_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> ReminderImageUrlResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    reminder = await reminders_repo.get_reminder_for_user(
        db, reminder_id=reminder_id, user_id=user.id
    )
    await cross_user_404(
        db, reminder, ctx,
        action="view_reminder_image", resource_type="reminder", resource_id=reminder_id,
    )
    assert reminder is not None
    url = await reminders_service.get_image_url(db, reminder=reminder)
    if url is None:
        await write_audit(
            db, ctx, action="view_reminder_image", resource_type="reminder",
            resource_id=reminder_id, allowed=False, reason="no_image",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await write_audit(
        db, ctx, action="view_reminder_image", resource_type="reminder",
        resource_id=reminder_id, allowed=True,
    )
    return ReminderImageUrlResponse(url=url)


@router.delete("/reminders/{reminder_id}/image", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_reminder_image(
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
        db, reminder, ctx,
        action="delete_reminder_image", resource_type="reminder", resource_id=reminder_id,
    )
    assert reminder is not None
    await reminders_service.remove_image(db, reminder=reminder)
    await write_audit(
        db, ctx, action="delete_reminder_image", resource_type="reminder",
        resource_id=reminder_id, allowed=True,
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


@router.post("/vitals", response_model=VitalsLogResponse, status_code=status.HTTP_201_CREATED)
async def log_vitals(
    body: VitalsLogRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> VitalsLogResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    count = await health_sync_service.log_manual_vitals(
        db,
        user_id=user.id,
        measured_at=body.measured_at,
        weight_kg=body.weight_kg,
        blood_pressure_systolic=body.blood_pressure_systolic,
        blood_pressure_diastolic=body.blood_pressure_diastolic,
        blood_glucose_mg_dl=body.blood_glucose_mg_dl,
    )
    await write_audit(
        db, ctx, action="log_vitals", resource_type="health_datapoint",
        allowed=True, log_metadata={"count": count},
    )
    return VitalsLogResponse(logged_count=count)


@router.get("/vitals", response_model=VitalsListResponse)
async def list_vitals(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
    type: HealthDatapointType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> VitalsListResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    rows = await health_sync_repo.list_manual_datapoints(
        db, user_id=user.id, types=[type] if type is not None else None, limit=limit
    )
    await write_audit(
        db, ctx, action="list_vitals", resource_type="health_datapoint", allowed=True
    )
    return VitalsListResponse(items=[VitalReadItem.model_validate(r) for r in rows])


@router.get("/health-summary", response_model=HealthSummaryResponse)
async def health_summary(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> HealthSummaryResponse:
    """Latest synced activity metrics (steps today, resting HR, HRV) for the
    patient's lifestyle dashboard. Missing metrics come back as null."""
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    summary = await health_sync_service.get_health_summary(db, user_id=user.id)
    await write_audit(
        db, ctx, action="view_health_summary", resource_type="health_summary", allowed=True
    )
    return HealthSummaryResponse(**summary)


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
    reminder = await cross_user_404(
        db,
        reminder,
        ctx,
        action="log_adherence",
        resource_type="reminder",
        resource_id=reminder_id,
    )
    if not reminder.active:
        await write_audit(
            db,
            ctx,
            action="log_adherence",
            resource_type="reminder",
            resource_id=reminder_id,
            allowed=False,
            reason="reminder_inactive",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="reminder_inactive"
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


# ── Symptom check-in ──────────────────────────────────────────────────────────


@router.get("/symptom-checkin/today", response_model=TodayCheckInResponse)
async def get_today_checkin(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> TodayCheckInResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    entry = await symptom_checkin_repo.get_today_checkin(db, user_id=user.id)
    await write_audit(
        db, ctx, action="view_symptom_checkin_today", resource_type="symptom_checkin", allowed=True
    )
    if entry is None:
        return TodayCheckInResponse(checked_in=False, entry=None)
    return TodayCheckInResponse(checked_in=True, entry=SymptomCheckInRead.model_validate(entry))


@router.post("/symptom-checkin", response_model=SymptomCheckInRead, status_code=status.HTTP_201_CREATED)
async def submit_checkin(
    body: SymptomCheckInCreate,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> SymptomCheckInRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    entry = await symptom_checkin_repo.create_checkin(
        db,
        user_id=user.id,
        mood=body.mood,
        energy=body.energy,
        note=body.note,
    )
    await write_audit(
        db,
        ctx,
        action="create_symptom_checkin",
        resource_type="symptom_checkin",
        resource_id=entry.id,
        allowed=True,
        log_metadata={"mood": body.mood, "energy": body.energy},
    )
    return SymptomCheckInRead.model_validate(entry)
