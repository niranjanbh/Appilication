# Kyros Claude Code Setup

This bundle contains the Claude Code configuration for the Kyros Platform repository:

```
kyros-claude-code-setup/
├── CLAUDE.md                              # Project memory, loaded every session
├── Makefile                               # All dev workflows
├── .claude/
│   ├── settings.json                      # Tool permissions (deny-first, healthcare-appropriate)
│   └── rules/                             # Path-scoped rules
│       ├── security.md                    # Always-on: the 20 non-negotiables
│       ├── backend.md                     # paths: backend/**/*.py
│       ├── migrations.md                  # paths: backend/alembic/**
│       ├── admin-ui.md                    # paths: backend/app/adminui/**
│       ├── tests.md                       # paths: backend/tests/**
│       ├── frontend-mobile.md             # paths: mobile/**/*.{ts,tsx}
│       ├── frontend-doctor.md             # paths: doctor-portal/**/*.{ts,tsx}
│       └── frontend-website.md            # paths: website/**/*.{ts,tsx,mdx}
└── scripts/
    └── extract-build-prompts.py           # P1–P30 splitter
```

## Installation

From the root of your `kyros-platform` repository:

```bash
# 1. Copy CLAUDE.md and Makefile to repo root
cp /path/to/kyros-claude-code-setup/CLAUDE.md ./
cp /path/to/kyros-claude-code-setup/Makefile ./

# 2. Copy the .claude/ directory
cp -r /path/to/kyros-claude-code-setup/.claude ./

# 3. Copy the extraction script
mkdir -p scripts
cp /path/to/kyros-claude-code-setup/scripts/extract-build-prompts.py scripts/
chmod +x scripts/extract-build-prompts.py

# 4. Place your strategy docs
mkdir -p docs/strategy
cp /path/to/kyros-build-spec.md            docs/strategy/build-spec.md
cp /path/to/backend-strategy.md      docs/strategy/backend-strategy.md
cp /path/to/kyros-app-design-strategy.md   docs/strategy/frontend-strategy.md

# 5. Place your existing skills (if you haven't already)
mkdir -p .claude/skills
# Copy each skill directory (the SKILL.md plus any companion files) under .claude/skills/

# 6. Extract the P1–P30 prompt queue into per-prompt files
python scripts/extract-build-prompts.py

# 7. Gitignore personal notes
echo "CLAUDE.local.md" >> .gitignore
echo ".claude/settings.local.json" >> .gitignore
```

You're ready. Start Claude Code in the repo root:

```bash
claude
```

Verify the setup loaded correctly:

```
> /memory
```

You should see `CLAUDE.md` and every `.claude/rules/*.md` listed, with the path-scoped rules
showing their `paths:` patterns.

## How the pieces fit together

**Loaded every session, automatically by Claude Code:**
- `CLAUDE.md` — project memory, the slim orienting document.
- `.claude/rules/security.md` — no `paths:` frontmatter, so it's always on.

**Loaded automatically when Claude Code reads matching files:**
- `.claude/rules/backend.md` triggers when editing `backend/**/*.py`.
- `.claude/rules/migrations.md` triggers when editing `backend/alembic/**`.
- `.claude/rules/admin-ui.md` triggers when editing `backend/app/adminui/**`.
- `.claude/rules/tests.md` triggers when editing `backend/tests/**`.
- `.claude/rules/frontend-mobile.md` triggers in `mobile/**/*.{ts,tsx}`.
- `.claude/rules/frontend-doctor.md` triggers in `doctor-portal/**/*.{ts,tsx}`.
- `.claude/rules/frontend-website.md` triggers in `website/**/*.{ts,tsx,mdx}`.

**Triggered by Claude Code's skill system when relevant to the prompt:**
- `.claude/skills/kyros-business-strategy/SKILL.md`
- `.claude/skills/kyros-clinical-compliance/SKILL.md`
- `.claude/skills/kyros-design-system/SKILL.md`
- `.claude/skills/kyros-customer-acquisition/SKILL.md`
- `.claude/skills/kyros-b2b2c-partnerships/SKILL.md`

