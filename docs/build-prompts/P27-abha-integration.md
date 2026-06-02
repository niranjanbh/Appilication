# P27 — ABHA Integration (M1)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/build-spec.md` — section 14 (ABHA integration approach)
- `.claude/skills/kyros-clinical-compliance/SKILL.md` — ABDM, ABHA

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Implement `app/integrations/abha.py` for sandbox API (sandbox.abdm.gov.in)
- Register Kyros as Health Information User (HIU) in sandbox
- Implement ABHA number verification flow
- Implement ABHA number creation flow (Aadhaar OTP)

In `mobile/`:
- ABHA linking screen in onboarding (optional)
- ABHA linking accessible from profile settings

**Acceptance:**
- Patient enters existing ABHA number → verified via sandbox
- Patient creates new ABHA number via Aadhaar OTP → linked to Kyros profile
- ABHA number persisted to `kc_patients.abha_number`

---

*To execute: tell Claude Code `Execute P27. Read docs/build-prompts/P27-abha-integration.md, then plan before editing.`*
