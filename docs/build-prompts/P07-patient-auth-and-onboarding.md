# P7 — Patient Auth + Onboarding (Mobile)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — patient mobile section
- `docs/strategy/backend-strategy.md` — §11 (auth + RBAC), §12 (API organization)
- `docs/strategy/build-spec.md` — section 8 (mobile)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `mobile/`:
- Implement (auth) routes: login, signup, verify-otp
- Implement (onboarding) routes: welcome, conditions, intake-form, consent, health-sync
- Connect to backend `/v1/auth/*` endpoints
- DPDP consent capture flow (every consent dialog records version + hash)
- HealthKit/Health Connect permission flow (per Section 7)

**Acceptance:**
- Fresh install → onboarding completes → tab navigation visible
- Consent decisions persist server-side via `/v1/users/me/consent`
- HealthKit/Health Connect permissions visible in device settings post-grant

---

*To execute: tell Claude Code `Execute P7. Read docs/build-prompts/P07-patient-auth-and-onboarding.md, then plan before editing.`*
