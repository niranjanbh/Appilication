# P26 — Care Coordinator Portal (Jinja2 + HTMX)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §3 (admin UI), §11 (coordinator scoping, clinical content stripping)
- `.claude/rules/admin-ui.md` — coordinator UI rules
- `docs/strategy/build-spec.md` — section 10 (care coordinator portal)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

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

---

*To execute: tell Claude Code `Execute P26. Read docs/build-prompts/P26-care-coordinator-portal.md, then plan before editing.`*
