"""Admin UI router — assembles all admin/coordinator HTML views and static file mount."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

from app.adminui.views.analytics import router as analytics_router
from app.adminui.views.audit_log import router as audit_log_router
from app.adminui.views.auth import router as auth_router
from app.adminui.views.consultations import router as consultations_router
from app.adminui.views.content import router as content_router
from app.adminui.views.dashboard import router as dashboard_router
from app.adminui.views.doctors import router as doctors_router
from app.adminui.views.dsr import router as dsr_router
from app.adminui.views.payments import router as payments_router
from app.adminui.views.staff import router as staff_router
from app.adminui.views.users import router as users_router

admin_router = APIRouter()

# Auth (login/logout) — no session required
admin_router.include_router(auth_router)

# Protected views
admin_router.include_router(dashboard_router)
admin_router.include_router(users_router)
admin_router.include_router(staff_router)
admin_router.include_router(doctors_router)
admin_router.include_router(consultations_router)
admin_router.include_router(payments_router)
admin_router.include_router(content_router)
admin_router.include_router(dsr_router)
admin_router.include_router(audit_log_router)
admin_router.include_router(analytics_router)

# Static files (CSS, HTMX, Alpine.js) — shared with coordinator portal
_static_dir = Path(__file__).parent / "static"
admin_static = StaticFiles(directory=str(_static_dir))
