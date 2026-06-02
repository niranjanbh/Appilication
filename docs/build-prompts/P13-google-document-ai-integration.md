# P13 — Google Document AI Integration

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §7 (Celery OCR queue), §13 (file storage)
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
- Implement `app/integrations/document_ai.py` calling Healthcare Document Parser in `asia-south1` region
- Service account credentials via AWS Secrets Manager
- Confidence thresholding logic per Section 5

**Acceptance:**
- Test lab PDF processed end-to-end within 60s
- Parsed JSON shape matches Section 5 specification
- Low-confidence fields flagged

---

*To execute: tell Claude Code `Execute P13. Read docs/build-prompts/P13-google-document-ai-integration.md, then plan before editing.`*
