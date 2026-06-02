# P3 — RBAC Middleware + Consent Capture

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §11 (auth + RBAC), §12 (API organization)
- `docs/strategy/build-spec.md` — section 4 (RBAC), section 15 (DPDP)
- `.claude/skills/kyros-clinical-compliance/SKILL.md` — consent, DPDP rules

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

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

---

*To execute: tell Claude Code `Execute P3. Read docs/build-prompts/P03-rbac-middleware-and-consent-capture.md, then plan before editing.`*
