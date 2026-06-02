# Kyros Backend & Infrastructure Strategy

**Document type:** Implementation-grade engineering blueprint
**Audience:** Backend engineers + Claude Code generating the Kyros foundation
**Scope:** FastAPI backend, PostgreSQL, Redis, Celery, Docker for local dev, EC2 Phase 1 → ECS Fargate Phase 2
**Anchors:** `kyros-build-spec.md` (technical spec), `kyros-business-strategy` (positioning), `kyros-clinical-compliance` (regulatory + audit rules)

Every recommendation in this document is opinionated and final. Where two reasonable paths exist, this document picks one, explains why, and moves on. Reopen a decision only with explicit reason.

---

## 1. Backend north star

### Philosophy

Kyros's backend is a **modular monolith**. One FastAPI 0.115 application, one Postgres 16 database, one Redis cluster, one Celery worker fleet. Six surfaces (public website, patient mobile, patient web portal, doctor portal, super admin portal, care coordinator portal) all consume this single backend.

This is the right default for Kyros for five concrete reasons:

1. **The product is one clinical workflow viewed through six lenses.** A consultation, a prescription, a lab report, an audit log — these are the same entities whether read by a patient, doctor, coordinator, or admin. Splitting into microservices would force network-hop joins across what is really one transactional bounded context. The data model is naturally cohesive.

2. **Team size in Phase A is small.** A two-to-five-engineer team building seven verticals on a 12-month timeline cannot afford the operational tax of multi-service deploys, distributed tracing across service boundaries, schema-coupled API contracts, and N copies of auth/audit/RBAC code.

3. **PHI access discipline is harder across services, not easier.** A monolith with one DB session enforces audit logging and RBAC in one place. A microservice mesh has to enforce it at every service boundary, and bugs in any one service can leak PHI. Centralized enforcement is a security feature, not a constraint.

4. **Indian telemedicine scale doesn't need it yet.** At the SOM ceiling described in `kyros-business-strategy` (~18,500 patients in Year 1, ARR ceiling ~₹4.25 Cr), the entire workload runs comfortably on a single EC2 t3.small in Phase 1 and a small ECS Fargate cluster in Phase 2. Microservices solve scale problems Kyros does not have.

5. **Compliance auditors prefer fewer trust boundaries.** Every additional service is a place where TLS, auth, and access control can be misconfigured. DPDP, NMC, and (eventually) ABDM auditors are happier with one application with one entry point than with eight services and a service mesh.

### Internal boundaries inside the monolith

The monolith is not a tangled blob. Domain boundaries are real and enforced by code structure, file layout, and review discipline. The four domains follow the build-spec table prefixes:

| Domain | Prefix | Owns |
|---|---|---|
| **Identity & auth** | `users`, `ad_consent_records`, `ad_audit_log` | Authentication, sessions, OTP, consent, audit |
| **Wellness** | `wn_*` | Self-tracked data: reminders, health datapoints, sync sessions. Patient-only access. |
| **Clinical** | `kc_*` | Consultations, prescriptions, lab orders/reports, doctor notes, pre-consult reports, payments, education |
| **Doctor** | `dr_*` | Doctor profiles, credentials, availability, scheduling |
| **Admin** | `ad_*` | Coordinators, DPDP requests, audit log queries, configuration |

Enforcement rules:

- A **router file** lives under exactly one domain. `api/v1/doctor/consultations.py` may not be the only place consultation logic exists; it must call into the `services/clinical/consultations.py` module, never reach across domains directly.
- A **service** in domain X can call services in other domains only via their public service-layer functions, never by importing another domain's repository or model directly. This makes the seam visible.
- A **repository** stays within its domain. `repositories/clinical/consultations_repo.py` does not import `dr_doctors` model except through the service layer.
- A **model file** can import models in other domains for foreign keys (Python typing requires it), but business logic across domains must traverse the service layer.

This is "modular monolith" in the literal Brandolini sense: physical separation by directory, logical separation by service-layer mediation, single deployment unit. If a domain ever needs to be extracted into its own service (unlikely before 50K patients), the seams are already drawn.

### What healthcare-grade backend discipline means here

"Healthcare-grade" is not a vibe. It is a concrete set of disciplines that change daily engineering decisions:

- **No PHI in logs, ever.** Patient name, phone, lab values, diagnosis, prescription contents — none of these appear in `structlog` output, Sentry events, or stdout. Logging emits IDs and event types. Sentry has a `before_send` PHI scrubber.
- **Audit log on every authorization decision, not just denials.** `ad_audit_log` records `allowed=true` and `allowed=false` with equal fidelity, because the absence of a record is suspicious in an investigation.
- **Cross-user access returns 404, never 403.** Returning 403 leaks the existence of a resource. The repository layer is the place where "this resource exists but isn't yours" and "this resource doesn't exist" collapse into one response.
- **Draft clinical artifacts are not retrievable by patients.** Doctor notes in draft state, unsigned prescriptions, doctor-only pre-consult prep notes — the repository's patient-scoped queries filter these out at the SQL level, not at the response-shaping layer. A bug in JSON serialization must not leak draft content.
- **Coordinators are blind to clinical content.** Coordinators see *that* a consultation happened and *its scheduling state*, never the prescription, lab values, or doctor notes. This is enforced by separate repository functions (`get_consultation_for_coordinator` vs `get_consultation_for_doctor`), each returning a different Pydantic schema with different fields.
- **Migrations are deliberate.** No automatic Alembic on app boot. A migration is a deploy step, run by a human or by CI, never by the app process. If the app finds the schema out of date at boot, it refuses to start.
- **Money is paise, integers only.** No `float` for money anywhere. Postgres column is `INT`, Pydantic schema is `int`, internal arithmetic is `int`. Decimal display is a presentation concern.
- **Webhooks are idempotent.** Razorpay, 100ms, and any future webhook handler de-duplicates on a Redis-stored key with a TTL longer than the source system's retry window.

### What to optimize for first

In order:

1. **Correctness of authorization.** A patient seeing another patient's lab report is a regulatory event. A bug here is a 72-hour breach notification under DPDP. This is the single highest-priority class of bug.
2. **Auditability.** Every PHI access is logged. The audit log is the artifact that proves Kyros's compliance posture to NMC, DPDP regulators, TPAs, and (eventually) insurance partners.
3. **Security at rest and in transit.** KMS-encrypted S3, KMS-encrypted RDS, TLS 1.3 only, argon2id hashes, no secrets in env vars in production.
4. **Correctness of money flows.** Razorpay webhook idempotency, paise integer arithmetic, GST invoice generation, refund flows.
5. **Speed and latency.** Important, but a slow correct system is recoverable; a fast wrong system is not.

This ordering is not negotiable in Phase A. It implies, for example, that we accept a P95 of 300ms on patient dashboard load if hitting 150ms would require skipping the audit log write.

### Complexity to accept early vs defer

**Accept early (build into the foundation):**
- RBAC dependency framework with role + ownership scoping
- Audit log on every authorization decision
- Soft delete pattern with `deleted_at` filtering centralized in repositories
- Append-only versioning for prescriptions and doctor notes
- Pydantic v2 schemas separated into request, response, and DB shapes (no leaking ORM models out the API)
- Configuration via Pydantic Settings with fail-fast validation
- Structured logging with request IDs
- Celery queue separation by workload class

**Defer (do not build into Phase A):**
- pgBouncer (add at Phase 2)
- TimescaleDB or any non-Postgres time-series store (only at 50M+ datapoint rows)
- Read replicas (Phase 2 only)
- Service mesh, sidecars, Istio, Envoy (never, on current trajectory)
- gRPC internal APIs (REST is fine, full stop)
- Event sourcing (the audit log is not event sourcing, do not confuse them)
- Schema-on-read with JSONB everywhere (use JSONB surgically, as described in §5)
- Hot reload of configuration (restart the process, healthcheck handles it)
- Custom rate limiter with Redis Lua scripts (use SlowAPI + Redis backend until proven insufficient)

---

## 2. Repository and monorepo structure

### Monorepo, with a clear "this is the backend" subtree

A single repository (`kyros-platform`) hosts all surfaces and infra. This matches the build-spec layout and is the right call because:

- Design tokens (`design-tokens/tokens.json`) are consumed by Tailwind configs in website, doctor portal, mobile, *and* the admin UI Jinja templates. A monorepo means one PR updates the brand surface across all six surfaces atomically.
- The OpenAPI schema generated from the FastAPI backend is consumed by the doctor portal, patient mobile, and website. Generating types from a single spec into multiple TS clients is a one-command monorepo task.
- Pull requests that touch backend + frontend together are easier to review and revert.
- Local development can run all surfaces against one backend with one `docker compose up`.

The tradeoff is repo size and CI fan-out, both manageable with selective CI paths.

### Top-level tree

```
kyros-platform/
├── backend/                      # FastAPI single backend (this document's primary subject)
├── website/                      # Next.js 14 public site
├── mobile/                       # Expo RN + RN Web (patient app + patient web portal)
├── doctor-portal/                # React 18 + Vite 5
├── design-tokens/                # Shared tokens consumed by all UI surfaces
│   ├── tokens.json
│   ├── package.json              # Published as @kyros/design-tokens within monorepo
│   └── tailwind-preset.js
├── infra/                        # Infrastructure as code + ops docs
│   ├── terraform/                # IaC for AWS (Phase 1 EC2 + RDS, Phase 2 ECS)
│   ├── docker/                   # Production Dockerfiles + compose for staging
│   ├── runbooks/                 # On-call runbooks (DPDP breach, RDS failover, etc.)
│   └── scripts/                  # Ops scripts that don't belong to backend
├── docs/                         # Cross-cutting docs (DPIA, ADRs, API conventions)
│   ├── adr/                      # Architecture Decision Records, numbered
│   ├── dpia-v1.md
│   ├── dpdp-breach-runbook.md
│   ├── api-conventions.md
│   └── README.md
├── scripts/                      # Cross-monorepo scripts (e.g., bump-versions.sh)
├── .github/
│   └── workflows/                # CI: backend.yml, mobile.yml, doctor-portal.yml, website.yml
├── .gitignore
├── .editorconfig
├── docker-compose.yml            # Top-level local dev compose (the one developers run)
├── docker-compose.test.yml       # Dedicated test environment (postgres, redis, backend)
├── Makefile                      # Common dev tasks: make dev, make test, make migrate, make seed
└── README.md
```

### Backend subtree (the heart of this document)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app factory + lifespan
│   ├── core/                     # Cross-cutting primitives, no domain logic
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic Settings, env loading
│   │   ├── logging.py            # structlog configuration, request ID injection
│   │   ├── security.py           # password hashing, JWT encode/decode primitives
│   │   ├── exceptions.py         # custom exception types + handler registration
│   │   ├── pagination.py         # cursor + offset pagination helpers
│   │   ├── ids.py                # UUID helpers, human-readable patient ID generator
│   │   ├── time.py               # tz-aware datetime helpers, defaults Asia/Kolkata
│   │   └── audit.py              # ad_audit_log write helper, called from deps
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py               # SQLAlchemy DeclarativeBase + naming convention
│   │   ├── session.py            # async engine, AsyncSessionLocal, get_db dep
│   │   ├── mixins.py             # TimestampMixin, SoftDeleteMixin, UUIDMixin
│   │   └── enums.py              # Python enums mirrored to Postgres enums
│   ├── models/                   # SQLAlchemy ORM models, organized by domain
│   │   ├── __init__.py           # re-export every model for Alembic autogen
│   │   ├── identity.py           # User, OTP, RefreshToken
│   │   ├── consent.py            # ad_consent_records, ad_data_subject_requests
│   │   ├── audit.py              # ad_audit_log (immutable, no soft delete)
│   │   ├── wellness.py           # wn_reminders, wn_reminder_logs, wn_health_*
│   │   ├── clinical.py           # kc_patients, kc_consultations, kc_prescriptions, ...
│   │   ├── doctor.py             # dr_doctors, dr_availability, dr_credentials
│   │   └── admin.py              # ad_coordinators, ad_configuration
│   ├── schemas/                  # Pydantic v2 request/response schemas, by domain
│   │   ├── __init__.py
│   │   ├── common.py             # Pagination, ErrorResponse, IDResponse
│   │   ├── auth.py
│   │   ├── patient.py            # patient-facing request/response shapes
│   │   ├── doctor.py             # doctor-facing shapes
│   │   ├── coordinator.py        # coordinator-facing shapes (restricted views)
│   │   ├── admin.py              # super-admin shapes (full access)
│   │   └── wellness.py
│   ├── repositories/             # Async query modules, one file per aggregate
│   │   ├── __init__.py
│   │   ├── users_repo.py
│   │   ├── patients_repo.py
│   │   ├── consultations_repo.py
│   │   ├── prescriptions_repo.py
│   │   ├── lab_reports_repo.py
│   │   ├── doctor_notes_repo.py
│   │   ├── doctors_repo.py
│   │   ├── availability_repo.py
│   │   ├── coordinators_repo.py
│   │   ├── reminders_repo.py
│   │   ├── health_datapoints_repo.py
│   │   ├── consent_repo.py
│   │   ├── audit_repo.py
│   │   └── payments_repo.py
│   ├── services/                 # Business logic, orchestrates repositories + integrations
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── otp_service.py
│   │   ├── consultation_service.py
│   │   ├── prescription_service.py
│   │   ├── lab_report_service.py
│   │   ├── ocr_service.py        # calls integrations/document_ai
│   │   ├── video_service.py      # calls integrations/hms_100ms
│   │   ├── payment_service.py
│   │   ├── pre_consult_report_service.py
│   │   ├── notification_service.py
│   │   ├── reminder_service.py
│   │   ├── health_sync_service.py
│   │   ├── dpdp_service.py       # export, erasure, grievance
│   │   ├── doctor_onboarding_service.py
│   │   └── coordinator_service.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py               # FastAPI dependency factory: get_current_user, enforce_role, get_db
│   │   ├── errors.py             # exception handlers registered on the app
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py         # APIRouter aggregator for v1
│   │       ├── auth.py           # /v1/auth/* (login, otp, refresh, logout)
│   │       ├── public/
│   │       │   ├── __init__.py
│   │       │   ├── leads.py
│   │       │   ├── doctors_directory.py
│   │       │   └── booking_inquiry.py
│   │       ├── clinic/
│   │       │   ├── __init__.py
│   │       │   ├── patient_profile.py
│   │       │   ├── consultations.py
│   │       │   ├── prescriptions.py
│   │       │   ├── lab_reports.py
│   │       │   ├── education.py
│   │       │   └── payments.py
│   │       ├── wellness/
│   │       │   ├── __init__.py
│   │       │   ├── reminders.py
│   │       │   └── health_sync.py
│   │       ├── doctor/
│   │       │   ├── __init__.py
│   │       │   ├── dashboard.py
│   │       │   ├── panel.py
│   │       │   ├── consultations.py
│   │       │   ├── notes.py
│   │       │   ├── prescriptions.py
│   │       │   ├── lab_review.py
│   │       │   ├── schedule.py
│   │       │   └── education_assignment.py
│   │       ├── admin/
│   │       │   ├── __init__.py
│   │       │   ├── doctors.py
│   │       │   ├── users.py
│   │       │   ├── coordinators.py
│   │       │   ├── content.py
│   │       │   ├── analytics.py
│   │       │   ├── audit_logs.py
│   │       │   └── configuration.py
│   │       ├── admin_coordinator/    # /v1/admin/coordinator/* — separate from /v1/admin/* for scoping
│   │       │   ├── __init__.py
│   │       │   ├── intake_queue.py
│   │       │   ├── scheduling.py
│   │       │   ├── triage.py
│   │       │   └── communication.py
│   │       ├── users.py              # /v1/users/me, /v1/users/me/data-export, etc.
│   │       └── webhooks/
│   │           ├── __init__.py
│   │           ├── razorpay.py
│   │           └── hms_100ms.py
│   ├── integrations/                 # External service adapters
│   │   ├── __init__.py
│   │   ├── s3.py                     # boto3 wrapper, signed URL generation
│   │   ├── document_ai.py            # Google Document AI client
│   │   ├── hms_100ms.py              # 100ms room creation, JWT generation
│   │   ├── razorpay.py
│   │   ├── msg91.py                  # OTP SMS
│   │   ├── aisensy.py                # WhatsApp utility messages
│   │   ├── sendgrid.py
│   │   ├── expo_push.py
│   │   ├── elevenlabs.py             # voice synthesis (admin-side, for content)
│   │   └── abha.py                   # ABDM sandbox/production (later)
│   ├── tasks/                        # Celery task definitions, by workload
│   │   ├── __init__.py
│   │   ├── celery_app.py             # Celery() instance, queue routing
│   │   ├── ocr_tasks.py              # parse_lab_report
│   │   ├── report_tasks.py           # generate_pre_consultation_report
│   │   ├── notification_tasks.py     # send push/email/whatsapp
│   │   ├── payment_tasks.py          # reconcile_payment, generate_invoice
│   │   ├── video_tasks.py            # provision_video_room (T-15min cron)
│   │   ├── dpdp_tasks.py             # data_export, data_erasure
│   │   ├── reminder_tasks.py         # dispatch_reminders (beat schedule)
│   │   ├── analytics_tasks.py        # rollup_daily_metrics
│   │   ├── maintenance_tasks.py      # cleanup, partition management
│   │   └── beat_schedule.py          # Celery beat schedule definition
│   ├── adminui/                      # Jinja2 + HTMX for super-admin + coordinator
│   │   ├── __init__.py
│   │   ├── router.py                 # mounts at /admin (super_admin role) and /coord (coordinator role)
│   │   ├── deps.py                   # session cookie auth for admin UI (separate from API JWT)
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── admin/
│   │   │   │   ├── dashboard.html
│   │   │   │   ├── doctors_list.html
│   │   │   │   ├── doctor_detail.html
│   │   │   │   ├── audit_logs.html
│   │   │   │   └── ...
│   │   │   └── coordinator/
│   │   │       ├── intake_queue.html
│   │   │       ├── patient_panel.html
│   │   │       └── ...
│   │   └── static/                   # CSS, small JS (Alpine.js, HTMX bundled)
│   └── observability/
│       ├── __init__.py
│       ├── sentry.py                 # Sentry init + PHI scrubber
│       ├── metrics.py                # Prometheus-compatible metrics (later)
│       └── middleware.py             # RequestIDMiddleware, AccessLogMiddleware
├── alembic/                          # Migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_init.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # async fixtures, DB transaction wrapping
│   ├── fixtures/
│   │   ├── users.py
│   │   ├── patients.py
│   │   ├── doctors.py
│   │   └── consultations.py
│   ├── unit/
│   │   ├── core/
│   │   ├── services/
│   │   └── repositories/
│   ├── integration/
│   │   ├── api/
│   │   │   ├── test_auth.py
│   │   │   ├── test_patient_routes.py
│   │   │   ├── test_doctor_routes.py
│   │   │   ├── test_coordinator_routes.py
│   │   │   ├── test_admin_routes.py
│   │   │   ├── test_webhooks.py
│   │   │   └── test_rbac_matrix.py
│   │   └── tasks/
│   │       ├── test_ocr_tasks.py
│   │       ├── test_report_tasks.py
│   │       └── test_notification_tasks.py
│   └── migration/
│       └── test_migrations_up_down.py
├── scripts/                          # Backend-local scripts
│   ├── seed_dev.py                   # idempotent dev seed: 2 doctors, 5 patients, 1 coordinator
│   ├── create_super_admin.py         # interactive script to bootstrap first admin
│   ├── generate_openapi.py           # writes openapi.json for client codegen
│   └── reset_dev_db.sh
├── Dockerfile                        # multi-stage: base, dev, prod
├── alembic.ini
├── pyproject.toml                    # ruff, mypy, pytest config + deps
├── uv.lock                           # or poetry.lock — see §3
├── .env.example                      # documented, committed
└── README.md
```

### Naming conventions

- **Modules:** snake_case singular for primitives (`config.py`, `security.py`), snake_case plural for collections (`models/clinical.py`, `repositories/consultations_repo.py`). The `_repo`, `_service` suffixes are not redundant; they read aloud cleanly in tracebacks and code review.
- **SQLAlchemy classes:** PascalCase singular. `User`, `Consultation`, `Prescription`, `LabReport`, `AuditLog`. The Postgres table name comes from the spec (`users`, `kc_consultations`); set via `__tablename__`.
- **Pydantic schemas:** `XxxCreate` for inbound create, `XxxUpdate` for inbound update, `XxxRead` for outbound, `XxxAdminRead` for outbound with extra fields visible only to admins. Per-role variants live in the same file when small, in role-specific subdirectories when they grow.
- **Repository functions:** verb + noun + scope. `get_consultation_for_patient(consult_id, patient_user_id)`, `list_consultations_for_doctor_panel(doctor_id, ...)`, `list_consultations_for_coordinator(coordinator_id, assigned_patient_ids, ...)`. Scope is a parameter, not an implicit context.
- **Service functions:** verb + noun, no scope suffix. The service trusts the router to have applied auth; the service's job is orchestration, not auth.
- **Celery task names:** `kyros.<domain>.<verb_noun>` for routing clarity. `kyros.clinical.parse_lab_report`, `kyros.clinical.generate_pre_consult_report`, `kyros.notification.send_push`, `kyros.payment.reconcile`.

### Why repositories, given FastAPI examples usually skip them

The standard FastAPI tutorial pattern is "service calls SQLAlchemy directly." That works for small apps and falls apart for Kyros for three reasons:

1. **RBAC pre-filter discipline.** Every read query for clinical data needs to be scoped by ownership at the SQL level. A repository function with explicit scope parameter (`get_consultation_for_patient(id, patient_user_id)`) is impossible to call wrong: forgetting the scope parameter is a type error. Inline SQLAlchemy in a service is a code review concern.

2. **Test isolation.** Unit tests for services can mock repositories trivially. Mocking SQLAlchemy expressions is misery.

3. **Query reuse across surfaces.** The same logical "list consultations" query has four variants (patient, doctor, coordinator, admin) with different filters and projections. A repository module is the natural home for the four variants side by side.

The repository is **thin**. It contains async query functions, returns ORM models or domain dataclasses, and does not return Pydantic schemas (the service layer or router does the schema conversion). It does no business logic beyond filtering.

---

## 3. FastAPI application architecture

### App entrypoint and lifespan

`app/main.py` exports a single factory:

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.observability.sentry import init_sentry
from app.observability.middleware import RequestIDMiddleware, AccessLogMiddleware
from app.api.v1.router import api_v1_router
from app.adminui.router import admin_ui_router
from app.api.errors import register_exception_handlers
from app.db.session import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging()
    init_sentry()
    # Schema sanity check (NOT migration): refuse to start if alembic head is not applied
    await _verify_schema_head()
    yield
    # Shutdown
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Kyros API",
        version=settings.app_version,
        openapi_url=settings.openapi_url,        # None in production
        docs_url=settings.docs_url,              # None in production
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    )
    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/v1")
    app.include_router(admin_ui_router)  # mounts /admin and /coord HTML routes
    return app

app = create_app()
```

The schema-head verification at startup catches the "deployed new code, forgot to run migration" failure mode. The app refuses to come up rather than serve traffic against an outdated schema.

### Configuration loading

Configuration is loaded once at process start via Pydantic Settings (see §8 for full design). The `settings` object is a process-global singleton. Tests override via dependency injection on a few key values, not by monkey-patching the module.

### Dependency injection strategy

FastAPI's `Depends` is the right tool. The patterns:

- `get_db()` yields an `AsyncSession`, scoped to the request, committed on success, rolled back on exception, always closed.
- `get_current_user()` extracts JWT from Authorization header, decodes, fetches user, returns `User` ORM. Raises 401 on missing/invalid/expired token. Audit-logs the auth attempt at warning level on failure.
- `enforce_role(*roles)` is a dependency factory returning a dependency that depends on `get_current_user` and raises 403 if role mismatch. Returns the User.
- `get_patient_user()`, `get_doctor_user()`, `get_coordinator_user()`, `get_admin_user()` are sugar over `enforce_role(Role.PATIENT)` etc.
- `get_audit_context(request: Request, user: User = Depends(get_current_user))` constructs an `AuditContext` object that carries `actor_user_id`, `actor_role`, `ip_address`, `user_agent`, `request_id`. Repository functions receive this and write audit log entries.

