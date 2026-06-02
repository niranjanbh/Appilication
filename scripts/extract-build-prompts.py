#!/usr/bin/env python3
"""
extract-build-prompts.py

Splits the P1–P30 Claude Code Prompt Queue out of `docs/strategy/build-spec.md` into
individual per-prompt files at `docs/build-prompts/P{nn}-{slug}.md`. Each file includes:

  * The prompt number and title
  * Required-reading suggestions (heuristic, based on prompt subject)
  * The original prompt body verbatim

Idempotent: re-running overwrites the output files cleanly. Existing files in
`docs/build-prompts/` that don't correspond to a current prompt are left alone (you can
diff against git to see what changed).

Run from repo root:
    python scripts/extract-build-prompts.py

Or pass paths explicitly:
    python scripts/extract-build-prompts.py --spec docs/strategy/build-spec.md \
                                            --out  docs/build-prompts
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

# ───────────────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────────────

# Heuristic: which strategy doc sections each prompt should consult.
# Keys are prompt numbers. Values are lists of (doc, "section or range") tuples.
# Add to this as new prompts are introduced.
PROMPT_READING: dict[int, list[tuple[str, str]]] = {
    1: [
        ("docs/strategy/backend-strategy.md", "§1 (north star), §2 (repo structure), §4 (Docker), §9 (bootstrap)"),
        ("docs/strategy/frontend-strategy.md", "monorepo + design tokens sections"),
        (".claude/skills/kyros-design-system/SKILL.md", "design tokens, color palette"),
    ],
    2: [
        ("docs/strategy/backend-strategy.md", "§3 (FastAPI), §5 (Postgres), §10 (schema impl), §11 (auth + RBAC)"),
        ("docs/strategy/build-spec.md", "section 2 (database schema, users + identity)"),
        (".claude/rules/security.md", "auth + secret rules"),
    ],
    3: [
        ("docs/strategy/backend-strategy.md", "§11 (auth + RBAC), §12 (API organization)"),
        ("docs/strategy/build-spec.md", "section 4 (RBAC), section 15 (DPDP)"),
        (".claude/skills/kyros-clinical-compliance/SKILL.md", "consent, DPDP rules"),
    ],
    4: [
        ("docs/strategy/frontend-strategy.md", "design tokens distribution"),
        (".claude/skills/kyros-design-system/SKILL.md", "primitives, color tokens, typography"),
        ("docs/strategy/build-spec.md", "section 7 (public website), section 8 (mobile)"),
    ],
    5: [
        ("docs/strategy/frontend-strategy.md", "website section"),
        ("docs/strategy/build-spec.md", "section 7 (public website), section 18 (phase scope)"),
        (".claude/skills/kyros-design-system/SKILL.md", "10-step visual rhythm"),
        (".claude/skills/kyros-clinical-compliance/SKILL.md", "claim discipline, doctor approval gate"),
        (".claude/skills/kyros-customer-acquisition/SKILL.md", "SEO architecture"),
    ],
    6: [
        ("docs/strategy/frontend-strategy.md", "website MDX system"),
        (".claude/skills/kyros-clinical-compliance/SKILL.md", "content review, citations, doctor approval"),
        (".claude/skills/kyros-customer-acquisition/SKILL.md", "content cadence, syndication"),
    ],
    7: [
        ("docs/strategy/frontend-strategy.md", "patient mobile section"),
        ("docs/strategy/backend-strategy.md", "§11 (auth + RBAC), §12 (API organization)"),
        ("docs/strategy/build-spec.md", "section 8 (mobile)"),
    ],
    8: [
        ("docs/strategy/backend-strategy.md", "§5 (Postgres), §10 (schema impl), §7 (Celery for reminders)"),
        ("docs/strategy/build-spec.md", "section 2 (wellness domain schema), section 11 (reminders)"),
    ],
    9: [
        ("docs/strategy/frontend-strategy.md", "patient mobile, health sync"),
        ("docs/strategy/backend-strategy.md", "§5 (Postgres partitioning for wn_health_datapoints)"),
        ("docs/strategy/build-spec.md", "section 12 (health data sync)"),
    ],
    10: [
        ("docs/strategy/backend-strategy.md", "§10 (schema impl, kc_ + dr_ + ad_ tables), §11 (RBAC scoping)"),
        ("docs/strategy/build-spec.md", "section 2 (kc_, dr_, ad_ schema)"),
    ],
    11: [
        ("docs/strategy/backend-strategy.md", "§7 (Celery payments queue), §6 (Redis idempotency), §13 (file storage for invoices)"),
        ("docs/strategy/build-spec.md", "section 13 (payment flows)"),
    ],
    12: [
        ("docs/strategy/backend-strategy.md", "§5 (Postgres row locking), §10 (schema), §11 (RBAC), §12 (API), §7 (Celery video provisioning)"),
        ("docs/strategy/build-spec.md", "section 2 (kc_consultations), section 5 (consultation lifecycle)"),
    ],
    13: [
        ("docs/strategy/backend-strategy.md", "§7 (Celery OCR queue), §13 (file storage)"),
        ("docs/strategy/build-spec.md", "section 6 (lab report OCR pipeline)"),
    ],
    14: [
        ("docs/strategy/backend-strategy.md", "§7 (Celery OCR), §13 (signed upload pattern), §12 (idempotency)"),
        ("docs/strategy/build-spec.md", "section 6 (lab report OCR pipeline)"),
    ],
    15: [
        ("docs/strategy/frontend-strategy.md", "biomarker visualization components"),
        ("docs/strategy/build-spec.md", "section 6 (biomarker visualization)"),
        (".claude/skills/kyros-design-system/SKILL.md", "data viz patterns"),
    ],
    16: [
        ("docs/strategy/backend-strategy.md", "§10 (append-only versioning), §11 (RBAC, draft prescriptions), §13 (PDF generation)"),
        ("docs/strategy/frontend-strategy.md", "doctor portal prescription writer"),
        ("docs/strategy/build-spec.md", "section 2 (kc_prescriptions), section 5 (prescription flow)"),
        (".claude/skills/kyros-clinical-compliance/SKILL.md", "prescription RMP signing"),
    ],
    17: [
        ("docs/strategy/backend-strategy.md", "§7 (Celery video provisioning), §6 (Redis locks)"),
        ("docs/strategy/build-spec.md", "section 5 (video consultation)"),
    ],
    18: [
        ("docs/strategy/frontend-strategy.md", "doctor portal section"),
        ("docs/strategy/build-spec.md", "section 9 (doctor portal)"),
        (".claude/skills/kyros-design-system/SKILL.md", "doctor portal visual register"),
    ],
    19: [
        ("docs/strategy/frontend-strategy.md", "doctor portal consultation room"),
        ("docs/strategy/backend-strategy.md", "§10 (kc_doctor_notes), §11 (doctor scoping)"),
        ("docs/strategy/build-spec.md", "section 9 (consultation view, notes)"),
    ],
    20: [
        ("docs/strategy/backend-strategy.md", "§7 (report tasks queue, T-24h cron), §13 (PDF generation)"),
        ("docs/strategy/build-spec.md", "section 16 (pre-consultation report generation)"),
    ],
    21: [
        ("docs/strategy/backend-strategy.md", "§7 (notification queue)"),
        ("docs/strategy/build-spec.md", "section 11 (notifications)"),
    ],
    22: [
        ("docs/strategy/build-spec.md", "section 17 (education content)"),
        (".claude/skills/kyros-clinical-compliance/SKILL.md", "content approval, citations"),
        (".claude/skills/kyros-customer-acquisition/SKILL.md", "content syndication"),
    ],
    23: [
        ("docs/strategy/frontend-strategy.md", "patient web portal (RN Web) section"),
        ("docs/strategy/build-spec.md", "section 8 (mobile + web portal)"),
    ],
    24: [
        ("docs/strategy/frontend-strategy.md", "doctor portal — schedule, profile, lab review"),
        ("docs/strategy/build-spec.md", "section 9 (doctor portal)"),
    ],
    25: [
        ("docs/strategy/backend-strategy.md", "§3 (admin UI mounting), §11 (admin scoping)"),
        (".claude/rules/admin-ui.md", "Jinja2 + HTMX patterns"),
        ("docs/strategy/build-spec.md", "section 10 (super admin portal)"),
    ],
    26: [
        ("docs/strategy/backend-strategy.md", "§3 (admin UI), §11 (coordinator scoping, clinical content stripping)"),
        (".claude/rules/admin-ui.md", "coordinator UI rules"),
        ("docs/strategy/build-spec.md", "section 10 (care coordinator portal)"),
    ],
    27: [
        ("docs/strategy/build-spec.md", "section 14 (ABHA integration approach)"),
        (".claude/skills/kyros-clinical-compliance/SKILL.md", "ABDM, ABHA"),
    ],
    28: [
        ("docs/strategy/backend-strategy.md", "§14 (observability), §7 (analytics rollup task)"),
        ("docs/strategy/build-spec.md", "section 10 (analytics)"),
    ],
    29: [
        ("docs/strategy/backend-strategy.md", "§7 (notification queue), §13 (templates)"),
        (".claude/skills/kyros-design-system/SKILL.md", "email template visual register"),
        ("docs/strategy/build-spec.md", "section 11 (notifications)"),
    ],
    30: [
        ("docs/strategy/backend-strategy.md", "§14 (observability), §16 (phased deployment)"),
        ("docs/strategy/build-spec.md", "section 14 (infrastructure plan)"),
    ],
}


# ───────────────────────────────────────────────────────────────────────────────
# Parsing
# ───────────────────────────────────────────────────────────────────────────────

PROMPT_HEADER_RE = re.compile(r"^####\s+P(\d+)\s+[—–-]\s+(.+?)\s*$")
# Stop when we hit any header at level #### or shallower OUTSIDE the prompt queue
STOP_HEADER_RE = re.compile(r"^(#{1,3}\s+|#### (?!P\d+\s+[—–-]))")


class Prompt(NamedTuple):
    number: int
    title: str
    body: str  # markdown body, no header


def parse_prompts(spec_text: str) -> list[Prompt]:
    lines = spec_text.splitlines()
    prompts: list[Prompt] = []
    i = 0
    while i < len(lines):
        m = PROMPT_HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        number = int(m.group(1))
        title = m.group(2).strip()
        # Collect body until next prompt header or any higher-level header
        body_lines: list[str] = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if PROMPT_HEADER_RE.match(nxt):
                break
            # Stop at any ## or ### header (we've left the prompt queue subsection)
            if re.match(r"^##\s+\S", nxt) or re.match(r"^###\s+\S", nxt):
                break
            body_lines.append(nxt)
            j += 1
        # Trim trailing blank lines
        while body_lines and body_lines[-1].strip() == "":
            body_lines.pop()
        prompts.append(Prompt(number, title, "\n".join(body_lines).strip()))
        i = j
    return prompts


# ───────────────────────────────────────────────────────────────────────────────
# Slug + file name
# ───────────────────────────────────────────────────────────────────────────────

def slugify(title: str) -> str:
    """Convert a prompt title to a filesystem-safe slug."""
    # Replace + with "and"
    s = title.lower().replace("+", " and ")
    # Strip parenthetical asides like "(Mobile)"
    s = re.sub(r"\([^)]*\)", " ", s)
    # Replace any non-alphanumeric run with a single hyphen
    s = re.sub(r"[^a-z0-9]+", "-", s)
    # Collapse multiple hyphens
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def filename_for(prompt: Prompt) -> str:
    return f"P{prompt.number:02d}-{slugify(prompt.title)}.md"


# ───────────────────────────────────────────────────────────────────────────────
# Rendering
# ───────────────────────────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """\
# P{n} — {title}

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

