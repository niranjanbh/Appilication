# P18 — Doctor Portal Foundation

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — doctor portal section
- `docs/strategy/build-spec.md` — section 9 (doctor portal)
- `.claude/skills/kyros-design-system/SKILL.md` — doctor portal visual register

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `doctor-portal/`:
- Implement auth flow connecting to `/v1/auth/login` with doctor role check
- Implement dashboard, patients (list + detail), consultations (today + upcoming + history)
- Implement profile view + edit

**Acceptance:**
- Doctor logs in, lands on dashboard
- Patient list shows doctor's panel patients only
- Cross-doctor patient access returns 404 (via API)

---

*To execute: tell Claude Code `Execute P18. Read docs/build-prompts/P18-doctor-portal-foundation.md, then plan before editing.`*
