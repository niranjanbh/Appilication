---
name: project-p20-status
description: P20 build status — pre-consultation report generation
metadata:
  type: project
---

P20 complete. No new migration needed (kc_pre_consultation_reports already existed from migration 0008).

**Why:** Pre-consultation report aggregates lab, adherence, wearable data 24h before each consultation.

**How to apply:** Start P21 fresh.

## What was built

### Backend
- `app/repositories/pre_consult_reports.py` — create_or_update, get_for_patient, get_for_doctor, update_doctor_notes, set_pdf_url, list_consultations_needing_reports
- `app/services/pre_consult_report_service.py` — build_lab_summary (top 5 biomarkers, 90d), build_adherence_summary (30d), build_wearable_summary (30d), generate_report_for_consultation, render_pre_consult_html
- `app/tasks/report_tasks.py` — generate_pre_consultation_report (per-consultation, routes to `reports` queue), generate_pre_consult_reports_for_tomorrow (cron fan-out)
- Beat schedule: `generate-pre-consult-reports-tomorrow` added to `app/worker.py` (4 AM UTC daily, T-24h window)
- `app/api/v1/clinic/pre_consult_reports.py` — GET /v1/clinic/patient/consultations/{id}/pre-consult-report (patient, no doctor_notes field)
- `app/api/v1/doctor/pre_consult_reports.py` — GET/PATCH /v1/doctor/consultations/{id}/pre-consult-report, POST .../generate
- Both routers wired into existing router files

### Mobile
- `mobile/lib/api/pre-consult-reports.ts` — typed API client
- `mobile/app/consultations/pre-consult-report.tsx` — read-only screen: lab summary with trend arrows, adherence bar, wearable stats cards, patient flags, PDF download

### Doctor Portal
- `doctor-portal/src/components/PreConsultReport.tsx` — full view + editable prep notes textarea (PATCH) + on-demand generate button
- Wired into ConsultationVideoLayout as new "Pre-consult" tab (first tab)
- Wired into ConsultationDetail page (cancelled/no-show view)

### Tests
- 16 RBAC matrix tests added (auth/role/404 for all 4 new endpoints)
- 319/319 tests pass

## Information symmetry
Patient and doctor see identical lab_summary, adherence_summary, wearable_summary, patient_flags. Only doctor_notes_pre_consult is doctor-only (absent from PatientPreConsultReportRead schema).
