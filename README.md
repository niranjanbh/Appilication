# Kyros Clinic Platform

India-first, doctor-first telemedicine clinic covering hormonal health, PCOS, thyroid,
weight management, skin/hair, men's intimate health, TRT, and longevity support.

## Surfaces

| Surface | Stack | Path |
|---|---|---|
| Patient mobile app | Expo 51 + React Native + React Native Web | `mobile/` |
| Patient web portal | React Native Web (same codebase as mobile) | `mobile/` |
| Doctor portal | Vite 5 + React 18 + TypeScript | `doctor-portal/` |
| Marketing website | Next.js 14 App Router + MDX | `website/` |
| Super admin portal | Jinja2 + HTMX + Alpine.js (served by FastAPI) | `backend/app/adminui/` |
| Coordinator portal | Jinja2 + HTMX + Alpine.js (served by FastAPI) | `backend/app/adminui/` |

All six surfaces are served by a single FastAPI modular monolith — one codebase, one
Postgres database, one deploy unit.

## Tech stack

**Backend:** FastAPI 0.115 · SQLAlchemy 2.0 async + asyncpg · Pydantic v2 · Alembic ·
Celery 5.4 · Postgres 16 · Redis 7 · argon2id · structlog · ruff · mypy strict ·
pytest + pytest-asyncio

**Frontend:** Next.js 14 App Router (website) · Vite 5 + React 18 + TypeScript (doctor
portal) · Expo 51 + React Native + React Native Web (mobile + web patient portal)

**Infra (local dev):** Docker Compose · MailHog (email preview)

**Infra (production):** AWS `ap-south-1` · EC2 → ECS Fargate · RDS Postgres · ElastiCache
Redis · S3 + KMS · Secrets Manager · CloudWatch · Sentry

**Integrations:** Razorpay (payments) · 100ms (video) · Google Document AI (OCR) · MSG91
(SMS OTP) · AiSensy (WhatsApp) · SendGrid (email) · Expo Push (mobile push) · ElevenLabs
(content voice) · ABDM/ABHA sandbox

## Repository layout

```
.
├── backend/                    # FastAPI monolith
│   ├── app/
│   │   ├── api/v1/             # REST endpoints (auth, clinic, doctor, admin, …)
│   │   ├── adminui/            # Jinja2 + HTMX super-admin + coordinator portals
│   │   ├── core/               # Config, security, RBAC, permissions, audit
│   │   ├── db/                 # Engine, session, enums
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── repositories/       # SQL layer (one file per aggregate)
│   │   ├── services/           # Business logic
│   │   ├── tasks/              # Celery tasks
│   │   └── observability/      # Structlog middleware, Sentry, metrics
│   ├── alembic/versions/       # 30 sequential migrations (0001–0030)
│   └── tests/                  # 827 integration + unit tests
├── doctor-portal/              # Vite + React 18 + TypeScript doctor SPA
├── mobile/                     # Expo 51 React Native (iOS / Android / Web)
├── website/                    # Next.js 14 marketing site + MDX content
├── design-tokens/              # Shared design tokens consumed by all frontends
├── infra/                      # CloudFormation templates, ECS task definitions
├── scripts/                    # Dev utilities, seed scripts, prompt extractor
├── docs/
│   ├── strategy/               # build-spec.md, backend-strategy.md, frontend-strategy.md
│   ├── build-prompts/          # P01–P39 per-prompt work units
│   ├── postman/                # Postman collection + environment
│   ├── runbook-prod.md
│   ├── dpdp-breach-runbook.md
│   └── dpia-v1.md
├── .claude/                    # Claude Code configuration (see .claude/SETUP.md)
├── CLAUDE.md                   # Project memory loaded every Claude Code session
├── Makefile                    # All dev workflows
├── docker-compose.yml          # Local dev services
└── docker-compose.test.yml     # Isolated test services (separate ports + DB)
```

## Local development

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Node.js 20+ and pnpm 9+ (for frontends)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (for backend work outside Docker)

### First-time setup

```bash
git clone <repo-url> kyros-platform
cd kyros-platform
make bootstrap
```

`make bootstrap` builds the backend image, starts Postgres + Redis, runs all migrations,
seeds development fixtures, then starts all services.

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Super admin portal | http://localhost:8000/admin |
| Coordinator portal | http://localhost:8000/coord |
| MailHog (email preview) | http://localhost:8025 |
| Postgres | localhost:5433 |
| Redis | localhost:6380 |

### Daily workflow

```bash
make dev          # start all services (foreground; Ctrl-C stops)
make up           # start all services (detached)
make logs         # tail backend + worker logs
make down         # stop services (keeps volumes)
```

