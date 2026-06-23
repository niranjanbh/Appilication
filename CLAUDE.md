# Kyros Platform — Project Memory

You are working on the Kyros Clinic platform: an India-first, doctor-first telemedicine clinic
covering hormonal health, PCOS, thyroid, weight management, skin/hair, men's intimate health,
TRT, and longevity support. This is a healthcare platform handling protected health information.
Get the security model right before getting anything else right.

## Where authoritative context lives

Read these on demand for the task at hand. They are long — read only the sections you need.

| When working on… | Read first |
|---|---|
| Any clinical or regulatory question | `.claude/skills/kyros-clinical-compliance/SKILL.md` |
| Brand voice, visual register, design tokens, content production | `.claude/skills/kyros-design-system/SKILL.md` |
| Positioning, pricing, unit economics, fundraising | `.claude/skills/kyros-business-strategy/SKILL.md` |
| D2C acquisition, social, SEO, founder content | `.claude/skills/kyros-customer-acquisition/SKILL.md` |
| Corporate wellness, insurance/TPA, doctor associations | `.claude/skills/kyros-b2b2c-partnerships/SKILL.md` |
| Backend implementation (FastAPI, Postgres, Celery, Docker, RBAC, audit) | `docs/strategy/backend-strategy.md` |
| Frontend implementation (mobile, doctor portal, website, admin UI) | `docs/strategy/frontend-strategy.md` |
| Database schema, API routes, P1–P30 prompts, decision log | `docs/strategy/build-spec.md` |
| The current build prompt | `docs/build-prompts/P{nn}-*.md` |

Do **not** read these files at session start. Read sections on demand. Use the table of contents
in each document to locate the right section.

## Locked stack — do not propose alternatives

**Backend:** FastAPI 0.115, SQLAlchemy 2.0 async + asyncpg, Pydantic v2, Alembic, Celery 5.4,
Postgres 16, Redis 7, argon2id, structlog, ruff, mypy strict, pytest + pytest-asyncio.

**Frontend:** Next.js 14 App Router (website), Vite 5 + React 18 + TypeScript strict (doctor
portal), Expo 51 + React Native + React Native Web (patient mobile + patient web portal),
Jinja2 + HTMX + Alpine.js (super admin + coordinator portals served by FastAPI).

**Infra:** Docker Compose for local dev, AWS in `ap-south-1` for production (EC2 Phase 1 → ECS
Fargate Phase 2), RDS Postgres, ElastiCache Redis, S3 + KMS for files, Secrets Manager for
secrets, CloudWatch for logs, Sentry for errors.

**Integrations:** Razorpay (payments), 100ms (video), Google Document AI (OCR), MSG91 (SMS OTP),
AiSensy (WhatsApp utility), SendGrid (email), Expo Push (mobile push), ElevenLabs (content
voice synthesis), ABDM/ABHA sandbox (later).

## Architectural rules — always on

- **Modular monolith.** One FastAPI backend serves all six surfaces. Domain separation by table
  prefix (`wn_`, `kc_`, `dr_`, `ad_`) and directory structure, not microservices.
- **One Postgres database.** Domains separated by table prefix, not Postgres schemas.
- **Repository pattern.** Routers call services; services call repositories. No direct
  SQLAlchemy in routers or services.
- **Resource scoping is a repository parameter** (`patient_user_id`, `doctor_id`), never an
  implicit context.
- **Money in paise as integers.** No floats, no Decimal at the storage boundary.
- **Timestamps stored UTC, displayed IST.** No naive datetimes anywhere.
- **All PHI lives in `ap-south-1`.** No cross-region replication outside India. No third-party
  tools without India data residency.

## Healthcare non-negotiables — never violated

See `.claude/rules/security.md` for the full twenty. Top eight to internalize:

1. Cross-user PHI access returns 404, never 403.
2. Draft prescriptions are never visible to patients by any path.
3. Every authorization decision writes to `ad_audit_log` — allowed and denied.
4. Migrations never auto-run on application boot.
5. No PHI in logs, ever. structlog and Sentry have PHI scrubbers.
6. Coordinators never see lab values, prescription contents, or doctor notes.
7. Webhooks are idempotent and HMAC-verified.
8. JWT and OTP secrets are minimum 32 chars, validated at startup.

## Commands

```bash
make bootstrap        # first-clone setup: build, postgres up, migrate, seed, all services up
make dev              # start all services (compose up)
make migrate          # apply Alembic migrations (never auto-runs)
make migrate-create   # generate a new migration via autogenerate
make seed             # populate dev fixtures (idempotent)
make test             # run pytest in compose-test environment
make logs             # tail backend + worker logs
make shell-db         # psql against the dev database
make shell-redis      # redis-cli against dev Redis
make shell-backend    # bash inside the backend container
make ruff             # lint backend
make mypy             # type-check backend
make openapi          # regenerate openapi.json for client codegen
make down             # stop services (keeps volumes)
make reset            # ⚠️ destroys volumes and rebootstraps (asks for confirmation)
```

## How to execute a build prompt (P1–P30)

When the user asks you to execute Pn:

1. Read `docs/build-prompts/P{nn}-*.md` — it contains the prompt, required reading, and
   acceptance criteria.
2. Open the strategy doc sections it references. Read only those sections.
3. **Plan first.** Outline the files you will create, the migrations you will write, the tests
   you will add. Pause and wait for the user to approve before editing.
4. Implement: code, Alembic migration (review before apply), tests.
5. Run `make test`. If anything fails, fix before declaring done.
6. Summarize what was added, what changed, and what the user should manually verify.

One prompt = one session. After finishing Pn, end the session. Start Pn+1 fresh.

## How to work day to day

- **Plan before editing.** For any multi-file change, outline the plan and wait for approval.
- **Migrations get reviewed.** Generate them with autogenerate, then open the file. Do not
  apply silently.
- **Tests are part of the deliverable, not optional.** Every new endpoint goes in the RBAC
  matrix at `tests/integration/api/test_rbac_matrix.py`.
- **Never commit secrets.** `.env` is gitignored. `.env.example` is the documented template.
- **Watch context.** If `/context` shows pressure, finish the current concern, then `/compact`
  or end the session.
- **When uncertain about a clinical claim, regulatory rule, or vocabulary choice, stop and
  read `.claude/skills/kyros-clinical-compliance/SKILL.md` before proceeding.**

## Plugin overrides

When the `agent-skills` plugin is active, Kyros's own rules take precedence in all conflicts:
- `.claude/rules/security.md` (20 non-negotiables) overrides the plugin's `security-and-hardening` skill.
- `.claude/skills/kyros-clinical-compliance/` overrides any generic compliance guidance.
- Do not enable the `simplify-ignore` or `sdd-cache` hooks from the plugin on this codebase.

## What not to do

- Do not propose microservices, gRPC internal communication, or Kubernetes.
- Do not propose Postgres schemas as the domain-separation mechanism (use table prefixes).
- Do not propose ORMs other than SQLAlchemy, web frameworks other than FastAPI, or front-end
  frameworks outside the locked stack.
- Do not auto-run migrations on app boot. The schema-head check at startup refuses to serve
  traffic against an outdated schema — that is the boundary.
- Do not generate marketing claims, clinical content, or doctor-attributed text without
  reading `kyros-clinical-compliance` first.
- Do not put PHI in logs, in Sentry events, in commit messages, in test fixtures (use synthetic
  data via Faker), or in error responses returned to the client.
