# P24 — Doctor Portal Polish (Schedule, Profile, Lab Review)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — doctor portal — schedule, profile, lab review
- `docs/strategy/build-spec.md` — section 9 (doctor portal)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `doctor-portal/`:
- Implement schedule management (availability CRUD, buffer time settings, duration preferences)
- Implement lab review interface: annotate biomarkers, flag for patient attention
- Implement profile management (NMC reg # read-only, specialty edit, bank details with verification)

**Acceptance:**
- Doctor adds 20 availability slots; patient booking sees them
- Doctor annotates a biomarker; patient sees annotation on next view
- Bank details edit triggers verification email to super admin

---

*To execute: tell Claude Code `Execute P24. Read docs/build-prompts/P24-doctor-portal-polish.md, then plan before editing.`*
