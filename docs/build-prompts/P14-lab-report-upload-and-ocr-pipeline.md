# P14 — Lab Report Upload + OCR Pipeline

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §7 (Celery OCR), §13 (signed upload pattern), §12 (idempotency)
- `docs/strategy/build-spec.md` — section 6 (lab report OCR pipeline)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Alembic migration `05_lab_reports.py` creating `kc_lab_orders`, `kc_lab_reports` per Section 2
- Implement `/v1/clinic/patient/lab-reports/*` endpoints
- Celery task `parse_lab_report(report_id)` per Section 5
- S3 storage in ap-south-1 with KMS encryption
- PATCH endpoint for OCR correction

In `mobile/`:
- Lab reports upload screen (camera + PDF picker)
- OCR processing indicator
- Manual correction interface

**Acceptance:**
- Patient uploads a lab PDF; OCR processes within 60s
- Patient corrects an OCR error; correction persists
- Confidence < 0.60 fields require correction before save

---

*To execute: tell Claude Code `Execute P14. Read docs/build-prompts/P14-lab-report-upload-and-ocr-pipeline.md, then plan before editing.`*