**Read on demand by Claude when working on a specific task:**
- `docs/strategy/build-spec.md` — full technical spec
- `docs/strategy/backend-strategy.md` — backend implementation blueprint
- `docs/strategy/frontend-strategy.md` — frontend implementation blueprint
- `docs/build-prompts/P{nn}-*.md` — the prompt for the current work unit

This layering is intentional. Naïvely loading all three 200KB strategy docs every session
would burn ~100K tokens before any code is written. The slim `CLAUDE.md` + path-scoped rules
keep startup context under ~5K tokens; the heavy docs load only when their sections are
actually needed.

## Executing build prompts

For each Pn (P1 through P30):

```bash
claude
```

In the session:

```
> Execute P1. Read docs/build-prompts/P01-repository-scaffolding.md, then plan
> before editing.
```

Claude Code will:
1. Read the prompt file (which has required reading + acceptance criteria).
2. Open the relevant strategy doc sections.
3. Present a plan and wait for approval.
4. Implement, run `make test`, summarize.

When done, exit (`/exit`) and start a fresh session for P2. **One prompt = one session.** This
keeps context clean, reduces cross-prompt contamination, and produces consistent output.

## Refreshing prompts after a spec edit

If `docs/strategy/build-spec.md` is edited (e.g., a prompt's acceptance criteria is clarified),
re-run the extractor:

```bash
make extract-prompts
# or directly:
python scripts/extract-build-prompts.py
```

This overwrites `docs/build-prompts/*.md` with the current content. Existing files for prompts
that no longer exist are left alone (review with `git status`).

## Adding new rules

When a code review catches something Claude Code should have known, decide:

- Does this apply to **every file**? → add to `.claude/rules/security.md` (if security/PHI) or
  `CLAUDE.md` (if architectural).
- Does this apply to **a specific subtree**? → add to the corresponding path-scoped rule.
- Is this a **multi-step procedure** Claude only needs sometimes? → make it a Claude skill in
  `.claude/skills/`.

Keep each rule file under ~100 lines. When a rule file grows beyond that, split it (e.g.,
`backend.md` could split into `backend-routing.md`, `backend-data.md`, `backend-tasks.md`).

## Customizing settings.json for your workflow

The shipped `settings.json` uses `defaultMode: "default"` (Claude asks before unmatched
operations). After working for a day, you'll notice which commands you keep approving — move
those to the `allow` list in `.claude/settings.local.json` (gitignored, personal).

To run Claude Code in a more permissive mode for trusted operations:

```bash
# Auto-approve edits and writes; still ask for shell
claude --permission-mode acceptEdits
```

To run in plan-only mode (read but don't write):

```bash
claude --permission-mode plan
```

## Troubleshooting

**"My CLAUDE.md isn't being followed."**
Run `/memory` to verify it's loaded. Make instructions more specific. Look for conflicts with
other CLAUDE.md or rules files.

**"Path-scoped rules aren't loading."**
Rules with `paths:` frontmatter load when Claude reads a matching file. Ask Claude to read a
backend file, then check `/memory` — `backend.md` should appear.

**"Context window is filling up."**
Don't do multiple prompts per session. End with `/exit`, start fresh for the next prompt. If
mid-prompt context pressure appears, finish the current concern, then `/compact`.

**"The extraction script fails."**
Check that `docs/strategy/build-spec.md` exists. The script expects `#### Pn — Title` headers
(with em-dash, en-dash, or hyphen) at lines 1479–1953 of the build spec. If the spec format
changes substantially, update `PROMPT_HEADER_RE` in the script.

---

See `docs/strategy/backend-strategy.md` and `docs/strategy/frontend-strategy.md` for the full
implementation blueprints.
