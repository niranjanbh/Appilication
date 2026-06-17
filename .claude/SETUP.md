# Kyros — Claude Code Setup

This document describes the Claude Code configuration layered into the Kyros Platform
repository. Read it once when onboarding; refer back when adding rules or troubleshooting.

## Directory layout

```
.claude/
├── SETUP.md                        ← this file
├── settings.json                   # Tool permissions (deny-first, healthcare-appropriate)
├── settings.local.json             # Personal overrides (gitignored)
├── rules/
│   ├── security.md                 # Always-on: the 20 PHI/security non-negotiables
│   ├── backend.md                  # Triggered on backend/**/*.py
│   ├── migrations.md               # Triggered on backend/alembic/**
│   ├── admin-ui.md                 # Triggered on backend/app/adminui/**
│   ├── tests.md                    # Triggered on backend/tests/**
│   ├── frontend-mobile.md          # Triggered on mobile/**/*.{ts,tsx}
│   ├── frontend-doctor.md          # Triggered on doctor-portal/**/*.{ts,tsx}
│   └── frontend-website.md         # Triggered on website/**/*.{ts,tsx,mdx}
└── skills/
    ├── kyros-clinical-compliance/  # Clinical/regulatory guidance
    ├── kyros-design-system/        # Brand voice, tokens, visual register
    ├── kyros-business-strategy/    # Positioning, pricing, unit economics
    ├── kyros-customer-acquisition/ # D2C, social, SEO, founder content
    └── kyros-b2b2c-partnerships/   # Corporate wellness, insurance/TPA
```

## How context loads

| File / layer | When it loads |
|---|---|
| `CLAUDE.md` | Every session, automatically |
| `.claude/rules/security.md` | Every session (no `paths:` frontmatter → always on) |
| `.claude/rules/backend.md` | When Claude reads any `backend/**/*.py` |
| `.claude/rules/migrations.md` | When Claude reads `backend/alembic/**` |
| `.claude/rules/admin-ui.md` | When Claude reads `backend/app/adminui/**` |
| `.claude/rules/tests.md` | When Claude reads `backend/tests/**` |
| `.claude/rules/frontend-*.md` | When Claude reads matching frontend paths |
| `.claude/skills/*/SKILL.md` | Triggered by Claude's skill system when relevant |
| `docs/strategy/build-spec.md` | Read on demand for schema / API / prompt queue |
| `docs/strategy/backend-strategy.md` | Read on demand for backend implementation |
| `docs/strategy/frontend-strategy.md` | Read on demand for frontend implementation |
| `docs/build-prompts/P{nn}-*.md` | Read on demand for the current work unit |

This layering keeps startup context under ~5 K tokens. The heavy strategy docs (~200 KB each)
load only when their sections are actually needed — otherwise every session would burn ~100 K
tokens before any code is written.

## Executing build prompts (P1–P30+)

Start a fresh Claude Code session per prompt:

```bash
claude
# then:
> Execute P31. Read docs/build-prompts/P31-*.md, then plan before editing.
```

Claude Code will:
1. Read the prompt file (required reading + acceptance criteria).
2. Open the relevant strategy doc sections.
3. Present a plan and wait for approval.
4. Implement, run `make test`, summarize.

**One prompt = one session.** Exit with `/exit` when done; start fresh for the next prompt.

## Refreshing build prompts after a spec edit

```bash
make extract-prompts
# or directly:
python scripts/extract-build-prompts.py
```

## Adding rules

When a code review catches something Claude Code should have known, place the rule:

- **Applies to every file** → `.claude/rules/security.md` (PHI/security) or `CLAUDE.md`
  (architecture)
- **Applies to a path subtree** → matching path-scoped rule file
- **Multi-step procedure used sometimes** → new skill under `.claude/skills/`

Keep each rule file under ~100 lines. Split when it grows beyond that.

## Customising settings.json

The shipped `settings.json` uses `defaultMode: "default"` (Claude asks before unmatched
operations). After a day of use, move repeatedly approved commands to
`.claude/settings.local.json` (gitignored).

```bash
# Auto-approve edits and writes; still confirm shell commands
claude --permission-mode acceptEdits

# Read-only / plan-only mode
claude --permission-mode plan
```

## Troubleshooting

**CLAUDE.md not followed** — run `/memory` to confirm it loaded. Make instructions more
specific. Check for conflicts with other CLAUDE.md or rule files.

**Path-scoped rules not loading** — rules with `paths:` load when Claude reads a matching
file. Ask Claude to open a backend file, then check `/memory`.

**Context window filling up** — never do two build prompts per session. End with `/exit`,
start fresh. If pressure appears mid-prompt, finish the current concern, then `/compact`.

**Extraction script fails** — confirm `docs/strategy/build-spec.md` exists and has
`#### Pn — Title` section headers. Update `PROMPT_HEADER_RE` in the script if the format
changed.
