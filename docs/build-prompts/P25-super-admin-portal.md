# P25 — Super Admin Portal (Jinja2 + HTMX)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §3 (admin UI mounting), §11 (admin scoping)
- `.claude/rules/admin-ui.md` — Jinja2 + HTMX patterns
- `docs/strategy/build-spec.md` — section 10 (super admin portal)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/admin_ui/`:
- Implement Jinja2 templates per Section 12
- Dashboard, user management, doctor pipeline, consultation management, content approval, audit log
- HTMX partial updates for table row actions
- Tailwind with shared design tokens

**Acceptance:**
- Super admin renders dashboard in < 200ms
- Doctor onboarding pipeline shows all applied → active stages
- Audit log filterable by actor, action, date

---

*To execute: tell Claude Code `Execute P25. Read docs/build-prompts/P25-super-admin-portal.md, then plan before editing.`*
