---
name: project-p24-status
description: P24 Doctor Portal Polish build status — schedule, lab review, profile enhancements
metadata:
  type: project
---

P24 complete. 368/368 tests pass (up from 341 in P23).

**Why:** Adds schedule management, lab report annotation, and profile polish to the doctor portal.

**How to apply:** Next prompt is P25 (Super Admin Portal — Jinja2 + HTMX).

## What was built

### Migration 0014 (`backend/alembic/versions/0014_doctor_portal_polish.py`)
- `dr_doctors.buffer_time_minutes INTEGER NOT NULL DEFAULT 5`
- `kc_lab_reports.doctor_commentary JSONB`
- `kc_lab_reports.patient_attention_flags JSONB`

### Backend new/modified files
- `app/api/v1/doctor/schedule.py` — GET /v1/doctor/schedule, POST /v1/doctor/schedule/bulk, DELETE /v1/doctor/schedule/{id}, PATCH /v1/doctor/schedule/preferences
- `app/api/v1/doctor/lab_review.py` — GET/GET /v1/doctor/patients/{id}/lab-reports[/{id}], PATCH /v1/doctor/lab-reports/{id}/annotate
- `app/api/v1/doctor/me.py` — extended PATCH (specialty, conditions_treated), POST /v1/doctor/me/bank-details (Fernet-encrypted, triggers Celery task)
- `app/api/v1/doctor/router.py` — includes schedule and lab_review routers
- `app/tasks/doctor_tasks.py` — kyros.doctor.bank_details_verification Celery task
- `app/core/config.py` — added `admin_alert_email`
- `app/repositories/doctor_portal.py` — availability CRUD, annotate_lab_report, save_bank_details_encrypted
- `app/models/doctor.py` — buffer_time_minutes field
- `app/models/clinic.py` — doctor_commentary, patient_attention_flags fields
- `app/api/v1/clinic/lab_reports.py` — patient-facing LabReportRead now exposes doctor_commentary + patient_attention_flags
- `pyproject.toml` — cryptography.* added to mypy overrides

### Frontend doctor-portal
- `routes/Schedule.tsx` — slot list, bulk-add form, preferences panel
- `routes/patients/LabReportAnnotate.tsx` — per-biomarker annotation + flag interface
- `routes/patients/PatientDetail.tsx` — lab reports section with annotation links
- `routes/Profile.tsx` — specialty/conditions edit + bank details form
- `App.tsx` — /schedule and /patients/:id/lab-reports/:reportId routes
- `components/Layout.tsx` — Schedule nav item added

### Tests
- `tests/integration/api/test_rbac_matrix.py` — 27 new tests for all new endpoints
- `tests/conftest.py` — added `create_doctor_with_profile` helper (User + dr_doctors row)
