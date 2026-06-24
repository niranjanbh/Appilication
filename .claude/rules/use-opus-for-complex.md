# Use Opus for Complex Tasks

When spawning subagents for complex, multi-step, or quality-critical work, use `model: "opus"`.

## What counts as complex

- Multi-file implementation or refactoring (3+ files)
- Architecture planning or design decisions
- Build prompt execution (P1-P30)
- Security-sensitive changes (auth, PHI, encryption)
- Database schema design or migration planning
- Full-stack feature implementation
- Debugging issues that span multiple layers (frontend + backend + infra)
- Code review of large diffs

## What stays on the default model

- Single-file edits or small bug fixes
- Code lookups, grep, file searches
- Simple Q&A or explanation requests
- Formatting, linting, or mechanical changes

## Rules

1. **Default to Opus for complex subagents.** Pass `model: "opus"` when spawning Agent for any
   task listed above.
2. **Ask before switching dynamically.** If uncertain whether a task warrants Opus, ask the user
   before spawning.
3. **Never downgrade mid-task.** If a task started on Opus, finish it on Opus.
