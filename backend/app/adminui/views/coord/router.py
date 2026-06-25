"""Coordinator portal sub-router — assembles all /coord/* views."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adminui.deps import verify_csrf
from app.adminui.views.coord.auth import router as auth_router
from app.adminui.views.coord.bulk_actions import router as bulk_actions_router
from app.adminui.views.coord.communication import router as communication_router
from app.adminui.views.coord.dashboard import router as dashboard_router
from app.adminui.views.coord.followups import router as followups_router
from app.adminui.views.coord.inquiries import router as inquiries_router
from app.adminui.views.coord.intake import router as intake_router
from app.adminui.views.coord.patients import router as patients_router
from app.adminui.views.coord.scheduling import router as scheduling_router

coord_router = APIRouter()

# Auth (login/logout/forgot-password) — no session yet, CSRF not applicable.
coord_router.include_router(auth_router)

# Protected views: verify_csrf no-ops on GET and validates the double-submit
# token on every POST.
_csrf = [Depends(verify_csrf)]
coord_router.include_router(dashboard_router, dependencies=_csrf)
coord_router.include_router(patients_router, dependencies=_csrf)
coord_router.include_router(intake_router, dependencies=_csrf)
coord_router.include_router(inquiries_router, dependencies=_csrf)
coord_router.include_router(scheduling_router, dependencies=_csrf)
coord_router.include_router(followups_router, dependencies=_csrf)
coord_router.include_router(communication_router, dependencies=_csrf)
coord_router.include_router(bulk_actions_router, dependencies=_csrf)