The key opinion: **authorization scope (own-resource-only) is NOT a dependency; it's a repository function parameter.** A dependency cannot know which resource ID will be in the path; the repository function takes the user's ID as a filter parameter and returns None for "not yours or not found." The router then raises 404. This is the cross-user 404 pattern enforced at the SQL layer.

Example:

```python
# api/v1/clinic/consultations.py
@router.get("/{consultation_id}", response_model=ConsultationRead)
async def get_consultation(
    consultation_id: UUID,
    user: User = Depends(get_patient_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    consult = await consultations_repo.get_consultation_for_patient(
        db, consultation_id=consultation_id, patient_user_id=user.id
    )
    if consult is None:
        await audit_repo.write(
            db, audit_ctx, action="view_consultation",
            resource_type="consultation", resource_id=consultation_id,
            allowed=False, reason="not_own_or_not_found",
        )
        raise HTTPException(404, detail="not found")
    await audit_repo.write(
        db, audit_ctx, action="view_consultation",
        resource_type="consultation", resource_id=consultation_id,
        allowed=True,
    )
    return ConsultationRead.model_validate(consult)
```

### Router grouping and versioning

API surface is versioned at the URL: `/v1/...`. Versioning at the URL (not header) is the right choice for Kyros because:

- The doctor portal, mobile app, and website are all clients we control, but they update on different cadences. URL versioning lets them pin a version explicitly.
- External integrators (TPAs, ABDM HIE-CM, B2B2C partners) prefer URL versioning for API contract clarity.

`api/v1/router.py` aggregates sub-routers with prefixes:

```python
api_v1_router = APIRouter()
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(public.router, prefix="/public", tags=["public"])
api_v1_router.include_router(clinic.router, prefix="/clinic/patient", tags=["clinic-patient"])
api_v1_router.include_router(wellness.router, prefix="/wellness", tags=["wellness"])
api_v1_router.include_router(doctor.router, prefix="/doctor", tags=["doctor"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_v1_router.include_router(admin_coordinator.router, prefix="/admin/coordinator", tags=["coordinator"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
```

The deliberate choice: **coordinator routes are under `/v1/admin/coordinator/*`, not `/v1/coordinator/*`.** Coordinators are an operational role inside the clinic, not a peer to patients. Placing them under `/admin/` signals that they're staff and their UI lives in the staff portal (Jinja + HTMX). This also matches the `assigned_patient_ids` scoping pattern: coordinator routes need patient-scoping logic that mirrors super admin, not patient-self.

### Middleware stack

In order (outermost first):

1. `RequestIDMiddleware`: reads `X-Request-ID` header or generates a UUID4; attaches to `structlog` context and `request.state.request_id`. Sets response header.
2. `AccessLogMiddleware`: logs `{method, path, status, duration_ms, request_id}` at INFO. Skips paths matching `/healthz`, `/readyz`. Never logs request or response bodies.
3. `CORSMiddleware`: configured per environment. Production allows only the production website + mobile API domain.
4. `TrustedHostMiddleware` (production only): enforces Host header matches `api.kyros.clinic`.

We deliberately do not put auth in middleware. Auth is per-route via dependencies because routes have different role/scope requirements and some (public, webhooks, healthchecks) skip it entirely. Middleware-based auth would require allowlists that drift.

### Exception handler structure

`app/api/errors.py` registers handlers for:

- `RequestValidationError` (Pydantic) → 422 with `{detail: [{loc, msg, type}], request_id}`.
- `HTTPException` → pass-through with `{detail, request_id}`.
- `IntegrityError` (SQLAlchemy unique violation, etc.) → 409 with a generic message; the specific constraint is logged but not returned (don't leak schema details).
- `KyrosDomainError` (custom base) → mapped to 4xx codes per subclass: `NotFoundError`→404, `ConflictError`→409, `BusinessRuleError`→422, `PaymentRequiredError`→402.
- Unhandled `Exception` → 500 with `{detail: "internal_server_error", request_id}`. Sentry captures via its own integration. The error message is never returned to the client.

Every response includes the request ID, so a user reporting an issue gives a single string that lets the on-call engineer locate the exact log line in CloudWatch.

### Auth and RBAC dependencies (mechanism only; full design in §11)

Three layers:

1. **Authentication** (`get_current_user`): validates JWT, returns User or raises 401.
2. **Role authorization** (`enforce_role(Role.X)`): checks user role, raises 403 on mismatch.
3. **Resource scoping** (repository function parameters): "is this resource accessible to this user?" — answered at the SQL level by the repository, returning None to trigger a 404 in the router.

The reason for separating roles into 403-raising and resources into 404-returning: role mismatch is a coarse-grained API surface fact (a patient hitting `/v1/doctor/*` is unambiguous misuse), whereas resource access is fine-grained PHI exposure (a patient hitting `/v1/clinic/patient/consultations/{other_patient_id}` is an enumeration probe and must be indistinguishable from a 404).

### Health endpoints

Two distinct endpoints with different semantics:

- `GET /healthz` (liveness): returns 200 with `{status: "ok", version: settings.app_version}`. No dependency checks. Used by AWS ALB / ECS to decide whether to restart the container. A liveness check that depends on DB will cause cascading restarts when DB has a hiccup.
- `GET /readyz` (readiness): returns 200 if backend can serve traffic. Checks: DB connection (one `SELECT 1`), Redis connection (one `PING`). Returns 503 with `{db: ok/fail, redis: ok/fail}` otherwise. Used by load balancer to gate traffic and by `docker compose` health checks to decide when dependent services can start.

Neither endpoint requires auth, neither logs at INFO level (would flood logs), both are exempt from rate limiting.

### Admin UI (Jinja2 + HTMX) routes

The admin UI is mounted on the same FastAPI app for one reason: deployment simplicity. Same Docker image, same Python process, same DB session machinery, same RBAC primitives.

Differences from the API surface:

- **Session cookies, not JWT.** The admin UI is a server-rendered web app; cookies are the right mechanism. The cookie is HttpOnly, Secure, SameSite=Lax, and stores an opaque session ID that maps to a Redis key.
- **CSRF protection** via `fastapi-csrf-protect` or hand-rolled double-submit token, since cookies are involved.
- **Separate URL namespace**: `/admin/*` for super admin, `/coord/*` for coordinator. Each has its own login page and session.
- **Templates use shared design tokens** via a Tailwind build that consumes `design-tokens/tokens.json`.
- **HTMX requests** are normal POSTs/GETs that return HTML fragments. They use the same service-layer functions as the API, but render to HTML via `Jinja2Templates`.

Mounting:

```python
admin_ui_router = APIRouter()
admin_ui_router.include_router(admin_html_router, prefix="/admin")
admin_ui_router.include_router(coordinator_html_router, prefix="/coord")
admin_ui_router.mount("/admin/static", StaticFiles(directory="app/adminui/static"), name="admin-static")
```

### Public vs authenticated route isolation

Three distinct "zones," each enforced by directory structure and dependency convention:

- **Zone 1: Public.** `/v1/public/*`, `/v1/auth/login`, `/v1/auth/otp/*`, `/healthz`, `/readyz`. No auth dependency. Rate-limited aggressively (per-IP) via Redis-backed limiter.
- **Zone 2: Authenticated patient/clinical.** `/v1/clinic/*`, `/v1/wellness/*`, `/v1/users/me/*`. Requires patient JWT. Rate-limited per-user.
- **Zone 3: Authenticated staff.** `/v1/doctor/*`, `/v1/admin/*`. Requires doctor/coordinator/super_admin JWT. Rate-limited per-user but at higher thresholds.
- **Zone 4: Webhooks.** `/v1/webhooks/*`. No JWT auth; instead, HMAC signature verification against the source service's secret. Rate-limited per-source-IP (allowlist of Razorpay / 100ms egress IPs in production).

This is enforced as a convention plus a CI test that asserts no `/v1/clinic/*` route is reachable without a JWT.

---

## 4. Docker strategy

### Philosophy

In local development, **everything except the frontend UI surfaces runs in Docker**. The frontends (Next.js, Vite, Expo) stay on the host because their build tooling (Metro, Vite HMR, Next.js dev server) is best served by native filesystem watching and they have their own dev server lifecycles. The backend, Postgres, Redis, and Celery workers run as compose services with a single `docker compose up`.

In production:

- **Phase 1 (EC2):** the same Docker images run on a single EC2 host via `docker compose` or systemd-managed containers. Postgres and Redis migrate to RDS and ElastiCache respectively, removing them from compose. Only `backend-api`, `celery-worker`, `celery-beat` run on the host.
- **Phase 2 (ECS Fargate):** the same Docker images run as ECS tasks. RDS, ElastiCache, S3 are managed AWS services. No compose; ECS task definitions per service.

The image that runs in production is **the same image that runs in local development**, with a different command and environment. There is no separate "dev image" with extra tools; there is the production image plus a thin "dev overlay" that adds bind mounts and `--reload`. This matters because production parity catches "works on my machine" bugs.

### Service inventory

| Service | Image | Local dev | Phase 1 prod | Phase 2 prod |
|---|---|---|---|---|
| `postgres` | `postgres:16.4-alpine` | compose, named volume | RDS db.t3.micro | RDS Multi-AZ db.t3.medium |
| `redis` | `redis:7.4-alpine` | compose, no persistence | ElastiCache t3.micro | ElastiCache Multi-AZ |
| `backend-api` | `kyros-backend:latest` | compose, bind mount, `uvicorn --reload` | EC2 systemd/compose, `uvicorn --workers 2` | ECS Fargate, gunicorn+uvicorn workers |
| `celery-worker` | `kyros-backend:latest` (same image) | compose, bind mount | EC2 | ECS Fargate task per queue |
| `celery-beat` | `kyros-backend:latest` (same image) | compose, bind mount | EC2 | ECS Fargate (single replica) |
| `mailhog` | `mailhog/mailhog:v1.0.1` | compose (dev only) | n/a | n/a |
| `flower` | omitted | omitted (see below) | omitted | optional |

**Why mailhog in local dev:** the notification service has email branches. Local dev should not call SendGrid/Postmark. Mailhog catches outbound SMTP on port 1025 and exposes a web UI on 8025. The notification service in dev mode targets mailhog. This is one container; the cost is zero.

**Why omit Flower:** Flower's value is monitoring queue depth, task latency, and worker health in production. In local dev, `docker compose logs celery-worker` plus `redis-cli LLEN celery` is sufficient. In production Phase 1, CloudWatch + Sentry are sufficient. Adding Flower introduces a publicly-exposable web UI with weak default auth — it's a footgun on EC2. Add Flower only if a specific need emerges and put it behind a VPN or strict IP allowlist.

**Why omit pgAdmin / RedisInsight:** local dev uses `psql` and `redis-cli` directly via `docker compose exec`. Adding GUIs adds containers, weakens habits, and creates noise in `docker compose ps`. Engineers who want a GUI install it on their host and connect to exposed ports.

### Dockerfile (multi-stage)

The backend Dockerfile is a single multi-stage file producing one of three targets: `base`, `dev`, or `prod`.

```dockerfile
# backend/Dockerfile
ARG PYTHON_VERSION=3.12.5-slim-bookworm

# ---- Stage 1: base — system deps + Python deps ----
FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.3 \
    PATH="/opt/venv/bin:$PATH"

# System deps:
# - libpq5: Postgres client library, used by asyncpg's psycopg2-binary fallback at install time
# - curl: healthcheck script in compose
# - tini: PID 1 signal handling
# - build-essential is in builder stage only; not in final image
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r kyros && useradd -r -g kyros -u 1000 -m -s /bin/bash kyros

WORKDIR /app

# ---- Stage 2: builder — install Python deps in a venv ----
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

COPY pyproject.toml uv.lock /app/
# We use uv for speed in CI; pip install also works if you prefer
RUN pip install uv==0.4.18 \
    && uv pip install --no-cache --system-deps --requirement pyproject.toml

# ---- Stage 3: dev — adds dev dependencies + watch tooling ----
FROM base AS dev

COPY --from=builder /opt/venv /opt/venv
# In dev, we install the full dependency set including dev/test extras
COPY pyproject.toml uv.lock /app/
RUN pip install uv==0.4.18 \
    && uv pip install --no-cache --system-deps --requirement pyproject.toml --extra dev

# Source mounted via bind mount in compose, so we don't COPY it here
USER kyros
EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- Stage 4: prod — minimal runtime ----
FROM base AS prod

COPY --from=builder /opt/venv /opt/venv

# Copy source AFTER deps so source changes don't bust the layer cache
COPY --chown=kyros:kyros . /app/

USER kyros
EXPOSE 8000

# Healthcheck targets /healthz (cheap, dependency-free)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
# In production, gunicorn manages multiple uvicorn workers
CMD ["gunicorn", "app.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "60", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5"]
```

Build targets:

```bash
# Local dev image
docker build --target dev -t kyros-backend:dev backend/

# Production image
docker build --target prod -t kyros-backend:$(git rev-parse --short HEAD) backend/
```

Key opinions:

- **Multi-stage with a `builder` stage** keeps the final image free of `gcc`, `build-essential`, and source maps. Final image is ~250 MB.
- **Non-root user (`kyros`, uid 1000)** matches a common host uid; bind-mounted source files have predictable ownership in dev.
- **`tini` as PID 1** handles SIGTERM correctly so uvicorn and gunicorn shut down gracefully.
- **Healthcheck on `/healthz` only** in the production stage; the dev stage omits the HEALTHCHECK directive because compose defines per-service health checks (more flexible there).
- **`uv` for dependency install** is ~10× faster than `pip` in CI. Falling back to `pip` is a one-line change if `uv` becomes a problem.
- **No `apt-get upgrade`**. We pin to the base image's security posture; upgrades happen by bumping the base image tag.

### docker-compose.yml (local development)

The compose file lives at the repo root, not inside `backend/`, because it orchestrates services across the monorepo (even if currently only backend services).

```yaml
# docker-compose.yml
name: kyros

services:
  postgres:
    image: postgres:16.4-alpine
    container_name: kyros-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: kyros
      POSTGRES_PASSWORD: kyros_dev_password
      POSTGRES_DB: kyros
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/docker/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kyros -d kyros"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 5s

  redis:
    image: redis:7.4-alpine
    container_name: kyros-redis
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "no", "--save", ""]
    ports:
      - "6379:6379"
    # No volume — local dev does not need Redis persistence
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mailhog:
    image: mailhog/mailhog:v1.0.1
    container_name: kyros-mailhog
    restart: unless-stopped
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI

  backend-api:
    build:
      context: ./backend
      target: dev
    image: kyros-backend:dev
    container_name: kyros-backend-api
    restart: unless-stopped
    env_file:
      - ./backend/.env
    environment:
      # Override DB host to use compose network name
      KYROS_DATABASE_URL: "postgresql+asyncpg://kyros:kyros_dev_password@postgres:5432/kyros"
      KYROS_REDIS_URL: "redis://redis:6379/0"
      KYROS_CELERY_BROKER_URL: "redis://redis:6379/1"
      KYROS_CELERY_RESULT_BACKEND: "redis://redis:6379/2"
      KYROS_SMTP_HOST: "mailhog"
      KYROS_SMTP_PORT: "1025"
      KYROS_ENV: "local"
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app:cached
      - backend_venv:/opt/venv  # protect host from container's venv
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/readyz"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

  celery-worker:
    image: kyros-backend:dev
    container_name: kyros-celery-worker
    restart: unless-stopped
    env_file:
      - ./backend/.env
    environment:
      KYROS_DATABASE_URL: "postgresql+asyncpg://kyros:kyros_dev_password@postgres:5432/kyros"
      KYROS_REDIS_URL: "redis://redis:6379/0"
      KYROS_CELERY_BROKER_URL: "redis://redis:6379/1"
      KYROS_CELERY_RESULT_BACKEND: "redis://redis:6379/2"
      KYROS_SMTP_HOST: "mailhog"
      KYROS_SMTP_PORT: "1025"
      KYROS_ENV: "local"
    volumes:
      - ./backend:/app:cached
      - backend_venv:/opt/venv
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      backend-api:
        condition: service_started
    command: >
      celery -A app.tasks.celery_app worker
      --loglevel=INFO
      --queues=ocr,notifications,reports,payments,maintenance,default
      --concurrency=4

  celery-beat:
    image: kyros-backend:dev
    container_name: kyros-celery-beat
    restart: unless-stopped
    env_file:
      - ./backend/.env
    environment:
      KYROS_DATABASE_URL: "postgresql+asyncpg://kyros:kyros_dev_password@postgres:5432/kyros"
      KYROS_REDIS_URL: "redis://redis:6379/0"
      KYROS_CELERY_BROKER_URL: "redis://redis:6379/1"
      KYROS_CELERY_RESULT_BACKEND: "redis://redis:6379/2"
      KYROS_ENV: "local"
    volumes:
      - ./backend:/app:cached
      - backend_venv:/opt/venv
      - celery_beat_data:/app/beat
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      celery -A app.tasks.celery_app beat
      --loglevel=INFO
      --schedule=/app/beat/celerybeat-schedule

volumes:
  postgres_data:
    name: kyros_postgres_data
  backend_venv:
    name: kyros_backend_venv
  celery_beat_data:
    name: kyros_celery_beat_data

networks:
  default:
    name: kyros_network
```

### Key compose decisions explained

**Container naming** uses the `kyros-` prefix on every container. `docker ps` is immediately readable and reduces collision with other compose stacks the engineer might run.

**Volume naming** uses the `kyros_` prefix. `docker volume ls` is greppable; removing all Kyros state is one command: `docker volume ls -q | grep ^kyros_ | xargs docker volume rm`.

**`restart: unless-stopped`** instead of `always`. Engineers stopping a container (`docker stop`) shouldn't have it auto-restart. `unless-stopped` survives daemon restarts but respects explicit stops.

**Bind mount for source code** at `./backend:/app:cached`. The `:cached` flag is a macOS optimization (no-op on Linux) that improves filesystem performance for the host-as-source-of-truth case.

**Named volume for `/opt/venv`** (`backend_venv`). Without this, the bind mount of `./backend` would shadow the container's `/opt/venv` if the host also had a `venv` directory. The named volume preserves the container's Python environment regardless of host directory state.

**Postgres init SQL** in `infra/docker/postgres/init.sql` runs once on first volume creation. It is **not** the Alembic schema. It creates the database (if not already created by env), enables required extensions (`pgcrypto`, `pg_trgm`, `uuid-ossp` — though we prefer `gen_random_uuid()` from `pgcrypto`), and optionally creates a read-only role for analytics. Alembic migrations are run as a separate one-shot command (see below).

```sql
-- infra/docker/postgres/init.sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Read-only role for analytics queries (used in admin UI)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kyros_readonly') THEN
    CREATE ROLE kyros_readonly NOLOGIN;
  END IF;
END
$$;
GRANT CONNECT ON DATABASE kyros TO kyros_readonly;
GRANT USAGE ON SCHEMA public TO kyros_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO kyros_readonly;
```

**Health checks with `condition: service_healthy`** ensure backend-api won't try to connect to a Postgres that's still initializing. This is one of the most common newbie-compose mistakes: backend logs flood with connection errors on first `up`, the engineer thinks the app is broken, restarts, eventually realizes it's a timing issue. `condition: service_healthy` makes it work first try.

**Redis without persistence in local dev** (`--appendonly no --save ""`). Local Redis state is ephemeral; persisting it slows down `up`/`down` cycles and can corrupt across compose version bumps. In production, ElastiCache handles persistence with proper backups.

**Ports exposed in local dev:**
- `5432` (postgres): for `psql -h localhost`, IDE database explorers.
- `6379` (redis): for `redis-cli -h localhost`.
- `8000` (backend): for browser, Postman, curl.
- `1025`/`8025` (mailhog): SMTP receiver + web UI.

**Ports NOT exposed in production:**
- Postgres and Redis are inside a VPC, never publicly reachable.
- Backend is reachable only through an ALB.
- Celery workers and beat are not on any external network.

### Migration workflow in Docker

Migrations are **never run automatically by the application process**. They are a deliberate, observable step.

**Local dev migration:**

```bash
docker compose run --rm backend-api alembic upgrade head
```

This spawns a one-shot container, runs migrations, exits. The `--rm` ensures no leftover containers.

**Creating a new migration:**

```bash
docker compose run --rm backend-api alembic revision --autogenerate -m "add kc_lab_orders.urgency_priority column"
```

The generated migration appears in `backend/alembic/versions/` on the host (via the bind mount). The engineer reviews it before committing.

**Seeding:**

```bash
docker compose run --rm backend-api python scripts/seed_dev.py
```

The seed script is idempotent: re-runs are safe and update-or-insert.

**Reset everything:**

```bash
docker compose down -v          # removes containers AND volumes
docker compose up -d postgres redis
docker compose run --rm backend-api alembic upgrade head
docker compose run --rm backend-api python scripts/seed_dev.py
docker compose up -d
```

**Why migrations are never auto-run on boot:**

1. **Production deploys are atomic.** Migrations on app boot mean every container instance racing to run them. With multiple ECS tasks, this is undefined behavior. With one EC2 host today, it still creates a "what migration ran when" ambiguity that audits hate.
2. **Backward-incompatible migrations break.** A migration that drops a column must happen *after* old code is fully drained, not on the next deploy's boot. The deploy choreography (deploy code that handles both schemas → run migration → deploy code that requires new schema) cannot be automated by app boot.
3. **Migrations should be reviewed and audited.** Running them via a CI step (`make migrate-prod`) gives a clear log artifact and a human-approved gate.

The Makefile target:

```makefile
migrate:
	docker compose run --rm backend-api alembic upgrade head

migrate-prod:
	@echo "Running production migration. Continue? [y/N]"
	@read ans && [ "$$ans" = "y" ]
	# Via SSH to EC2 / via ECS RunTask in Phase 2
	# See infra/scripts/run-migration-prod.sh
	./infra/scripts/run-migration-prod.sh
```

### Hot reload strategy

Backend hot reload is via `uvicorn --reload` in the dev stage. The bind mount at `./backend:/app` means file changes on host are visible inside the container immediately, and uvicorn restarts the app process.

**Things that don't hot-reload and require a container restart:**

- Changes to `pyproject.toml` (new dep). Run `docker compose build backend-api` then `docker compose up -d backend-api`.
- Changes to Alembic models that need a new migration. Run the migration explicitly.
- Changes to Celery task definitions. Run `docker compose restart celery-worker celery-beat`. (Celery does not have reliable autoreload; do not enable `--autoreload` in production.)

### Test containers

We use **a dedicated `docker-compose.test.yml`** rather than testcontainers-python, for these reasons:

- Test compose is observable: engineers can `docker compose -f docker-compose.test.yml up -d` and inspect the test DB while debugging a failing test.
- Compose is the same orchestration concept developers already know.
- Testcontainers adds a dependency that takes ~15s to set up per test process; compose-up-once is faster for the development loop.
- CI runs the same compose file as developers (modulo image build).

```yaml
# docker-compose.test.yml
name: kyros-test

services:
  postgres-test:
    image: postgres:16.4-alpine
    environment:
      POSTGRES_USER: kyros
      POSTGRES_PASSWORD: test
      POSTGRES_DB: kyros_test
    tmpfs:
      - /var/lib/postgresql/data  # in-memory for speed, no persistence needed
    ports:
      - "55432:5432"  # different host port to avoid collision with dev
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kyros -d kyros_test"]
      interval: 2s
      timeout: 2s
      retries: 10

  redis-test:
    image: redis:7.4-alpine
    command: ["redis-server", "--save", ""]
    tmpfs:
      - /data
    ports:
      - "56379:6379"
```

Tests run on the host (not in compose) with `DATABASE_URL=postgresql+asyncpg://kyros:test@localhost:55432/kyros_test`. This is fast: pytest doesn't need to be in a container.

CI runs the same way: spin up `docker-compose.test.yml`, run pytest on the runner, tear down.

### Environment variable handling

In compose, env vars come from three places, in precedence order (last wins):

1. `env_file: ./backend/.env` — developer-local secrets and config (gitignored)
2. `environment:` block in the compose service — overrides for compose-specific values (DB host = service name, etc.)
3. Shell environment at `docker compose up` time

In production:

- **Phase 1 (EC2):** env vars come from `.env` files baked into the EC2 user-data or pulled from AWS Secrets Manager via a startup script that writes `/etc/kyros/backend.env`, then docker compose reads it.
- **Phase 2 (ECS):** task definition has `secrets` entries that pull from Secrets Manager. No `.env` on disk.

### Secrets

`.env.example` is committed and documents every variable:

```bash
# backend/.env.example
KYROS_ENV=local
KYROS_APP_VERSION=dev
KYROS_LOG_LEVEL=DEBUG

# Database
KYROS_DATABASE_URL=postgresql+asyncpg://kyros:kyros_dev_password@postgres:5432/kyros
KYROS_DATABASE_POOL_SIZE=10
KYROS_DATABASE_MAX_OVERFLOW=10

# Redis
KYROS_REDIS_URL=redis://redis:6379/0
KYROS_CELERY_BROKER_URL=redis://redis:6379/1
KYROS_CELERY_RESULT_BACKEND=redis://redis:6379/2

# Auth
KYROS_JWT_SECRET=change-me-in-real-env
KYROS_JWT_ALGORITHM=HS256
KYROS_JWT_ACCESS_TOKEN_TTL_SECONDS=3600
KYROS_JWT_REFRESH_TOKEN_TTL_SECONDS=2592000
KYROS_ARGON2_TIME_COST=3
KYROS_ARGON2_MEMORY_COST=65536
KYROS_ARGON2_PARALLELISM=4

# OTP
KYROS_OTP_TTL_SECONDS=300
KYROS_OTP_MAX_ATTEMPTS=5
KYROS_OTP_RESEND_COOLDOWN_SECONDS=60

# CORS
KYROS_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:19006

# S3
KYROS_AWS_REGION=ap-south-1
KYROS_S3_BUCKET_PHI=kyros-phi-dev
KYROS_AWS_ACCESS_KEY_ID=                # use IAM role in prod; key only for local LocalStack or real AWS in dev
KYROS_AWS_SECRET_ACCESS_KEY=
KYROS_S3_KMS_KEY_ID=                     # for SSE-KMS

# Razorpay
KYROS_RAZORPAY_KEY_ID=
KYROS_RAZORPAY_KEY_SECRET=
KYROS_RAZORPAY_WEBHOOK_SECRET=

# 100ms
KYROS_HMS_ACCESS_KEY=
KYROS_HMS_SECRET=
KYROS_HMS_TEMPLATE_ID=

# Google Document AI
KYROS_GCP_PROJECT_ID=
KYROS_DOCUMENT_AI_PROCESSOR_ID=
KYROS_DOCUMENT_AI_LOCATION=asia-south1
KYROS_GCP_SERVICE_ACCOUNT_JSON=          # path to JSON file, or the JSON inline (for prod via Secrets Manager)

# MSG91
KYROS_MSG91_AUTH_KEY=
KYROS_MSG91_TEMPLATE_ID=

# WhatsApp (AiSensy)
KYROS_AISENSY_API_KEY=
KYROS_AISENSY_PROJECT_ID=

# Email
KYROS_SMTP_HOST=mailhog
KYROS_SMTP_PORT=1025
KYROS_SMTP_USER=
KYROS_SMTP_PASSWORD=
KYROS_EMAIL_FROM=noreply@kyros.clinic

# Sentry
KYROS_SENTRY_DSN=
KYROS_SENTRY_ENVIRONMENT=local
KYROS_SENTRY_TRACES_SAMPLE_RATE=0.1
```

The `.env` file is the same shape, with real values, and is gitignored.

In production, none of these live in `.env`. They live in AWS Secrets Manager. A boot-time script reads from Secrets Manager and either writes a transient `.env` on disk (Phase 1 EC2) or injects them as ECS task secrets (Phase 2).

### What must never be in production env vars

- Any value that changes per deployment slot (canary vs prod): these belong in feature flags or runtime config.
- KMS-encrypted blobs (those decrypt on first use via the application).
- Database connection strings with embedded passwords for production: use Secrets Manager with rotation, and inject the URL at boot.

---

## 5. PostgreSQL strategy

### Why PostgreSQL 16

For Kyros, PostgreSQL 16 is the right database choice for these specific reasons:

- **Healthcare transactions are relational.** A consultation has a patient, a doctor, optional prescription, optional lab order, payment, audit entries. These relationships are well-modeled as foreign keys with strict referential integrity. NoSQL would force denormalization that creates consistency bugs.
- **JSONB lets us handle structured-but-evolving payloads** without abandoning relational discipline. Lab OCR output, intake responses, wearable summaries, and consent metadata are natural JSONB targets — bounded structure, queryable, indexable.
- **`gen_random_uuid()` from `pgcrypto`** generates UUIDv4 in the database, removing the round-trip cost of generating IDs in Python.
- **Partial indexes and expression indexes** let us index "active consultations" or "non-deleted patients" without bloating index size on historical data.
- **Range types and exclusion constraints** prevent overlapping doctor availability slots at the DB level. This is a Postgres-only feature that other databases can't replicate cleanly.
- **Native partitioning by RANGE** on timestamp gives us monthly partitions for `wn_health_datapoints` and `ad_audit_log` without third-party extensions.
- **RDS support is mature.** Postgres 16 on RDS in `ap-south-1` is a one-click reality with point-in-time recovery, automated backups, and Multi-AZ failover.

### One database, multiple domains via table prefixes

The build spec mandates one database with domain-prefixed tables (`wn_`, `kc_`, `dr_`, `ad_`). We do **not** use Postgres schemas (the `CREATE SCHEMA` namespace feature) for these domains. Reasoning:

- Schemas complicate Alembic configuration. `include_schemas=True` and per-schema search paths add friction without benefit at our scale.
- Cross-domain queries (a consultation joined to a doctor joined to a patient) are constant. Schemas make these visually noisy.
- Backup and restore are easier with one schema (`public`).
- Domain isolation is achieved by code structure (`models/clinical.py`, `repositories/clinical/...`), not by SQL schema separation.

We *do* use schemas for one purpose: a separate `audit` schema is acceptable for the immutable audit log if we eventually replicate it to a different store, but for Phase A it stays in `public.ad_audit_log`.

### Schema-wide conventions

Every table follows these conventions, enforced via a SQLAlchemy `DeclarativeBase` and mixins:

**Naming convention (Alembic + SQLAlchemy):**

```python
# app/db/base.py
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)
```

This guarantees stable constraint names across `alembic autogenerate` runs.

**UUID primary keys, generated in DB:**

```python
# app/db/mixins.py
from sqlalchemy import Column, DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from uuid import UUID as PyUUID

class UUIDMixin:
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
```

The `server_default=text("gen_random_uuid()")` is critical: the DB generates the ID. Python never sees the ID before insert. This also means inserts work in bulk-insert and trigger-driven contexts.

**Timestamps in UTC, displayed in IST:**

Every `TIMESTAMPTZ` column stores UTC. Python `datetime.now(timezone.utc)` is the only acceptable way to generate timestamps in app code. Display conversion to IST (`Asia/Kolkata`) happens at the presentation layer (Pydantic serializer for API, Jinja filter for admin UI).

This avoids the perennial bug where one developer writes naive `datetime.now()` and another writes `datetime.now(tz=KOLKATA)` and the values are inconsistent.

**Soft delete pattern:**

- `deleted_at` is nullable; `NULL` means active.
- Every repository function filters `deleted_at IS NULL` by default. A separate `*_with_deleted` variant exists for admin views.
- Hard delete (`DELETE FROM ...`) happens only via DPDP erasure flow (see §13) and via partition rotation for time-series data.

**Why NOT use a `status='deleted'` enum:** soft delete via `deleted_at` lets us index on it cheaply (partial index `WHERE deleted_at IS NULL`), gives us the deletion timestamp for free, and doesn't conflict with the legitimate `status` enums on tables like consultations and prescriptions.

### Enums: Postgres-native, mirrored in Python

Build-spec tables use enums (consultation status, role, condition category, etc.). We use **Postgres-native ENUMs** mirrored as Python `enum.Enum` subclasses:

```python
# app/db/enums.py
from enum import StrEnum

class Role(StrEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    COORDINATOR = "coordinator"
    SUPER_ADMIN = "super_admin"
    SYSTEM = "system"

class ConsultationStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class ConditionCategory(StrEnum):
    THYROID = "thyroid"
    WEIGHT = "weight"
    PCOS = "pcos"
    SKIN_HAIR = "skin_hair"
    MENS_INTIMATE = "mens_intimate"
    HORMONES_TRT = "hormones_trt"
    LONGEVITY = "longevity"
```

In SQLAlchemy:

```python
from sqlalchemy import Enum as SAEnum

class Consultation(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "kc_consultations"
    status: Mapped[ConsultationStatus] = mapped_column(
        SAEnum(ConsultationStatus, name="consultation_status", create_type=False),
        nullable=False,
        default=ConsultationStatus.SCHEDULED,
    )
```

`create_type=False` means SQLAlchemy won't auto-create the type; instead, Alembic migrations create them explicitly. This gives us control over enum value additions (Postgres can `ALTER TYPE ADD VALUE` but cannot remove without rebuilding the type).

**Enum migration discipline:**

- Adding a value: a forward-only migration with `op.execute("ALTER TYPE consultation_status ADD VALUE IF NOT EXISTS 'rescheduled'")`.
- Renaming a value: requires `CREATE TYPE _new`, copy column data, drop old type. Rarely worth it; usually deprecate the old value and stop writing it.
- Removing a value: a multi-step migration: stop writing the value in code, backfill rows that have it, then remove via type recreation. Plan as a multi-deploy effort.

### Migrations

Alembic, exclusively. Configuration sketch:

```python
# alembic/env.py (excerpts)
from app.db.base import Base
from app.models import *  # noqa — register all models with Base.metadata
from app.core.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.alembic_database_url)  # sync URL for migrations

target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,             # detect type changes
            compare_server_default=True,   # detect default changes
            include_schemas=False,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()
```

**Alembic uses a SYNC connection**, even though the app uses asyncpg. Alembic's autogenerate and DDL operations are simpler synchronous. The `alembic_database_url` in settings is the same DSN minus the `+asyncpg` driver, plus `+psycopg2` (we add `psycopg2-binary` to the dependencies for this purpose only).

**Migration patterns to enforce in code review:**

- Every column add is nullable OR has a server_default. Backfill nulls in a separate migration if needed.
- Index creation in production uses `CREATE INDEX CONCURRENTLY` (cannot be in a transaction). The migration uses `with op.get_context().autocommit_block():` and `op.create_index(..., postgresql_concurrently=True)`.
- Column type changes that rewrite the table are avoided on tables > 1M rows. If unavoidable, do a phased migration: add new column, dual-write, backfill, switch reads, drop old.
- Foreign keys are added with `ON DELETE` semantics explicitly specified (CASCADE, RESTRICT, or SET NULL). Defaults are not acceptable in healthcare.

### Indexing philosophy

Indexes are added when justified by a real query, never speculatively. The justification is documented in the migration message.

Phase-A indexes that earn their place from day one:

**On `users`:**
- `UNIQUE (email)` where `deleted_at IS NULL` — partial unique to allow soft-deleted users to be recreated.
- `UNIQUE (phone)` where `deleted_at IS NULL` — same reasoning.
- `(role)` — for "list all doctors", "list all coordinators" admin queries.

**On `kc_patients`:**
- `UNIQUE (user_id)` (1:1 with users).
- `UNIQUE (kyros_patient_id)` (human-readable ID).
- `(assigned_coordinator_id)` where `deleted_at IS NULL` — coordinator panel queries.
- `(preferred_doctor_id)` — doctor panel queries.
- GIN on `primary_conditions` (JSONB) — "patients with PCOS" filter.

**On `kc_consultations`:**
- `(patient_id, scheduled_start_at DESC)` — patient's history view.
- `(doctor_id, scheduled_start_at DESC)` — doctor schedule view.
- `(coordinator_id, status)` where `deleted_at IS NULL` — coordinator queue.
- `(status, scheduled_start_at)` — Celery scan for "consultations needing video room provisioning at T-15min".
- `(condition_category, scheduled_start_at)` — analytics rollups.

**On `kc_lab_reports`:**
- `(patient_id, report_date DESC)` — patient's labs view.
- `(doctor_reviewed_by, reviewed_at)` — doctor pending review queue.

**On `ad_audit_log`:**
- `(actor_user_id, timestamp DESC)` — "what did this user do" forensics.
- `(resource_type, resource_id, timestamp DESC)` — "who touched this consultation" forensics.
- `(timestamp DESC)` BRIN index — efficient on append-only time-ordered data.

**On `wn_health_datapoints`:**
- See partitioning below; per-partition indexes on `(user_id, recorded_at)`.

### JSONB vs normalized columns

The rule: **JSONB for payloads whose shape is bounded but evolves; normalized columns for anything you'll query, sort, or filter on regularly.**

Concrete decisions from the build spec:

| Field | Choice | Reason |
|---|---|---|
| `kc_lab_reports.parsed_json` | JSONB | Biomarker structure is provider-dependent; we query lab values via lab-specific endpoints with structured projection, not WHERE clauses. |
| `kc_lab_reports.ocr_confidence_avg` | DECIMAL column | Filtered ("low confidence reports for doctor review"). |
| `kc_pre_consultation_reports.lab_summary` | JSONB | Composite snapshot; never queried inside, displayed whole. |
| `kc_patients.primary_conditions` | JSONB (array) | GIN-indexed; queried with `?` operator for "patients with X". |
| `kc_consultations.condition_category` | ENUM column | High-volume filter; needs efficient index. |
| `ad_audit_log.metadata` | JSONB | Heterogeneous extra context. Forensics queries occasionally search; GIN-index if a real query emerges. |
| `wn_health_datapoints.value` | numeric column + `value_unit` text | Time-series queries need WHERE on value; JSONB would be wrong. |

### Partitioning

Two tables are partitioned by `RANGE` on time:

**`wn_health_datapoints`** — partitioned monthly by `recorded_at`:

```sql
CREATE TABLE wn_health_datapoints (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    data_type VARCHAR(50) NOT NULL,
    value NUMERIC(12,4) NOT NULL,
    value_unit VARCHAR(20) NOT NULL,
    source VARCHAR(50) NOT NULL,                 -- 'healthkit' | 'health_connect' | 'manual'
    source_record_id VARCHAR(255) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB,
    PRIMARY KEY (id, recorded_at),               -- partition key must be in PK
    UNIQUE (user_id, source, source_record_id, recorded_at)
) PARTITION BY RANGE (recorded_at);

CREATE TABLE wn_health_datapoints_2026_06 PARTITION OF wn_health_datapoints
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE INDEX ix_wn_hdp_2026_06_user_time ON wn_health_datapoints_2026_06 (user_id, data_type, recorded_at DESC);
```

A Celery task (`maintenance_tasks.ensure_partitions_ahead`) runs monthly via beat, ensuring partitions exist 3 months ahead.

**`ad_audit_log`** — partitioned monthly by `timestamp`. Same pattern. Reasoning: audit logs grow indefinitely, and we want cheap "drop old partition" semantics for retention policy (e.g., move old partitions to cold storage at 5 years).

### Soft delete: behavior in practice

Repository pattern:

```python
# repositories/patients_repo.py
async def get_patient_by_user_id(
    db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> Patient | None:
    stmt = select(Patient).where(Patient.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Patient.deleted_at.is_(None))
    return await db.scalar(stmt)
```

We do **not** install SQLAlchemy event listeners or query hooks that automatically inject `deleted_at IS NULL`. Reasoning: implicit filtering is a footgun. An admin-side query that needs deleted rows would be confusing if a hidden filter blocked them. Repository functions make the policy explicit and reviewable.

### Connection pooling

For async FastAPI with asyncpg:

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,          # default 10
    max_overflow=settings.database_max_overflow,    # default 10
    pool_pre_ping=True,                              # ping before use, recover from idle drops
    pool_recycle=1800,                               # recycle connections every 30min
    echo=False,                                      # never True in production
    connect_args={"server_settings": {"jit": "off"}},  # disable JIT for predictable latency
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

Sizing:

- Single EC2 t3.small (2 vCPUs): 2 uvicorn workers × 10 pool size = 20 connections potentially open. RDS db.t3.micro supports ~85 connections; we have plenty of headroom.
- Pool size of 10 + overflow of 10 = burst capacity of 20 per worker.
- `pool_pre_ping` catches connections silently dropped by RDS during failover.
- `expire_on_commit=False` is essential for async; it avoids attempting to lazy-load attributes after the session is closed.
- `autoflush=False` makes queries deterministic; you flush explicitly when you want to.

### pgBouncer: use later, not now

In Phase 1 (single EC2, ~20 connections), pgBouncer adds operational complexity for no measurable gain.

In Phase 2 (ECS Fargate, multiple tasks each with their own pool), pgBouncer in `transaction` mode becomes valuable: many short-lived tasks can share a smaller backend pool. Add it as a sidecar or a separate ECS service when:

- Total backend connections approach 50% of RDS instance max_connections, OR
- Connection wait times appear in DB metrics.

Implementation note: pgBouncer in transaction mode does not support session-level features (LISTEN/NOTIFY, prepared statements pooled across connections). Asyncpg's prepared statement cache must be disabled when behind pgBouncer transaction mode: `connect_args={"statement_cache_size": 0}`.

### Transaction boundaries in service methods

The pattern: **one HTTP request = one transaction.** The `get_db` dependency opens a session, commits on success, rolls back on exception.

Services do not commit or roll back; they perform operations. The router-level dependency manages the transaction lifecycle. This means:

- A service function that orchestrates multiple writes is atomic by default.
- A service function called from a Celery task uses a separate session (Celery tasks have their own session lifecycle).
- Services never call `db.commit()`. If a service legitimately needs to commit mid-flow (rare; consider it a code smell), it does so explicitly and documents why.

Celery task session pattern:

```python
# tasks/celery_app.py
from contextlib import asynccontextmanager
from app.db.session import AsyncSessionLocal

@asynccontextmanager
async def task_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Tasks use this context manager; one task invocation = one DB session = one transaction.

### Row locking for concurrency-sensitive flows

Three places where we explicitly lock:

1. **Doctor availability slot booking.** Two patients booking the same slot must serialize. Lock the slot row with `SELECT ... FOR UPDATE` inside the transaction.

   ```python
   stmt = (
       select(Availability)
       .where(Availability.id == slot_id)
       .where(Availability.status == AvailabilityStatus.AVAILABLE)
       .with_for_update()
   )
   ```

2. **Payment idempotency.** When processing a Razorpay webhook, lock the payment row to prevent two simultaneous handlers from double-recording. Combined with the idempotency key in Redis (see §6).

3. **Prescription versioning.** When a doctor edits a signed prescription, lock the current prescription row, supersede it (set `superseded_by_id`), insert the new version. Inside a transaction.

For everything else, the default `READ COMMITTED` isolation is sufficient. We do not use `SERIALIZABLE` (the operational cost — retry storms on conflict — outweighs the benefit).

### Idempotency patterns

Two layers:

1. **HTTP-level idempotency** for mutating endpoints. The client sends an `Idempotency-Key` header. The backend stores `(idempotency_key, user_id, response_hash)` in Redis with a 24h TTL. A duplicate request with the same key returns the cached response. Applies to: `POST /consultations` (booking), `POST /payments`, `POST /lab-reports` (upload).

2. **Task-level idempotency** for Celery. Every task either has natural idempotency (writing with unique constraints on natural keys) or uses a Redis-stored "task ran for this resource" marker.

### Backup and restore

Local dev: nothing. The volume is disposable.

Production Phase 1 (RDS db.t3.micro): automated daily snapshots with 7-day retention. Point-in-time recovery enabled. Manual snapshot before every migration. Restore drill quarterly to verify backups actually work.

Production Phase 2 (RDS db.t3.medium Multi-AZ): same plus 30-day retention, snapshot to a separate AWS account (replication target) for ransomware-resistant backup.

### Local Postgres init script

`infra/docker/postgres/init.sql` runs only on first volume creation. It creates extensions, the read-only role, and nothing else. **It does not create tables.** Tables come from Alembic migrations.

If the init script and Alembic migrations conflict (someone manually edits init.sql to add a table), Alembic will fail or autogenerate phantom migrations. Keep init.sql minimal and migration-only as the source of schema truth.

### Production RDS migration path

When promoting from local Docker Postgres to RDS:

1. Create RDS instance in `ap-south-1`, Postgres 16.x, KMS-encrypted.
2. Run `init.sql` against RDS (create extensions, roles).
3. Run `alembic upgrade head` from a bastion or via ECS RunTask.
4. (If migrating data) `pg_dump` from old → `pg_restore` to new.
5. Update `KYROS_DATABASE_URL` secret in Secrets Manager.
6. Restart backend pods. Validate via `/readyz`.
7. Verify with smoke tests.

---

## 6. Redis strategy

### Why Redis is used in Kyros

Redis serves five specific purposes:

1. **Celery broker** — task queue messaging.
2. **Celery result backend** — task result storage (with TTL).
3. **OTP storage** — short-lived, TTL-bound.
4. **Rate limiting** — per-IP and per-user request counters.
5. **Idempotency keys** — HTTP and webhook idempotency.

Beyond these, we use Redis sparingly. Caching of read-heavy endpoints (e.g., public doctor directory) is acceptable but should be added only when a real latency problem appears.

### Redis database (logical DB) layout

Redis supports 16 logical DBs (`SELECT 0` through `SELECT 15`). We use named DBs for isolation:

| DB | Purpose | Eviction |
|---|---|---|
| 0 | General application cache (rate limits, idempotency, OTP) | `volatile-ttl` |
| 1 | Celery broker (`redis://.../1`) | `noeviction` |
| 2 | Celery result backend (`redis://.../2`) | `volatile-ttl` |

`noeviction` for the Celery broker is critical: losing a queued task is unacceptable. We size Redis with headroom and alert on memory pressure rather than risk evicted jobs.

### Key naming convention

A strict pattern: `{namespace}:{entity}:{id}[:{sub}]`. Examples:

- `otp:phone:+919999000000` — OTP code for a phone, TTL 5 min.
- `otp:phone:+919999000000:attempts` — failed attempt counter, TTL 15 min.
- `otp:phone:+919999000000:cooldown` — resend cooldown, TTL 60 sec.
- `ratelimit:ip:1.2.3.4:/v1/auth/otp/request` — sliding window counter.
- `ratelimit:user:{uuid}:/v1/clinic/patient/consultations` — per-user counter.
- `idempotency:user:{uuid}:{key}` — HTTP idempotency entry.
- `webhook:razorpay:{event_id}` — webhook dedup marker.
- `session:admin:{session_id}` — admin UI session cookie value mapping.
- `lock:consultation:{uuid}` — distributed lock.

Namespace prefixes mean we can flush a specific class of keys without touching others: `redis-cli --scan --pattern 'ratelimit:*' | xargs redis-cli DEL`.

### OTP storage

OTP flow uses Redis as the canonical store; OTPs **never** go to Postgres. Reasoning: OTPs are short-lived (5 min), high-frequency, and need atomic increment for attempt counting. Postgres would be overkill and would add row turnover noise.

Implementation:

```python
# services/otp_service.py
async def issue_otp(redis: Redis, phone: str) -> str:
    cooldown_key = f"otp:phone:{phone}:cooldown"
    if await redis.exists(cooldown_key):
        raise BusinessRuleError("otp_cooldown")
    code = generate_numeric_code(6)
    code_key = f"otp:phone:{phone}"
    # Use SET with EX + NX semantics; pipeline for atomicity
    pipe = redis.pipeline()
    pipe.set(code_key, hash_otp(code), ex=settings.otp_ttl_seconds)
    pipe.set(cooldown_key, "1", ex=settings.otp_resend_cooldown_seconds)
    pipe.delete(f"otp:phone:{phone}:attempts")  # reset attempts on new issuance
    await pipe.execute()
    return code  # passed to SMS gateway, never returned in API response

async def verify_otp(redis: Redis, phone: str, code: str) -> bool:
    code_key = f"otp:phone:{phone}"
    attempts_key = f"otp:phone:{phone}:attempts"
    attempts = await redis.incr(attempts_key)
    if attempts == 1:
        await redis.expire(attempts_key, 900)  # 15 min window for attempts
    if attempts > settings.otp_max_attempts:
        await redis.delete(code_key)  # invalidate code after too many attempts
        raise BusinessRuleError("otp_too_many_attempts")
    stored = await redis.get(code_key)
    if stored is None:
        raise BusinessRuleError("otp_expired")
    if not constant_time_compare(stored, hash_otp(code)):
        raise BusinessRuleError("otp_invalid")
    await redis.delete(code_key, attempts_key)  # one-shot consume
    return True
```

The hash function for OTP is `HMAC-SHA256(otp_secret, code)`. We never store raw OTPs even in Redis. The `otp_secret` is a deployment-wide secret in Secrets Manager.

### Rate limiting

We use a sliding-window counter pattern, not a fixed-window counter (fixed windows allow 2× burst at boundaries). Implementation via SlowAPI-on-Redis or hand-rolled with a Lua script.

The hand-rolled pattern, for transparency:

```lua
-- A sliding-window rate limit using sorted sets.
-- KEYS[1] = rate limit key
-- ARGV[1] = window seconds, ARGV[2] = max requests, ARGV[3] = now (epoch ms)
local key = KEYS[1]
local window_ms = tonumber(ARGV[1]) * 1000
local max = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cutoff = now - window_ms
redis.call('ZREMRANGEBYSCORE', key, 0, cutoff)
local count = redis.call('ZCARD', key)
if count >= max then
  return 0
end
redis.call('ZADD', key, now, now .. '-' .. math.random())
redis.call('PEXPIRE', key, window_ms)
return max - count
```

Defaults (tunable per environment):

| Surface | Limit |
|---|---|
| `/v1/auth/otp/request` per phone | 3 per 15 min |
| `/v1/auth/otp/request` per IP | 30 per 15 min |
| `/v1/auth/login` per IP | 20 per 5 min |
| `/v1/clinic/patient/*` per user | 120 per minute |
| `/v1/doctor/*` per user | 300 per minute |
| `/v1/admin/*` per user | 600 per minute |
| `/v1/public/*` per IP | 60 per minute |
| `/v1/webhooks/razorpay` per IP (allowlist enforced too) | 1000 per minute |

429 responses include `Retry-After` and `X-RateLimit-Remaining` headers.

### Distributed locks

Used for:

- Doctor availability booking (preventing double-booking despite the DB-level row lock — Redis lock is the first line, DB row lock is the durable backstop).
- Celery task de-duplication (preventing two workers from processing the same OCR job).

We use Redlock-style locks via the `redis-py` client's `Lock()` interface — not because we need quorum across multiple Redis instances (we don't, Phase A has one), but because the API is idiomatic and handles lock TTLs.