{reading_block}

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

{body}

---

*To execute: tell Claude Code `Execute P{n}. Read docs/build-prompts/{filename}, then plan before editing.`*
"""

DEFAULT_READING = [
    ("docs/strategy/build-spec.md", "the section this prompt belongs to"),
    ("docs/strategy/backend-strategy.md", "the architectural section most relevant"),
    (".claude/skills/kyros-clinical-compliance/SKILL.md", "if PHI or clinical content is involved"),
]


def render_reading_block(n: int) -> str:
    items = PROMPT_READING.get(n, DEFAULT_READING)
    return "\n".join(f"- `{path}` — {what}" for path, what in items)


def render_prompt(prompt: Prompt) -> str:
    return PROMPT_TEMPLATE.format(
        n=prompt.number,
        title=prompt.title,
        reading_block=render_reading_block(prompt.number),
        body=prompt.body,
        filename=filename_for(prompt),
    )


# ───────────────────────────────────────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Extract P1–P30 prompts from the Kyros build spec.")
    parser.add_argument("--spec", type=Path, default=Path("docs/strategy/build-spec.md"))
    parser.add_argument("--out", type=Path, default=Path("docs/build-prompts"))
    parser.add_argument("--dry-run", action="store_true", help="Print what would be written; don't write.")
    args = parser.parse_args()

    if not args.spec.exists():
        print(f"ERROR: build spec not found at {args.spec}", file=sys.stderr)
        return 1

    spec_text = args.spec.read_text(encoding="utf-8")
    prompts = parse_prompts(spec_text)

    if not prompts:
        print(f"ERROR: no prompts (#### Pn — Title) found in {args.spec}", file=sys.stderr)
        return 1

    expected = set(range(1, 31))
    found = {p.number for p in prompts}
    missing = sorted(expected - found)
    extra = sorted(found - expected)
    if missing:
        print(f"WARNING: prompts missing from spec: {missing}", file=sys.stderr)
    if extra:
        print(f"NOTE: prompts beyond P30 present: {extra}", file=sys.stderr)

    args.out.mkdir(parents=True, exist_ok=True)

    for prompt in sorted(prompts, key=lambda p: p.number):
        target = args.out / filename_for(prompt)
        content = render_prompt(prompt)
        if args.dry_run:
            print(f"would write: {target} ({len(content)} bytes)")
        else:
            target.write_text(content, encoding="utf-8")
            print(f"wrote: {target}")

    print(f"\nDone. {len(prompts)} prompts processed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
