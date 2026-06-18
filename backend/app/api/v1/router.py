from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin.analytics import router as admin_analytics_router
from app.api.v1.admin.content import router as admin_content_router
from app.api.v1.admin.coupons import router as admin_coupons_router
from app.api.v1.admin.doctors import router as admin_doctors_router
from app.api.v1.admin.dsr import router as admin_dsr_router
from app.api.v1.admin.internal import router as admin_internal_router
from app.api.v1.admin.pricing import router as admin_pricing_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.clinic.abha import router as abha_router
from app.api.v1.clinic.biomarker_trends import router as biomarker_trends_router
from app.api.v1.clinic.consultations import router as clinic_router
from app.api.v1.clinic.doctors import router as patient_doctors_router
from app.api.v1.clinic.education import router as patient_education_router
from app.api.v1.clinic.lab_reports import router as lab_reports_router
from app.api.v1.clinic.patient_notes import router as patient_notes_router
from app.api.v1.clinic.pre_consult_reports import router as patient_pre_consult_router
from app.api.v1.clinic.prescriptions import router as patient_prescriptions_router
from app.api.v1.doctor.router import doctor_router
from app.api.v1.payments.router import router as payments_router
from app.api.v1.public.router import router as public_router
from app.api.v1.users.notifications import router as notifications_router
from app.api.v1.users.router import router as users_router
from app.api.v1.webhooks.router import router as webhooks_router
from app.api.v1.wellness.router import router as wellness_router

api_v1_router = APIRouter()

api_v1_router.include_router(public_router, prefix="/public")
api_v1_router.include_router(auth_router, prefix="/auth")
api_v1_router.include_router(users_router, prefix="/users")
api_v1_router.include_router(notifications_router, prefix="/users")
api_v1_router.include_router(wellness_router, prefix="/wellness")
api_v1_router.include_router(payments_router, prefix="/payments")
api_v1_router.include_router(webhooks_router, prefix="/webhooks")
api_v1_router.include_router(abha_router, prefix="/clinic/patient")
api_v1_router.include_router(clinic_router, prefix="/clinic/patient")
api_v1_router.include_router(lab_reports_router, prefix="/clinic/patient")
api_v1_router.include_router(biomarker_trends_router, prefix="/clinic/patient")
api_v1_router.include_router(patient_prescriptions_router, prefix="/clinic/patient")
api_v1_router.include_router(patient_pre_consult_router, prefix="/clinic/patient")
api_v1_router.include_router(patient_education_router, prefix="/clinic/patient")
api_v1_router.include_router(patient_notes_router, prefix="/clinic/patient")
api_v1_router.include_router(patient_doctors_router, prefix="/clinic/patient")
api_v1_router.include_router(doctor_router, prefix="/doctor")
api_v1_router.include_router(admin_content_router, prefix="/admin")
api_v1_router.include_router(admin_analytics_router, prefix="/admin")
api_v1_router.include_router(admin_doctors_router, prefix="/admin")
api_v1_router.include_router(admin_pricing_router, prefix="/admin")
api_v1_router.include_router(admin_coupons_router, prefix="/admin")
api_v1_router.include_router(admin_dsr_router, prefix="/admin")
api_v1_router.include_router(admin_internal_router, prefix="/admin")
