# P21 — Notification Stack (Expo Push + WhatsApp + Email)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §7 (notification queue)
- `docs/strategy/build-spec.md` — section 11 (notifications)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Implement `app/services/notifications.py` with dispatchers for Expo Push, WhatsApp (via AiSensy/Wati), Email (via SendGrid)
- Notification templates: appointment confirmation, reminder, medication reminder, lab result, pre-consultation report ready
- WhatsApp utility templates submitted for Meta approval (placeholder in code; submission process documented)
- Push notifications use generic language (per Section 9.8)

**Acceptance:**
- Appointment confirmation fires to all 3 channels
- WhatsApp message delivery via test number works
- Push notifications appear on physical device
- No condition names in push text

---

*To execute: tell Claude Code `Execute P21. Read docs/build-prompts/P21-notification-stack.md, then plan before editing.`*
