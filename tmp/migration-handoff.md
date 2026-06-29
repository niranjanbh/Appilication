# Migration Handoff — Consultation `book` path fix

**Created:** 2026-06-26
**Branch:** dev
**Why this file exists:** This laptop applied code-only changes that need NO migration. A
related improvement (Part 3 below) DOES need a database migration. Per our working rule we do
**not** run migrations on this machine — they are performed on the migration laptop. This file
tells the next Claude session (on the other laptop) exactly what to do.

---

## Working rule for migrations (follow this every time)

When a change is requested:

1. **If it does NOT require a DB migration** (code only — routes, services, repos that don't
   change columns/enums/indexes, frontend, config): **apply it here and continue.**
2. **If it DOES require a migration** (new/changed column, enum, index, constraint, table):
   **STOP before generating/applying the migration.** Apply any safe code-only parts, then
   append a section to this file (`tmp/migration-handoff.md`) describing:
   - the exact model/schema change,
   - the migration command to run,
   - what to review in the generated migration,
   - how to apply it (`make migrate`, never auto-run),
   - the follow-up code/next steps that depend on the migrated schema.
3. Commit the code + this file so the migration laptop picks it up via git.
4. **Lifecycle:** these handoff notes live in `tmp/` only while pending. Once the migration is
   applied, tested, and committed on the migration laptop, **delete the handoff file** (here,
   `tmp/migration-handoff.md`) in that same commit. The note is a baton, not a record — git
   history keeps the permanent trail.

The schema-head check refuses to serve traffic against an outdated schema, so the app on THIS
laptop will keep working on the old schema until the migration laptop applies the change and
this laptop pulls.

---

## ✅ Already applied on this laptop (NO migration — done)

### Part 1 — `book` consultations are now explicitly zero-fee
- **File:** `backend/app/adminui/views/coord/scheduling.py`, `book_consultation()`
- **Change:** removed the `pricing_service.get_consultation_fee_paise(...)` lookup; now passes
  `consultation_fee_paise=0` to `coord_repo.book_consultation_for_patient`.
- **Why:** coordinator-"booked" consults create no Razorpay order (`payment_id` stays NULL) and
  are already excluded from revenue analytics by the payment join. Storing a real fee showed a
  phantom charge in the patient app that nothing ever collects. A fee-bearing booking still goes
  through the patient-request → assign flow.

### Part 2 — Patient app shows "Complimentary" for a ₹0 fee
- **File:** `mobile/app/consultations/[id].tsx` (Fee row in the details card)
- **Change:** when `consultation_fee_paise === 0`, render `Complimentary` instead of `₹0`.

**Neither part touches the schema. Safe to commit and run as-is.**

---

## ⏳ PENDING on the migration laptop — Part 3: `booking_source` column

This is the OPTIONAL analytics-segmentation marker. It adds a column, so it must be migrated.
Do NOT do this on the non-migration laptop.

### What Claude should do on the OTHER (migration) laptop

**Step 0 — sync first**
```bash
git pull            # pick up Parts 1+2 and this file
make dev            # bring the stack up (Postgres, backend)
```

**Step 1 — edit the model**
`backend/app/models/clinic.py`, in `class Consultation`, after the `coordinator_id` column
(~line 149), add:
```python
    # How the consultation entered the system. Drives revenue segmentation:
    # 'coordinator_booked' and 'on_demand' are complimentary (no order); only
    # 'patient_request' carries a paid Razorpay order through the assign flow.
    booking_source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'patient_request'")
    )
```
(`String` and `text` are already imported in that file.)

**Step 2 — set the marker at each entry point** in `backend/app/repositories/`:
- `coordinator_portal.py` → `book_consultation_for_patient`: set `booking_source="coordinator_booked"`
  on the `Consultation(...)` constructor.
- `consultations.py` → `create_adhoc_consultation` (on-demand): set `booking_source="on_demand"`.
- `consultations.py` → `create_consultation_request`: leave default (`patient_request`).

**Step 3 — generate the migration (autogenerate)**
```bash
make migrate-create     # name it e.g. add_booking_source_to_consultations
```

**Step 4 — REVIEW the generated migration before applying.** It must contain only:
```python
def upgrade() -> None:
    op.add_column(
        "kc_consultations",
        sa.Column("booking_source", sa.String(length=30),
                  server_default=sa.text("'patient_request'"), nullable=False),
    )

def downgrade() -> None:
    op.drop_column("kc_consultations", "booking_source")
```
- Confirm autogenerate did NOT pick up unrelated drift (drop columns, enum changes, etc.). If it
  did, delete those lines — keep the migration to this one column.
- Existing rows backfill to `'patient_request'` via the server default. That is correct: every
  pre-existing consult that mattered for revenue went through the assign/order flow.

**Step 5 — apply it**
```bash
make migrate        # never auto-runs on boot; this is the deliberate apply step
make test           # confirm green
```

**Step 6 — commit** model + repo + migration together, push, and note in this file that Part 3
is DONE so the other laptop can `git pull` and drop the schema-mismatch.

---

## Next steps (after Part 3 migration is live)

1. **Revenue analytics segmentation** — `backend/app/repositories/analytics.py`,
   `get_revenue_data`: optionally `LEFT JOIN` instead of `JOIN kc_payments` and group/label by
   `booking_source`, so complimentary consults are reported as their own segment instead of
   silently dropped. (Revenue numbers themselves don't change — comp consults are still ₹0 — but
   consultation counts and per-consult averages become honest.)
2. **Regenerate API clients** if `booking_source` should be exposed to any surface:
   `make openapi && make generate-clients`. (Not required for Parts 1–2.)
3. **Open audit gaps — status** (from the consultation-flow review):
   - ✅ Unpaid `scheduled` consults never expire → slot leak — FIXED (`expire_unpaid_scheduled`
     beat task + `get_expired_unpaid_consultations`).
   - ✅ Doctor portal "Complete" button on non-`in_progress` → silent 409 — FIXED (gated to
     `in_progress`, error surfaced, join invalidates the query).
   - ✅ Patient can join a room the doctor can't open — FIXED (patient join now enforces the
     same TPG gate and returns an actionable 409; mobile shows the reason).
   - ✅ Coordinator coupon at assign + coordinator no-show action — FIXED.
   - ⏳ Hand-written API types vs. generated clients (#7) — STILL OPEN. Needs the codegen
     toolchain: run `make openapi && make generate-clients` on a machine with `uv` + node,
     then commit the regenerated `mobile/lib/api/generated/` and
     `doctor-portal/src/api/generated/`. No concrete data bug today; this is standards/drift
     prevention.
