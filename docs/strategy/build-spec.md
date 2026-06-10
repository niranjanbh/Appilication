---
name: kyros-build-spec
description: The master technical specification for the Kyros platform. NOT a skill — this is a product spec that Claude Code reads to generate the entire application. Covers backend (FastAPI + SQLAlchemy + PostgreSQL), database schema across all surfaces, API route map, RBAC implementation, OCR pipeline, video consultation integration, HealthKit + Health Connect sync, public website, patient mobile + web portal, doctor portal, super admin portal, care coordinator portal, infrastructure, DPDP compliance architecture, pre-consultation report generation, ABHA integration. Final section is the complete Claude Code prompt queue P1–P30, rebuilt from scratch.
sequence: Product spec, not a skill. References all 5 skills but does not duplicate their content.
---

# Kyros Build Spec

This is the master technical specification for the Kyros platform. It is **not a skill** — skills capture reusable strategic and operational rules. This spec captures **product-specific technical decisions** that Claude Code reads when generating the application.

The five skills (business-strategy, clinical-compliance, design-system, customer-acquisition, b2b2c-partnerships) own the strategic and operational layer. This spec owns the technical architecture and execution. **Zero overlap with the skill files.** This spec references them but does not restate their content.

## Document Map

1. Architecture Overview
2. Database Schema (Complete, All Surfaces)
3. API Route Map with RBAC
4. RBAC Implementation
5. OCR Pipeline (Lab Reports)
6. Video Consultation Integration (100ms)
7. Health Data Sync (HealthKit + Health Connect)
8. Public Website (Next.js)
9. Patient Mobile App (Expo React Native)
10. Patient Web Portal (React Native Web)
11. Doctor Portal (React + Vite)
12. Super Admin Portal (Jinja2 + HTMX)
13. Care Coordinator Portal (Jinja2 + HTMX)
14. Infrastructure Plan (Phase 1 → Phase 2)
15. DPDP Compliance Architecture
16. Pre-Consultation Report Generation
17. ABHA Integration Approach
18. Phase Scope on Public Website
19. **Claude Code Prompt Queue P1–P30** (rebuilt from scratch)

---

## 1. Architecture Overview

### Single backend serving all surfaces

One FastAPI 0.115 backend (`kyros-backend`) serves:
- Public website API endpoints (booking, contact, lead capture)
- Patient mobile app and patient web portal (`/v1/clinic/patient/*`, `/v1/wellness/*`)
- Doctor portal (`/v1/doctor/*`)
- Super admin portal (`/v1/admin/*`)
- Care coordinator portal (`/v1/admin/coordinator/*`)

One PostgreSQL 16 database with **domain-prefixed tables**:

| Prefix | Domain | Examples |
|---|---|---|
| `wn_` | Wellness (patient self-tracking, agnostic of clinical care) | `wn_health_sync_sessions`, `wn_health_datapoints`, `wn_reminders` |
| `kc_` | Kyros Clinic (clinical care delivery) | `kc_patients`, `kc_consultations`, `kc_prescriptions`, `kc_lab_orders` |
| `dr_` | Doctor-side data | `dr_doctors`, `dr_availability`, `dr_credentials` |
| `ad_` | Admin/operational | `ad_coordinators`, `ad_audit_log`, `ad_consent_records` |

### Tech stack (locked)

**Backend:**
- FastAPI 0.115
- SQLAlchemy 2.0 async + asyncpg
- Pydantic v2 for schemas
- Alembic for migrations
- Celery 5.4 + Redis for async tasks
- structlog for structured logging
- ruff + mypy strict for code quality
- pytest + pytest-asyncio for tests

**Mobile (Patient app + Patient web portal):**
- Expo React Native (custom dev client, not Expo Go)
- TypeScript strict mode
- expo-router for navigation
- TanStack Query v5 for server state
- Victory Native XL for charts (mobile)
- Recharts for charts (web)
- @kingstinct/react-native-healthkit for iOS health data
- react-native-health-connect for Android health data
- React Native Web for the patient web portal (shared codebase, ~85% reuse)

**Doctor Portal (React + Vite):**
- React 18, Vite 5, TypeScript
- Tailwind CSS with shared design tokens
- shadcn/ui base components
- TanStack Query v5
- Recharts for charts

**Super Admin + Care Coordinator (Jinja2 + HTMX):**
- Server-rendered HTML
- HTMX 2.0 for partial updates
- Alpine.js for small client interactions
- Tailwind CSS with shared design tokens
- Performance target: page render < 200ms

**Public Website (Next.js):**
- Next.js 14 App Router
- TypeScript
- Tailwind CSS with shared design tokens
- next-mdx-remote for content articles
- Static generation (SSG) for SEO surfaces
- Server actions for booking/contact

**Third-party services (committed):**
- **Video:** 100ms (Indian-origin, India-region data residency, side-panel UI support)
- **OCR:** Google Document AI (Indian region, healthcare parser)
- **Payments:** Razorpay (RBI e-mandate, GST invoicing, T+2 settlement)
- **Push notifications:** Expo Push + FCM
- **WhatsApp:** AiSensy or Wati (Indian BSP, DPDP-aligned)
- **Email:** SendGrid India region or Postmark
- **OTP/SMS:** MSG91 (Indian, DPDP-aligned)
- **Voice synthesis:** ElevenLabs (settings per design-system; cloned founder voice for non-clinical + Kyros Clinical Editor voice for clinical)

### Repository layout

```
kyros-platform/
├── backend/                    # FastAPI single backend
│   ├── app/
│   │   ├── core/              # config, security, RBAC
│   │   ├── db/                # SQLAlchemy models, sessions
│   │   ├── api/v1/
│   │   │   ├── public/        # /v1/public/* (no auth)
│   │   │   ├── clinic/        # /v1/clinic/* (patient)
│   │   │   ├── doctor/        # /v1/doctor/*
│   │   │   ├── admin/         # /v1/admin/*
│   │   │   └── wellness/      # /v1/wellness/*
│   │   ├── tasks/             # Celery tasks
│   │   ├── services/          # business logic
│   │   └── integrations/      # 100ms, Document AI, Razorpay, etc.
│   ├── alembic/
│   ├── admin_ui/              # Jinja2 templates for super-admin + coordinator
│   ├── tests/
│   └── pyproject.toml
├── mobile/                     # Expo (mobile + RN Web patient portal)
│   ├── app/                   # expo-router routes
│   ├── components/
│   ├── lib/
│   └── package.json
├── doctor-portal/             # React + Vite
│   ├── src/
│   └── package.json
├── website/                    # Next.js public site
│   ├── app/
│   ├── content/               # MDX articles
│   └── package.json
└── design-tokens/             # Shared design tokens
    └── tokens.json
```

The design tokens are a single source consumed by Tailwind configs in all three frontends.

---

## 2. Database Schema (Complete, All Surfaces)

All tables have:
- `id UUID PK DEFAULT gen_random_uuid()`
- `created_at TIMESTAMPTZ DEFAULT NOW()`
- `updated_at TIMESTAMPTZ DEFAULT NOW()`
- `deleted_at TIMESTAMPTZ NULL` (soft delete pattern)

### Core identity tables

**users** (single users table; roles distinguish patient/doctor/coordinator/super_admin)
```
users
├── id UUID PK
├── role ENUM (patient | doctor | coordinator | super_admin)
├── email VARCHAR(255) UNIQUE
├── phone VARCHAR(20) UNIQUE (E.164)
├── phone_verified BOOL
├── email_verified BOOL
├── password_hash VARCHAR(255)  -- argon2id
├── name VARCHAR(255)
├── date_of_birth DATE
├── gender ENUM (female | male | non_binary | prefer_not_to_say)
├── city VARCHAR(100)
├── state VARCHAR(100)
├── language_preference VARCHAR(10)  -- en, hi, te, etc.
├── timezone VARCHAR(50) DEFAULT 'Asia/Kolkata'
├── last_login_at TIMESTAMPTZ
└── deleted_at TIMESTAMPTZ
```

### Wellness domain (`wn_*`)

**wn_reminders** — water intake, supplement, gym, custom reminders
```
wn_reminders
├── id UUID PK
├── user_id UUID FK users(id) ON DELETE CASCADE
├── type ENUM (water | supplement | medication | gym | custom)
├── label VARCHAR(255)
├── schedule_cron VARCHAR(100)  -- standard cron
├── schedule_interval_minutes INT  -- for interval-based reminders
├── active BOOL DEFAULT TRUE
├── notification_channels JSONB  -- [push, whatsapp, email]
└── metadata JSONB  -- type-specific data
```

**wn_reminder_logs** — adherence tracking
```
wn_reminder_logs
├── id UUID PK
├── reminder_id UUID FK wn_reminders(id)
├── user_id UUID FK users(id)
├── scheduled_at TIMESTAMPTZ
├── action ENUM (taken | skipped | snoozed | missed)
├── action_at TIMESTAMPTZ
└── notes VARCHAR(500)
```

**wn_health_sync_sessions** — track each HealthKit/Health Connect sync
```
wn_health_sync_sessions
├── id UUID PK
├── user_id UUID FK users(id)
├── source ENUM (apple_health | google_health_connect)
├── synced_at TIMESTAMPTZ
├── data_range_start TIMESTAMPTZ
├── data_range_end TIMESTAMPTZ
├── record_count INT
├── consent_id UUID FK ad_consent_records(id)
└── status ENUM (success | partial | failed)
```

