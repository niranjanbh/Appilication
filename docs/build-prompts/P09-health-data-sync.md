# P9 — Health Data Sync (Mobile + Backend)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — patient mobile, health sync
- `docs/strategy/backend-strategy.md` — §5 (Postgres partitioning for wn_health_datapoints)
- `docs/strategy/build-spec.md` — section 12 (health data sync)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `mobile/`:
- Integrate `@kingstinct/react-native-healthkit` (iOS) and `react-native-health-connect` (Android)
- Background sync every 4 hours via Background Tasks (iOS) / WorkManager (Android)
- Last 7 days of data fetched per sync
- Batched POST to `/v1/wellness/health-sync`

In `backend/`:
- Implement `/v1/wellness/health-sync` POST endpoint
- Idempotent on `(user_id, source, source_record_id)`
- Refuse sync if consent revoked

**Acceptance:**
- Physical iPhone (custom dev client) syncs steps + heart rate
- Physical Android (Health Connect installed) syncs equivalent
- Re-syncing same datapoint is no-op
- Revoked consent returns 403

---

*To execute: tell Claude Code `Execute P9. Read docs/build-prompts/P09-health-data-sync.md, then plan before editing.`*
