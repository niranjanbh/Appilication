# P6 — Public Website Content System

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — website MDX system
- `.claude/skills/kyros-clinical-compliance/SKILL.md` — content review, citations, doctor approval
- `.claude/skills/kyros-customer-acquisition/SKILL.md` — content cadence, syndication

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `website/`:
- Implement MDX content system at `content/learn/{vertical}/{slug}.mdx`
- Frontmatter: `title`, `slug`, `vertical`, `doctor_author_id`, `doctor_reviewed_at`, `references`
- Doctor byline auto-rendered with NMC reg number
- "Medically reviewed" date stamp
- References section with bibliography component
- URL structure: `/learn/{vertical}/{slug}/`
- Static generation + ISR for content updates
- Seed 3 example articles per vertical (21 articles total, placeholder doctor authors)

**Acceptance:**
- Articles render with byline, review date, references
- Sitemap.xml auto-generated
- Each article emits Article schema with Person (doctor) authorship

---

*To execute: tell Claude Code `Execute P6. Read docs/build-prompts/P06-public-website-content-system.md, then plan before editing.`*