**wn_health_datapoints** — partitioned monthly on `measured_at`
```
wn_health_datapoints  (partitioned by RANGE on measured_at, monthly)
├── id UUID PK
├── user_id UUID FK users(id)
├── source ENUM (apple_health | google_health_connect | manual)
├── source_session_id UUID FK wn_health_sync_sessions(id)
├── source_record_id VARCHAR(255)  -- HK/HC native identifier for idempotency
├── type ENUM (steps | heart_rate | resting_heart_rate | hrv | sleep_duration | sleep_quality | weight | blood_pressure_systolic | blood_pressure_diastolic | blood_glucose | workout | active_calories)
├── value JSONB  -- shape varies by type
├── measured_at TIMESTAMPTZ
└── UNIQUE (user_id, source, source_record_id)  -- idempotency

-- BRIN index on measured_at for trend queries
-- BTREE index on (user_id, type, measured_at DESC) for "latest 30 days of X" queries
```

**wn_water_intake**, **wn_supplements** — simple per-user tracking tables (omitted for brevity; follow same pattern)

### Kyros Clinic domain (`kc_*`)

**kc_patients** — extended patient profile (1:1 with users where role=patient)
```
kc_patients
├── id UUID PK
├── user_id UUID FK users(id) UNIQUE
├── kyros_patient_id VARCHAR(20) UNIQUE  -- human-readable: KYR-2026-00001
├── abha_number VARCHAR(20) NULL  -- optional
├── primary_conditions JSONB  -- array of vertical codes
├── preferred_doctor_id UUID FK dr_doctors(id) NULL
├── assigned_coordinator_id UUID FK ad_coordinators(id) NULL
├── allergies TEXT
├── chronic_conditions TEXT
├── current_medications TEXT
├── emergency_contact JSONB
└── intake_complete_at TIMESTAMPTZ
```

**kc_consultations**
```
kc_consultations
├── id UUID PK
├── patient_id UUID FK kc_patients(id)
├── doctor_id UUID FK dr_doctors(id)
├── coordinator_id UUID FK ad_coordinators(id) NULL
├── condition_category ENUM (thyroid | weight | pcos | skin_hair | mens_intimate | hormones_trt | longevity)
├── consultation_type ENUM (initial | follow_up)
├── scheduled_start_at TIMESTAMPTZ
├── scheduled_end_at TIMESTAMPTZ
├── actual_start_at TIMESTAMPTZ NULL
├── actual_end_at TIMESTAMPTZ NULL
├── status ENUM (scheduled | confirmed | in_progress | completed | cancelled | no_show)
├── video_room_id VARCHAR(100) NULL  -- 100ms room ID
├── video_session_id VARCHAR(100) NULL  -- 100ms session ID
├── recording_consent BOOL DEFAULT FALSE
├── recording_url VARCHAR(500) NULL  -- if recording_consent=true, encrypted S3 URL
├── pre_consultation_report_id UUID FK kc_pre_consultation_reports(id) NULL
├── consultation_fee_paise INT
├── payment_id UUID FK kc_payments(id) NULL
└── cancellation_reason VARCHAR(500) NULL
```

**kc_prescriptions**
```
kc_prescriptions
├── id UUID PK
├── consultation_id UUID FK kc_consultations(id)
├── doctor_id UUID FK dr_doctors(id)
├── patient_id UUID FK kc_patients(id)
├── status ENUM (draft | signed | dispensed | cancelled)
├── signed_at TIMESTAMPTZ NULL
├── pdf_url VARCHAR(500) NULL  -- generated post-signing
├── version INT DEFAULT 1  -- append-only; edits create new version
└── superseded_by_id UUID FK kc_prescriptions(id) NULL
```

**kc_prescription_items**
```
kc_prescription_items
├── id UUID PK
├── prescription_id UUID FK kc_prescriptions(id)
├── drug_generic_name VARCHAR(255)  -- INN/generic only; never brand in DB
├── drug_form ENUM (tablet | capsule | syrup | injection | topical | other)
├── dosage VARCHAR(100)  -- "50mcg", "1 tablet", "5mg"
├── frequency VARCHAR(100)  -- "once daily", "twice daily after meals"
├── duration_days INT NULL
├── instructions TEXT
├── refill_allowed BOOL DEFAULT FALSE
└── order_index INT
```

**kc_lab_orders**
```
kc_lab_orders
├── id UUID PK
├── consultation_id UUID FK kc_consultations(id) NULL
├── doctor_id UUID FK dr_doctors(id)
├── patient_id UUID FK kc_patients(id)
├── tests JSONB  -- [{name, code, urgency}]
├── status ENUM (ordered | sample_collected | resulted | reviewed | superseded)
├── lab_name VARCHAR(255) NULL  -- patient's choice; not pre-bound
├── result_uploaded_at TIMESTAMPTZ NULL
├── result_file_url VARCHAR(500) NULL  -- S3 ap-south-1
├── parsed_json JSONB NULL  -- OCR output
├── ocr_confidence_avg DECIMAL(3,2) NULL
└── reviewed_at TIMESTAMPTZ NULL
```

**kc_lab_reports** (patient-uploaded reports, not from kc_lab_orders)
```
kc_lab_reports
├── id UUID PK
├── patient_id UUID FK kc_patients(id)
├── uploaded_by_user_id UUID FK users(id)
├── source ENUM (kyros_order | patient_upload)
├── lab_order_id UUID FK kc_lab_orders(id) NULL
├── lab_name VARCHAR(255)
├── report_date DATE
├── file_url VARCHAR(500)  -- S3 ap-south-1
├── parsed_json JSONB  -- OCR output: [{biomarker_name, value, unit, ref_low, ref_high, flag}]
├── ocr_confidence_avg DECIMAL(3,2)
├── patient_corrected BOOL DEFAULT FALSE
└── doctor_reviewed_by UUID FK dr_doctors(id) NULL
```

**kc_doctor_notes**
```
kc_doctor_notes
├── id UUID PK
├── consultation_id UUID FK kc_consultations(id)
├── doctor_id UUID FK dr_doctors(id)
├── patient_id UUID FK kc_patients(id)
├── note_type ENUM (clinical | coordinator_only | patient_visible | private)
├── content TEXT
├── version INT DEFAULT 1  -- append-only
└── superseded_by_id UUID FK kc_doctor_notes(id) NULL
```

**kc_pre_consultation_reports**
```
kc_pre_consultation_reports
├── id UUID PK
├── patient_id UUID FK kc_patients(id)
├── consultation_id UUID FK kc_consultations(id) UNIQUE
├── generated_at TIMESTAMPTZ
├── lab_summary JSONB  -- key biomarkers + trends since last consult
├── adherence_summary JSONB  -- medication/supplement compliance rate
├── wearable_summary JSONB  -- steps/HR/sleep averages
├── patient_flags JSONB  -- concerns flagged in pre-consult questionnaire
├── intake_responses JSONB  -- pre-consult questionnaire
├── pdf_url VARCHAR(500)
├── doctor_reviewed_at TIMESTAMPTZ NULL
└── doctor_notes_pre_consult TEXT NULL  -- doctor's prep notes
```

**kc_education_assignments**
```
kc_education_assignments
├── id UUID PK
├── content_id UUID FK kc_education_content(id)
├── patient_id UUID FK kc_patients(id)
├── assigned_by_doctor_id UUID FK dr_doctors(id)
├── consultation_id UUID FK kc_consultations(id) NULL
├── read_at TIMESTAMPTZ NULL
└── notes VARCHAR(500)
```

**kc_education_content**
```
kc_education_content
├── id UUID PK
├── title VARCHAR(255)
├── slug VARCHAR(255) UNIQUE
├── content_type ENUM (article | video | pdf)
├── condition_category JSONB  -- array of verticals it applies to
├── content_url VARCHAR(500)
├── body_md TEXT  -- for articles
├── reviewed_by_doctor_id UUID FK dr_doctors(id)
├── reviewed_at TIMESTAMPTZ
├── status ENUM (draft | published | archived)
└── ai_disclosure BOOL DEFAULT FALSE  -- if AI-generated, must disclose
```

**kc_payments**
```
kc_payments
├── id UUID PK
├── user_id UUID FK users(id)
├── consultation_id UUID FK kc_consultations(id) NULL
├── razorpay_order_id VARCHAR(100) UNIQUE
├── razorpay_payment_id VARCHAR(100) NULL
├── amount_paise INT
├── currency VARCHAR(3) DEFAULT 'INR'
├── status ENUM (created | attempted | paid | failed | refunded | partial_refunded)
├── gst_invoice_number VARCHAR(50) NULL
└── gst_invoice_url VARCHAR(500) NULL
```

### Doctor domain (`dr_*`)

**dr_doctors**
```
dr_doctors
├── id UUID PK
├── user_id UUID FK users(id) UNIQUE
├── nmc_registration_number VARCHAR(50) UNIQUE
├── nmc_state_council VARCHAR(100)
├── verified_at TIMESTAMPTZ NULL
├── specialty JSONB  -- ["endocrinologist", "general_medicine"]
├── conditions_treated JSONB  -- vertical codes from condition_category enum
├── consultation_languages JSONB  -- ["en", "hi"]
├── status ENUM (applied | documents_submitted | verified | onboarding | active | inactive | suspended)
├── consultation_duration_minutes_default INT DEFAULT 20
├── revenue_share_pct DECIMAL(5,2)  -- e.g., 50.00 = 50%
├── bank_details_encrypted BYTEA  -- KMS-encrypted blob
├── bio_short VARCHAR(500)
├── bio_long TEXT
├── photo_url VARCHAR(500)
└── onboarding_stage VARCHAR(50)
```

**dr_availability**
```
dr_availability
├── id UUID PK
├── doctor_id UUID FK dr_doctors(id)
├── slot_start TIMESTAMPTZ
├── slot_end TIMESTAMPTZ
├── status ENUM (available | booked | blocked)
├── consultation_id UUID FK kc_consultations(id) NULL
└── UNIQUE (doctor_id, slot_start)
```

**dr_credentials** (for audit + display)
```
dr_credentials
├── id UUID PK
├── doctor_id UUID FK dr_doctors(id)
├── credential_type ENUM (mbbs | md | dnb | dm | mch | fellowship | certification)
├── institution VARCHAR(255)
├── year INT
├── document_url VARCHAR(500) NULL
└── verified_by_admin_id UUID FK users(id) NULL
```

