# P12 — Consultation Booking + Schema

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §5 (Postgres row locking), §10 (schema), §11 (RBAC), §12 (API), §7 (Celery video provisioning)
- `docs/strategy/build-spec.md` — section 2 (kc_consultations), section 5 (consultation lifecycle)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Alembic migration `04_consultations.py` creating `kc_consultations`, `kc_doctor_notes`, `kc_pre_consultation_reports` per Section 2
- Implement `/v1/clinic/patient/consultations/*` endpoints
- Booking flow: slot lookup → payment intent → Razorpay order → booking confirmation
- Patient sees upcoming + history

In `mobile/`:
- Implement consultations tab and booking flow per Section 9.1
- Pre-consultation questionnaire flow

**Acceptance:**
- Patient books a consultation, pays via Razorpay test mode, sees confirmation
- Doctor's availability calendar reflects the booking
- Cancellation policy enforced (refund window, no-show handling)

---

*To execute: tell Claude Code `Execute P12. Read docs/build-prompts/P12-consultation-booking-and-schema.md, then plan before editing.`*
