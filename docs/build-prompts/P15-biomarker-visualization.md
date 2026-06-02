# P15 — Biomarker Visualization

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — biomarker visualization components
- `docs/strategy/build-spec.md` — section 6 (biomarker visualization)
- `.claude/skills/kyros-design-system/SKILL.md` — data viz patterns

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `mobile/`:
- Implement biomarker trend chart at `app/biomarkers/[name].tsx` using Victory Native XL
- Reference range bands (sage tint normal, saffron warning, alert red critical)
- 7d/30d/90d/1y/all toggle
- "Better / steady / worse" trend indicator with subtle animation
- Tap point → consultation linkage if applicable

In `backend/`:
- Implement `/v1/clinic/patient/biomarker-trends/{biomarker}` endpoint
- Aggregates values from `kc_lab_reports.parsed_json` across patient's history

**Acceptance:**
- Chart renders at 60fps on Redmi Note 11 (mid-range Android test device)
- Reference range bands visually distinct
- Trend indicator matches mathematical direction of change

---

*To execute: tell Claude Code `Execute P15. Read docs/build-prompts/P15-biomarker-visualization.md, then plan before editing.`*
