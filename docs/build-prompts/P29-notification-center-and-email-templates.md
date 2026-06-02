# P29 — Notification Center + Email Templates

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §7 (notification queue), §13 (templates)
- `.claude/skills/kyros-design-system/SKILL.md` — email template visual register
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
- Implement notification center: in-app inbox of all notifications sent to patient
- Email templates rendered with kyros-design-system tokens
- WhatsApp utility templates documented and ready for Meta approval submission

In `mobile/`:
- Notification center screen
- Notification preferences

**Acceptance:**
- Patient sees all notifications received in chronological order
- Email templates render correctly in Gmail, Outlook, Apple Mail
- WhatsApp template approval documentation complete

---

*To execute: tell Claude Code `Execute P29. Read docs/build-prompts/P29-notification-center-and-email-templates.md, then plan before editing.`*
