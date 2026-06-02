# P2 — Database Foundation + Identity

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §3 (FastAPI), §5 (Postgres), §10 (schema impl), §11 (auth + RBAC)
- `docs/strategy/build-spec.md` — section 2 (database schema, users + identity)
- `.claude/rules/security.md` — auth + secret rules

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

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

---

*To execute: tell Claude Code `Execute P2. Read docs/build-prompts/P02-database-foundation-and-identity.md, then plan before editing.`*
