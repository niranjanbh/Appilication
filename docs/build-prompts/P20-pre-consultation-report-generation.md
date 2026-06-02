# P20 — Pre-Consultation Report Generation

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §7 (report tasks queue, T-24h cron), §13 (PDF generation)
- `docs/strategy/build-spec.md` — section 16 (pre-consultation report generation)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Implement Celery task `generate_pre_consultation_report(consultation_id)` per Section 16
- Scheduled at T-24h via celery-beat
- PDF rendered via WeasyPrint, stored in S3
- Both patient and doctor endpoints to fetch

In `mobile/`:
- Implement pre-consultation report view screen (read-only)
- Surface low-confidence OCR fields for review

In `doctor-portal/`:
- Implement pre-consultation report view (editable doctor prep notes)
- Patient and doctor see identical content (per locked product principle)

**Acceptance:**
- Report generated within 5s
- PDF accessible to both patient and doctor
- Doctor edits prep notes; patient does not see edit
- Information symmetry verified: lab summary, adherence, wearable summary identical

---

*To execute: tell Claude Code `Execute P20. Read docs/build-prompts/P20-pre-consultation-report-generation.md, then plan before editing.`*