### Admin/operational domain (`ad_*`)

**ad_coordinators**
```
ad_coordinators
├── id UUID PK
├── user_id UUID FK users(id) UNIQUE
├── status ENUM (active | inactive)
├── assigned_patient_ids JSONB  -- array of kc_patients.id
└── employee_id VARCHAR(50) NULL
```

**ad_audit_log** — every authorisation decision + every PHI access
```
ad_audit_log
├── id UUID PK
├── actor_user_id UUID FK users(id)
├── actor_role ENUM (patient | doctor | coordinator | super_admin | system)
├── action VARCHAR(100)  -- "view_patient", "create_prescription", "access_lab_report"
├── resource_type VARCHAR(100)
├── resource_id UUID
├── allowed BOOL
├── reason VARCHAR(255) NULL  -- if denied, why
├── ip_address INET
├── user_agent VARCHAR(500)
├── timestamp TIMESTAMPTZ DEFAULT NOW()
└── metadata JSONB
```

**ad_consent_records** — DPDP consent capture
```
ad_consent_records
├── id UUID PK
├── user_id UUID FK users(id)
├── consent_type ENUM (terms | privacy | telemedicine | data_processing | health_sync | marketing | recording | research)
├── version VARCHAR(20)  -- "v2.0" — consent text version
├── granted BOOL
├── granted_at TIMESTAMPTZ
├── revoked_at TIMESTAMPTZ NULL
├── ip_address INET
└── consent_text_hash VARCHAR(64)  -- SHA-256 of the consent text shown
```

**ad_data_subject_requests** — DPDP data principal rights
```
ad_data_subject_requests
├── id UUID PK
├── user_id UUID FK users(id)
├── request_type ENUM (access | correction | erasure | grievance)
├── status ENUM (received | in_progress | completed | rejected)
├── received_at TIMESTAMPTZ
├── completed_at TIMESTAMPTZ NULL
└── notes TEXT
```

---

## 3. API Route Map with RBAC

