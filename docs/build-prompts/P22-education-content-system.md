# P22 — Education Content System

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/build-spec.md` — section 17 (education content)
- `.claude/skills/kyros-clinical-compliance/SKILL.md` — content approval, citations
- `.claude/skills/kyros-customer-acquisition/SKILL.md` — content syndication

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Alembic migration `07_education.py` creating `kc_education_content`, `kc_education_assignments` per Section 2
- Implement `/v1/admin/content/*` endpoints
- Implement `/v1/doctor/consultations/{id}/education` POST (doctor assigns content)
- Implement `/v1/clinic/patient/education/*` GET + read tracking

In `mobile/`:
- Education content viewer
- Read tracking
- Library browsable + doctor-assigned highlighted

**Acceptance:**
- Doctor assigns content during consultation
- Patient sees assigned content
- Mark-as-read updates server state

---

*To execute: tell Claude Code `Execute P22. Read docs/build-prompts/P22-education-content-system.md, then plan before editing.`*