### Database

```bash
make migrate                   # apply pending Alembic migrations
make migrate-create            # autogenerate a new migration
make migrate-history           # show migration history
make migrate-current           # show current DB head
make migrate-downgrade-one     # roll back one migration (dev only)
make seed                      # re-run seed fixtures (idempotent)
make create-super-admin        # create a super-admin user interactively
make shell-db                  # psql into the dev database
make shell-redis               # redis-cli into dev Redis
```

Migrations **never run automatically on app boot**. A schema-version mismatch causes the
app to refuse to start with a clear error.

### Testing

```bash
make test              # run full pytest suite in isolated compose-test environment
make test-watch        # run tests in watch mode
make test-rbac         # run RBAC matrix tests only
make test-migrations   # run migration up/down round-trip tests
```

Tests run against a separate Postgres instance (port 55432) and Redis (port 56379) defined
in `docker-compose.test.yml`. The suite currently has **827 tests** (integration + unit).

### Code quality

```bash
make ruff          # lint backend Python
make ruff-fix      # auto-fix lint issues
make mypy          # type-check backend (strict mode)
make lint          # ruff + mypy together
make format        # ruff format
```

### Frontend

```bash
make install-frontend      # pnpm install for all workspaces
make typecheck-frontend    # tsc --noEmit for website + doctor-portal + mobile
make build-frontend        # production build for all frontends
make openapi               # regenerate openapi.json from live server
make generate-clients      # regenerate TypeScript API clients from openapi.json
```

### Utilities

```bash
make shell-backend     # bash inside the backend container
make shell-worker      # bash inside the Celery worker container
make postman           # export Postman collection to docs/postman/
make extract-prompts   # split build-spec.md into per-prompt files in docs/build-prompts/
```

## API structure

All REST endpoints live under `/v1/`:

| Prefix | Audience | Description |
|---|---|---|
| `/v1/public/` | Unauthenticated | Doctors list, booking inquiry, health content |
| `/v1/auth/` | All | Login, OTP, refresh, password reset, Google OAuth |
| `/v1/users/` | All authenticated | Profile, notifications, DPDP erasure request |
| `/v1/wellness/` | Patient | Reminders, health sync |
| `/v1/payments/` | Patient | Razorpay checkout, invoice download |
| `/v1/clinic/patient/` | Patient | Consultations, lab reports, prescriptions, ABHA, notes |
| `/v1/doctor/` | Doctor | Patient panel, notes, lab orders, prescriptions, video |
| `/v1/admin/` | Super admin / Admin | Content, analytics, DSR, pricing, coupons, doctors |
| `/v1/webhooks/` | Internal | Razorpay webhook (HMAC-verified) |
| `/admin/` | Super admin (session cookie) | Jinja2 super-admin portal |
| `/coord/` | Coordinator (session cookie) | Jinja2 coordinator portal |

## Architecture rules

- **Modular monolith.** One FastAPI app serves all six surfaces. Domain separation by table
  prefix (`wn_`, `kc_`, `dr_`, `ad_`) and directory, not microservices.
- **Repository pattern.** Routers → Services → Repositories. No SQLAlchemy in routers.
- **Cross-user PHI returns 404, never 403.** Scoping is a repository parameter.
- **Money in paise as integers.** No floats at the storage boundary.
- **Timestamps stored UTC, displayed IST.** No naive datetimes.
- **Every authorization decision is audit-logged** (allowed and denied) to `ad_audit_log`.
- **Migrations reviewed before apply.** Auto-run on boot is disabled; startup schema-head
  check refuses traffic against a stale schema.

See `.claude/rules/security.md` for the full 20 healthcare non-negotiables.

## Claude Code setup

See [`.claude/SETUP.md`](.claude/SETUP.md) for the Claude Code configuration guide —
rule loading order, how to add new rules, skill descriptions, and troubleshooting.

## Key docs

| Document | Purpose |
|---|---|
| `docs/strategy/build-spec.md` | Full DB schema, API route catalogue, P1–P39 prompt queue |
| `docs/strategy/backend-strategy.md` | Backend implementation blueprint (FastAPI, RBAC, Celery, …) |
| `docs/strategy/frontend-strategy.md` | Frontend implementation blueprint (mobile, doctor portal, website) |
| `docs/runbook-prod.md` | Production runbook (deploy, rollback, on-call) |
| `docs/dpdp-breach-runbook.md` | DPDP 72-hour breach notification procedure |
| `docs/dpia-v1.md` | Data Protection Impact Assessment v1 |