### Public (no auth)

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/public/conditions` | List of 7 verticals |
| POST | `/v1/public/lead` | Lead magnet signups |
| POST | `/v1/public/booking-inquiry` | Pre-account booking inquiry |
| GET | `/v1/public/doctors` | Public doctor directory (limited fields) |

### Patient (`/v1/clinic/patient/*` + `/v1/wellness/*`)

RBAC: `enforce_role("patient")`, scoped to `user_id`.

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/clinic/patient/consultations` | List own consultations |
| GET | `/v1/clinic/patient/consultations/{id}` | Detail; cross-user → 404 |
| POST | `/v1/clinic/patient/consultations` | Book consultation |
| POST | `/v1/clinic/patient/consultations/{id}/reschedule` | |
| POST | `/v1/clinic/patient/consultations/{id}/cancel` | |
| GET | `/v1/clinic/patient/consultations/{id}/join` | Get 100ms join token |
| GET | `/v1/clinic/patient/prescriptions` | List own |
| GET | `/v1/clinic/patient/prescriptions/{id}` | Detail; cross-user → 404 |
| GET | `/v1/clinic/patient/prescriptions/{id}/pdf` | Signed URL to PDF |
| GET | `/v1/clinic/patient/lab-reports` | List own |
| POST | `/v1/clinic/patient/lab-reports` | Upload report (multipart) |
| GET | `/v1/clinic/patient/lab-reports/{id}` | Detail with parsed biomarkers |
| PATCH | `/v1/clinic/patient/lab-reports/{id}` | Correct OCR results |
| GET | `/v1/clinic/patient/pre-consultation-reports/{consultation_id}` | Get report |
| GET | `/v1/clinic/patient/education` | List assigned education |
| POST | `/v1/clinic/patient/education/{id}/read` | Mark as read |
| GET | `/v1/clinic/patient/biomarker-trends/{biomarker}` | Trend chart data |
| GET | `/v1/wellness/reminders` | List own reminders |
| POST | `/v1/wellness/reminders` | Create reminder |
| PATCH | `/v1/wellness/reminders/{id}` | Edit |
| DELETE | `/v1/wellness/reminders/{id}` | |
| POST | `/v1/wellness/reminders/{id}/log` | Log adherence (taken/skipped/snoozed) |
| POST | `/v1/wellness/health-sync` | Batch upload HealthKit/Health Connect data |
| GET | `/v1/wellness/health-data/{type}` | Time series for a given type |
| GET | `/v1/users/me` | Own profile |
| PATCH | `/v1/users/me` | Edit own profile |
| POST | `/v1/users/me/data-export` | DPDP access request |
| POST | `/v1/users/me/delete` | DPDP erasure request |

### Doctor (`/v1/doctor/*`)

RBAC: `enforce_role("doctor")`, scoped to doctor's panel patients (cross-doctor patient access → 404).

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/doctor/dashboard` | Today's consults + pending actions |
| GET | `/v1/doctor/patients` | List own panel patients |
| GET | `/v1/doctor/patients/{id}` | Detail; not own patient → 404 |
| GET | `/v1/doctor/patients/{id}/consultations` | Patient's consult history with this doctor |
| GET | `/v1/doctor/patients/{id}/labs` | All labs for this patient |
| GET | `/v1/doctor/patients/{id}/prescriptions` | All prescriptions |
| GET | `/v1/doctor/patients/{id}/health-data/{type}` | Wearable trends |
| GET | `/v1/doctor/consultations/today` | |
| GET | `/v1/doctor/consultations/upcoming` | |
| GET | `/v1/doctor/consultations/{id}` | Detail |
| GET | `/v1/doctor/consultations/{id}/join` | Get 100ms host join token |
| POST | `/v1/doctor/consultations/{id}/notes` | Add note (append-only) |
| GET | `/v1/doctor/consultations/{id}/pre-consultation-report` | Get patient's report |
| PATCH | `/v1/doctor/consultations/{id}/pre-consultation-report` | Add doctor prep notes |
| POST | `/v1/doctor/consultations/{id}/prescription` | Create prescription |
| POST | `/v1/doctor/prescriptions/{id}/sign` | Doctor digital sign |
| POST | `/v1/doctor/consultations/{id}/lab-order` | Order labs |
| POST | `/v1/doctor/consultations/{id}/education` | Assign education |
| GET | `/v1/doctor/schedule` | Get availability |
| POST | `/v1/doctor/schedule/availability` | Add availability slots |
| PATCH | `/v1/doctor/schedule/availability/{id}` | Block/unblock |
| GET | `/v1/doctor/me` | Own profile |
| PATCH | `/v1/doctor/me` | Edit |

### Super Admin (`/v1/admin/*`)

RBAC: `enforce_role("super_admin")`, no patient/doctor scoping.

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/admin/dashboard` | Platform-wide metrics |
| GET | `/v1/admin/users` | List all users |
| GET | `/v1/admin/users/{id}` | Detail |
| POST | `/v1/admin/users/{id}/role` | Promote/demote |
| POST | `/v1/admin/users/{id}/suspend` | |
| POST | `/v1/admin/users/{id}/restore` | |
| GET | `/v1/admin/doctors/pipeline` | Doctor onboarding pipeline |
| POST | `/v1/admin/doctors/{id}/verify` | NMC verification approval |
| POST | `/v1/admin/doctors/{id}/activate` | Activate panel doctor |
| GET | `/v1/admin/consultations` | All consultations |
| POST | `/v1/admin/consultations/{id}/refund` | Trigger Razorpay refund |
| GET | `/v1/admin/content` | Education content library |
| POST | `/v1/admin/content/{id}/approve` | Doctor-reviewed approval |
| GET | `/v1/admin/audit-log` | Full audit log |
| GET | `/v1/admin/coordinators` | List coordinators |
| POST | `/v1/admin/coordinators/{id}/assign-patients` | Assign patient panel |
| GET | `/v1/admin/analytics/funnel` | Acquisition funnel |
| GET | `/v1/admin/analytics/retention` | Cohort retention |
| GET | `/v1/admin/analytics/revenue` | Revenue dashboards |

### Care Coordinator (`/v1/admin/coordinator/*`)

RBAC: `enforce_role("coordinator")`, scoped to `ad_coordinators.assigned_patient_ids`.

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/admin/coordinator/dashboard` | Today's intake queue + flags |
| GET | `/v1/admin/coordinator/patients` | Assigned patients only |
| GET | `/v1/admin/coordinator/patients/{id}` | Limited fields only: name/age/gender/conditions; **NO** lab values, prescription content, doctor notes |
| GET | `/v1/admin/coordinator/intake-queue` | New consultation requests |
| POST | `/v1/admin/coordinator/intake/{id}/triage` | Assign doctor, confirm slot |
| GET | `/v1/admin/coordinator/schedule` | All doctors' availability (read-only) |
| POST | `/v1/admin/coordinator/schedule/book` | Book on behalf of patient |
| POST | `/v1/admin/coordinator/communications/whatsapp` | Send WhatsApp template message |
| POST | `/v1/admin/coordinator/communications/email` | Send templated email |
| GET | `/v1/admin/coordinator/communications/log` | Communication history |

---

## 4. RBAC Implementation

### Roles

```python
class Role(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    COORDINATOR = "coordinator"
    SUPER_ADMIN = "super_admin"
    SYSTEM = "system"  # for Celery tasks
```

### Dependency pattern

```python
def enforce_role(*allowed: Role):
    async def dep(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in [r.value for r in allowed]:
            raise HTTPException(status_code=403, detail="forbidden")
        return current_user
    return dep
```

### Cross-user 404 pattern

For resources scoped to a user, unauthorised access returns 404 (not 403) to prevent resource enumeration:

```python
async def get_consultation_for_patient(
    consultation_id: UUID,
    current_user: User = Depends(enforce_role(Role.PATIENT)),
    db: AsyncSession = Depends(get_db),
) -> Consultation:
    consult = await db.scalar(
        select(Consultation)
        .join(Patient, Consultation.patient_id == Patient.id)
        .where(
            Consultation.id == consultation_id,
            Patient.user_id == current_user.id,
            Consultation.deleted_at.is_(None),
        )
    )
    if consult is None:
        await audit_log(current_user, "view_consultation", "consultation", consultation_id, allowed=False, reason="not_own_or_not_found")
        raise HTTPException(status_code=404, detail="not found")
    await audit_log(current_user, "view_consultation", "consultation", consultation_id, allowed=True)
    return consult
```

The same pattern for doctor (scoped to doctor's panel) and coordinator (scoped to `assigned_patient_ids`).

### Audit log on every authorisation decision

Every endpoint dependency wraps `audit_log()` regardless of success/failure. Stored in `ad_audit_log`.

---

## 5. OCR Pipeline (Lab Reports)

### Provider: Google Document AI

Decision rationale lives in counsel notes (Google Document AI 95.8% vs Textract 94.2% on Braincuber 2026 benchmark; better on degraded Indian lab PDF scans; built-in healthcare/identity parsers; 200+ language support).

### Configuration

- Region: `asia-south1` (Mumbai) — DPDP requirement
- Processor: **Healthcare Document Parser** (production) + **OCR Processor** (fallback for non-medical scans)
- Service account credentials stored in AWS Secrets Manager; rotated quarterly

### Flow

```
Patient uploads lab report
     ↓
POST /v1/clinic/patient/lab-reports (multipart)
     ↓
File stored in S3 ap-south-1 with KMS encryption
     ↓
kc_lab_reports row created with status=ocr_pending
     ↓
Celery task parse_lab_report(report_id) dispatched
     ↓
Document AI called with file from S3
     ↓
Healthcare parser extracts: biomarker name, value, unit, ref range, flag
     ↓
For each biomarker:
  - confidence < 0.85 → mark for doctor review
  - confidence < 0.60 → require patient correction before saving
     ↓
parsed_json + ocr_confidence_avg saved to kc_lab_reports
     ↓
Patient receives push notification + WhatsApp utility message
     ↓
If linked to consultation, doctor sees in pre-consultation report
```

### Parsed JSON shape

```json
{
  "lab_name": "Redcliffe Labs",
  "report_date": "2026-05-20",
  "patient_info": {
    "name_on_report": "Niranjan K",
    "age": 35,
    "gender": "M"
  },
  "biomarkers": [
    {
      "name": "TSH",
      "value": "4.82",
      "unit": "mIU/L",
      "ref_low": "0.4",
      "ref_high": "4.0",
      "flag": "high",
      "confidence": 0.94
    }
  ],
  "overall_confidence": 0.91
}
```

### Manual correction

`PATCH /v1/clinic/patient/lab-reports/{id}` allows the patient to correct OCR results before save. Each corrected field flags `patient_corrected = TRUE` and reduces future trust scoring on similar layouts.

---

## 6. Video Consultation Integration (100ms)

### Provider: 100ms

Indian-origin SFU-based video. Twilio Video reached EOL on 5 December 2024 — out of consideration. 100ms India-region data residency available.

### Configuration

- Region: India (Mumbai data center)
- Recording: opt-in only, stored encrypted in S3 ap-south-1
- Side-panel UI: 100ms supports custom UI; doctor side-panel shows patient labs + prescriptions during call
- Mobile SDK: `@100mslive/react-native-room-kit`
- Web SDK: `@100mslive/react-room-kit`

### Flow

```
Consultation scheduled
     ↓
At T-15min, Celery task provisions 100ms room
     ↓
kc_consultations.video_room_id stored
     ↓
Patient and doctor receive notification with deeplink
     ↓
Patient/doctor opens app → calls GET /v1/clinic/patient/consultations/{id}/join (or /v1/doctor/...)
     ↓
Backend generates role-scoped JWT (patient_role or doctor_role)
     ↓
Client SDK joins room with JWT
     ↓
Doctor's side-panel UI loads patient context via parallel API calls
     ↓
Consultation happens
     ↓
On end: doctor prompted for notes + prescription + lab order
     ↓
Recording (if consented) processed by 100ms → URL stored in kc_consultations.recording_url
```

### Recording consent

Recording is **opt-in per consultation**, not blanket. Surface a consent dialog before the call starts on both sides. Record consent decision in `ad_consent_records`.

---

## 7. Health Data Sync (HealthKit + Health Connect)

### Stack

- **iOS:** `@kingstinct/react-native-healthkit` — Swift-based, TypeScript-first, actively maintained
- **Android:** `react-native-health-connect` (matinzd) — de facto standard
- **Custom dev client required:** `expo-dev-client` + `npx expo prebuild`. Not available in Expo Go.

### Data points synced (Phase A)

| Type | iOS (HealthKit) | Android (Health Connect) | Cadence |
|---|---|---|---|
| Steps | `HKQuantityTypeIdentifierStepCount` | `Steps` | Daily aggregate |
| Heart rate | `HKQuantityTypeIdentifierHeartRate` | `HeartRate` | Per-reading |
| Resting HR | `HKQuantityTypeIdentifierRestingHeartRate` | `RestingHeartRate` | Daily |
| HRV | `HKQuantityTypeIdentifierHeartRateVariabilitySDNN` | `HeartRateVariabilityRmssd` | Daily |
| Sleep duration | `HKCategoryTypeIdentifierSleepAnalysis` | `SleepSession` | Per-session |
| Weight | `HKQuantityTypeIdentifierBodyMass` | `Weight` | Per-reading |
| Blood pressure | `HKCorrelationTypeIdentifierBloodPressure` | `BloodPressure` | Per-reading |
| Blood glucose | `HKQuantityTypeIdentifierBloodGlucose` | `BloodGlucose` | Per-reading |
| Workout | `HKWorkoutType` | `ExerciseSession` | Per-session |

### Flow

```
User grants HealthKit/Health Connect permissions in onboarding
     ↓
ad_consent_records row created (consent_type=health_sync)
     ↓
Background sync runs every 4 hours when app is active or via Background Tasks (iOS) / WorkManager (Android)
     ↓
Last 7 days of data fetched from native API
     ↓
Datapoints batched into POST /v1/wellness/health-sync
     ↓
Backend deduplicates on (user_id, source, source_record_id)
     ↓
wn_health_datapoints rows inserted into monthly partition
     ↓
wn_health_sync_sessions row records the sync
     ↓
Trends recomputed lazily on chart query
```

### DPDP compliance

- All synced data transmitted to `ap-south-1`
- Explicit consent at HealthKit/Health Connect authorisation
- Data categories documented in DPDP Notice
- Consent revocable from app settings → triggers data deletion workflow

---

## 8. Public Website (Next.js)

### Stack

- Next.js 14 App Router, TypeScript, Tailwind
- next-mdx-remote for articles
- Static generation for SEO; ISR for content updates
- Hosted on Vercel (India region) or self-hosted on EC2 ap-south-1

### Routes

```
/                              Home
/conditions                    All 7 verticals overview
/conditions/thyroid            Thyroid condition page
/conditions/weight-management
/conditions/pcos
/conditions/skin-and-hair
/conditions/mens-intimate-health
/conditions/hormones-trt
/conditions/longevity
/learn/{vertical}/{slug}       Long-tail SEO articles
/doctors                       Public doctor directory
/doctors/{slug}                Individual doctor profile
/pricing                       Pricing
/how-it-works                  Process explanation
/about                         About + honest startup state
/advisory-board                With placeholder pattern
/our-doctors                   With placeholder pattern
/for-doctors                   Doctor recruitment landing
/faq                           Faq
/contact                       Contact form
/legal/privacy                 DPDP privacy notice
/legal/terms                   Terms of use
/legal/telemedicine-consent    NMC TPG consent
/legal/data-deletion           DPDP data deletion process
```

### Schema markup

Every condition page emits `MedicalCondition` + `MedicalWebPage`. Every learn article emits `Article` + `Person` (doctor author). Every doctor profile emits `Physician` + `Person`. FAQ pages emit `FAQPage`.

### Content production

- Articles authored in MDX with frontmatter: `title`, `slug`, `vertical`, `doctor_author_id`, `doctor_reviewed_at`, `references`
- Doctor byline auto-rendered from frontmatter
- `Medically reviewed` date stamp
- References section with Indian primary sources

### Phase scope

**Only Phase A surfaces on the public website.** Wearables (Phase B) and AI (Phase C) never appear in marketing copy. Patient-facing wearable features exist only inside the authenticated app under explicit consent + disclosure.

### Conversion architecture

- Primary CTA: "Talk to a doctor" / "Take the assessment"
- Booking flow: condition selection → symptom questionnaire → care coordinator triage → slot booking
- Pre-consultation consent page (DPDP + NMC TPG)
- Honest startup state: only on About, Advisory Board, Our Doctors, Testimonials placeholder

---

## 9. Patient Mobile App (Expo React Native)

### Stack

- Expo 51+ with custom dev client (not Expo Go)
- TypeScript strict
- expo-router for file-based navigation
- TanStack Query v5
- Victory Native XL for charts
- Lucide React Native for icons
- Cormorant Garamond + DM Sans loaded via expo-font

### Module structure

```
mobile/app/
├── (auth)/
│   ├── login.tsx
│   ├── signup.tsx
│   └── verify-otp.tsx
├── (onboarding)/
│   ├── welcome.tsx
│   ├── conditions.tsx        # which conditions are you addressing
│   ├── intake-form.tsx       # condition-specific intake
│   ├── consent.tsx           # DPDP + telemedicine consent
│   └── health-sync.tsx       # HealthKit/Health Connect permission
├── (tabs)/
│   ├── home.tsx              # dashboard
│   ├── consultations.tsx     # consultation hub
│   ├── reports.tsx           # labs + prescriptions
│   ├── reminders.tsx         # wellness reminders
│   └── profile.tsx
├── consultations/
│   ├── [id].tsx              # consultation detail
│   ├── book.tsx              # booking flow
│   └── join/[id].tsx         # video join screen
├── lab-reports/
│   ├── upload.tsx            # camera + file picker
│   ├── [id].tsx              # report detail with biomarkers
│   └── correct/[id].tsx      # OCR correction
├── prescriptions/
│   └── [id].tsx              # prescription detail
├── biomarkers/
│   └── [name].tsx            # trend chart for a biomarker
├── education/
│   └── [id].tsx              # education content viewer
└── settings/
    ├── data-export.tsx
    ├── data-deletion.tsx
    └── notifications.tsx
```

### Feature modules

#### 9.1 Consultation Hub

- Schedule new consultation: condition → slot picker → payment (Razorpay) → confirmation
- Reschedule / cancel with policy display
- Upcoming consultation with countdown
- Consultation history with notes + prescription + labs linked
- Pre-consultation questionnaire flow
- From a consultation detail: linked labs, prescriptions, education, consolidated report

#### 9.2 Lab Reports (Flagship Feature)

- Upload any lab report (Kyros-ordered or external):
    - Camera capture
    - PDF upload
    - File picker
- OCR runs server-side; patient sees progress indicator
- Manual correction interface before save
- Biomarker visualization:
    - Individual trend charts (7d/30d/90d/1y/all) using Victory Native XL
    - Reference range bands (sage tint for normal, saffron for warning, alert red for critical)
    - "Better / steady / worse" trend indicator with subtle animation
- Consolidated lab view: all biomarkers from one report, grouped by panel
- Historical comparison: same biomarker across multiple reports overlaid
- Flagged tests summary: out-of-range values sorted by severity
- Doctor commentary on specific biomarkers (added by doctor, visible to patient)

#### 9.3 Prescriptions

- Historical prescriptions with timeline
- Each prescription: drug generic name, dosage, frequency, duration, instructions
- Dosage change tracking: visualization of dosage changes over time (e.g., levothyroxine 25mcg → 50mcg → 75mcg)
- Linked to consultation
- PDF download

#### 9.4 Wellness Reminders

- Water intake (interval-based, configurable window)
- Medication (linked to prescriptions where possible)
- Supplement intake
- Manual custom reminders
- Gym/workout reminders
- Adherence logging: taken / skipped / snoozed

#### 9.5 Health Data Integration

- HealthKit (iOS) + Health Connect (Android) sync
- Synced data visualized alongside lab trends
- Manual entry fallback

#### 9.6 Consolidated Doctor Report (Pre-Consultation)

- Auto-generated 24h before each consultation
- Patient sees the same report the doctor sees (no information asymmetry)
- Components: lab trend summary, medication adherence, wearable data, intake responses, patient-flagged concerns
- PDF downloadable

#### 9.7 Education

- Condition-specific content assigned by doctor
- Library browsable
- Read/watched tracking

#### 9.8 Profile & Privacy

- DPDP rights surfaced as first-class actions: View / Download / Delete my data
- ABHA linking (optional)
- Notification preferences
- Privacy-first UI: phone/address masked by default, "verify to view"
- Notifications use generic language ("Your appointment is confirmed") — never condition names in push text

---

## 10. Patient Web Portal (React Native Web)

### Why RNW

Single Expo codebase serves mobile + responsive web with ~85% component reuse. Same data, same features, responsive design.

- Desktop: sidebar navigation
- Mobile web: bottom tab bar (same as mobile app)
- Chart interactions: hover tooltips on trend lines, zoomable time ranges
- File upload via drag-and-drop on desktop
- Print view for lab reports and prescriptions

The public website (kyrosclinic.com) remains a separate Next.js app (SEO-critical, static-generated). The authenticated patient portal uses RNW.

---

## 11. Doctor Portal (React + Vite)

### Stack

- React 18, Vite 5, TypeScript strict
- Tailwind with shared design tokens
- shadcn/ui base components (mention to user when adding)
- TanStack Query v5
- Recharts for charts
- 100ms web SDK for video

### Module structure

```
doctor-portal/src/
├── routes/
│   ├── dashboard.tsx
│   ├── patients/
│   │   ├── index.tsx          # list
│   │   └── [id].tsx           # patient detail
│   ├── consultations/
│   │   ├── today.tsx
│   │   ├── upcoming.tsx
│   │   └── [id].tsx           # consultation view with video + side panel
│   ├── schedule.tsx
│   └── profile.tsx
├── components/
│   ├── ConsultationVideoLayout.tsx
│   ├── PatientContextPanel.tsx
│   ├── PrescriptionBuilder.tsx
│   ├── LabOrderBuilder.tsx
│   └── NotesPanel.tsx
└── lib/
```

### Module detail

#### 11.1 Doctor Dashboard
- Today's consultations with countdown
- Patient queue: pre-consultation flags
- Recent activity
- Pending actions
- Quick stats

#### 11.2 Pre-Consultation Preparation
- Auto-generated consolidated patient report (same as patient sees)
- Doctor can annotate ("reviewed", prep notes)
- Doctor can add "doctor-only" notes invisible to patient

#### 11.3 Consultation Interface
- Video call (100ms web SDK) on left
- Side panel: patient history, consolidated report, previous prescriptions, lab results
- Real-time notes panel during consultation
- Post-call: structured notes, prescription, lab order, follow-up, education assignment

#### 11.4 Patient Management
- Patient list with search/filter
- Patient detail:
    - Demographics, conditions
    - Consultation history with notes
    - Lab reports with trend charts
    - Prescription history with dosage changes
    - Wearable data trends
    - Reminder adherence
    - Education assignments

#### 11.5 Prescription Issuance
- Prescription builder
- IMC format output
- Dosage titration tracking
- Sign-off required before patient visibility
- Drug lookup (generic name, standard dosages — see clinical-compliance for vocabulary rules)

#### 11.6 Lab Report Review
- Review uploaded reports
- Doctor commentary on biomarkers
- Flag tests for patient attention
- Order new labs

#### 11.7 Schedule Management
- View upcoming slots
- Mark availability
- Consultation duration preferences
- Buffer time settings

#### 11.8 Doctor Profile
- NMC registration (read-only, verified by super admin)
- Specialty credentials
- Conditions treated
- Languages
- Bank details for revenue share (edit with verification)

---

## 12. Super Admin Portal (Jinja2 + HTMX)

### Stack

- Jinja2 templates served by FastAPI
- HTMX 2.0 for partial updates
- Alpine.js for small interactions
- Tailwind with shared design tokens

### Module structure

```
backend/admin_ui/templates/
├── base.html
├── dashboard.html
├── users/
├── doctors/
│   ├── pipeline.html
│   └── detail.html
├── consultations/
├── content/
│   ├── library.html
│   └── approval.html
├── analytics/
├── audit-log.html
└── coordinators/
```

### Modules

#### 12.1 Platform Dashboard
- Total users, doctors, coordinators
- New registrations (daily/weekly/monthly)
- Active consultations
- Revenue (Razorpay payment breakdown)
- Lab reports OCR queue
- Platform health (uptime, DB, Redis, last migration, Sentry error rate)

#### 12.2 User Management
- All users searchable
- Patient detail, doctor detail, coordinator detail
- Role assignment
- Subscription tier
- Suspend / delete (DPDP workflow trigger)

#### 12.3 Doctor Onboarding
- Application pipeline: Applied → Documents Submitted → Verified → Onboarding → Active
- NMC number verification
- Specialty + conditions setup
- Revenue share percentage

#### 12.4 Consultation Management
- All consultations across all doctors
- Override actions: reschedule, cancel, refund (Razorpay refund initiation)
- Dispute log

#### 12.5 Content Management
- Education content library
- Approval status (draft, doctor-reviewed, published)
- Condition mapping
- Doctor reviewer assignments

#### 12.6 Platform Configuration
- Pricing per condition/duration
- Revenue share percentages
- Reminder channel configuration
- Notification templates (WhatsApp, email)
- Feature flags

#### 12.7 Analytics & Reporting
- Acquisition funnel
- Cohort retention
- Doctor utilization
- Condition mix
- Revenue by condition/doctor/time
- CSV export

#### 12.8 Audit Log
- Full audit trail
- Filter by actor, action, date
- PHI redaction for coordinator views

---

## 13. Care Coordinator Portal (Jinja2 + HTMX)

### Access level

Assigned patients only. No cross-coordinator visibility. **No financial data, no platform configuration, no clinical content (lab values, prescriptions, doctor notes).** Minimum necessary clinical data only.

### Modules

#### 13.1 Coordinator Dashboard
- Today's intake queue
- Scheduled consultations for today/this week
- Patient flags (high-severity intake responses)
- Pending follow-up (patients past 14 days without follow-up booking)
- Unread WhatsApp/email threads

#### 13.2 Intake & Triage
- New consultation requests with intake summary
- Triage decision: confirm → assign doctor → notify patient
- Escalate emergency symptoms to super admin
- Coordinator notes added before passing to doctor

#### 13.3 Patient Communication
- WhatsApp thread per patient (via Business API)
- Email thread per patient
- Communication templates: appointment confirmation, reminder, pre-consultation instructions, post-consultation follow-up
- Communication log
- **Cannot send clinical advice** — scheduling, logistics, general support only

#### 13.4 Scheduling
- Doctor availability calendar (read-only)
- Book on behalf of patient
- Reschedule/cancel with notification
- Waitlist management

#### 13.5 Patient Profile (Limited View)
- Name, age, gender, conditions being treated
- Consultation history: **dates, doctors, status only** (no notes, no lab values, no prescription details)
- Contact information
- Coordinator notes (visible to coordinators + super admin)

### What coordinators CANNOT see

- Lab report values or trends
- Prescription drug names or dosages
- Doctor consultation notes
- Wearable health data
- Financial/payment details
- Other coordinators' patient assignments
- Platform analytics or configuration

---

## 14. Infrastructure Plan

### Phase 1 (Pre-launch through ~₹50K MRR)

- **Compute:** Single EC2 t3.small (2 vCPU, 2 GB RAM) in ap-south-1
- **Database:** RDS db.t3.micro PostgreSQL 16 with daily snapshots
- **Cache:** ElastiCache Redis t3.micro for Celery + caching
- **Storage:** S3 ap-south-1 with KMS encryption (lab reports, prescriptions, recordings)
- **CDN:** CloudFront for public website + static assets
- **Email:** SendGrid India region or Postmark
- **SMS:** MSG91
- **WhatsApp:** AiSensy or Wati
- **Monitoring:** Sentry + AWS CloudWatch
- **Cost target:** ~₹15,000–25,000/month all-in

### Phase 2 trigger conditions (migrate to ECS Fargate)

Migrate when **either** of:
- MRR > ₹50,000/month
- Concurrent active users > 500

### Phase 2 (Post-trigger)

- **Compute:** ECS Fargate with auto-scaling (2 vCPU, 4 GB RAM tasks)
- **Database:** RDS Multi-AZ, db.t3.medium with read replicas in same AZ
- **Cache:** ElastiCache Redis Multi-AZ
- **Load balancer:** Application Load Balancer with TLS 1.3
- **WAF:** AWS WAF with managed rule sets
- **Video CDN:** Cloudflare Stream for consultation recordings
- **Cost target:** ~₹80,000–1,50,000/month

### Phase 2 time-series migration trigger

If `wn_health_datapoints` partition queries exceed 500ms p95 OR aggregate row count crosses 50M, evaluate TimescaleDB migration. Until then, PostgreSQL 16 with monthly partitioning + BRIN indexes handles ~10K patients × 365 days × 5 datapoint types = ~18M rows/year comfortably.

---

## 15. DPDP Compliance Architecture

The regulatory rationale lives in kyros-clinical-compliance. The technical implementation lives here.

### Data residency

All patient data — application database, S3 storage, OCR processing, video processing, voice synthesis metadata — resides in `ap-south-1` (Mumbai) or India region of the third-party service. Hard requirement.

### Encryption

- **At rest:** KMS-encrypted RDS, S3, EBS volumes
- **In transit:** TLS 1.3 mandatory; HSTS preload; certificate pinning on mobile clients
- **Application-level:** sensitive fields (bank details, NMC documents) encrypted with separate KMS key

### Consent management

- `ad_consent_records` table captures every consent decision with version + hash
- Consent revocable from patient app settings
- Consent revocation triggers async data deletion workflow

### Breach reporting

- Automated detection: Sentry alerts for unauthorized data access patterns
- Manual workflow: 72-hour reporting timeline to Data Protection Board
- Runbook: `docs/dpdp-breach-runbook.md`

### Data principal rights (DPDP §11–§14)

- **Access:** `POST /v1/users/me/data-export` — generates complete data export as ZIP within 7 days
- **Correction:** profile edit endpoints + lab report OCR correction
- **Erasure:** `POST /v1/users/me/delete` — soft delete with 30-day grace period, then hard delete from primary tables + S3 + backup retention queue
- **Grievance:** in-app form → routes to DPO email

### DPIA

A Data Protection Impact Assessment is mandatory before launch. Document at `docs/dpia-v1.md`. Updated annually.

### DPO

Designated DPO with public-facing email (`dpo@kyrosclinic.com`). For pre-launch and early Phase 1, the founder doubles as DPO with documented role description.

---

## 16. Pre-Consultation Report Generation

### Trigger

Celery task `generate_pre_consultation_report(consultation_id)` runs at:
- T-24h before scheduled consultation (scheduled cron)
- On-demand by doctor

### Inputs aggregated

| Source | Data | Time window |
|---|---|---|
| `kc_lab_reports` | Biomarkers + trends | 90 days |
| `kc_prescriptions` | Current + recent | 180 days |
| `wn_reminder_logs` | Medication adherence | 30 days |
| `wn_health_datapoints` | Steps, HR, sleep, weight | 30 days |
| `kc_consultations` | Previous notes (same doctor) | All time |
| Intake form responses | Patient-flagged concerns | Current consultation |

### Output

`kc_pre_consultation_reports` row with:
- `lab_summary`: top 5 biomarkers with direction of change
- `adherence_summary`: medication compliance rate %
- `wearable_summary`: average steps, resting HR, sleep duration
- `patient_flags`: array of flagged concerns
- `intake_responses`: full pre-consult questionnaire

PDF rendered with WeasyPrint, stored in S3 ap-south-1.

### Information symmetry

**Patient and doctor see identical content.** No "doctor sees more than patient." This is a locked product principle. The only doctor-only fields are doctor's own prep notes (`doctor_notes_pre_consult`), added by the doctor after review.

---

## 17. ABHA Integration Approach

ABHA (Ayushman Bharat Health Account) integration is **optional, not mandatory.**

### Milestones (sandbox → production)

- **M1 — ABHA Capture/Verification (Phase 1):** patient enters ABHA number or creates one via Aadhaar/mobile OTP. Kyros verifies via ABDM sandbox API.
- **M2 — Health Information Provider (Phase 2):** Kyros publishes consultation summaries, prescriptions, and lab reports to patient's ABHA-linked health locker on consent.
- **M3 — Health Information User (Phase 3+):** Kyros ingests external records (from other hospitals, labs) via patient consent flow.

### Timeline

- Sandbox registration (sandbox.abdm.gov.in): 2–4 weeks approval
- M1 implementation: 4–6 weeks development
- Production certification: 4–8 weeks
- Q4 2026 production target

### Cost

- Sandbox + certification: free
- Custom integration development: estimated $2,500+ (WEF analysis)
- Pre-built connectors available: EHR.Network ABDMc, Nirmitee.io

---

## 18. Phase Scope on Public Website

**Only Phase A surfaces on the public website.**

### Phase A (visible publicly, Year 1)

Doctor consultations, lab orders, prescriptions, dashboards, education content, wellness reminders.

### Phase B (in-app only, Year 2)

Wearables integration. **Never mentioned on public marketing site.** Surfaced only inside authenticated patient app after explicit health-sync consent.

### Phase C (internal/investor only, Year 3+)

AI-augmented care, digital twin framing. **Never on public site.** Discussed only in investor materials and internal product roadmap.

This phase scoping is a regulatory + brand decision: the wearables and AI stories are credibility weapons once they're real, not marketing claims while they're roadmap.

---

## 19. Claude Code Prompt Queue P1–P30

This section is the complete prompt queue, rebuilt from scratch. Each prompt is a self-contained Claude Code instruction with file scope and acceptance criteria. Prompts are sequenced for dependency order.

### Foundation (P1–P6)

#### P1 — Repository Scaffolding

Create the repository structure described in Section 1. Initialize:
- `backend/` with FastAPI 0.115, SQLAlchemy 2.0 async, Pydantic v2, Alembic, ruff, mypy strict, pytest
- `mobile/` with Expo 51 + TypeScript strict + expo-router
- `doctor-portal/` with Vite + React 18 + TypeScript strict + Tailwind
- `website/` with Next.js 14 App Router + TypeScript + Tailwind
- `design-tokens/` with `tokens.json` containing the locked palette and typography (per kyros-design-system)

**Acceptance:**
- `cd backend && uv sync && pytest` runs (zero tests OK)
- `cd mobile && pnpm install && pnpm typecheck` passes
- `cd doctor-portal && pnpm install && pnpm typecheck && pnpm build` passes
- `cd website && pnpm install && pnpm typecheck && pnpm build` passes
- Tailwind configs in all three frontends consume `design-tokens/tokens.json`

#### P2 — Database Foundation + Identity

In `backend/`:
- Configure SQLAlchemy async with asyncpg and ap-south-1 RDS connection settings
- Implement Alembic migration `01_initial_schema.py` creating `users`, `ad_consent_records`, `ad_audit_log`, `ad_data_subject_requests` tables per Section 2
- Implement `app/db/models/users.py`, `app/db/models/admin.py`
- Implement `app/core/security.py` with argon2id password hashing, JWT issue/verify
- Implement `app/api/v1/auth/` with `signup`, `login`, `verify-otp`, `refresh-token` endpoints
- Implement OTP via MSG91 integration in `app/integrations/msg91.py`

**Acceptance:**
- `alembic upgrade head` runs cleanly
- pytest covers signup → OTP verify → login → refresh flow
- JWT contains `user_id` + `role` claims
- Every auth event logged to `ad_audit_log`

#### P3 — RBAC Middleware + Consent Capture

In `backend/`:
- Implement `app/core/rbac.py` with `enforce_role()` dependency and `cross_user_404()` helper per Section 4
- Implement `app/services/consent.py` for capturing and revoking consent
- Implement `/v1/users/me`, `/v1/users/me/data-export`, `/v1/users/me/delete` endpoints
- Implement Celery task `app/tasks/data_subject_request.py` for DPDP access/erasure workflows

**Acceptance:**
- pytest: same-user can access own data (200); other-user access returns 404
- Consent decisions persisted with version hash
- Data export generates ZIP within 60s for test fixtures
- Erasure soft-deletes with 30-day grace period

#### P4 — Design Token Distribution

Convert `design-tokens/tokens.json` into:
- `mobile/lib/design-tokens.ts` (typed export)
- `doctor-portal/src/design-tokens.ts`
- `website/lib/design-tokens.ts`
- Tailwind config preset shared across all three frontends in `design-tokens/tailwind-preset.js`

Implement base primitives in each frontend per kyros-design-system: Button (Forest, Saffron, Outline, Ghost), Card (white-on-ivory, ivory-on-peach-mist), PullQuote (italic Cormorant, terracotta/saffron border), Stat, Tag.

**Acceptance:**
- All three frontends render a Storybook/showcase page demonstrating each primitive
- Color values trace to `tokens.json` (no hex literals in component code)
- Cormorant Garamond + DM Sans + Tiro Devanagari Hindi load correctly

#### P5 — Public Website Foundation (Next.js)

In `website/`:
- Implement home, conditions overview, 7 condition pages, how-it-works, pricing, about, advisory-board, our-doctors, for-doctors, faq, contact, legal pages (privacy, terms, telemedicine consent, data deletion)
- Apply visual rhythm 10-step pattern per kyros-design-system
- Schema markup: MedicalCondition, MedicalWebPage, Person, FAQPage, Article
- Honest startup state on About, Advisory Board, Our Doctors only
- Booking flow: condition → intake form → contact submission (no auth yet)

**Acceptance:**
- All pages render
- Lighthouse SEO score ≥ 95
- Lighthouse Performance ≥ 80 on mobile
- Schema markup validates in Google Rich Results Test
- Booking flow submits to `/v1/public/booking-inquiry`

#### P6 — Public Website Content System

In `website/`:
- Implement MDX content system at `content/learn/{vertical}/{slug}.mdx`
- Frontmatter: `title`, `slug`, `vertical`, `doctor_author_id`, `doctor_reviewed_at`, `references`
- Doctor byline auto-rendered with NMC reg number
- "Medically reviewed" date stamp
- References section with bibliography component
- URL structure: `/learn/{vertical}/{slug}/`
- Static generation + ISR for content updates
- Seed 3 example articles per vertical (21 articles total, placeholder doctor authors)

**Acceptance:**
- Articles render with byline, review date, references
- Sitemap.xml auto-generated
- Each article emits Article schema with Person (doctor) authorship

### Patient app foundation (P7–P12)

#### P7 — Patient Auth + Onboarding (Mobile)

In `mobile/`:
- Implement (auth) routes: login, signup, verify-otp
- Implement (onboarding) routes: welcome, conditions, intake-form, consent, health-sync
- Connect to backend `/v1/auth/*` endpoints
- DPDP consent capture flow (every consent dialog records version + hash)
- HealthKit/Health Connect permission flow (per Section 7)

**Acceptance:**
- Fresh install → onboarding completes → tab navigation visible
- Consent decisions persist server-side via `/v1/users/me/consent`
- HealthKit/Health Connect permissions visible in device settings post-grant

#### P8 — Wellness Domain Schema + Reminders

In `backend/`:
- Alembic migration `02_wellness_domain.py` creating `wn_reminders`, `wn_reminder_logs`, `wn_health_sync_sessions`, `wn_health_datapoints` (partitioned monthly) per Section 2
- Implement `/v1/wellness/reminders/*` endpoints
- Implement `/v1/wellness/reminders/{id}/log` for adherence tracking

In `mobile/`:
- Implement reminders tab: list, create, edit, delete
- Local notification scheduling via `expo-notifications`
- Tap notification → adherence logging dialog (taken/skipped/snoozed)

**Acceptance:**
- Patient creates a reminder; notification fires at scheduled time
- Tapping notification logs adherence to backend
- Reminder list shows adherence rate per reminder

#### P9 — Health Data Sync (Mobile + Backend)

In `mobile/`:
- Integrate `@kingstinct/react-native-healthkit` (iOS) and `react-native-health-connect` (Android)
- Background sync every 4 hours via Background Tasks (iOS) / WorkManager (Android)
- Last 7 days of data fetched per sync
- Batched POST to `/v1/wellness/health-sync`

In `backend/`:
- Implement `/v1/wellness/health-sync` POST endpoint
- Idempotent on `(user_id, source, source_record_id)`
- Refuse sync if consent revoked

**Acceptance:**
- Physical iPhone (custom dev client) syncs steps + heart rate
- Physical Android (Health Connect installed) syncs equivalent
- Re-syncing same datapoint is no-op
- Revoked consent returns 403

#### P10 — Kyros Clinic Schema (Patients, Doctors, Coordinators)

In `backend/`:
- Alembic migration `03_clinic_domain.py` creating `kc_patients`, `dr_doctors`, `dr_availability`, `dr_credentials`, `ad_coordinators` per Section 2
- Implement `app/db/models/clinic.py`, `app/db/models/doctor.py`, `app/db/models/coordinator.py`
- Seed development data: 3 demo doctors (different specialties), 1 coordinator, 5 demo patients

**Acceptance:**
- `alembic upgrade head` runs cleanly
- Seed data loads via `python -m scripts.seed_demo`
- Patient ↔ user 1:1 relationship enforced
- Doctor NMC registration number uniqueness enforced

#### P11 — Razorpay Integration

In `backend/`:
- Implement `app/integrations/razorpay.py` for order creation, payment capture, refund, GST invoicing
- Implement `kc_payments` table per Section 2
- Webhook endpoint `/v1/webhooks/razorpay` with signature verification
- RBI e-mandate flow for subscription billing (annual programs)

**Acceptance:**
- Test mode order creation works
- Webhook signature verification rejects tampered payloads
- Refund initiates and completes within Razorpay test mode
- GST invoice URL generated per successful payment

#### P12 — Consultation Booking + Schema

In `backend/`:
- Alembic migration `04_consultations.py` creating `kc_consultations`, `kc_doctor_notes`, `kc_pre_consultation_reports` per Section 2
- Implement `/v1/clinic/patient/consultations/*` endpoints
- Booking flow: slot lookup → payment intent → Razorpay order → booking confirmation
- Patient sees upcoming + history

In `mobile/`:
- Implement consultations tab and booking flow per Section 9.1
- Pre-consultation questionnaire flow

**Acceptance:**
- Patient books a consultation, pays via Razorpay test mode, sees confirmation
- Doctor's availability calendar reflects the booking
- Cancellation policy enforced (refund window, no-show handling)

### OCR + lab reports (P13–P15)

#### P13 — Google Document AI Integration

In `backend/`:
- Implement `app/integrations/document_ai.py` calling Healthcare Document Parser in `asia-south1` region
- Service account credentials via AWS Secrets Manager
- Confidence thresholding logic per Section 5

**Acceptance:**
- Test lab PDF processed end-to-end within 60s
- Parsed JSON shape matches Section 5 specification
- Low-confidence fields flagged

#### P14 — Lab Report Upload + OCR Pipeline

In `backend/`:
- Alembic migration `05_lab_reports.py` creating `kc_lab_orders`, `kc_lab_reports` per Section 2
- Implement `/v1/clinic/patient/lab-reports/*` endpoints
- Celery task `parse_lab_report(report_id)` per Section 5
- S3 storage in ap-south-1 with KMS encryption
- PATCH endpoint for OCR correction

In `mobile/`:
- Lab reports upload screen (camera + PDF picker)
- OCR processing indicator
- Manual correction interface

**Acceptance:**
- Patient uploads a lab PDF; OCR processes within 60s
- Patient corrects an OCR error; correction persists
- Confidence < 0.60 fields require correction before save

#### P15 — Biomarker Visualization

In `mobile/`:
- Implement biomarker trend chart at `app/biomarkers/[name].tsx` using Victory Native XL
- Reference range bands (sage tint normal, saffron warning, alert red critical)
- 7d/30d/90d/1y/all toggle
- "Better / steady / worse" trend indicator with subtle animation
- Tap point → consultation linkage if applicable

In `backend/`:
- Implement `/v1/clinic/patient/biomarker-trends/{biomarker}` endpoint
- Aggregates values from `kc_lab_reports.parsed_json` across patient's history

**Acceptance:**
- Chart renders at 60fps on Redmi Note 11 (mid-range Android test device)
- Reference range bands visually distinct
- Trend indicator matches mathematical direction of change

### Prescriptions, video, pre-consult report (P16–P20)

#### P16 — Prescription Issuance (Doctor + Patient)

In `backend/`:
- Alembic migration `06_prescriptions.py` creating `kc_prescriptions`, `kc_prescription_items` per Section 2
- Implement `/v1/doctor/consultations/{id}/prescription` POST
- Implement `/v1/doctor/prescriptions/{id}/sign` POST
- Implement `/v1/clinic/patient/prescriptions/*` GET endpoints
- PDF generation via WeasyPrint (IMC format)

In `mobile/`:
- Prescription list screen
- Prescription detail with PDF download
- Dosage change tracking visualization

**Acceptance:**
- Doctor creates prescription (via doctor portal in later prompt, stub for now)
- Patient sees prescription post-signing
- PDF renders with NMC reg number, drug generic name, dosage, frequency, duration

#### P17 — 100ms Video Integration

In `backend/`:
- Implement `app/integrations/hms.py` for room provisioning, JWT generation
- Celery task `provision_video_room(consultation_id)` runs at T-15min
- Update `kc_consultations.video_room_id` post-provision
- `/v1/clinic/patient/consultations/{id}/join` and `/v1/doctor/consultations/{id}/join` return role-scoped JWTs

In `mobile/`:
- Integrate `@100mslive/react-native-room-kit`
- Pre-call waiting room
- In-call layout
- Post-call return to consultation detail

**Acceptance:**
- Two devices on Indian 4G hold a 30-min consultation
- One-way latency < 300ms p95
- Recording opt-in dialog presented before call starts

#### P18 — Doctor Portal Foundation

In `doctor-portal/`:
- Implement auth flow connecting to `/v1/auth/login` with doctor role check
- Implement dashboard, patients (list + detail), consultations (today + upcoming + history)
- Implement profile view + edit

**Acceptance:**
- Doctor logs in, lands on dashboard
- Patient list shows doctor's panel patients only
- Cross-doctor patient access returns 404 (via API)

#### P19 — Doctor Consultation View + Notes

In `doctor-portal/`:
- Implement `ConsultationVideoLayout` component: video on left (100ms web SDK), patient context panel on right
- `PatientContextPanel`: tabs for previous notes, prescriptions, labs, wearable data
- `NotesPanel`: real-time notes during call
- Post-call summary: notes, prescription builder, lab order builder, follow-up scheduling

In `backend/`:
- Implement `/v1/doctor/consultations/{id}/notes` POST (append-only, version-tracked)
- Implement `/v1/doctor/consultations/{id}/lab-order` POST

**Acceptance:**
- Doctor completes a consultation end-to-end on a single screen
- Notes saved with version increment on every save
- Lab order persists to `kc_lab_orders`

#### P20 — Pre-Consultation Report Generation

In `backend/`:
- Implement Celery task `generate_pre_consultation_report(consultation_id)` per Section 16
- Scheduled at T-24h via celery-beat
- PDF rendered via WeasyPrint, stored in S3
- Both patient and doctor endpoints to fetch

In `mobile/`:
- Implement pre-consultation report view screen (read-only)
- Surface low-confidence OCR fields for review

In `doctor-portal/`:
- Implement pre-consultation report view (editable doctor prep notes)
- Patient and doctor see identical content (per locked product principle)

**Acceptance:**
- Report generated within 5s
- PDF accessible to both patient and doctor
- Doctor edits prep notes; patient does not see edit
- Information symmetry verified: lab summary, adherence, wearable summary identical

### Notifications, web portal, education (P21–P25)

#### P21 — Notification Stack (Expo Push + WhatsApp + Email)

In `backend/`:
- Implement `app/services/notifications.py` with dispatchers for Expo Push, WhatsApp (via AiSensy/Wati), Email (via SendGrid)
- Notification templates: appointment confirmation, reminder, medication reminder, lab result, pre-consultation report ready
- WhatsApp utility templates submitted for Meta approval (placeholder in code; submission process documented)
- Push notifications use generic language (per Section 9.8)

**Acceptance:**
- Appointment confirmation fires to all 3 channels
- WhatsApp message delivery via test number works
- Push notifications appear on physical device
- No condition names in push text

#### P22 — Education Content System

In `backend/`:
- Alembic migration `07_education.py` creating `kc_education_content`, `kc_education_assignments` per Section 2
- Implement `/v1/admin/content/*` endpoints
- Implement `/v1/doctor/consultations/{id}/education` POST (doctor assigns content)
- Implement `/v1/clinic/patient/education/*` GET + read tracking

In `mobile/`:
- Education content viewer
- Read tracking
- Library browsable + doctor-assigned highlighted

**Acceptance:**
- Doctor assigns content during consultation
- Patient sees assigned content
- Mark-as-read updates server state

#### P23 — Patient Web Portal (RNW)

In `mobile/`:
- Configure React Native Web in Expo project
- Verify ~85% component reuse across mobile + web
- Web-specific: sidebar navigation (desktop), hover tooltips on charts, drag-and-drop file upload, print views

Deploy patient web portal to `app.kyrosclinic.com` subdomain.

**Acceptance:**
- Identical features available on mobile + web
- Lighthouse Performance ≥ 80 on responsive web
- File upload via drag-and-drop on desktop
- Print view for prescription PDFs

#### P24 — Doctor Portal Polish (Schedule, Profile, Lab Review)

In `doctor-portal/`:
- Implement schedule management (availability CRUD, buffer time settings, duration preferences)
- Implement lab review interface: annotate biomarkers, flag for patient attention
- Implement profile management (NMC reg # read-only, specialty edit, bank details with verification)

**Acceptance:**
- Doctor adds 20 availability slots; patient booking sees them
- Doctor annotates a biomarker; patient sees annotation on next view
- Bank details edit triggers verification email to super admin

#### P25 — Super Admin Portal (Jinja2 + HTMX)

In `backend/admin_ui/`:
- Implement Jinja2 templates per Section 12
- Dashboard, user management, doctor pipeline, consultation management, content approval, audit log
- HTMX partial updates for table row actions
- Tailwind with shared design tokens

**Acceptance:**
- Super admin renders dashboard in < 200ms
- Doctor onboarding pipeline shows all applied → active stages
- Audit log filterable by actor, action, date

### Coordinator portal, ABHA, polish (P26–P30)

#### P26 — Care Coordinator Portal (Jinja2 + HTMX)

In `backend/admin_ui/`:
- Implement coordinator routes per Section 13
- Strict access enforcement: cannot view doctor notes, prescription content, lab values, wearable data
- Intake queue with triage workflow
- WhatsApp + email communication interface
- Scheduling on behalf of patients

**Acceptance:**
- Coordinator sees only assigned patients
- Penetration test: API probing for unauthorized data returns 404 consistently
- Coordinator triages an intake → consultation booked → doctor notified

#### P27 — ABHA Integration (M1)

In `backend/`:
- Implement `app/integrations/abha.py` for sandbox API (sandbox.abdm.gov.in)
- Register Kyros as Health Information User (HIU) in sandbox
- Implement ABHA number verification flow
- Implement ABHA number creation flow (Aadhaar OTP)

In `mobile/`:
- ABHA linking screen in onboarding (optional)
- ABHA linking accessible from profile settings

**Acceptance:**
- Patient enters existing ABHA number → verified via sandbox
- Patient creates new ABHA number via Aadhaar OTP → linked to Kyros profile
- ABHA number persisted to `kc_patients.abha_number`

#### P28 — Analytics + Reporting

In `backend/`:
- Implement `/v1/admin/analytics/*` endpoints
- Acquisition funnel: website visitors → assessments → bookings → completions
- Cohort retention: patients returning for follow-up vs churned
- Doctor utilization: consultations per doctor per week
- Condition mix: distribution across 7 verticals
- Revenue by condition, doctor, time period
- CSV export

In `backend/admin_ui/`:
- Analytics dashboards in super admin portal

**Acceptance:**
- Funnel data populated from `ad_audit_log` + booking events
- Retention chart shows 30/60/90 day cohort behavior
- CSV export downloads any table within 10s for 10K-row datasets

#### P29 — Notification Center + Email Templates

In `backend/`:
- Implement notification center: in-app inbox of all notifications sent to patient
- Email templates rendered with kyros-design-system tokens
- WhatsApp utility templates documented and ready for Meta approval submission

In `mobile/`:
- Notification center screen
- Notification preferences

**Acceptance:**
- Patient sees all notifications received in chronological order
- Email templates render correctly in Gmail, Outlook, Apple Mail
- WhatsApp template approval documentation complete

#### P30 — Production Deployment + Observability

- Configure ECS Fargate task definitions (Phase 2 ready)
- Configure RDS Multi-AZ
- Configure ElastiCache Redis Multi-AZ
- Configure CloudWatch dashboards + Sentry
- Configure AWS WAF managed rule sets
- Configure CloudFront for public website
- Configure backup retention (RDS daily snapshots 30-day, S3 versioning)
- Document runbook: `docs/runbook-prod.md`
- Document DPDP breach runbook: `docs/dpdp-breach-runbook.md`
- Document DPIA: `docs/dpia-v1.md`

**Acceptance:**
- Phase 1 EC2 t3.small deployment live in ap-south-1
- All four frontends (website, doctor-portal, mobile via TestFlight + Play Internal, RNW patient portal) deployed
- Sentry catches errors from all services
- CloudWatch alarms configured for: API 5xx > 1%, RDS CPU > 80%, Redis memory > 80%
- DPDP DPIA documented + DPO designated + breach runbook ready

---

## Decision Log (Locked, Do Not Reopen Without Explicit User Reopen)

1. **Video provider:** 100ms (not Twilio EOL'd 5 Dec 2024; LiveKit as backup if 100ms pricing becomes prohibitive above 5,000 hours/month)
2. **OCR provider:** Google Document AI (95.8% vs Textract 94.2% on Braincuber 2026 benchmark; better on degraded Indian lab PDFs; built-in healthcare parser)
3. **Mobile charts:** Victory Native XL (Skia-based, 60fps on mid-range Android)
4. **Web charts:** Recharts
5. **Notifications:** Expo Push + WhatsApp utility (₹0.115/msg, free in 24h service window) + Email (no SMS as primary)
6. **Patient web portal:** React Native Web (single Expo codebase, ~85% reuse)
7. **Doctor portal:** React + Vite (data-heavy views require client state)
8. **Super admin + Care coordinator portals:** Jinja2 + HTMX (server-rendered, < 200ms render)
9. **Public website:** Next.js 14 App Router (SEO-critical, static generation)
10. **HealthKit/Health Connect:** @kingstinct/react-native-healthkit + react-native-health-connect (custom dev client required)
11. **Time-series storage:** PostgreSQL 16 monthly partitioning; evaluate TimescaleDB only at 50M+ rows or 500ms+ p95 query latency
12. **Payments:** Razorpay (subscription billing, RBI e-mandate, GST invoicing, T+2 settlement)
13. **Infrastructure:** EC2 t3.small Phase 1 → ECS Fargate at MRR > ₹50K/month OR concurrent users > 500
14. **Data residency:** ap-south-1 hard requirement (DPDP)
15. **ABHA:** optional, M1 (verify/capture) Phase 1; M2 (HIP) Phase 2; M3 (HIU) Phase 3+

---

## Cross-References

- **kyros-business-strategy** — positioning, pricing, three pillars, honest startup state
- **kyros-clinical-compliance** — regulatory rules, vocabulary, doctor approval gate, DPDP rationale
- **kyros-design-system** — visual register, color tokens, typography, voice settings
- **kyros-customer-acquisition** — public website SEO architecture, GBP, WhatsApp utility usage
- **kyros-b2b2c-partnerships** — HRIS integration, TPA claims API integration, marketplace API integration