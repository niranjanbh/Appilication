# P8 — Wellness Domain Schema + Reminders

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §5 (Postgres), §10 (schema impl), §7 (Celery for reminders)
- `docs/strategy/build-spec.md` — section 2 (wellness domain schema), section 11 (reminders)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Alembic migration `02_wellness_domain.py` creating `wn_reminders`, `wn_reminder_logs`, `wn_health_sync_sessions`, `wn_health_datapoints` (partitioned monthly) per Section 2
- Implement `/v1/wellness/reminders/*` endpoints
- Implement `/v1/wellness/reminders/{id}/log` for adherence tracking

In `mobile/`:
- Implement reminders tab: list, create, edit, delete
- Local notification scheduling via `expo-notifications`
- Tap notification → adherence logging dialog (taken/skipped/snoozed)

**Acceptance:**
- Patient creates a reminder; notification fires at scheduled time
- Tapping notification logs adherence to backend
- Reminder list shows adherence rate per reminder

---

*To execute: tell Claude Code `Execute P8. Read docs/build-prompts/P08-wellness-domain-schema-and-reminders.md, then plan before editing.`*
