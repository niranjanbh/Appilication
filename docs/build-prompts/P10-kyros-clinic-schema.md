# P10 — Kyros Clinic Schema (Patients, Doctors, Coordinators)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §10 (schema impl, kc_ + dr_ + ad_ tables), §11 (RBAC scoping)
- `docs/strategy/build-spec.md` — section 2 (kc_, dr_, ad_ schema)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Alembic migration `03_clinic_domain.py` creating `kc_patients`, `dr_doctors`, `dr_availability`, `dr_credentials`, `ad_coordinators` per Section 2
- Implement `app/db/models/clinic.py`, `app/db/models/doctor.py`, `app/db/models/coordinator.py`
- Seed development data: 3 demo doctors (different specialties), 1 coordinator, 5 demo patients

**Acceptance:**
- `alembic upgrade head` runs cleanly
- Seed data loads via `python -m scripts.seed_demo`
- Patient ↔ user 1:1 relationship enforced
- Doctor NMC registration number uniqueness enforced

---

*To execute: tell Claude Code `Execute P10. Read docs/build-prompts/P10-kyros-clinic-schema.md, then plan before editing.`*
