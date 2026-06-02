# P1 — Repository Scaffolding

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §1 (north star), §2 (repo structure), §4 (Docker), §9 (bootstrap)
- `docs/strategy/frontend-strategy.md` — monorepo + design tokens sections
- `.claude/skills/kyros-design-system/SKILL.md` — design tokens, color palette

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

Create the repository structure described in Section 1. Initialize:
- `backend/` with FastAPI 0.115, SQLAlchemy 2.0 async, Pydantic v2, Alembic, ruff, mypy strict, pytest
- `mobile/` with Expo 51 + TypeScript strict + expo-router
- `doctor-portal/` with Vite + React 18 + TypeScript strict + Tailwind
- `website/` with Next.js 14 App Router + TypeScript + Tailwind
- `design-tokens/` with `tokens.json` containing the locked palette and typography (per kyros-design-system)

**Acceptance:**
- `cd backend && uv sync && pytest` runs (zero tests OK)
- `cd mobile && pnpm install && pnpm typecheck` passes
- `cd doctor-portal && pnpm install && pnpm typecheck && pnpm build` passes
- `cd website && pnpm install && pnpm typecheck && pnpm build` passes
- Tailwind configs in all three frontends consume `design-tokens/tokens.json`

---

*To execute: tell Claude Code `Execute P1. Read docs/build-prompts/P01-repository-scaffolding.md, then plan before editing.`*