```python
async with redis.lock(f"lock:consultation:{consultation_id}", timeout=10, blocking_timeout=2):
    # critical section
    ...
```

Locks always have a TTL. A lock held forever (process crashed) automatically releases after the timeout, preventing deadlock.

### Idempotency guards

For mutating HTTP endpoints with `Idempotency-Key`:

```python
# middleware or dependency
async def idempotency_check(
    request: Request,
    user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    key = request.headers.get("Idempotency-Key")
    if not key:
        return None  # idempotency optional unless route requires it
    storage_key = f"idempotency:user:{user.id}:{key}"
    cached = await redis.get(storage_key)
    if cached:
        return json.loads(cached)  # return cached response
    # caller will store result with TTL after success
    return None
```

For Razorpay webhooks, the event has a unique `id`. We `SETNX` on `webhook:razorpay:{event_id}` with a 7-day TTL. Returns 200 immediately if already seen.

### What should NOT be in Redis

- **Anything PHI.** No lab values, no prescription contents, no patient names. Redis is volatile by design; PHI must be in encrypted Postgres or S3.
- **The source of truth for any business state.** A booking confirmation is in Postgres; Redis can cache it but cannot be the only place it lives.
- **Long-lived sessions.** Admin UI session entries (~hours) are fine, but anything longer goes to Postgres.
- **Large blobs.** No JSON over 100 KB. Redis is a key-value store with sub-ms expectations; bloated values destroy that.

### Memory and TTL discipline

Every key has a TTL. There is no exception. A key without a TTL is a code review reject.

Why: Redis without TTL discipline grows until OOM. Memory pressure causes evictions in unpredictable order (with `volatile-ttl`, oldest-TTL keys go first; without TTLs, with `noeviction`, writes start failing).

ElastiCache Phase 1 sizing: `cache.t3.micro` (0.5 GB usable). At a few thousand active users, the rate-limit + OTP + idempotency footprint is < 100 MB. Headroom is enormous.

### Redis failure modes

If Redis is down:

- **OTP issuance fails (503).** Acceptable; auth flows degrade gracefully with a clear error.
- **Rate limiting falls open or closed (configurable).** Default: fall open (let traffic through, alert), because failing closed in a Redis outage means the entire API stops working.
- **Celery broker is down → tasks queue in-memory at the API and lose on restart.** Bad. We catch broker connection errors at task dispatch time and surface a 503 to the user with a "please retry" message, OR for non-urgent tasks, write a queue row to Postgres and have a separate Celery beat task pick them up (a "DB fallback queue" for must-not-lose tasks).
- **Idempotency cache misses → duplicate request might be processed twice.** For most endpoints, the database has its own uniqueness constraint (e.g., `kc_payments.razorpay_order_id UNIQUE`), so the duplicate fails at the DB layer. We rely on DB uniqueness as the durable backstop.

### Local dev Redis

The compose service runs `redis-server --appendonly no --save ""` — pure in-memory, no persistence. Sufficient for development; `docker compose down -v` resets state.

### Production ElastiCache

Phase 1: `cache.t3.micro` single-AZ, encrypted in transit and at rest.

Phase 2: `cache.t3.medium` Multi-AZ with automatic failover, IAM authentication if AWS supports it for our use case.

Cluster mode (sharding) is not needed at Phase 2 scale; a single primary + replica is sufficient. Only switch to cluster mode if memory exceeds 6 GB per node.

---

## 7. Celery strategy

### Why Celery, given alternatives

Phase A alternatives considered: ARQ (async, Redis-only, lighter), RQ (simple but Python-thread limited), FastAPI BackgroundTasks (in-process, lost on crash). Celery wins for Kyros because:

- **Mature ecosystem** — 14+ years of production patterns, well-known operational pitfalls.
- **Multiple queues with per-queue concurrency** — OCR (long, I/O bound) and report generation (CPU bound) want different worker configurations.
- **Beat for periodic tasks** — partition rolling, reminders, analytics rollups, video room provisioning, all on a single beat schedule.
- **Result backend integration** — when the HTTP API needs to poll task status (lab OCR completion), the result is queryable.
- **Sentry integration is native** — task failures appear in Sentry without custom plumbing.

