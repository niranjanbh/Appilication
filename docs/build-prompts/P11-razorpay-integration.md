# P11 — Razorpay Integration

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §7 (Celery payments queue), §6 (Redis idempotency), §13 (file storage for invoices)
- `docs/strategy/build-spec.md` — section 13 (payment flows)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Implement `app/integrations/razorpay.py` for order creation, payment capture, refund, GST invoicing
- Implement `kc_payments` table per Section 2
- Webhook endpoint `/v1/webhooks/razorpay` with signature verification
- RBI e-mandate flow for subscription billing (annual programs)

**Acceptance:**
- Test mode order creation works
- Webhook signature verification rejects tampered payloads
- Refund initiates and completes within Razorpay test mode
- GST invoice URL generated per successful payment

---

*To execute: tell Claude Code `Execute P11. Read docs/build-prompts/P11-razorpay-integration.md, then plan before editing.`*
