# P23 — Patient Web Portal (RNW)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — patient web portal (RN Web) section
- `docs/strategy/build-spec.md` — section 8 (mobile + web portal)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `mobile/`:
- Configure React Native Web in Expo project
- Verify ~85% component reuse across mobile + web
- Web-specific: sidebar navigation (desktop), hover tooltips on charts, drag-and-drop file upload, print views

Deploy patient web portal to `app.kyros.clinic` subdomain.

**Acceptance:**
- Identical features available on mobile + web
- Lighthouse Performance ≥ 80 on responsive web
- File upload via drag-and-drop on desktop
- Print view for prescription PDFs

---

*To execute: tell Claude Code `Execute P23. Read docs/build-prompts/P23-patient-web-portal.md, then plan before editing.`*
