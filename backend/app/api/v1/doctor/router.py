from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.doctor.care_plans import router as care_plans_router
from app.api.v1.doctor.consultations import router as consultations_router
from app.api.v1.doctor.content import router as content_router
from app.api.v1.doctor.drugs import router as drugs_router
from app.api.v1.doctor.icd10 import router as icd10_router
from app.api.v1.doctor.lab_review import router as lab_review_router
from app.api.v1.doctor.me import router as me_router
from app.api.v1.doctor.patient_notes import router as patient_notes_router
from app.api.v1.doctor.patients import router as patients_router
from app.api.v1.doctor.pre_consult_reports import router as pre_consult_router
from app.api.v1.doctor.prescriptions import router as prescriptions_router
from app.api.v1.doctor.schedule import router as schedule_router
from app.api.v1.doctor.video import router as video_router

doctor_router = APIRouter()
doctor_router.include_router(me_router)
doctor_router.include_router(care_plans_router)
doctor_router.include_router(content_router)
doctor_router.include_router(patients_router)
doctor_router.include_router(consultations_router)
doctor_router.include_router(prescriptions_router)
doctor_router.include_router(video_router)
doctor_router.include_router(pre_consult_router)
doctor_router.include_router(schedule_router)
doctor_router.include_router(lab_review_router)
doctor_router.include_router(drugs_router)
doctor_router.include_router(icd10_router)
doctor_router.include_router(patient_notes_router)
