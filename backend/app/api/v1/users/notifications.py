"""Notification center endpoints — patient in-app inbox and preferences."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.rbac import get_patient_user
from app.core.audit import AuditContext, write_audit
from app.core.pagination import PaginationParams
from app.core.rbac import cross_user_404
from app.db.enums import ActorRole

router = APIRouter(tags=["notifications"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class NotificationRead(BaseModel):
    id: uuid.UUID
    template_name: str
    title: str
    body: str
    channels: list[str]
    data: dict[str, Any]
    read_at: datetime | None
    sent_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationRead]
    total: int
    page: int
    page_size: int
    pages: int
    unread_count: int


class MarkAllReadResponse(BaseModel):
    marked_read: int


class NotificationPreferencesRead(BaseModel):
    push: bool
    whatsapp: bool
    email: bool


class NotificationPreferencesUpdate(BaseModel):
    push: bool | None = None
    whatsapp: bool | None = None
    email: bool | None = None


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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    from app.models.identity import User as UserModel
    from app.repositories import notifications as notif_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    params = PaginationParams(page=page, page_size=page_size)

    items, total = await notif_repo.list_for_user(
        db,
        user_id=user.id,
        limit=params.limit,
        offset=params.offset,
        unread_only=unread_only,
    )
    unread_count = await notif_repo.count_unread(db, user_id=user.id)
    pages = max(1, -(-total // params.page_size))

    await write_audit(
        db,
        ctx,
        action="list_notifications",
        resource_type="notification",
        resource_id=user.id,
        allowed=True,
    )
    return NotificationListResponse(
        items=[NotificationRead.model_validate(n) for n in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
        unread_count=unread_count,
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> NotificationRead:
    from app.models.identity import User as UserModel
    from app.repositories import notifications as notif_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    notif = await notif_repo.mark_read(db, notification_id=notification_id, user_id=user.id)
    notif = await cross_user_404(
        db,
        notif,
        ctx,
        action="mark_notification_read",
        resource_type="notification",
        resource_id=notification_id,
    )
    await write_audit(
        db,
        ctx,
        action="mark_notification_read",
        resource_type="notification",
        resource_id=notif.id,
        allowed=True,
    )
    return NotificationRead.model_validate(notif)


@router.post("/notifications/read-all", response_model=MarkAllReadResponse)
async def mark_all_notifications_read(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> MarkAllReadResponse:
    from app.models.identity import User as UserModel
    from app.repositories import notifications as notif_repo

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    count = await notif_repo.mark_all_read(db, user_id=user.id)
    await write_audit(
        db,
        ctx,
        action="mark_all_notifications_read",
        resource_type="notification",
        resource_id=user.id,
        allowed=True,
        log_metadata={"marked_read": count},
    )
    return MarkAllReadResponse(marked_read=count)


@router.get("/notification-preferences", response_model=NotificationPreferencesRead)
async def get_notification_preferences(
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> NotificationPreferencesRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    prefs: dict[str, bool] = dict(user.notification_preferences or {})
    await write_audit(
        db,
        ctx,
        action="view_notification_preferences",
        resource_type="user",
        resource_id=user.id,
        allowed=True,
    )
    return NotificationPreferencesRead(
        push=bool(prefs.get("push", True)),
        whatsapp=bool(prefs.get("whatsapp", True)),
        email=bool(prefs.get("email", True)),
    )


@router.patch("/notification-preferences", response_model=NotificationPreferencesRead)
async def update_notification_preferences(
    body: NotificationPreferencesUpdate,
    request: Request,
    db: DbSession,
    user: object = Depends(get_patient_user),
) -> NotificationPreferencesRead:
    from sqlalchemy import update as sa_update

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    current: dict[str, bool] = dict(user.notification_preferences or {})
    if body.push is not None:
        current["push"] = body.push
    if body.whatsapp is not None:
        current["whatsapp"] = body.whatsapp
    if body.email is not None:
        current["email"] = body.email

    await db.execute(
        sa_update(UserModel)
        .where(UserModel.id == user.id)
        .values(notification_preferences=current)
    )
    await db.flush()

    await write_audit(
        db,
        ctx,
        action="update_notification_preferences",
        resource_type="user",
        resource_id=user.id,
        allowed=True,
        log_metadata=dict(current),
    )
    return NotificationPreferencesRead(**current)
