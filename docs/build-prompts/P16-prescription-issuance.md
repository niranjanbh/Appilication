# P16 — Prescription Issuance (Doctor + Patient)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §10 (append-only versioning), §11 (RBAC, draft prescriptions), §13 (PDF generation)
- `docs/strategy/frontend-strategy.md` — doctor portal prescription writer
- `docs/strategy/build-spec.md` — section 2 (kc_prescriptions), section 5 (prescription flow)
- `.claude/skills/kyros-clinical-compliance/SKILL.md` — prescription RMP signing

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Alembic migration `06_prescriptions.py` creating `kc_prescriptions`, `kc_prescription_items` per Section 2
- Implement `/v1/doctor/consultations/{id}/prescription` POST
- Implement `/v1/doctor/prescriptions/{id}/sign` POST
- Implement `/v1/clinic/patient/prescriptions/*` GET endpoints
- PDF generation via WeasyPrint (IMC format)

In `mobile/`:
- Prescription list screen
- Prescription detail with PDF download
- Dosage change tracking visualization

**Acceptance:**
- Doctor creates prescription (via doctor portal in later prompt, stub for now)
- Patient sees prescription post-signing
- PDF renders with NMC reg number, drug generic name, dosage, frequency, duration

---

*To execute: tell Claude Code `Execute P16. Read docs/build-prompts/P16-prescription-issuance.md, then plan before editing.`*
