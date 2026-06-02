# P4 — Design Token Distribution

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — design tokens distribution
- `.claude/skills/kyros-design-system/SKILL.md` — primitives, color tokens, typography
- `docs/strategy/build-spec.md` — section 7 (public website), section 8 (mobile)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

Convert `design-tokens/tokens.json` into:
- `mobile/lib/design-tokens.ts` (typed export)
- `doctor-portal/src/design-tokens.ts`
- `website/lib/design-tokens.ts`
- Tailwind config preset shared across all three frontends in `design-tokens/tailwind-preset.js`

Implement base primitives in each frontend per kyros-design-system: Button (Forest, Saffron, Outline, Ghost), Card (white-on-ivory, ivory-on-peach-mist), PullQuote (italic Cormorant, terracotta/saffron border), Stat, Tag.

**Acceptance:**
- All three frontends render a Storybook/showcase page demonstrating each primitive
- Color values trace to `tokens.json` (no hex literals in component code)
- Cormorant Garamond + DM Sans + Tiro Devanagari Hindi load correctly

---

*To execute: tell Claude Code `Execute P4. Read docs/build-prompts/P04-design-token-distribution.md, then plan before editing.`*