The async/sync friction with Celery (it's a sync-first library) is real but manageable. Tasks that need DB I/O use a pattern that bridges to async (described below).

### Queue design

Five queues plus `default`:

| Queue | Workload class | Concurrency | Rationale |
|---|---|---|---|
| `ocr` | I/O bound, slow (5–30s per task) | 4 | Document AI calls are network-bound; high concurrency on a single worker process is fine. |
| `notifications` | I/O bound, fast (1–3s) | 8 | High volume, low per-task cost. |
| `reports` | CPU + I/O bound (PDF generation via WeasyPrint, 3–10s) | 2 | WeasyPrint is CPU intensive; oversubscribing pegs the worker. |
| `payments` | I/O bound, low volume, critical | 2 | Razorpay reconciliation, low volume but errors here cost money; prefer slower careful execution. |
| `maintenance` | mixed, low volume | 2 | Cleanup jobs, partition management, analytics rollups. |
| `default` | catchall | 4 | Anything unrouted lands here. |

In Phase 1 (single EC2), all five queues run in **one Celery worker process** with `--queues=ocr,notifications,reports,payments,maintenance,default`. The single process serves all queues with the union of concurrencies (4+8+2+2+2+4 = 22 worker slots, which on a t3.small with 2 GB RAM is realistic if we use `--pool=prefork` with a memory-aware concurrency).

In Phase 2 (ECS Fargate), each queue is a separate ECS service with its own task definition and autoscaling. This is the scaling unlock.

### Worker pool choice

Default `prefork` (process-based) is the right pool for Kyros. The `gevent` and `eventlet` pools have async I/O benefits but break libraries that aren't gevent-safe (some boto3 patterns, certain crypto operations). Prefork is the safe default.

`solo` pool is used in tests only.

### Task routing

```python
# tasks/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery("kyros")
celery_app.conf.broker_url = settings.celery_broker_url
celery_app.conf.result_backend = settings.celery_result_backend
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "Asia/Kolkata"  # for beat schedule readability; tasks still use UTC internally
celery_app.conf.enable_utc = True

# Result backend TTL: results auto-expire after 24h
celery_app.conf.result_expires = 86400

# Task routing by name prefix
celery_app.conf.task_routes = {
    "kyros.clinical.parse_lab_report":         {"queue": "ocr"},
    "kyros.clinical.generate_pre_consult_*":   {"queue": "reports"},
    "kyros.notification.*":                    {"queue": "notifications"},
    "kyros.payment.*":                         {"queue": "payments"},
    "kyros.video.*":                           {"queue": "default"},
    "kyros.dpdp.*":                            {"queue": "maintenance"},
    "kyros.maintenance.*":                     {"queue": "maintenance"},
}

celery_app.conf.task_acks_late = True              # ack after task completes
celery_app.conf.task_reject_on_worker_lost = True  # re-queue if worker dies mid-task
celery_app.conf.worker_prefetch_multiplier = 1     # one task per worker at a time (fairness)
celery_app.conf.task_default_retry_delay = 60      # base retry delay
celery_app.conf.task_default_max_retries = 5

# Discover tasks
celery_app.autodiscover_tasks([
    "app.tasks.ocr_tasks",
    "app.tasks.report_tasks",
    "app.tasks.notification_tasks",
    "app.tasks.payment_tasks",
    "app.tasks.video_tasks",
    "app.tasks.dpdp_tasks",
    "app.tasks.reminder_tasks",
    "app.tasks.analytics_tasks",
    "app.tasks.maintenance_tasks",
])

# Beat schedule
from app.tasks.beat_schedule import beat_schedule
celery_app.conf.beat_schedule = beat_schedule
```

### Retries and backoff

Every task that contacts an external service uses exponential backoff with jitter:

```python
@celery_app.task(
    name="kyros.clinical.parse_lab_report",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, DocumentAITransientError),
    retry_backoff=True,            # exponential
    retry_backoff_max=600,         # cap at 10 min
    retry_jitter=True,             # add randomness
    max_retries=5,
)
def parse_lab_report(self, lab_report_id: str) -> dict:
    ...
```

For tasks that hit Razorpay (mutating money), we use `autoretry_for=()` empty and retry manually only after verifying the operation didn't already succeed (idempotency check).

### Idempotency in tasks

Every task must be safe to run twice. Patterns:

- **Natural idempotency via unique constraints.** Inserting a payment row keyed on `razorpay_order_id` (UNIQUE) — a duplicate insert fails harmlessly; the task catches `IntegrityError` and returns success.
- **State-machine guards.** OCR task checks `kc_lab_reports.parsed_json` is null before parsing; if already populated, exits early.
- **Redis markers** for tasks without DB anchors: `task:notification:{notification_id}` SETNX with 24h TTL.

A task that cannot be made idempotent must be flagged in code review and discussed; we don't ship non-idempotent tasks.

### Long-running vs short-running

Phase-A task time profile:

| Task | Typical duration | Profile |
|---|---|---|
| `parse_lab_report` | 5–30s | I/O bound (Document AI call) |
| `generate_pre_consult_report` | 3–10s | CPU + I/O (WeasyPrint + DB queries) |
| `provision_video_room` | 1–3s | I/O (100ms API) |
| `send_push_notification` | <2s | I/O (Expo Push) |
| `send_whatsapp_utility` | <2s | I/O (AiSensy) |
| `reconcile_payment` | 1–3s | I/O (Razorpay verify) |
| `generate_data_export` | 30s–5min | I/O + CPU (zip generation, S3 upload) |
| `process_data_erasure` | 1–10min | I/O (multi-table deletes + S3 deletes) |

Tasks expected to run > 60 seconds use a separate execution model: they emit progress updates to Redis (`task_progress:{task_id}` → JSON), and the HTTP API can poll progress.

For tasks > 10 minutes (data export of a large patient history), we use a "chunked task" pattern: the orchestrator task spawns child tasks per chunk, each writes its piece to S3, a final task assembles the manifest. This avoids worker timeouts.

### Beat schedule

```python
# tasks/beat_schedule.py
from celery.schedules import crontab

beat_schedule = {
    # Provision 100ms video room 15 minutes before scheduled start
    "provision-video-rooms-soon": {
        "task": "kyros.video.provision_upcoming_rooms",
        "schedule": crontab(minute="*/1"),  # every minute
    },
    # Generate pre-consultation reports for tomorrow's appointments
    "generate-pre-consult-reports-tomorrow": {
        "task": "kyros.clinical.generate_pre_consult_reports_for_tomorrow",
        "schedule": crontab(hour=4, minute=0),  # 4 AM IST daily
    },
    # Dispatch reminders (water, supplements, medications)
    "dispatch-due-reminders": {
        "task": "kyros.reminder.dispatch_due",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
    # Razorpay payment reconciliation (catch missed webhooks)
    "reconcile-pending-payments": {
        "task": "kyros.payment.reconcile_pending",
        "schedule": crontab(minute=0, hour="*/2"),  # every 2h
    },
    # Daily analytics rollup
    "rollup-daily-metrics": {
        "task": "kyros.analytics.rollup_daily",
        "schedule": crontab(hour=2, minute=30),  # 2:30 AM IST
    },
    # Ensure DB partitions exist 3 months ahead
    "ensure-partitions-ahead": {
        "task": "kyros.maintenance.ensure_partitions_ahead",
        "schedule": crontab(hour=3, minute=0, day_of_month=1),  # monthly
    },
    # DPDP soft-delete grace period sweep
    "process-erasure-grace-expiries": {
        "task": "kyros.dpdp.process_pending_erasures",
        "schedule": crontab(hour=1, minute=0),  # 1 AM IST daily
    },
    # Audit log integrity check (verify nothing was deleted/altered)
    "verify-audit-log-integrity": {
        "task": "kyros.maintenance.verify_audit_integrity",
        "schedule": crontab(hour=5, minute=0),  # 5 AM IST daily
    },
}
```

Beat runs as a **single replica**. Two beat instances would double-fire tasks. In Phase 2 ECS, beat is its own service with `desired_count: 1` and no autoscaling. If beat is unhealthy, an alarm pages the on-call.

### Tasks and DB sessions

The bridge from sync Celery to async SQLAlchemy:

```python
# tasks/_helpers.py
import asyncio
from app.db.session import AsyncSessionLocal

def run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.run(coro)

# tasks/ocr_tasks.py
@celery_app.task(name="kyros.clinical.parse_lab_report", bind=True, ...)
def parse_lab_report(self, lab_report_id: str) -> dict:
    return run_async(_parse_lab_report_async(lab_report_id))

async def _parse_lab_report_async(lab_report_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        try:
            report = await lab_reports_repo.get_by_id_with_lock(db, UUID(lab_report_id))
            if report is None or report.parsed_json is not None:
                return {"skipped": True, "reason": "already_parsed_or_missing"}
            file_bytes = await s3_client.download(report.file_url)
            parsed = await document_ai_client.parse_healthcare(file_bytes)
            report.parsed_json = parsed["json"]
            report.ocr_confidence_avg = parsed["confidence"]
            await db.commit()
            await notification_service.notify_lab_parsed(db, report.patient_id)
            return {"ok": True, "report_id": lab_report_id}
        except Exception:
            await db.rollback()
            raise
```

Each task invocation gets its own event loop (`asyncio.run`), its own DB session, and its own commit/rollback. No event loop is shared across tasks.

### Task logging

Tasks use the same `structlog` configuration as the app. Every task log line includes:

- `task_id` (Celery's own UUID)
- `task_name`
- `resource_id` (the entity the task operates on)
- `attempt` (retry count)

Example:

```python
import structlog
logger = structlog.get_logger()

@celery_app.task(name="kyros.clinical.parse_lab_report", bind=True, ...)
def parse_lab_report(self, lab_report_id: str):
    log = logger.bind(
        task_name="parse_lab_report",
        task_id=self.request.id,
        attempt=self.request.retries + 1,
        lab_report_id=lab_report_id,
    )
    log.info("task.started")
    try:
        result = run_async(_parse_lab_report_async(lab_report_id))
        log.info("task.completed", **result)
        return result
    except Exception as e:
        log.exception("task.failed", error=str(e))
        raise
```

No PHI in task logs. The `lab_report_id` is fine; the parsed values are not.

### Task observability

Three layers:

1. **Sentry** captures unhandled task exceptions automatically via `sentry-sdk[celery]`.
2. **CloudWatch logs** capture structlog output (in Phase 1 via the awslogs Docker driver; in Phase 2 via the awslogs ECS log driver).
3. **Queue depth metrics** via a Celery beat task that publishes `redis.LLEN celery_queue_X` to CloudWatch every minute.

Flower is omitted (see §4) but the redis-based queue depth metric replaces its most useful information.

### Avoiding duplicate work

For "trigger a task once per resource transition" semantics (e.g., "OCR this lab report exactly once when it's uploaded"), the pattern:

1. The HTTP handler that creates the resource dispatches the task.
2. The task itself checks current resource state at the start.
3. If state is "already processed" or "in progress by another worker," exit early.

For "trigger a task at most once per N minutes" semantics (e.g., "send a digest email no more than once an hour"), the pattern: Redis `SETNX` with TTL guards the dispatch.

### Critical reliability tasks

The OCR pipeline and notification dispatch are flagged "must-not-lose" workloads. Reliability tactics:

- **Task `acks_late=True`**: task ack happens after success, so a worker crash mid-task requeues.
- **Retry on transient errors with exponential backoff up to 5 attempts.**
- **Database-anchored state**: a task whose work is "set field X on row Y" leaves the row in a state that lets us detect "needs work" by scanning. A reconciliation beat task (`reconcile_pending_lab_ocr` every 30 min) finds rows in `kc_lab_reports` where `parsed_json IS NULL AND created_at < NOW() - INTERVAL '15 minutes'` and re-dispatches.
- **Dead-letter philosophy:** we do not maintain a separate dead-letter queue. After max retries, the task logs an error to Sentry, writes a row to a `failed_tasks` table (or sets a `processing_failed` flag on the source row), and an admin UI surface lets operators retry manually. This is simpler than DLQ infrastructure and gives operations explicit control.

### Phase-A task list (the launch set)

| Task name | Trigger | Queue | Notes |
|---|---|---|---|
| `kyros.clinical.parse_lab_report` | On lab report upload | `ocr` | Idempotent via parsed_json check |
| `kyros.clinical.reconcile_pending_lab_ocr` | Beat every 30 min | `ocr` | Retries failed OCR jobs |
| `kyros.clinical.generate_pre_consult_report` | On demand by doctor + T-24h cron | `reports` | WeasyPrint PDF |
| `kyros.clinical.generate_pre_consult_reports_for_tomorrow` | Beat daily 04:00 | `reports` | Bulk job |
| `kyros.video.provision_upcoming_rooms` | Beat every minute | `default` | T-15min before scheduled_start |
| `kyros.video.provision_video_room` | Direct call | `default` | Single room creation |
| `kyros.notification.send_push` | On event | `notifications` | Expo Push |
| `kyros.notification.send_whatsapp_utility` | On event | `notifications` | AiSensy |
| `kyros.notification.send_email` | On event | `notifications` | SendGrid/SMTP |
| `kyros.payment.reconcile` | On webhook | `payments` | Razorpay verify |
| `kyros.payment.reconcile_pending` | Beat every 2h | `payments` | Catch missed webhooks |
| `kyros.payment.generate_gst_invoice` | On payment success | `payments` | PDF + S3 |
| `kyros.reminder.dispatch_due` | Beat every 5 min | `notifications` | Scans wn_reminders |
| `kyros.dpdp.generate_data_export` | On user request | `maintenance` | Chunked, can take minutes |
| `kyros.dpdp.process_data_erasure` | After 30-day grace expiry | `maintenance` | Idempotent |
| `kyros.dpdp.process_pending_erasures` | Beat daily | `maintenance` | Scans expired grace period |
| `kyros.maintenance.ensure_partitions_ahead` | Beat monthly | `maintenance` | Create next 3 months' partitions |
| `kyros.maintenance.cleanup_orphaned_uploads` | Beat daily | `maintenance` | S3 housekeeping |
| `kyros.maintenance.verify_audit_integrity` | Beat daily | `maintenance` | Hash-chain audit log check |
| `kyros.analytics.rollup_daily` | Beat daily 02:30 | `maintenance` | Patient/consult/revenue rollups |

---

## 8. Configuration and environment management

### Pydantic Settings v2 strategy

Configuration is a Pydantic Settings class. Single source of truth. Validation at startup.

```python
# app/core/config.py
from functools import lru_cache
from typing import Literal
from pydantic import Field, PostgresDsn, RedisDsn, AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="KYROS_",
        case_sensitive=False,
        extra="forbid",
    )

    # ----- App identity -----
    env: Literal["local", "test", "staging", "production"] = "local"
    app_version: str = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    openapi_url: str | None = "/openapi.json"
    docs_url: str | None = "/docs"

    # ----- Database -----
    database_url: PostgresDsn
    database_pool_size: int = 10
    database_max_overflow: int = 10
    database_echo: bool = False

    # ----- Redis / Celery -----
    redis_url: RedisDsn
    celery_broker_url: RedisDsn
    celery_result_backend: RedisDsn

    # ----- Auth -----
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "RS256"] = "HS256"
    jwt_access_token_ttl_seconds: int = 3600
    jwt_refresh_token_ttl_seconds: int = 2592000  # 30 days
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4

    # ----- OTP -----
    otp_secret: str = Field(min_length=32)
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60

    # ----- CORS -----
    cors_allowed_origins: list[AnyHttpUrl] = []

    # ----- AWS -----
    aws_region: str = "ap-south-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    s3_bucket_phi: str
    s3_kms_key_id: str | None = None

    # ----- Razorpay -----
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # ----- 100ms -----
    hms_access_key: str = ""
    hms_secret: str = ""
    hms_template_id: str = ""

    # ----- Google Document AI -----
    gcp_project_id: str = ""
    document_ai_processor_id: str = ""
    document_ai_location: str = "asia-south1"
    gcp_service_account_json: str = ""  # JSON string or @file:/path

    # ----- MSG91 -----
    msg91_auth_key: str = ""
    msg91_template_id: str = ""

    # ----- WhatsApp (AiSensy) -----
    aisensy_api_key: str = ""
    aisensy_project_id: str = ""

    # ----- Email -----
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@kyros.clinic"

    # ----- Sentry -----
    sentry_dsn: str | None = None
    sentry_environment: str = "local"
    sentry_traces_sample_rate: float = 0.1

    # ----- Derived properties -----
    @property
    def alembic_database_url(self) -> str:
        # Convert async URL to sync for Alembic
        return str(self.database_url).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    # ----- Validators -----
    @field_validator("openapi_url", "docs_url")
    @classmethod
    def disable_docs_in_production(cls, v, info):
        # In production, both should be None (set explicitly via env)
        return v

    @field_validator("jwt_secret", "otp_secret")
    @classmethod
    def secret_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("secret must be at least 32 characters")
        if v.startswith("change-me") and __import__("os").environ.get("KYROS_ENV") == "production":
            raise ValueError("default secret value not allowed in production")
        return v

@lru_cache
def get_settings() -> Settings:
    return Settings()  # raises ValidationError if env is broken

settings = get_settings()
```

### Fail-fast at startup

The `lifespan` startup runs `get_settings()` first. If env is broken, the app refuses to start with a clear error. This is the only acceptable failure mode for config issues — never silently fall back to defaults for security-relevant values.

A second startup check verifies that production-required values are actually populated:

```python
# in lifespan startup
if settings.is_production:
    required = ["jwt_secret", "otp_secret", "razorpay_webhook_secret",
                "hms_access_key", "hms_secret", "s3_bucket_phi", "sentry_dsn"]
    missing = [k for k in required if not getattr(settings, k)]
    if missing:
        raise RuntimeError(f"Production env missing: {missing}")
```

### Local .env

Lives at `backend/.env` (gitignored). Contains real values for local dev: a known-good JWT secret, mailhog SMTP host, etc. The `.env.example` is the canonical documented version.

### Staging .env

Similar shape to local, with real staging secrets injected from Secrets Manager. Staging is in `ap-south-1`, isolated VPC, separate RDS instance.

### Production secrets via AWS Secrets Manager

Production never reads `.env` from disk in the application. Instead:

- A boot script (run before the Python process starts) reads from Secrets Manager and either:
  - **Phase 1 (EC2 + Docker Compose):** writes `/etc/kyros/backend.env` and references it via `env_file` in compose, OR
  - **Phase 2 (ECS Fargate):** ECS task definition references Secrets Manager ARNs in the `secrets` block; ECS injects them as env vars at container start.

Either way, the application reads its config via `Settings()` from env vars, the same code path as local dev. The difference is purely how those env vars arrive in the process environment.

Secrets are organized in Secrets Manager:

- `kyros/prod/database` → `{ "url": "..." }` (Postgres URL)
- `kyros/prod/redis` → `{ "url": "..." }`
- `kyros/prod/jwt` → `{ "secret": "..." }`
- `kyros/prod/razorpay` → `{ "key_id": "...", "key_secret": "...", "webhook_secret": "..." }`
- `kyros/prod/hms` → `{ "access_key": "...", "secret": "...", "template_id": "..." }`
- ... and so on per integration.

This grouping lets us rotate per-integration secrets independently and lets IAM policies grant access per-secret.

Rotation:
- JWT secret rotation is hard (invalidates all tokens). Plan: dual-secret support (accept tokens signed with old or new for a transition window) or document a quarterly enforced re-login.
- OTP secret rotation invalidates in-flight OTPs only (acceptable, 5-minute TTL).
- Razorpay / 100ms / Document AI keys rotate per provider's schedule, manual deploy.

### Public vs secret config

| Type | Examples | Storage |
|---|---|---|
| Public config | `aws_region`, `cors_allowed_origins`, `jwt_algorithm`, `otp_ttl_seconds` | env vars / `.env` |
| Secret config | `jwt_secret`, `razorpay_key_secret`, `hms_secret`, `gcp_service_account_json` | Secrets Manager (prod); `.env` (dev) |

The Pydantic Settings class doesn't distinguish; the distinction is operational. Public config can appear in CI logs, status pages, and infrastructure-as-code without redaction. Secret config never appears in logs, CI output, or error messages.

### Per-service config in Docker Compose

The backend-api, celery-worker, and celery-beat services all use the same `env_file: ./backend/.env`. They run the same code with the same configuration. Operational difference is only in command (uvicorn vs celery worker vs celery beat).

Compose-time overrides (in the `environment:` block of the service) handle compose-network-specific values: `KYROS_DATABASE_URL` points to `postgres:5432` (compose service name), `KYROS_REDIS_URL` points to `redis:6379`, `KYROS_SMTP_HOST=mailhog`.

### How Celery and FastAPI share config

They share the same Pydantic `Settings` class via `from app.core.config import settings`. There is no separate "celery config." Beat schedule, queue routing, retry policies — all derive from the same source.

This avoids configuration drift: a developer who changes `KYROS_OTP_TTL_SECONDS` updates both the API's OTP issuance and the maintenance task that purges old OTPs (if any) without coordinating two configuration files.

### Avoiding configuration drift

Three disciplines:

1. **`.env.example` is the documented source of truth.** Every variable used in code must appear in `.env.example` with a sensible default or empty placeholder. CI runs a check that compares `Settings` fields to `.env.example` keys.

2. **`extra="forbid"` in Pydantic Settings** rejects unknown env vars. A typo like `KYROS_JTW_SECRET` raises an error instead of silently being ignored.

3. **No conditional config based on env name in code.** If something needs to behave differently in production, it should be a config value (`enable_feature_x: bool`), not `if settings.is_production: ...`. Two exceptions: docs/openapi URL disabling (security), and Sentry transport disabling for tests.

---

## 9. Bootstrap and local development flow

### First-clone experience

The goal: a new engineer clones the repo, runs three commands, and has a fully working local backend with seed data in under five minutes.

```bash
git clone git@github.com:kyros-clinic/kyros-platform.git
cd kyros-platform
make bootstrap
```

`make bootstrap` is the orchestrator. It runs:

```makefile
# Makefile (excerpt)
.PHONY: bootstrap dev migrate seed test down clean reset

bootstrap:
	@test -f backend/.env || cp backend/.env.example backend/.env
	@echo "→ Building backend image (dev target)..."
	docker compose build backend-api
	@echo "→ Starting infrastructure (postgres, redis)..."
	docker compose up -d postgres redis
	@echo "→ Waiting for postgres health..."
	@until docker compose ps postgres | grep -q "healthy"; do sleep 1; done
	@echo "→ Running migrations..."
	docker compose run --rm backend-api alembic upgrade head
	@echo "→ Seeding development data..."
	docker compose run --rm backend-api python scripts/seed_dev.py
	@echo "→ Starting all services..."
	docker compose up -d
	@echo
	@echo "✓ Kyros backend ready."
	@echo "  API:        http://localhost:8000"
	@echo "  Docs:       http://localhost:8000/docs"
	@echo "  Mailhog UI: http://localhost:8025"
	@echo "  Logs:       make logs"

dev:
	docker compose up

migrate:
	docker compose run --rm backend-api alembic upgrade head

seed:
	docker compose run --rm backend-api python scripts/seed_dev.py

test:
	docker compose -f docker-compose.test.yml up -d
	cd backend && uv run pytest
	docker compose -f docker-compose.test.yml down

down:
	docker compose down

reset:
	docker compose down -v
	$(MAKE) bootstrap

logs:
	docker compose logs -f --tail=100 backend-api celery-worker
```

After `make bootstrap`, the engineer also runs the frontend they're working on (e.g., `cd doctor-portal && npm install && npm run dev`).

### Recommended startup order

Inside compose, the dependency graph is:

```
postgres (healthy)  ─┐
                     ├──► backend-api (healthy)  ─┐
redis (healthy)     ─┤                             ├──► celery-worker
                     └─────────────────────────────┘
                                                    │
                                                    └──► celery-beat
mailhog             ────► (independent)
```

The `depends_on: condition: service_healthy` declarations enforce this. A naive `docker compose up` from scratch produces:

1. Postgres image pull, container start, init.sql runs.
2. Redis image pull, container start.
3. Both hit healthy state within ~5 seconds.
4. Backend-api builds (first time only), then starts, runs schema sanity check against Postgres (refuses if migration not applied — see below for migration-first flow).
5. Celery-worker and celery-beat start once backend-api is up (so they can import the same code with confidence the codebase is loadable).

The schema sanity check in backend-api's lifespan is the key correctness lever: if a developer pulls new code that introduces a migration and forgets to run it, the backend refuses to come up with a clear "schema version mismatch — run `make migrate`" error.

### Avoiding race conditions

Two race conditions worth calling out:

1. **Backend-api connecting to Postgres before init.sql finishes.** Solved by `condition: service_healthy` on the postgres dependency, plus `pg_isready` as the healthcheck. `pg_isready` only returns 0 after Postgres is fully accepting connections.

2. **Celery-worker starting before backend-api applies migrations.** Solved by ordering migration runs as a separate `docker compose run --rm` step (not part of `docker compose up`). The `make bootstrap` target runs migrations after postgres is healthy and before starting backend-api / celery-worker.

### What's automated vs manual

**Automated in `make bootstrap`:**
- `.env` file creation from `.env.example` (only if missing — won't overwrite real secrets).
- Image build (first time only; subsequent runs use cached layers).
- Postgres + Redis startup.
- Migration application.
- Dev seed.
- All services up.

**Manual (not in bootstrap):**
- Filling `.env` with real third-party keys (Razorpay test keys, 100ms test app credentials, etc.). The seed script and most of the API works without these for the first session.
- Creating an interactive super admin: `make create-super-admin` runs `scripts/create_super_admin.py` which prompts for email and password.
- Database resets: `make reset` (destructive — requires confirmation).
- Generating an OpenAPI spec for client codegen: `make openapi`.

### Daily development loop

```bash
# Morning: pull and start
git pull
docker compose up -d
make migrate     # if there are new migrations
# code, code, code — uvicorn --reload picks up file changes automatically

# Run tests
make test

# End of day
docker compose down  # or leave running; the volumes survive
```

### Seed script

`scripts/seed_dev.py` is idempotent. It creates a known, reproducible state:

- 1 super admin user (`admin@kyros.local` / `admin_dev_password`)
- 2 coordinators (`coord1@kyros.local`, `coord2@kyros.local`)
- 3 doctors across verticals: endocrinologist, dermatologist, OB-GYN
- 8 patients across the seven condition categories
- 4 scheduled consultations (mix of statuses)
- 2 lab reports with parsed OCR
- 1 prescription (draft and signed)
- 5 audit log entries (to give the admin UI something to render)

The script uses `INSERT ... ON CONFLICT DO UPDATE` patterns so running it twice doesn't error and updates fields to the canonical state. It's safe to run after schema migrations to refresh the dev fixture.

### Frontend integration

The four frontend surfaces all consume the same backend at `http://localhost:8000`:

| Surface | Default dev port |
|---|---|
| Next.js website | `http://localhost:3000` |
| Doctor portal (Vite) | `http://localhost:5173` |
| Expo dev (web) | `http://localhost:19006` |
| Patient web portal (RN Web) | `http://localhost:19006` |

CORS in dev is configured to allow all four origins. In prod, only the real production origins.

For the admin UI (Jinja + HTMX), there is no separate frontend dev server — it's served by the same FastAPI process at `http://localhost:8000/admin`.

---

## 10. Schema implementation strategy

### Source of truth

The build spec's database schema (build-spec §2) is authoritative. This document does not redesign it; instead, it defines **how to implement it cleanly** in SQLAlchemy + Alembic.

### Model organization by domain

One file per domain in `app/models/`:

- `models/identity.py` — `User`, `RefreshToken`
- `models/consent.py` — `ConsentRecord`, `DataSubjectRequest`
- `models/audit.py` — `AuditLog` (partitioned, no soft delete)
- `models/wellness.py` — `Reminder`, `ReminderLog`, `HealthSyncSession`, `HealthDatapoint`
- `models/clinical.py` — `Patient`, `Consultation`, `Prescription`, `PrescriptionItem`, `LabOrder`, `LabReport`, `DoctorNote`, `PreConsultationReport`, `EducationAssignment`, `EducationContent`, `Payment`
- `models/doctor.py` — `Doctor`, `Availability`, `Credential`
- `models/admin.py` — `Coordinator`, `Configuration`

The `models/__init__.py` re-exports every model. This is necessary because Alembic's autogenerate inspects `Base.metadata`, and `Base.metadata` is only populated by importing each model module.

```python
# models/__init__.py
from app.models.identity import User, RefreshToken
from app.models.consent import ConsentRecord, DataSubjectRequest
from app.models.audit import AuditLog
from app.models.wellness import Reminder, ReminderLog, HealthSyncSession, HealthDatapoint
from app.models.clinical import (
    Patient, Consultation, Prescription, PrescriptionItem,
    LabOrder, LabReport, DoctorNote, PreConsultationReport,
    EducationAssignment, EducationContent, Payment,
)
from app.models.doctor import Doctor, Availability, Credential
from app.models.admin import Coordinator, Configuration

__all__ = [
    "User", "RefreshToken",
    "ConsentRecord", "DataSubjectRequest",
    "AuditLog",
    "Reminder", "ReminderLog", "HealthSyncSession", "HealthDatapoint",
    "Patient", "Consultation", "Prescription", "PrescriptionItem",
    "LabOrder", "LabReport", "DoctorNote", "PreConsultationReport",
    "EducationAssignment", "EducationContent", "Payment",
    "Doctor", "Availability", "Credential",
    "Coordinator", "Configuration",
]
```

### Migration ordering (Phase A)

A clean Phase-A migration sequence:

1. **`0001_init_extensions_and_enums.py`** — `CREATE EXTENSION IF NOT EXISTS pgcrypto; pg_trgm; btree_gin;` + all Postgres ENUM types. Enums first so subsequent tables can reference them.

2. **`0002_identity_and_consent.py`** — `users`, `refresh_tokens`, `ad_consent_records`, `ad_data_subject_requests`.

3. **`0003_audit_log.py`** — `ad_audit_log` partitioned by month, plus the first 6 months of partitions.

4. **`0004_doctor_domain.py`** — `dr_doctors`, `dr_availability` (with `EXCLUDE USING gist` for slot overlap), `dr_credentials`.

5. **`0005_admin_coordinator.py`** — `ad_coordinators`, `ad_configuration`.

6. **`0006_clinical_core.py`** — `kc_patients`, `kc_consultations`, `kc_doctor_notes`.

7. **`0007_clinical_prescriptions.py`** — `kc_prescriptions`, `kc_prescription_items`.

8. **`0008_clinical_labs.py`** — `kc_lab_orders`, `kc_lab_reports`.

9. **`0009_clinical_payments_education.py`** — `kc_payments`, `kc_education_content`, `kc_education_assignments`.

10. **`0010_clinical_pre_consult.py`** — `kc_pre_consultation_reports`.

11. **`0011_wellness_reminders.py`** — `wn_reminders`, `wn_reminder_logs`.

12. **`0012_wellness_health_data.py`** — `wn_health_sync_sessions`, `wn_health_datapoints` partitioned by month + first 6 months of partitions.

13. **`0013_indexes_phase_a.py`** — all indexes enumerated in §5, with `CREATE INDEX CONCURRENTLY` where the table is non-empty in production (not relevant at first deploy, but the pattern is in place).

Splitting migrations this way makes review tractable. Each migration is one logical concern.

### Append-only entity patterns

Three entities are append-only: prescriptions, doctor notes, audit log.

**Prescriptions and doctor notes:**

```python
class Prescription(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "kc_prescriptions"
    # ...
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kc_prescriptions.id", ondelete="RESTRICT"),
        nullable=True,
    )
```

The edit pattern: load current → mark `superseded_by_id` on the new row → insert new row with `version = old.version + 1`. Reads filter `superseded_by_id IS NULL` for "current" view; admin queries can show full history.

UI never offers a "delete prescription" affordance; it offers "supersede." A retracted prescription is a new version with `status='cancelled'`.

**Audit log:**

`ad_audit_log` has no `updated_at` column and no soft delete. Inserts only. Enforced by:

1. SQLAlchemy model defines `__mapper_args__ = {"eager_defaults": True}` and has no `updated_at` mixin.
2. Postgres-level: a `BEFORE UPDATE` trigger raises an exception:

```sql
CREATE OR REPLACE FUNCTION prevent_audit_log_modification() RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'ad_audit_log is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_audit_log_update
  BEFORE UPDATE OR DELETE ON ad_audit_log
  FOR EACH ROW
  EXECUTE FUNCTION prevent_audit_log_modification();
```

This is paranoid but cheap. A compromised application credential cannot tamper with the audit log without `pg_proc` access (which is restricted to superuser).

3. An additional `verify_audit_integrity` Celery beat task computes a daily hash chain and stores in a separate "audit integrity ledger." Tampering would break the chain visibly.

### Consent record versioning

`ad_consent_records` stores both the consent decision and a hash of the consent text shown at the time. Pattern:

- The consent text for each consent type is a versioned file in the repo (`docs/consent/telemedicine_v2.md`).
- On consent grant, the API records the version string (`"v2.0"`), the SHA-256 hash of the canonical text, the timestamp, and IP.
- Revoking a consent does not delete the row; it sets `revoked_at`. The audit trail of "user X granted v1.0 on date Y, revoked on date Z, granted v2.0 on date W" is queryable.
- A new consent version (text changes) requires re-consent. A scheduled task on app boot can flag users whose latest consent for type T is on an obsolete version, and the next API request from that user gets a "consent required" response that the client surfaces as a re-consent prompt.

### Soft delete helpers

Centralized in repositories. Pattern:

```python
# repositories/_helpers.py
def filter_active(stmt, model):
    """Apply soft-delete filter; chainable."""
    return stmt.where(model.deleted_at.is_(None))
```

Repositories use it consistently:

```python
async def list_consultations_for_patient(db, *, patient_user_id):
    stmt = (
        select(Consultation)
        .join(Patient, Consultation.patient_id == Patient.id)
        .where(Patient.user_id == patient_user_id)
    )
    stmt = filter_active(stmt, Consultation)
    stmt = filter_active(stmt, Patient)
    return (await db.scalars(stmt.order_by(Consultation.scheduled_start_at.desc()))).all()
```

### Indexes and partial indexes

Beyond the §5 enumeration, two specific partial index patterns recur:

**Active-only unique constraints:**

```python
Index(
    "uq_users_email_active",
    "email",
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
)
```

This lets a soft-deleted user be recreated with the same email (an edge case for GDPR/DPDP erasure-then-rejoin scenarios).

**Pending-task scans:**

```python
Index(
    "ix_kc_lab_reports_ocr_pending",
    "created_at",
    postgresql_where=text("parsed_json IS NULL AND deleted_at IS NULL"),
)
```

This makes the OCR reconciliation beat task efficient regardless of total table size.

### Patient-only access patterns

Every patient-scoped repository function takes `patient_user_id` (the `users.id`) as a required parameter, not `patient_id` (the `kc_patients.id`). Reasoning: the application's "current user" identity is `users.id`. Passing `patient_id` would require the router to first resolve the patient ID from the user, creating a step where a bug could swap IDs. Repositories do the join.

```python
async def get_lab_report_for_patient(
    db: AsyncSession, *, lab_report_id: UUID, patient_user_id: UUID,
) -> LabReport | None:
    stmt = (
        select(LabReport)
        .join(Patient, LabReport.patient_id == Patient.id)
        .where(
            LabReport.id == lab_report_id,
            Patient.user_id == patient_user_id,
            LabReport.deleted_at.is_(None),
            Patient.deleted_at.is_(None),
        )
    )
    return await db.scalar(stmt)
```

A function name with `_for_patient` suffix has a `patient_user_id` parameter and applies patient scoping. A function without the suffix is admin-context only.

### Doctor-panel scoping

The "doctor's panel" = patients with consultations involving this doctor (current or past). Pattern:

```python
async def list_patients_for_doctor_panel(
    db: AsyncSession, *, doctor_id: UUID, condition: ConditionCategory | None = None,
) -> Sequence[Patient]:
    """Patients who have had at least one consultation with this doctor."""
    stmt = (
        select(Patient)
        .distinct()
        .join(Consultation, Consultation.patient_id == Patient.id)
        .where(
            Consultation.doctor_id == doctor_id,
            Consultation.deleted_at.is_(None),
            Patient.deleted_at.is_(None),
        )
    )
    if condition:
        stmt = stmt.where(Consultation.condition_category == condition)
    return (await db.scalars(stmt.order_by(Patient.created_at.desc()))).all()
```

The doctor cannot see a patient who has never consulted with them. If two doctors share a patient (rare but possible — e.g., thyroid + dermatology), both see the patient *only with respect to their own consultations*. Cross-doctor consultations are not visible.

### Coordinator restricted access

Coordinators have a JSONB array of assigned patient IDs on `ad_coordinators.assigned_patient_ids`. Scoping:

```python
async def list_patients_for_coordinator(
    db: AsyncSession, *, coordinator_id: UUID,
) -> Sequence[Patient]:
    coord = await db.scalar(
        select(Coordinator).where(Coordinator.id == coordinator_id, Coordinator.deleted_at.is_(None))
    )
    if coord is None or not coord.assigned_patient_ids:
        return []
    stmt = (
        select(Patient)
        .where(Patient.id.in_(coord.assigned_patient_ids))
        .where(Patient.deleted_at.is_(None))
        .order_by(Patient.created_at.desc())
    )
    return (await db.scalars(stmt)).all()
```

Coordinator-facing repository functions return Pydantic schemas (`CoordinatorPatientView`, `CoordinatorConsultationView`) that omit clinical fields:

- `CoordinatorPatientView` includes: name, phone, city, primary_conditions, assigned_coordinator_id, last_consult_at, next_consult_at, intake_complete.
- `CoordinatorPatientView` excludes: lab values, prescription items, doctor notes, intake form free-text responses.

This is enforced in the schema layer, not just the repository. Even if a coordinator-route handler accidentally received a full Patient ORM model, serializing through `CoordinatorPatientView` would drop the forbidden fields.

### Trend-query friendly biomarker and health data

For `wn_health_datapoints`:

- Partitioned monthly by `recorded_at`.
- Per-partition index on `(user_id, data_type, recorded_at DESC)`.
- A query like "last 30 days of steps for user X" hits at most 2 partitions and uses the index.

For `kc_lab_reports.parsed_json`:

- JSONB index is not added by default. Biomarker trend queries iterate report rows (typically 5–20 per patient), extracting from parsed_json in app code.
- If we later need "all TSH values across all patients" admin queries, we add a materialized derived table (`kc_biomarker_observations`) with first-class columns, populated by a trigger or a Celery task on report parse.

Why we don't extract biomarkers into a normalized table from day one: lab providers' result formats vary; the parsed_json shape evolves; and Phase-A queries are all "this patient's biomarkers over time," which is bounded by patient and report-row count. We optimize later.

### What to introduce first in Phase A

Based on the P1–P30 prompt queue in the build spec, the Phase-A model introduction order is:

1. `users` (P2-P3)
2. `dr_doctors`, `dr_availability`, `dr_credentials` (P4)
3. `kc_patients` (P7)
4. `kc_consultations` (P8)
5. `ad_audit_log`, `ad_consent_records` (P5-P6)
6. `kc_lab_reports`, `kc_lab_orders` (P13-P14)
7. `kc_prescriptions`, `kc_prescription_items` (P16-P17)
8. `kc_pre_consultation_reports` (P19)
9. `wn_reminders`, `wn_reminder_logs` (P11)
10. `wn_health_sync_sessions`, `wn_health_datapoints` (P12)
11. `kc_payments`, `kc_education_*` (P15, P25)
12. `ad_coordinators` (P26)

Each prompt in the queue gets one or two migrations; total Phase-A migrations: ~13–15.

---

## 11. Auth and RBAC backend strategy

### JWT auth: design choices

**Algorithm:** HS256 in Phase 1, with a path to RS256 in Phase 2.

Reasoning: HS256 is simpler (single shared secret), faster, and sufficient for a single backend trusted boundary. RS256 becomes valuable when we have multiple services that need to verify tokens without sharing the signing secret — not Phase A.

**Access token TTL:** 60 minutes.
**Refresh token TTL:** 30 days, rotating on use.

**Claims:**

```python
{
  "sub": "<user_uuid>",
  "role": "patient" | "doctor" | "coordinator" | "super_admin",
  "iat": 1700000000,
  "exp": 1700003600,
  "jti": "<random_uuid>",         # for revocation
  "session_id": "<session_uuid>", # ties to refresh token family
  "v": 1                          # claim schema version
}
```

`sub` is the user UUID; `role` is included so role checks don't require a DB hit on every request. The role is verified against DB on sensitive operations (e.g., admin actions, money flows) where stale role claims could be exploited; for routine reads, the JWT-claimed role is trusted.

`jti` (JWT ID) lets us blacklist a specific token. We do not maintain a "blocked JTI" list of every token (Redis bloat); we use `session_id` for coarser revocation.

### Refresh token rotation

Refresh tokens are **opaque random strings**, not JWTs. They're stored hashed (SHA-256) in `refresh_tokens` table:

```python
class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id"), nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

Rotation flow on `POST /v1/auth/refresh`:

1. Validate refresh token (hash, lookup, check not revoked, check not expired).
2. **Detect reuse:** if the presented refresh token was already used (its `revoked_at` is set and a child token exists), this is a token theft signal. Revoke the entire `session_id` family. Force re-login.
3. Issue new access token + new refresh token.
4. Mark old refresh token `revoked_at = NOW()`, point new token's `parent_id` to old.

This is "refresh token rotation with reuse detection," the OAuth 2.0 BCP pattern. It bounds the blast radius of a stolen refresh token.

### Password hashing

Argon2id with parameters tuned for ~100ms hash time on production hardware:

- `time_cost=3`
- `memory_cost=65536` (64 MiB)
- `parallelism=4`

We use the `argon2-cffi` library. Verification uses constant-time comparison.

Passwords are never logged, never returned in responses, never stored in plaintext.

### OTP handling

Flow described in §6 (Redis-stored, hashed, attempt-counted, TTL-bound). Two-channel OTP for high-risk actions (login from new device, payment confirmation) sends both SMS and WhatsApp; the user enters one and we cancel the other.

OTP issuance rate-limited per phone (3/15min), per IP (30/15min), and globally per-phone-and-IP combo. Anti-fraud rules emerge in production as we see patterns.

### Session invalidation

Three layers of revocation, by granularity:

1. **Single device logout** — revoke that device's `session_id` family. All refresh tokens with that session_id get `revoked_at` set. Access token continues to work until its 60-minute TTL expires (we accept this limitation; the alternative is a Redis blacklist per JTI which has cost).

2. **All sessions for user** — revoke all `session_id`s for the user. Used on password change, suspected account compromise, DPDP erasure.

3. **Global token invalidation** — bump the `v` (version) field in JWT claims and increment a global "minimum acceptable version" config. Used in emergencies (JWT secret rotation, security incident). Forces all users to re-login.

### Role enforcement

The dependency pattern (§3):

```python
def enforce_role(*allowed: Role):
    async def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(403, detail="forbidden")
        return user
    return dep

get_patient_user = enforce_role(Role.PATIENT)
get_doctor_user = enforce_role(Role.DOCTOR)
get_coordinator_user = enforce_role(Role.COORDINATOR)
get_admin_user = enforce_role(Role.SUPER_ADMIN)
get_staff_user = enforce_role(Role.DOCTOR, Role.COORDINATOR, Role.SUPER_ADMIN)
```

Role is taken from the JWT claim. For sensitive operations (admin-only writes, money flows), the handler additionally re-fetches the user from DB and checks `db_user.role == jwt_user.role`. This catches the stale-claim attack where a former admin's still-valid token is used after demotion.

### Cross-user 404 pattern (the discipline)

Every resource-scoped endpoint returns 404 on "resource doesn't exist OR isn't yours." The router code looks like:

```python
@router.get("/{prescription_id}")
async def get_prescription(
    prescription_id: UUID,
    user: User = Depends(get_patient_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    prescription = await prescriptions_repo.get_for_patient(
        db, prescription_id=prescription_id, patient_user_id=user.id,
    )
    if prescription is None:
        await audit_repo.write(
            db, audit_ctx, action="view_prescription",
            resource_type="prescription", resource_id=prescription_id,
            allowed=False, reason="not_own_or_not_found",
        )
        raise HTTPException(404, detail="not found")
    if prescription.status == PrescriptionStatus.DRAFT:
        # Draft prescriptions are never patient-visible
        await audit_repo.write(
            db, audit_ctx, action="view_prescription",
            resource_type="prescription", resource_id=prescription_id,
            allowed=False, reason="draft_not_visible",
        )
        raise HTTPException(404, detail="not found")
    await audit_repo.write(
        db, audit_ctx, action="view_prescription",
        resource_type="prescription", resource_id=prescription_id,
        allowed=True,
    )
    return PatientPrescriptionRead.model_validate(prescription)
```

Note: the draft prescription state is **also** translated to 404, not 403. Patients should be unable to distinguish "doesn't exist" from "exists but you can't see it yet." Otherwise, the response timing or status code becomes an information channel.

### Coordinator patient-scope restriction

```python
async def list_patients_for_coordinator(...) -> Sequence[Patient]:
    """See §10 — only patients whose IDs are in coordinator.assigned_patient_ids."""
```

Coordinator handlers always start with:

```python
@router.get("/patients/{patient_id}")
async def get_patient_for_coordinator(
    patient_id: UUID,
    user: User = Depends(get_coordinator_user),
    db: AsyncSession = Depends(get_db),
):
    coord = await coordinators_repo.get_by_user_id(db, user.id)
    if coord is None:
        raise HTTPException(403, detail="coordinator profile not configured")
    if patient_id not in coord.assigned_patient_ids:
        raise HTTPException(404, detail="not found")
    patient = await patients_repo.get_by_id_for_staff(db, patient_id)
    return CoordinatorPatientView.model_validate(patient)
```

The schema (`CoordinatorPatientView`) strips clinical fields, as in §10.

### Doctor own-panel restriction

A doctor sees only patients with whom they have at least one consultation:

```python
async def get_patient_for_doctor(
    db: AsyncSession, *, patient_id: UUID, doctor_id: UUID,
) -> Patient | None:
    stmt = (
        select(Patient)
        .where(Patient.id == patient_id, Patient.deleted_at.is_(None))
        .where(
            exists().where(
                Consultation.patient_id == Patient.id,
                Consultation.doctor_id == doctor_id,
                Consultation.deleted_at.is_(None),
            )
        )
    )
    return await db.scalar(stmt)
```

### Admin global access

Super admins access everything. The `enforce_role(Role.SUPER_ADMIN)` dependency is sufficient. No scoping. But every admin access is audit-logged.

Two extra controls on admin actions:

1. **Read-mostly default.** Admin UI is read-mostly. Destructive operations (deactivate doctor, refund payment) require a confirmation step with reason text, captured in audit log.

2. **Money-mover actions require fresh authentication.** Razorpay refund, doctor payout adjustments, and similar actions check that the admin's session is recent (re-authenticated within the last 10 minutes). Otherwise force re-authentication.

### Audit log hooks

Every authorization decision writes to `ad_audit_log`. Centralized via:

```python
# repositories/audit_repo.py
async def write(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    allowed: bool,
    reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    entry = AuditLog(
        actor_user_id=ctx.actor_user_id,
        actor_role=ctx.actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        allowed=allowed,
        reason=reason,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
        timestamp=datetime.now(timezone.utc),
        metadata=metadata or {},
    )
    db.add(entry)
    # No flush — let the request transaction commit it atomically with the main work.
```

Critical: audit writes are part of the same transaction as the action they describe. If the action is rolled back, the audit row is rolled back too (this matches what we want — we don't log actions that didn't happen).

The one exception: **denial audit logs are also written in the same transaction, then the transaction commits before the 403/404 is raised.** A denied access is a real event we want recorded. Implementation: write audit entry, commit, then raise.

```python
async def deny_and_audit(db, ctx, *, action, resource_type, resource_id, reason):
    await audit_repo.write(db, ctx, action=action, resource_type=resource_type,
                            resource_id=resource_id, allowed=False, reason=reason)
    await db.commit()
    raise HTTPException(404, detail="not found")
```

### Middleware vs dependency tradeoffs

We chose dependencies, not middleware, for auth. Why:

- **Per-route configurability.** Public routes, webhook routes, and health endpoints skip auth. With middleware, this requires allowlists that drift. With dependencies, each route declares its needs.
- **Role differentiation per route.** Patient and doctor have different dependencies. Middleware would need to inspect the URL.
- **Testability.** Dependencies are mockable per-test trivially via `app.dependency_overrides`.

The middleware-friendly parts of auth (extracting the request ID, structlog binding) are in middleware. The middleware never decides "is this user authorized for this action" — only "what context does this request have."

### Where auth ends and authorization begins

- **Authentication** = "who is this user?" — answered by JWT decode + DB lookup. Output: a `User` ORM instance.
- **Authorization** = "is this user allowed to do X with resource Y?" — split into:
  - *Role authorization*: "is this user the right role?" — enforced by `enforce_role` dependency.
  - *Resource authorization*: "does this user own/have access to this resource?" — enforced by repository function parameters (cross-user 404).
  - *Business-rule authorization*: "is this action valid given resource state?" (e.g., "can't refund an already-refunded payment") — enforced by service layer.

This three-way split is reflected in the audit log's `reason` field for denials, which helps forensics distinguish "wrong role" from "not your resource" from "invalid state transition."

### Testability

Security must be testable. We maintain `tests/integration/api/test_rbac_matrix.py` which is a parameterized test cross-multiplying:

- Every authenticated endpoint
- Every role (patient, doctor, coordinator, super_admin, unauthenticated)
- For resource-scoped endpoints: own vs other's resource

Expected status codes are tabulated and asserted. Adding a new endpoint requires adding it to the matrix; CI fails if a route lacks a matrix entry. This catches the "I added an endpoint and forgot to think about RBAC" case.

---

## 12. API organization strategy

### Route groups

The build spec defines the route map; this document defines the implementation conventions.

| URL prefix | File | Auth | Role | Scoping |
|---|---|---|---|---|
| `/v1/auth/*` | `api/v1/auth.py` | varies | varies | n/a |
| `/v1/public/*` | `api/v1/public/*` | none | n/a | n/a |
| `/v1/clinic/patient/*` | `api/v1/clinic/*` | JWT | patient | self only |
| `/v1/wellness/*` | `api/v1/wellness/*` | JWT | patient | self only |
| `/v1/doctor/*` | `api/v1/doctor/*` | JWT | doctor | own panel |
| `/v1/admin/*` | `api/v1/admin/*` | JWT | super_admin | global |
| `/v1/admin/coordinator/*` | `api/v1/admin_coordinator/*` | JWT | coordinator | assigned patients |
| `/v1/users/me/*` | `api/v1/users.py` | JWT | any | self only |
| `/v1/webhooks/*` | `api/v1/webhooks/*` | HMAC | n/a | n/a |

### Response schemas: organized by audience

For the same underlying entity, we maintain per-audience Pydantic schemas. Example for `Consultation`:

- `PatientConsultationRead` — patient view: own consultation, doctor name + bio, scheduled time, video room join URL.
- `DoctorConsultationRead` — doctor view: patient info, intake responses, prior notes, lab summary.
- `CoordinatorConsultationView` — coordinator view: patient name, time, status, video room status — no clinical content.
- `AdminConsultationRead` — admin view: all fields, including audit trail summary.

The repository returns the ORM model; the router converts via `XxxRead.model_validate(orm_instance)`. Pydantic v2's `model_config = ConfigDict(from_attributes=True)` makes this clean.

This separation also lets us version response schemas independently per audience. If the doctor portal needs a new field, we add it to `DoctorConsultationRead` without affecting patient app.

### Preventing route sprawl

Conventions enforced in code review:

- **One file per resource per audience.** `api/v1/clinic/consultations.py` is the patient's view of consultations. `api/v1/doctor/consultations.py` is the doctor's. They share the same underlying repository functions and service-layer logic.
- **No mixed-audience handlers.** A handler is either patient-facing or doctor-facing, never both. The dependency declares the role.
- **Service methods are audience-agnostic.** `consultation_service.book(...)` works regardless of who called it. Booking-specific authorization is in the router. The service trusts the router.

### Consistent error shape

All error responses have the same shape:

```json
{
  "detail": "human-readable message or machine code",
  "request_id": "req_01HXXX...",
  "type": "validation_error" | "not_found" | "conflict" | "rate_limited" | "internal"
}
```

422 (validation) includes `errors`: an array of `{loc, msg, type}` from Pydantic.

Frontend clients can switch on `type` for branching logic; the `detail` is displayed to users (when appropriate).

The error shape is asserted in middleware: every 4xx/5xx response goes through a final `register_exception_handlers` that ensures conformity.

### Pagination, filtering, sorting

**Pagination**: cursor-based for time-ordered list endpoints (consultations, lab reports, audit logs); offset-based for catalog endpoints (doctor directory, education content).

Cursor format: opaque base64 of `{"last_id": "...", "last_timestamp": "..."}`. Frontend treats it as opaque.

Response envelope:

```json
{
  "items": [ ... ],
  "next_cursor": "eyJsYXN0X2lkIjogIi4uLiJ9",
  "has_more": true,
  "total": null
}
```

`total` is null for cursor pagination (counting all rows for every page request is wasteful). For offset pagination, `total` is populated.

**Filtering**: query parameters with validation via Pydantic models for clarity:

```python
class ConsultationListQuery(BaseModel):
    status: ConsultationStatus | None = None
    condition: ConditionCategory | None = None
    from_date: date | None = None
    to_date: date | None = None
    cursor: str | None = None
    limit: int = Field(20, ge=1, le=100)
```

The router declares `query: ConsultationListQuery = Depends()`.

**Sorting**: limited to documented, indexed columns. A `sort` query parameter accepts values like `scheduled_at:desc`. Default sort is documented per endpoint. Arbitrary sort is rejected.

### Idempotency on mutating endpoints

`POST /v1/clinic/patient/consultations` (booking) and `POST /v1/clinic/patient/lab-reports` (upload) accept an `Idempotency-Key` header. See §6 for the Redis-backed implementation. The pattern is: client generates a UUID, sends with the request; if the request times out, retrying with the same key returns the cached result (200 or 4xx) instead of double-booking.

Webhook endpoints have natural idempotency via source event IDs.

### Versioning strategy

Major version in URL: `/v1/`, `/v2/`. Breaking changes bump the major. We expect to be on `/v1/` for at least 2 years.

Within a major version:
- **Adding fields** to response schemas is non-breaking. Clients ignore unknown fields.
- **Adding endpoints** is non-breaking.
- **Adding optional query/body params with defaults** is non-breaking.
- **Renaming fields, removing fields, changing types, removing endpoints** is breaking. Requires `/v2/` (or a documented deprecation period with parallel support).

OpenAPI spec is exported via `make openapi` to `backend/openapi.json` and consumed by frontend codegen.

### Content negotiation

JSON only for API endpoints. No XML, no form-encoded responses. Request bodies: JSON for API, `multipart/form-data` for file uploads.

The admin UI uses `text/html` responses and `application/x-www-form-urlencoded` request bodies, but it's a separate concern (Jinja templates, HTMX).

### Standard headers

Every API response includes:

- `X-Request-ID`: the request ID (also in the response body's `request_id`).
- `X-RateLimit-Remaining` and `Retry-After`: on rate-limited responses.
- `X-Kyros-API-Version`: e.g., `v1`.

Every API request is expected to include:

- `Authorization: Bearer <jwt>` for authenticated routes.
- `Idempotency-Key: <uuid>` (optional, for mutating endpoints).
- `X-Request-ID: <uuid>` (optional, generated by server if absent).
- `Accept-Language: <bcp47>` (informational; we localize from user profile, not headers, but log this for analytics).

---

## 13. File storage and document strategy

### S3 bucket layout

**One bucket per environment** (`kyros-phi-dev`, `kyros-phi-staging`, `kyros-phi-prod`), all in `ap-south-1`, all KMS-encrypted with environment-specific KMS keys.

**Path conventions:**

```
patients/{patient_uuid}/lab-reports/{lab_report_uuid}/{filename}
patients/{patient_uuid}/lab-reports/{lab_report_uuid}/parsed.json    # archived OCR output
patients/{patient_uuid}/prescriptions/{prescription_uuid}/v{version}.pdf
patients/{patient_uuid}/pre-consult-reports/{consultation_uuid}.pdf
patients/{patient_uuid}/exports/{export_uuid}.zip                    # DPDP data exports
patients/{patient_uuid}/consultations/{consultation_uuid}/recording.mp4

doctors/{doctor_uuid}/credentials/{credential_uuid}/{filename}
doctors/{doctor_uuid}/photo/avatar.jpg

content/education/{content_uuid}/{filename}
content/static/...                                                    # logos, brand assets
```

The `patients/{patient_uuid}/...` prefix is the access control unit. IAM policies on production buckets restrict object-level access by key prefix, in addition to application-level RBAC.

### Encryption

**At rest:**
- S3 SSE-KMS with environment-specific CMK.
- A separate KMS key for "highly sensitive" objects (doctor bank details, NMC documents) — `kyros-phi-prod-sensitive`. Less-permissioned roles can decrypt the general PHI key but not the sensitive key.

**In transit:**
- TLS 1.3 only.
- S3 bucket policy requires `aws:SecureTransport == true`.

### Signed upload pattern

Patient uploads a lab report:

1. Patient app calls `POST /v1/clinic/patient/lab-reports/initiate-upload` with `{filename, content_type, size}`.
2. Backend validates: content_type in allowlist (`application/pdf`, `image/jpeg`, `image/png`), size ≤ 10 MB.
3. Backend creates a `kc_lab_reports` row in `status='upload_pending'`, generates an S3 pre-signed PUT URL (15-minute expiry, content-type pinned, content-length-range constrained).
4. Returns `{lab_report_id, upload_url, fields}` to client.
5. Client uploads directly to S3 (no proxy through backend — saves bandwidth and processing).
6. Client calls `POST /v1/clinic/patient/lab-reports/{id}/finalize` to signal completion.
7. Backend HEADs the S3 object to confirm it exists and matches expected size/content-type.
8. Backend updates row to `status='ocr_pending'` and dispatches the OCR Celery task.

This pattern matters because:

- **Lab report PDFs can be large** (scanned multi-page documents up to 10 MB). Proxying through backend doubles the network bandwidth requirement and risks API gateway timeouts.
- **The S3 pre-signed URL is short-lived** (15 min), tied to a specific key, content type, and size range. A leaked URL is barely useful.
- **The finalize step gives us audit-log control**: only after finalize does the row enter the OCR pipeline.

### Signed download pattern

Same idea inverted:

1. Patient app calls `GET /v1/clinic/patient/lab-reports/{id}/download`.
2. Backend resolves access (cross-user 404 if not theirs).
3. Backend generates pre-signed GET URL, 10-minute expiry.
4. Returns 302 redirect to S3 URL, OR returns `{url}` for clients that prefer to fetch on their own.

The 302-redirect approach is simpler for browsers; the JSON-URL approach is friendlier for SPAs that want progress bars or revoke-on-cancel control.

**For prescriptions**, the same pattern. A prescription PDF is only retrievable when `status='signed'`; drafts are not downloadable by patients (the 404 pattern).

### When to proxy through backend vs direct signed URL

Direct signed URL (default): lab report PDFs, prescription PDFs, pre-consult report PDFs, recordings, exports, doctor photos.

Proxy through backend (exception): nothing in Phase A. If we ever need to dynamically watermark a prescription PDF or render a per-request view, we'd add a proxy endpoint. Not now.

### Metadata storage

S3 object metadata is the source of truth for:

- `Content-Type`
- `Content-Disposition` (set on signed URL generation, controls download filename)
- `x-amz-meta-uploaded-by` (user UUID)
- `x-amz-meta-resource-id` (matching DB row UUID)

The S3 object content is canonical; the DB row tracks its existence and processing state. Cross-checks:

- A daily `cleanup_orphaned_uploads` task lists S3 objects matching `*/upload_pending*` and confirms a `status='upload_pending'` row exists. Orphans (uploaded but never finalized) older than 24h are deleted from S3 and the corresponding DB row marked.
- Conversely, DB rows with `file_url` set but missing in S3 trigger a Sentry alert.

### Retention

| Object | Retention |
|---|---|
| Lab report PDFs | Patient lifetime + 7 years post-erasure for medico-legal record. Erased on DPDP erasure request after grace period. |
| Prescription PDFs | Patient lifetime + 7 years (NMC Telemedicine Practice Guidelines retention requirement). |
| Pre-consult report PDFs | 1 year after consultation, then archived. |
| Consultation recordings | 90 days, then deleted unless explicitly retained for clinical record (rare). |
| Data exports | 7 days after generation, then deleted. |
| Doctor credentials | Permanent (verification artifact). |

S3 Lifecycle Policies enforce automated transitions: standard storage → Standard-IA at 30 days → Glacier Instant Retrieval at 180 days for objects whose retention extends beyond active use.

### Access logging

S3 bucket access logs go to a separate logging bucket (`kyros-s3-logs-prod`) with 90-day retention. CloudTrail data events on the PHI bucket are enabled for forensic completeness.

Application-level: every signed URL generation writes to `ad_audit_log` (`action='generate_download_url'`). The combination of S3 access logs and audit log lets forensics reconstruct: who asked, when, for what, and whether the download actually happened.

### Content-type validation

On upload:
- Allowlist content types per endpoint.
- The pre-signed URL pins the content type — uploads with a different content type are rejected by S3.
- On finalize, backend HEADs the object and verifies the content type matches.
- For PDFs, an async Celery task additionally validates magic bytes (the file starts with `%PDF-`).

### File size limits

- Lab report PDF: 10 MB.
- Lab report image (single scan): 5 MB.
- Doctor credential: 5 MB.
- Doctor photo: 2 MB.
- Education content (PDF or video): 100 MB.

Limits are enforced at three layers:
1. The pre-signed URL has a `content-length-range` constraint.
2. The Nginx/ALB upstream timeout and max body size are set above these limits for the proxy paths only.
3. The finalize endpoint re-checks size.

### Local development emulation

For local dev, we have two options:

**Option A (recommended for Phase A): use real S3 with a dev bucket.** Each developer gets credentials with access only to `kyros-phi-dev`. Pros: production parity, signed URL behavior identical, no extra container. Cons: requires AWS access for every developer.

**Option B (fallback): LocalStack.** Run `localstack/localstack:s3-latest` as a compose service, point `KYROS_AWS_ENDPOINT_URL` at it. The boto3 client respects the endpoint URL override. Pros: fully offline, free, fast. Cons: behavior drift from real S3 (signed URLs, KMS), occasional surprises.

For Phase A we use Option A as default; LocalStack stays in `docker-compose.yml` commented-out for engineers who want offline development.

### File handling in tasks

Celery tasks (OCR, PDF generation) download from S3 to a `/tmp` temp directory, process, upload result, delete the temp file. Tasks never persist downloads beyond a single invocation.

PDF generation (WeasyPrint) targets `/tmp/{uuid}.pdf`, then uploads, then deletes. The upload uses `boto3.client('s3').upload_file()` with KMS encryption parameters.

### Why we don't use S3 Object Lock or versioning

Versioning is enabled on the bucket (so a malicious or buggy delete can be undone within a recovery window) but Object Lock is not. Object Lock with retention periods conflicts with DPDP erasure obligations — the user has the right to demand erasure within a defined window, and immutable storage blocks compliance.

Our retention is enforced by application logic + Lifecycle Policies, not by Object Lock.

---

## 14. Observability and operations

### Structured logging

`structlog` is the only logging library used. Every log line is JSON in production, key=value in local dev.

Configuration:

```python
# app/core/logging.py
import logging
import sys
import structlog
from app.core.config import settings

def configure_logging():
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
    ]
    if settings.env == "local":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=pre_chain + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    # Quiet noisy libs
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

### Request IDs

`RequestIDMiddleware` generates or reads `X-Request-ID`, binds it to structlog's context vars, attaches to `request.state.request_id`. Every log line within that request is annotated. Response includes the header.

```python
class RequestIDMiddleware:
    async def __call__(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:24]}"
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()
```

### PHI scrubbing

A Sentry `before_send` hook strips known PHI fields before events leave the process:

```python
PHI_FIELDS = {"email", "phone", "name", "date_of_birth", "address",
              "abha_number", "kyros_patient_id", "bank_details_encrypted",
              "biomarker_value", "prescription_content"}

def sentry_before_send(event, hint):
    def scrub(obj):
        if isinstance(obj, dict):
            return {k: ("[REDACTED]" if k.lower() in PHI_FIELDS else scrub(v)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [scrub(x) for x in obj]
        return obj
    event["extra"] = scrub(event.get("extra", {}))
    event["contexts"] = scrub(event.get("contexts", {}))
    # Request body: strip entirely on routes known to carry PHI
    if event.get("request", {}).get("url", "").startswith("/v1/clinic/"):
        event["request"]["data"] = "[REDACTED]"
    return event
```

The same scrubber is also applied to structlog output via a processor in production environments.

### Tracing

We do not run OpenTelemetry / Jaeger / X-Ray in Phase 1. Reasoning: the cost of running a tracing backend exceeds its value at our scale. Request IDs + structured logs are sufficient for forensic reconstruction.

In Phase 2, we add OpenTelemetry instrumentation (`opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`, `opentelemetry-instrumentation-celery`) exporting to AWS X-Ray. The instrumentation hooks are added pre-emptively in Phase 1 but no exporter is configured.

### Sentry

Sentry SDK initialized with:

- `dsn` from config (per env)
- `environment` = env name
- `release` = `settings.app_version` (set from CI build, e.g., git short SHA)
- `traces_sample_rate` = 0.1 in production, 0.0 in local
- `profiles_sample_rate` = 0.0 (not used)
- `integrations` = `[FastApiIntegration(), CeleryIntegration(), SqlalchemyIntegration()]`
- `before_send` = PHI scrubber (above)
- `send_default_pii` = False

Alerts configured:
- Issue alert on every new error type.
- Issue alert on > 50 events per minute for any error.
- Performance alert on P95 transaction duration > 1s on `/v1/clinic/*` routes.

### Metrics

We don't run Prometheus in Phase 1. CloudWatch metrics are sufficient:

- ALB target health
- ECS task CPU/memory (Phase 2) or EC2 host CPU/memory (Phase 1)
- RDS CPU, connections, IOPS, replica lag
- ElastiCache CPU, memory, evictions
- Custom metrics (published via CloudWatch PutMetricData):
  - Celery queue depth (per queue, every minute)
  - Active user count (5-minute window)
  - Webhook receipt counts by source
  - DPDP request counts by type
  - Audit log write rate

The custom metrics are written by a single beat task (`maintenance_tasks.publish_metrics`) every minute.

### Health endpoints

Already specified in §3:

- `GET /healthz`: liveness, no deps, always 200 when process is alive.
- `GET /readyz`: readiness, checks DB + Redis, returns details.

In production, ALB target group is `/healthz`, not `/readyz` (we don't want DB hiccups causing instance churn).

### Queue depth observability

The `publish_metrics` beat task:

```python
@celery_app.task(name="kyros.maintenance.publish_metrics")
def publish_metrics():
    queue_names = ["ocr", "notifications", "reports", "payments", "maintenance", "default"]
    redis = get_redis_sync()
    cloudwatch = boto3.client("cloudwatch", region_name=settings.aws_region)
    metric_data = []
    for q in queue_names:
        depth = redis.llen(q)
        metric_data.append({
            "MetricName": "CeleryQueueDepth",
            "Dimensions": [{"Name": "Queue", "Value": q}],
            "Value": depth,
            "Unit": "Count",
        })
    cloudwatch.put_metric_data(Namespace="Kyros/Backend", MetricData=metric_data)
```

CloudWatch alarm on `CeleryQueueDepth > 100 for queue=ocr for 10 min` pages on-call.

### DB pool observability

`engine.pool.status()` returns a string with current pool state. We expose this via an admin-only endpoint `GET /v1/admin/internal/db-pool-status`. CloudWatch alarm if pool utilization > 80% sustained.

### Cron and task observability

Every beat task logs `task.beat.scheduled` on dispatch and `task.beat.completed` on success. A daily summary task emails admin if any beat task missed its window (didn't run when expected, computed by comparing latest run timestamp to schedule).

### Audit log monitoring

Two automated audits:

1. **Daily integrity check** (`verify_audit_integrity` Celery beat task): computes the hash of the previous day's audit log rows in timestamp order. Compares against the prior day's recorded hash. Drift triggers Sentry alert.

2. **Anomaly detection**: rate-of-denials per actor over 1-hour window. > 20 denials/hour for a single actor → Sentry warning. Patterns surface "user trying to enumerate other patients' resources" or "compromised account."

### Alerting thresholds

Pager (PagerDuty or equivalent):
- API 5xx rate > 1% sustained for 5 min.
- DB connection failures.
- ALB target unhealthy for > 3 min.
- Celery queue depth on `ocr` > 200 sustained for 10 min.
- Payment webhook failure rate > 5% in 10 min.
- DPDP erasure task failed.

Slack notifications (non-pager):
- New Sentry error types.
- Beat task missed its window.
- Audit integrity check failed.
- Daily summary (request counts, error rates, P95 latencies).

### Local debugging experience

- `docker compose logs -f backend-api` shows structured logs in color.
- `docker compose exec backend-api bash` drops into the container for ad-hoc psql / redis-cli / python.
- `make shell-db` opens psql against the dev database.
- `make shell-redis` opens redis-cli.
- The dev `Settings` has `database_echo=False` by default; an engineer can set `KYROS_DATABASE_ECHO=true` in `.env` to log every SQL statement.
- `/docs` (Swagger UI) and `/redoc` are enabled in local and staging.

### Production runbook basics

Runbooks live in `infra/runbooks/`. Phase-A required runbooks:

- `database-failover.md` — RDS failover procedure.
- `dpdp-breach.md` — 72-hour notification process.
- `celery-stuck.md` — what to do when queue depth alarms fire.
- `payment-reconciliation-mismatch.md` — Razorpay/DB reconciliation steps.
- `s3-orphan-cleanup.md` — manual orphan cleanup procedure.
- `audit-integrity-failure.md` — investigation procedure for hash chain breaks.
- `restore-from-backup.md` — RDS PITR and snapshot restore procedure.

Every runbook ends with "after the incident: post-mortem template." Post-mortems live in `docs/postmortems/YYYY-MM-DD-title.md`.

---

## 15. Testing strategy

### Pyramid

The Kyros test pyramid in numbers:

- **Unit tests**: ~60% of test count. Pure-function logic in `core/`, repository signatures, service-layer orchestration with mocked repos.
- **Integration tests**: ~35% of test count. Async API tests against a real Postgres + Redis. The bulk of correctness coverage.
- **End-to-end**: ~5% of test count. Limited to critical user journeys (signup, book, consult, prescribe) and run nightly, not on every PR.

### Test framework

`pytest` + `pytest-asyncio` (with `asyncio_mode = auto`). `httpx.AsyncClient` for API tests. `pytest-postgresql` rejected in favor of compose-managed Postgres (see §4); reason: faster CI, fewer flake modes.

### Async test fixtures

```python
# tests/conftest.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import create_app
from app.db.base import Base
from app.db.session import get_db

TEST_DB_URL = "postgresql+asyncpg://kyros:test@localhost:55432/kyros_test"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    """Each test runs in a transaction that's rolled back at the end."""
    async with test_engine.connect() as connection:
        async with connection.begin() as transaction:
            session = async_sessionmaker(bind=connection, expire_on_commit=False)()
            yield session
            await session.close()
            await transaction.rollback()

@pytest_asyncio.fixture
async def client(db_session):
    app = create_app()
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

Key choice: **per-test transaction rollback for isolation, not full DB cleanup.** This is ~50× faster than truncating tables, and works because every test gets its own connection with its own transaction.

For tests that need committed data (e.g., testing that a Celery task can see committed state from a separate session), we use a different fixture that does explicit cleanup.

### Fixtures

```python
# tests/fixtures/users.py
import pytest_asyncio
from app.models import User
from app.db.enums import Role
from app.core.security import hash_password

@pytest_asyncio.fixture
async def patient_user(db_session) -> User:
    user = User(
        email="patient@test.com",
        phone="+919000000001",
        role=Role.PATIENT,
        password_hash=hash_password("test_password"),
        phone_verified=True,
        email_verified=True,
        name="Test Patient",
    )
    db_session.add(user)
    await db_session.flush()
    return user

@pytest_asyncio.fixture
async def patient_auth_headers(patient_user) -> dict:
    from app.core.security import create_access_token
    token = create_access_token(user_id=patient_user.id, role=Role.PATIENT)
    return {"Authorization": f"Bearer {token}"}
```

Doctor, coordinator, super_admin fixtures follow the same pattern. Consultation, lab report, prescription fixtures build composite states.

### Unit tests

Target: pure-function logic where the assertion is "given input X, output Y." Examples:

- `core.security.hash_password` produces argon2id hashes verifiable by `verify_password`.
- `core.ids.generate_kyros_patient_id` produces format `KYR-YYYY-NNNNN`.
- `core.time.now_utc` returns tz-aware UTC datetime.
- Pydantic schema validation for request models.

### Integration tests for API

The dominant test type. Pattern:

```python
@pytest.mark.asyncio
async def test_patient_cannot_view_other_patient_consultation(
    client, patient_user, patient_auth_headers, db_session,
):
    # Setup: another patient with a consultation
    other_patient_user = await create_user(db_session, role=Role.PATIENT, email="other@test.com")
    other_consultation = await create_consultation(db_session, patient_user=other_patient_user)

    # Act: current patient tries to access other's consultation
    response = await client.get(
        f"/v1/clinic/patient/consultations/{other_consultation.id}",
        headers=patient_auth_headers,
    )

    # Assert: 404, not 403 (cross-user 404 pattern)
    assert response.status_code == 404
    assert response.json()["detail"] == "not found"

    # Assert: denial logged to audit log
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_user.id,
            AuditLog.action == "view_consultation",
            AuditLog.allowed == False,
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"
```

### Migration tests

```python
# tests/migration/test_migrations_up_down.py
@pytest.mark.asyncio
async def test_migrations_round_trip():
    """All migrations apply cleanly forward and backward."""
    from alembic import command
    from alembic.config import Config
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL_SYNC)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")  # all down-migrations must work
    command.upgrade(cfg, "head")
```

Migrations without proper `downgrade()` implementations are caught here. CI runs this test.

### Celery task tests

Tasks are tested at three levels:

1. **Function-level**: the underlying `_parse_lab_report_async` is tested directly, with Document AI mocked.
2. **Task-level**: `parse_lab_report.apply()` (eager mode) verifies the wrapper, retry logic, and task signature.
3. **Integration**: end-to-end "upload lab report → Celery worker (eager) → DB updated" tests.

Eager mode in tests:

```python
@pytest.fixture(autouse=True)
def celery_eager(monkeypatch):
    monkeypatch.setattr("app.tasks.celery_app.celery_app.conf.task_always_eager", True)
    monkeypatch.setattr("app.tasks.celery_app.celery_app.conf.task_eager_propagates", True)
```

### Redis-related tests

We use a real Redis (in compose-test, port 56379) rather than mocking. Each test gets a different DB number (`SELECT N`) for isolation, or `FLUSHDB` at test start.

For OTP, rate limiting, idempotency: real Redis behavior matters; mocking misses subtle bugs (e.g., TTL race conditions).

### RBAC matrix tests

A single parameterized test enumerates the role/endpoint matrix:

```python
@pytest.mark.parametrize("endpoint,methods,allowed_roles,denied_roles", RBAC_MATRIX)
@pytest.mark.asyncio
async def test_rbac_matrix(client, endpoint, methods, allowed_roles, denied_roles, all_user_fixtures):
    for method in methods:
        for role_fixture in denied_roles:
            user = all_user_fixtures[role_fixture]
            headers = make_auth_headers(user)
            response = await client.request(method, endpoint, headers=headers)
            assert response.status_code in (403, 404), \
                f"{role_fixture} should be denied on {method} {endpoint}"
```

The `RBAC_MATRIX` is a list of dictionaries declared in the test file. Adding a new endpoint to the API requires adding it to the matrix (a CI lint enforces this).

### Auth tests

OTP issuance, OTP verification, login (email+password and phone+OTP), refresh token rotation, refresh token reuse detection, logout, password change, all-sessions revocation. Each is its own test.

Critical scenarios:
- Refresh token reuse detection: send a refresh token twice, verify the second attempt revokes the entire session family.
- Token tampering: change a claim, verify decode fails.
- Expired token: forge a past `exp`, verify 401.

### Payment webhook tests

Razorpay webhook tests use captured real-world payloads (sanitized) as fixtures. Each test verifies:
- Signature verification accepts valid payloads.
- Signature verification rejects invalid payloads.
- Idempotency: same payload twice updates DB once.
- Order ID mismatch / missing order returns 400.

### OCR mock tests

Google Document AI client is mocked at the boundary. Tests provide canned responses for various scenarios:
- High-confidence biomarker extraction
- Low-confidence biomarkers (flagged for doctor review)
- OCR failure (timeout, malformed PDF)
- Non-medical document (fallback to OCR processor)

### File upload tests

Pre-signed URL flow tested end-to-end with `moto` (a boto3 mock library) or against LocalStack S3. Verify:
- Pre-signed URL is generated with correct constraints.
- Finalize endpoint rejects when S3 object is missing.
- Finalize endpoint rejects when size or content-type doesn't match.

### Docker-based test environment

`docker-compose.test.yml` (described in §4) spins up postgres-test and redis-test on different ports. CI runs:

```yaml
# .github/workflows/backend.yml (excerpt)
- name: Start test services
  run: docker compose -f docker-compose.test.yml up -d
- name: Wait for services
  run: |
    timeout 30 sh -c 'until docker compose -f docker-compose.test.yml exec -T postgres-test pg_isready -U kyros; do sleep 1; done'
- name: Install Python deps
  run: cd backend && pip install uv && uv pip install --system -r pyproject.toml --extra dev
- name: Run migrations
  run: cd backend && alembic upgrade head
  env:
    KYROS_DATABASE_URL: postgresql+asyncpg://kyros:test@localhost:55432/kyros_test
- name: Run tests
  run: cd backend && pytest -v --cov=app --cov-report=xml
  env:
    KYROS_DATABASE_URL: postgresql+asyncpg://kyros:test@localhost:55432/kyros_test
    KYROS_REDIS_URL: redis://localhost:56379/0
```

### Seed fixtures for tests

`tests/fixtures/` mirrors the seed script's intent: minimal known states, factory functions for composing scenarios. Faker is used for generating realistic-looking but synthetic data (names, phones, emails). PHI in tests is always synthetic.

### Coverage and quality gates

- **Coverage minimum**: 80% line coverage on `app/` (excluding `models/` which is mostly declarations and `integrations/` which is mock-heavy).
- **Mypy strict mode** on `app/`.
- **Ruff** with rule set `E, F, I, B, UP, N, S, C90, SIM, PL`.
- **Pytest collected** must include the RBAC matrix test.

CI fails on any of these.

### What we do not test

- The Postgres engine itself (we trust RDS).
- Third-party SDK internals (we trust boto3, razorpay-python, etc.).
- The Docker daemon, networking, file system.

These are infrastructure assumptions, not Kyros code.

---

## 16. Phased deployment strategy

### Phase 0: Local development

Already detailed in §4 and §9. Single-machine Docker Compose. Engineers run the same image they'll deploy.

### Phase 1: Pre-launch through ~₹50K MRR

**Compute:** Single EC2 t3.small (2 vCPU, 2 GB RAM) in `ap-south-1`. Docker Compose on the host, managed by systemd unit (`kyros-backend.service`).

**Topology:**

```
                            Internet
                                │
                          ┌─────▼──────┐
                          │ CloudFront │ (static assets, image cache)
                          └─────┬──────┘
                                │
                          ┌─────▼──────┐
                          │  AWS WAF   │
                          └─────┬──────┘
                                │
                          ┌─────▼──────┐
                          │    ALB     │ (TLS 1.3, HTTP/2)
                          └─────┬──────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
        ┌─────▼──────┐   ┌─────▼──────┐   ┌─────▼──────┐
        │  EC2-1     │   │  Lambda    │   │ Static     │
        │ Backend    │   │ (later)    │   │ (S3+CF)    │
        │ + Celery   │   └────────────┘   └────────────┘
        │ + Beat     │
        └─────┬──────┘
              │
       ┌──────┴──────────────┐
       │                     │
  ┌────▼─────┐         ┌────▼─────┐
  │ RDS PG16 │         │ ElastiC. │
  │t3.micro  │         │ Redis    │
  └──────────┘         └──────────┘
```

**Services running on the EC2:**

```yaml
# /etc/kyros/docker-compose.yml (production)
services:
  backend-api:
    image: ECR_REGISTRY/kyros-backend:GIT_SHA
    restart: unless-stopped
    env_file: /etc/kyros/backend.env
    ports:
      - "127.0.0.1:8000:8000"  # bind to localhost only; ALB reaches via host networking
    healthcheck: ...
    deploy:
      resources:
        limits:
          memory: 1G
    command: gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

  celery-worker:
    image: ECR_REGISTRY/kyros-backend:GIT_SHA
    restart: unless-stopped
    env_file: /etc/kyros/backend.env
    command: celery -A app.tasks.celery_app worker --loglevel=INFO --queues=ocr,notifications,reports,payments,maintenance,default --concurrency=8
    deploy:
      resources:
        limits:
          memory: 768M

  celery-beat:
    image: ECR_REGISTRY/kyros-backend:GIT_SHA
    restart: unless-stopped
    env_file: /etc/kyros/backend.env
    command: celery -A app.tasks.celery_app beat --loglevel=INFO --schedule=/var/lib/kyros/beat/celerybeat-schedule
    volumes:
      - /var/lib/kyros/beat:/app/beat
```

The ALB forwards `*.kyros.clinic` to the EC2's 8000 port. The EC2 is in a public subnet with security group allowing 80/443 from ALB and 22 from a bastion only.

RDS is in a private subnet, security group allows 5432 only from the EC2 SG. Same for ElastiCache.

**Configuration source:** Secrets Manager. A boot script (`/usr/local/bin/kyros-prepare-env.sh`) runs as a systemd `oneshot` unit before `kyros-backend.service`. It reads from Secrets Manager and writes `/etc/kyros/backend.env`.

**Deployment process** (Phase 1):

1. CI builds image, pushes to ECR with `GIT_SHA` and `latest` tags.
2. CI SSHes to EC2 (via bastion), runs:
   ```bash
   docker pull ECR/kyros-backend:GIT_SHA
   docker compose -f /etc/kyros/docker-compose.yml up -d
   ```
3. Old containers stop after new ones pass healthchecks (compose default).
4. ALB target group health check on `/healthz` flips traffic.

**Migration process** (Phase 1):

1. CI step `pre-deploy` runs `docker run --rm ECR/kyros-backend:GIT_SHA alembic upgrade head` against RDS using a Secrets Manager-pulled connection string. Run from a CI runner with network access to the VPC (e.g., via a CI-IP allowlist on RDS or by running from an ECS task in the VPC).
2. Only if migration succeeds, proceed to container rollout.
3. Migrations are forward-only in production. Rollbacks happen by deploying the previous image and accepting that the schema is now ahead of the code (the new schema must be backward-compatible — see "zero-downtime considerations").

**Cost target:** ~₹15,000–25,000/month all-in (matches build spec).

### Phase 2: Post-trigger (MRR > ₹50K or concurrent users > 500)

**Compute:** ECS Fargate with auto-scaling. Each component is a separate ECS service:

- `kyros-backend-api` — 2 tasks min, 10 tasks max, scaling on ALB request count.
- `kyros-celery-ocr` — 2 tasks min, 6 tasks max, scaling on queue depth.
- `kyros-celery-notifications` — 1 task min, 4 tasks max.
- `kyros-celery-reports` — 1 task min, 3 tasks max.
- `kyros-celery-payments` — 1 task min, 2 tasks max.
- `kyros-celery-maintenance` — 1 task, no autoscaling.
- `kyros-celery-beat` — 1 task, **no autoscaling**, no replicas.

Task sizes start at 2 vCPU + 4 GB RAM. Adjust based on observed usage.

**Database:** RDS Multi-AZ db.t3.medium (or db.r6g.large for predictable workload). Daily snapshots + PITR. One read replica in the same AZ for analytics queries (admin UI heavy queries).

**Cache:** ElastiCache Redis Multi-AZ, automatic failover.

**Load balancer:** ALB with TLS 1.3, ACM certificate, HSTS preload header.

**WAF:** AWS WAF with managed rule sets: Core Rule Set, Known Bad Inputs, IP Reputation, Bot Control.

**Video CDN:** Cloudflare Stream for consultation recordings playback.

**Migration deployment in Phase 2:**

A separate ECS RunTask invocation runs migrations:

```bash
aws ecs run-task \
  --cluster kyros-prod \
  --task-definition kyros-migrate:latest \
  --launch-type FARGATE \
  --network-configuration ...
```

The migration task definition uses the same image with command override `alembic upgrade head`. CI waits for the task to complete with status `STOPPED` and `exitCode: 0`. Only then triggers the service updates.

**Zero-downtime deploys:**

ECS rolling deploys (default) drain old tasks while new tasks accept traffic. The backend's schema-head check at startup ensures new tasks refuse to start until migrations are applied — preventing the failure mode where a new task starts against an outdated schema.

Schema migration patterns that preserve zero-downtime:

- **Adding a column:** nullable or with default. Both old and new code work.
- **Removing a column:** multi-deploy. Deploy 1: stop writing to column. Deploy 2 (some delay): remove column.
- **Renaming a column:** multi-deploy. Deploy 1: add new column, dual-write, code reads from old. Deploy 2: code reads from new. Deploy 3: stop writing old. Deploy 4: drop old.
- **Adding a foreign key:** if the target column has nulls, do `NOT VALID` first (`ALTER TABLE ... ADD CONSTRAINT ... NOT VALID`), then validate in a separate migration (`ALTER TABLE ... VALIDATE CONSTRAINT ...`). Avoids long table lock.
- **Adding an index:** always `CREATE INDEX CONCURRENTLY` in production.

**Backup and restore basics:**

- RDS automated backups: 30 days retention.
- Manual snapshot before every migration (CI step).
- Snapshot copy to a separate AWS account (cross-account replication), 90-day retention. This is ransomware-resistant.
- Quarterly restore drill: restore yesterday's snapshot to a temp instance, run smoke tests, terminate.
- S3 bucket versioning enabled with lifecycle to expire non-current versions after 30 days.

**Disaster recovery RPO/RTO targets:**

- **RPO** (max data loss): 5 minutes (RDS PITR granularity).
- **RTO** (recovery time): 4 hours for full region failure (warm standby in `ap-south-2`, manual cutover).

A cold-standby region is not maintained in Phase 1; the cost is unjustified pre-revenue. Phase 2 adds a warm standby per cost analysis.

### Worker deployment evolution

| Phase | Beat | Workers |
|---|---|---|
| Local | 1 process in compose | 1 process, all queues |
| Phase 1 | 1 process on EC2 | 1 process on EC2, all queues, concurrency=8 |
| Phase 2 | 1 ECS task, desired=1 | Per-queue ECS services, autoscaling per queue |

The beat constraint (1 replica, ever) is the operational constant. Two beat instances double-fire all tasks. If beat dies, alarms fire and on-call investigates.

### Architecture evolution without rewrite

The monolith stays a monolith. What evolves:

- **More worker queues** as new workload types emerge.
- **Read replica adoption** for admin analytics, behind a separate session pool.
- **CDN expansion** for static education content.
- **Multi-region** only at significant scale (10K+ active patients), and only `ap-south-1` + `ap-south-2`, never outside India.
- **gRPC or message-bus internal communication**: only if we extract a service (we don't anticipate this in Year 1–2).

What stays put:

- One repository.
- One backend application (FastAPI).
- One Postgres database (with read replicas later).
- One Redis (with HA later).
- Domain boundaries enforced by code structure, not by services.

---

## 17. Backend and infra non-negotiables

These twenty rules are not aspirational. They are inviolable. Code that violates them does not merge. They are the day-zero compliance posture for Kyros.

1. **Cross-user PHI access always returns 404, never 403.** A patient probing for another patient's resources must not be able to enumerate by status code.

2. **Draft prescriptions are never visible to patients, by any path.** Repository-level filtering. Even pre-signed PDF URLs are not generated for draft prescriptions.

3. **All PHI in S3 is encrypted with SSE-KMS, and S3 objects are never public.** Bucket policies enforce `aws:SecureTransport` and deny `s3:GetObject` for `principal: "*"`.

4. **Migrations never run implicitly on application boot.** A new deploy with a pending migration is a failed deploy. The schema-head check at startup is the safety net.

5. **Coordinators never see lab values, prescription contents, or doctor notes — at the schema layer.** Coordinator-scoped Pydantic schemas omit clinical fields. A coordinator-routed endpoint that uses a non-coordinator schema is a code review reject.

6. **Webhook handlers are idempotent and verify HMAC signatures.** No webhook handler trusts its body without signature verification against the configured secret. Replay of the same event ID is a no-op.

7. **All money is stored in paise as integers.** No `float`, no `Decimal` at the storage boundary. Display conversion to rupees is presentation-layer.

8. **Redis is never the source of truth for any business state.** OTPs, rate limits, idempotency keys, and locks live in Redis with TTLs. Anything durable lives in Postgres.

9. **Audit log entries are immutable.** Postgres trigger blocks UPDATE/DELETE on `ad_audit_log`. A daily integrity hash check validates the chain.

10. **OCR retry logic is idempotent.** A task that runs twice on the same lab report produces the same result and updates the row at most once.

11. **No PHI in application logs.** Patient names, phone numbers, lab values, prescription contents are never logged. structlog and Sentry have PHI scrubbers. Reviews enforce this.

12. **JWT secrets and OTP secrets are minimum 32 characters and validated at startup.** Production refuses to start with default placeholder values.

13. **Every authorization decision is audit-logged.** Both allowed and denied. The audit log is the artifact of compliance, not a debugging tool.

14. **Refresh tokens rotate on use, with reuse detection.** A reused refresh token revokes the entire session family. Implementation per OAuth 2.0 BCP.

15. **Patient profile changes require re-verification of contact info.** Email changes require email OTP. Phone changes require SMS OTP. Both at the same time require both.

16. **Doctor-only fields (clinical notes) are physically separated from patient-visible content by repository function.** Patients never query against `kc_doctor_notes` directly; doctor-visible views project explicit fields.

17. **Data residency: every byte of PHI lives in `ap-south-1` (Mumbai) or the India region of the third-party service.** No cross-region replication outside India. No third-party tools that don't offer India residency.

18. **All inbound API traffic terminates at TLS 1.3.** HTTP redirects to HTTPS. HSTS with preload. Mobile app pins certificates.

19. **Pre-signed S3 URLs have maximum 15-minute TTL.** Long-lived signed URLs are a liability. If a UI needs longer, it re-requests.

20. **Doctor consent for recording is captured per consultation, before the call starts.** Stored in `ad_consent_records` with the consent text hash. No blanket recording.

---

## Appendix A — Recommended docker-compose service map

```yaml
# docker-compose.yml — single-file local development orchestration
name: kyros

services:
  # ─── Stateful infrastructure (replaced by RDS/ElastiCache in production) ───

  postgres:
    image: postgres:16.4-alpine
    container_name: kyros-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: kyros
      POSTGRES_PASSWORD: kyros_dev_password
      POSTGRES_DB: kyros
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/docker/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kyros -d kyros"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 5s

  redis:
    image: redis:7.4-alpine
    container_name: kyros-redis
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "no", "--save", ""]
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ─── Developer convenience (dev only, no production analog) ───

  mailhog:
    image: mailhog/mailhog:v1.0.1
    container_name: kyros-mailhog
    restart: unless-stopped
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI

  # ─── Kyros application (same image, three commands) ───

  backend-api:
    build:
      context: ./backend
      target: dev
    image: kyros-backend:dev
    container_name: kyros-backend-api
    restart: unless-stopped
    env_file: ./backend/.env
    environment:
      KYROS_DATABASE_URL: postgresql+asyncpg://kyros:kyros_dev_password@postgres:5432/kyros
      KYROS_REDIS_URL: redis://redis:6379/0
      KYROS_CELERY_BROKER_URL: redis://redis:6379/1
      KYROS_CELERY_RESULT_BACKEND: redis://redis:6379/2
      KYROS_SMTP_HOST: mailhog
      KYROS_SMTP_PORT: "1025"
      KYROS_ENV: local
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app:cached
      - backend_venv:/opt/venv
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/readyz"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

  celery-worker:
    image: kyros-backend:dev
    container_name: kyros-celery-worker
    restart: unless-stopped
    env_file: ./backend/.env
    environment:
      KYROS_DATABASE_URL: postgresql+asyncpg://kyros:kyros_dev_password@postgres:5432/kyros
      KYROS_REDIS_URL: redis://redis:6379/0
      KYROS_CELERY_BROKER_URL: redis://redis:6379/1
      KYROS_CELERY_RESULT_BACKEND: redis://redis:6379/2
      KYROS_SMTP_HOST: mailhog
      KYROS_SMTP_PORT: "1025"
      KYROS_ENV: local
    volumes:
      - ./backend:/app:cached
      - backend_venv:/opt/venv
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      backend-api: { condition: service_started }
    command: >
      celery -A app.tasks.celery_app worker
      --loglevel=INFO
      --queues=ocr,notifications,reports,payments,maintenance,default
      --concurrency=4

  celery-beat:
    image: kyros-backend:dev
    container_name: kyros-celery-beat
    restart: unless-stopped
    env_file: ./backend/.env
    environment:
      KYROS_DATABASE_URL: postgresql+asyncpg://kyros:kyros_dev_password@postgres:5432/kyros
      KYROS_REDIS_URL: redis://redis:6379/0
      KYROS_CELERY_BROKER_URL: redis://redis:6379/1
      KYROS_CELERY_RESULT_BACKEND: redis://redis:6379/2
      KYROS_ENV: local
    volumes:
      - ./backend:/app:cached
      - backend_venv:/opt/venv
      - celery_beat_data:/app/beat
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: >
      celery -A app.tasks.celery_app beat
      --loglevel=INFO
      --schedule=/app/beat/celerybeat-schedule

volumes:
  postgres_data:
    name: kyros_postgres_data
  backend_venv:
    name: kyros_backend_venv
  celery_beat_data:
    name: kyros_celery_beat_data

networks:
  default:
    name: kyros_network
```

---

## Appendix B — Recommended backend folder tree

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory + lifespan
│   │
│   ├── core/                         # Cross-cutting primitives
│   │   ├── __init__.py
│   │   ├── config.py                 # Pydantic Settings
│   │   ├── logging.py                # structlog setup
│   │   ├── security.py               # password hashing, JWT primitives
│   │   ├── exceptions.py             # KyrosDomainError hierarchy
│   │   ├── pagination.py
│   │   ├── ids.py                    # UUID helpers, KYR-id generator
│   │   ├── time.py                   # tz-aware datetime
│   │   └── audit.py                  # audit context dataclass
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                   # DeclarativeBase + naming convention
│   │   ├── session.py                # async engine + get_db
│   │   ├── mixins.py                 # UUIDMixin, TimestampMixin, SoftDeleteMixin
│   │   └── enums.py                  # StrEnum mirrors of Postgres enums
│   │
│   ├── models/
│   │   ├── __init__.py               # re-exports all models for Alembic
│   │   ├── identity.py               # User, RefreshToken
│   │   ├── consent.py                # ConsentRecord, DataSubjectRequest
│   │   ├── audit.py                  # AuditLog (partitioned, append-only)
│   │   ├── wellness.py               # Reminder, ReminderLog, HealthSyncSession, HealthDatapoint
│   │   ├── clinical.py               # Patient, Consultation, Prescription, ...
│   │   ├── doctor.py                 # Doctor, Availability, Credential
│   │   └── admin.py                  # Coordinator, Configuration
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── auth.py
│   │   ├── patient.py
│   │   ├── doctor.py
│   │   ├── coordinator.py
│   │   ├── admin.py
│   │   └── wellness.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── _helpers.py
│   │   ├── users_repo.py
│   │   ├── refresh_tokens_repo.py
│   │   ├── patients_repo.py
│   │   ├── consultations_repo.py
│   │   ├── prescriptions_repo.py
│   │   ├── lab_orders_repo.py
│   │   ├── lab_reports_repo.py
│   │   ├── doctor_notes_repo.py
│   │   ├── pre_consult_reports_repo.py
│   │   ├── doctors_repo.py
│   │   ├── availability_repo.py
│   │   ├── coordinators_repo.py
│   │   ├── reminders_repo.py
│   │   ├── health_datapoints_repo.py
│   │   ├── consent_repo.py
│   │   ├── data_subject_requests_repo.py
│   │   ├── audit_repo.py
│   │   ├── payments_repo.py
│   │   └── education_repo.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── otp_service.py
│   │   ├── consultation_service.py
│   │   ├── prescription_service.py
│   │   ├── lab_report_service.py
│   │   ├── ocr_service.py
│   │   ├── video_service.py
│   │   ├── payment_service.py
│   │   ├── pre_consult_report_service.py
│   │   ├── notification_service.py
│   │   ├── reminder_service.py
│   │   ├── health_sync_service.py
│   │   ├── dpdp_service.py
│   │   ├── doctor_onboarding_service.py
│   │   ├── coordinator_service.py
│   │   └── education_service.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                   # get_current_user, enforce_role, get_db, get_audit_context
│   │   ├── errors.py                 # exception handlers
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── public/
│   │       │   ├── __init__.py
│   │       │   ├── leads.py
│   │       │   ├── doctors_directory.py
│   │       │   └── booking_inquiry.py
│   │       ├── clinic/
│   │       │   ├── __init__.py
│   │       │   ├── patient_profile.py
│   │       │   ├── consultations.py
│   │       │   ├── prescriptions.py
│   │       │   ├── lab_reports.py
│   │       │   ├── education.py
│   │       │   └── payments.py
│   │       ├── wellness/
│   │       │   ├── __init__.py
│   │       │   ├── reminders.py
│   │       │   └── health_sync.py
│   │       ├── doctor/
│   │       │   ├── __init__.py
│   │       │   ├── dashboard.py
│   │       │   ├── panel.py
│   │       │   ├── consultations.py
│   │       │   ├── notes.py
│   │       │   ├── prescriptions.py
│   │       │   ├── lab_review.py
│   │       │   ├── schedule.py
│   │       │   └── education_assignment.py
│   │       ├── admin/
│   │       │   ├── __init__.py
│   │       │   ├── doctors.py
│   │       │   ├── users.py
│   │       │   ├── coordinators.py
│   │       │   ├── content.py
│   │       │   ├── analytics.py
│   │       │   ├── audit_logs.py
│   │       │   └── configuration.py
│   │       ├── admin_coordinator/
│   │       │   ├── __init__.py
│   │       │   ├── intake_queue.py
│   │       │   ├── scheduling.py
│   │       │   ├── triage.py
│   │       │   └── communication.py
│   │       └── webhooks/
│   │           ├── __init__.py
│   │           ├── razorpay.py
│   │           └── hms_100ms.py
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── s3.py
│   │   ├── document_ai.py
│   │   ├── hms_100ms.py
│   │   ├── razorpay.py
│   │   ├── msg91.py
│   │   ├── aisensy.py
│   │   ├── sendgrid.py
│   │   ├── expo_push.py
│   │   ├── elevenlabs.py
│   │   └── abha.py
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── _helpers.py               # run_async, task_db_session
│   │   ├── ocr_tasks.py
│   │   ├── report_tasks.py
│   │   ├── notification_tasks.py
│   │   ├── payment_tasks.py
│   │   ├── video_tasks.py
│   │   ├── dpdp_tasks.py
│   │   ├── reminder_tasks.py
│   │   ├── analytics_tasks.py
│   │   ├── maintenance_tasks.py
│   │   └── beat_schedule.py
│   │
│   ├── adminui/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── deps.py                   # session cookie auth
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── admin/...
│   │   │   └── coordinator/...
│   │   └── static/
│   │       ├── css/
│   │       ├── js/
│   │       └── img/
│   │
│   └── observability/
│       ├── __init__.py
│       ├── sentry.py
│       ├── metrics.py
│       └── middleware.py
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_init_extensions_and_enums.py
│       ├── 0002_identity_and_consent.py
│       ├── 0003_audit_log.py
│       ├── 0004_doctor_domain.py
│       └── ...
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── patients.py
│   │   ├── doctors.py
│   │   ├── consultations.py
│   │   └── ...
│   ├── unit/
│   │   ├── core/
│   │   ├── services/
│   │   └── repositories/
│   ├── integration/
│   │   ├── api/
│   │   │   ├── test_auth.py
│   │   │   ├── test_patient_routes.py
│   │   │   ├── test_doctor_routes.py
│   │   │   ├── test_coordinator_routes.py
│   │   │   ├── test_admin_routes.py
│   │   │   ├── test_webhooks.py
│   │   │   └── test_rbac_matrix.py
│   │   └── tasks/
│   │       ├── test_ocr_tasks.py
│   │       ├── test_report_tasks.py
│   │       └── test_notification_tasks.py
│   └── migration/
│       └── test_migrations_up_down.py
│
├── scripts/
│   ├── seed_dev.py
│   ├── create_super_admin.py
│   ├── generate_openapi.py
│   └── reset_dev_db.sh
│
├── Dockerfile
├── alembic.ini
├── pyproject.toml
├── uv.lock
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

---

## Appendix C — Recommended first-week implementation sequence

This sequence assumes one engineer (or Claude Code) implementing from a clean repo. Each day is bounded by a clear deliverable.

### Day 1: Foundation infrastructure

**Goal:** `make bootstrap` works. The container starts. Health endpoints respond.

Tasks:
1. Create monorepo skeleton (top-level tree from §2).
2. Create `backend/` with `pyproject.toml` listing all locked dependencies.
3. Write `Dockerfile` (multi-stage) and `docker-compose.yml` (the appendix A version).
4. Write `infra/docker/postgres/init.sql` (extensions, read-only role).
5. Write `app/core/config.py` (full Pydantic Settings as in §8).
6. Write `app/core/logging.py` (structlog setup).
7. Write `app/db/base.py`, `app/db/session.py`, `app/db/mixins.py`, `app/db/enums.py` (minimal).
8. Write `app/main.py` with lifespan but no routes yet, plus `/healthz` and `/readyz`.
9. Write `Makefile` with `bootstrap`, `dev`, `migrate`, `seed`, `test`, `down`, `reset`, `logs`, `shell-db`, `shell-redis`.
10. Initialize Alembic. Empty initial migration `0001_init_extensions_and_enums.py` creates Postgres extensions and registers the enum types from `db/enums.py`.

**Acceptance:** `git clone && make bootstrap` produces `curl localhost:8000/healthz` returning `{"status":"ok"}` and `curl localhost:8000/readyz` returning `{"db":"ok","redis":"ok"}`.

### Day 2: Identity, auth, and audit log

**Goal:** Users can register, log in, refresh, log out. Every action is audit-logged.

Tasks:
1. Migration `0002_identity_and_consent.py`: `users` (with role enum), `refresh_tokens`, `ad_consent_records`, `ad_data_subject_requests`.
2. Migration `0003_audit_log.py`: `ad_audit_log` partitioned by month, first 3 months of partitions, append-only trigger.
3. Models for `User`, `RefreshToken`, `ConsentRecord`, `DataSubjectRequest`, `AuditLog`.
4. Repositories: `users_repo`, `refresh_tokens_repo`, `audit_repo`, `consent_repo`.
5. `app/core/security.py`: argon2id wrappers, JWT encode/decode, refresh token generation + hashing.
6. `app/services/auth_service.py`, `app/services/otp_service.py`.
7. `app/integrations/msg91.py` (stub for local dev, real for prod).
8. `app/api/deps.py`: `get_db`, `get_current_user`, `enforce_role`, `get_audit_context`, `get_patient_user`, `get_doctor_user`, `get_coordinator_user`, `get_admin_user`.
9. `app/api/v1/auth.py`: `POST /v1/auth/login`, `POST /v1/auth/otp/request`, `POST /v1/auth/otp/verify`, `POST /v1/auth/refresh`, `POST /v1/auth/logout`.
10. `app/api/errors.py`: exception handlers.
11. Integration tests for the auth flow (the 8 happy + sad paths above).
12. `scripts/create_super_admin.py`: interactive script for first admin.

**Acceptance:** End-to-end OTP login flow works in local dev (with the OTP visible in mailhog or stdout for development convenience). Refresh token rotation works. Reuse detection triggers session-wide revocation. RBAC dependencies raise 403 for wrong role. Every action lands in `ad_audit_log`.

### Day 3: Doctor domain + super admin + coordinator role

**Goal:** Super admin can onboard a doctor through the admin UI. A coordinator user exists.

Tasks:
1. Migration `0004_doctor_domain.py`: `dr_doctors`, `dr_availability` (with `EXCLUDE USING gist (doctor_id WITH =, tstzrange(slot_start, slot_end) WITH &&)` for slot overlap prevention), `dr_credentials`.
2. Migration `0005_admin_coordinator.py`: `ad_coordinators`, `ad_configuration`.
3. Models, repositories, services for doctor + coordinator.
4. `app/api/v1/admin/doctors.py`: list, create, update, set-active, list-credentials.
5. `app/api/v1/admin/coordinators.py`: list, create, assign-patient.
6. Set up the Jinja2 admin UI skeleton at `/admin`:
   - Login page (separate from API auth — session cookies).
   - Admin dashboard (counts).
   - Doctor management screens (HTMX-driven list, doctor detail).
7. RBAC matrix entries for all new endpoints.

**Acceptance:** A super admin logs in via `/admin`, creates a doctor profile, the doctor record is created and viewable. Coordinator user creation works. A coordinator JWT cannot access `/v1/admin/doctors`.

### Day 4: Patient domain + consultation booking core

**Goal:** A patient can sign up, complete intake, and book a consultation against a doctor's availability.

Tasks:
1. Migration `0006_clinical_core.py`: `kc_patients`, `kc_consultations`, `kc_doctor_notes`.
2. Models, repositories.
3. `app/services/consultation_service.py`: `book_consultation` with row locking on availability slot.
4. `app/api/v1/clinic/patient_profile.py`: GET/PATCH `/v1/clinic/patient/me`, intake form.
5. `app/api/v1/clinic/consultations.py`: list, get, book.
6. `app/api/v1/doctor/schedule.py`: list available slots, mark slot blocked, list booked consultations.
7. Cross-user 404 tests for consultation access.
8. Idempotency-key handling on `POST /v1/clinic/patient/consultations`.

**Acceptance:** A patient JWT books a consultation, the corresponding `dr_availability` row flips to `booked`, the consultation appears in both patient's and doctor's list endpoints. Booking the same slot twice with the same idempotency key returns the same result. Without idempotency key, the second booking fails on the `dr_availability` constraint.

### Day 5: File upload pipeline + first Celery task

**Goal:** Pre-signed upload works. Celery worker processes a placeholder task. The OCR pipeline scaffold exists, even with a stub Document AI.

Tasks:
1. Migration `0008_clinical_labs.py`: `kc_lab_orders`, `kc_lab_reports`.
2. `app/integrations/s3.py`: pre-signed PUT/GET URL generation, HEAD object verification.
3. `app/api/v1/clinic/lab_reports.py`: `POST /initiate-upload`, `POST /{id}/finalize`, `GET /{id}/download`, `PATCH /{id}` (corrections).
4. `app/tasks/celery_app.py`: full Celery app config with task routing.
5. `app/tasks/ocr_tasks.py`: `parse_lab_report` task with the async-bridge pattern.
6. `app/integrations/document_ai.py`: real client for prod, stub returning a canned JSON for local dev.
7. Beat schedule: register `reconcile_pending_lab_ocr` (every 30 min) and a placeholder for `provision_video_room`.
8. Tests: full upload flow + OCR task (eager mode).

**Acceptance:** A patient initiates a lab report upload, uploads to S3 (or LocalStack), finalizes. The OCR task runs (in eager mode in test, in real worker in dev). The parsed JSON lands in `kc_lab_reports.parsed_json`. The patient can correct the parsed values. The download endpoint returns a signed URL that resolves to the original PDF.

### Day 6: Prescriptions + pre-consult report + video room scaffold

**Goal:** Doctor can write a prescription. Pre-consult report generation works. 100ms room provisioning task fires.

Tasks:
1. Migration `0007_clinical_prescriptions.py`: `kc_prescriptions`, `kc_prescription_items`.
2. Migration `0010_clinical_pre_consult.py`: `kc_pre_consultation_reports`.
3. Models, repositories, services.
4. `app/services/prescription_service.py`: draft → sign flow with versioning. Signing generates the PDF via WeasyPrint and uploads to S3.
5. `app/services/pre_consult_report_service.py`: aggregates lab + adherence + wearable + intake into the report row. PDF via WeasyPrint.
6. `app/tasks/report_tasks.py`: `generate_pre_consultation_report` task + the T-24h beat task.
7. `app/integrations/hms_100ms.py`: room creation + role-scoped JWT generation.
8. `app/tasks/video_tasks.py`: `provision_upcoming_rooms` beat task scanning consultations with `status='confirmed' AND scheduled_start_at < NOW() + INTERVAL '15 minutes' AND video_room_id IS NULL`.
9. `app/api/v1/doctor/prescriptions.py`: full CRUD on draft, sign endpoint.
10. `app/api/v1/clinic/prescriptions.py`: list, get, download — drafts return 404.
11. Tests including: a draft prescription cannot be retrieved by the patient (cross-user 404 + state-based 404).

**Acceptance:** A doctor creates a prescription, fills items, signs it. The PDF appears in S3. The patient can list and download signed prescriptions but not drafts. A consultation 14 minutes from now gets a 100ms room provisioned by the beat task. The pre-consult report task runs on demand and produces a PDF.

### Day 7: Wrap-up — payments scaffolding, RBAC matrix completeness, seed script, deployment skeleton

**Goal:** Razorpay scaffold exists. RBAC matrix tests pass. The seed script populates a complete realistic state.

Tasks:
1. Migration `0009_clinical_payments_education.py`: `kc_payments`, `kc_education_*`.
2. `app/integrations/razorpay.py`: order creation, payment verification, signature verification.
3. `app/api/v1/clinic/payments.py`: `POST /payments` (creates Razorpay order), `POST /payments/{id}/verify`.
4. `app/api/v1/webhooks/razorpay.py`: HMAC verification, idempotency, payment status updates.
5. Test the webhook with sanitized real-world payload fixtures.
6. Complete RBAC matrix test for every endpoint added during the week. CI rule that fails if a `/v1/*` route lacks a matrix entry.
7. Full `scripts/seed_dev.py`: super admin, 2 coordinators, 3 doctors, 8 patients, 4 consultations in various states, 2 lab reports (one with high-confidence OCR, one needing review), 1 signed prescription, 1 draft prescription, audit log entries.
8. Write `infra/terraform/` skeleton for Phase 1 EC2 + RDS + ElastiCache (Terraform files only, not applied).
9. Write `infra/runbooks/database-failover.md` and `infra/runbooks/dpdp-breach.md`.
10. Tag `v0.1.0`.

**Acceptance:** Running `make bootstrap` produces a state where:
- An engineer logs in as the seeded super admin, sees the dashboard with real counts.
- A seeded patient JWT can book a consultation, upload a lab report, view prescriptions.
- A seeded doctor JWT can see their panel, write a prescription, sign it.
- A coordinator JWT can see their assigned patients but not lab values or prescription contents.
- The RBAC matrix test passes for all endpoints.
- CI builds the production image successfully.
- A Razorpay test-mode end-to-end payment flow completes.

### What comes next (week 2+)

Following the build-spec prompt queue (P7 onwards): wellness reminders, health data sync endpoints, education content, notification dispatch, full coordinator portal screens, DPDP rights endpoints (export and erasure), ABHA M1 implementation.

By end of week 4, the backend covers everything required for a Phase A pilot launch: a small cohort of patients, a doctor panel, the full consultation lifecycle, payments, lab reports, prescriptions, and the regulatory compliance posture (audit log, consent records, DPDP requests).

---

## Closing note

This document picks one path at every branch. It is opinionated by design: a backend that defers every architectural decision to runtime is a backend that ships nothing. Where this document disagrees with a future preference, reopen the specific section with concrete reasoning — do not partially adopt patterns that depend on each other.

The patterns here are conservative for healthcare. They will feel over-engineered relative to a typical D2C startup backend. That is correct. A patient seeing another patient's lab report is a regulatory incident, not a bug to be fixed in the next sprint. The discipline embedded in these choices — cross-user 404, audit log on every authorization decision, manual migration gates, idempotency everywhere, no PHI in logs — is the discipline that lets Kyros earn the trust embedded in the third pillar: "One platform, where privacy is the point."

The platform serves real chronic-disease patients with serious clinical workflows. The backend has to deserve them. Build it that way from the first migration.
