# P28 — Analytics + Reporting

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §14 (observability), §7 (analytics rollup task)
- `docs/strategy/build-spec.md` — section 10 (analytics)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Implement `/v1/admin/analytics/*` endpoints
- Acquisition funnel: website visitors → assessments → bookings → completions
- Cohort retention: patients returning for follow-up vs churned
- Doctor utilization: consultations per doctor per week
- Condition mix: distribution across 7 verticals
- Revenue by condition, doctor, time period
- CSV export

In `backend/admin_ui/`:
- Analytics dashboards in super admin portal

**Acceptance:**
- Funnel data populated from `ad_audit_log` + booking events
- Retention chart shows 30/60/90 day cohort behavior
- CSV export downloads any table within 10s for 10K-row datasets

---

*To execute: tell Claude Code `Execute P28. Read docs/build-prompts/P28-analytics-and-reporting.md, then plan before editing.`*
