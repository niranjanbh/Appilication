# P5 — Public Website Foundation (Next.js)

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — website section
- `docs/strategy/build-spec.md` — section 7 (public website), section 18 (phase scope)
- `.claude/skills/kyros-design-system/SKILL.md` — 10-step visual rhythm
- `.claude/skills/kyros-clinical-compliance/SKILL.md` — claim discipline, doctor approval gate
- `.claude/skills/kyros-customer-acquisition/SKILL.md` — SEO architecture

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `website/`:
- Implement home, conditions overview, 7 condition pages, how-it-works, pricing, about, advisory-board, our-doctors, for-doctors, faq, contact, legal pages (privacy, terms, telemedicine consent, data deletion)
- Apply visual rhythm 10-step pattern per kyros-design-system
- Schema markup: MedicalCondition, MedicalWebPage, Person, FAQPage, Article
- Honest startup state on About, Advisory Board, Our Doctors only
- Booking flow: condition → intake form → contact submission (no auth yet)

**Acceptance:**
- All pages render
- Lighthouse SEO score ≥ 95
- Lighthouse Performance ≥ 80 on mobile
- Schema markup validates in Google Rich Results Test
- Booking flow submits to `/v1/public/booking-inquiry`

---

*To execute: tell Claude Code `Execute P5. Read docs/build-prompts/P05-public-website-foundation.md, then plan before editing.`*
