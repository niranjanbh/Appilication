"""Admin UI router — assembles all admin/coordinator HTML views and static file mount."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.staticfiles import StaticFiles

from app.adminui.deps import verify_csrf
from app.adminui.views.analytics import router as analytics_router
from app.adminui.views.audit_log import router as audit_log_router
from app.adminui.views.auth import router as auth_router
from app.adminui.views.bulk_actions import router as bulk_actions_router
from app.adminui.views.consultations import router as consultations_router
from app.adminui.views.content import router as content_router
from app.adminui.views.coupons import router as coupons_router
from app.adminui.views.dashboard import router as dashboard_router
from app.adminui.views.doctors import router as doctors_router
from app.adminui.views.dsr import router as dsr_router
from app.adminui.views.medication_catalog import router as medication_catalog_router
from app.adminui.views.payments import router as payments_router
from app.adminui.views.pricing import router as pricing_router
from app.adminui.views.settings import router as settings_router
from app.adminui.views.staff import router as staff_router
from app.adminui.views.users import router as users_router

admin_router = APIRouter()

# Auth (login/logout/forgot-password) — no session yet, so CSRF is enforced
# per-handler inside auth.py (only /reauth needs it). Not covered here.
admin_router.include_router(auth_router)

# Protected views. CSRF is enforced at the router level: verify_csrf no-ops on
# GET/HEAD/OPTIONS and validates the double-submit token on every POST.
_csrf = [Depends(verify_csrf)]
admin_router.include_router(dashboard_router, dependencies=_csrf)
admin_router.include_router(users_router, dependencies=_csrf)
admin_router.include_router(staff_router, dependencies=_csrf)
admin_router.include_router(doctors_router, dependencies=_csrf)
admin_router.include_router(consultations_router, dependencies=_csrf)
admin_router.include_router(payments_router, dependencies=_csrf)
admin_router.include_router(pricing_router, dependencies=_csrf)
admin_router.include_router(coupons_router, dependencies=_csrf)
admin_router.include_router(medication_catalog_router, dependencies=_csrf)
admin_router.include_router(content_router, dependencies=_csrf)
admin_router.include_router(dsr_router, dependencies=_csrf)
admin_router.include_router(audit_log_router, dependencies=_csrf)
admin_router.include_router(analytics_router, dependencies=_csrf)
admin_router.include_router(settings_router, dependencies=_csrf)
# Bulk multi-select actions + CSV exports. POSTs are CSRF-protected; GET exports
# no-op past verify_csrf. Each handler enforces its own session tier internally.
admin_router.include_router(bulk_actions_router, dependencies=_csrf)

# Static files (CSS, HTMX, Alpine.js) — shared with coordinator portal
_static_dir = Path(__file__).parent / "static"
admin_static = StaticFiles(directory=str(_static_dir))
