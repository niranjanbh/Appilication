---
paths:
  - "backend/alembic/**"
---

# Migration Rules

Migrations are deliberate, reviewed, and forward-only in production. Reckless migrations are
the single largest source of healthcare outages and data corruption.

## Generation

- Use `alembic revision --autogenerate -m "<descriptive message>"` from inside the backend
  container: `docker compose run --rm backend-api alembic revision --autogenerate -m "..."`.
- The autogenerate output is a starting point, not the final migration. **Always open the
  generated file and review it before applying.**
- Migration message describes the change in present tense: "add kc_lab_orders.urgency
  column", "create dr_availability table", "backfill kc_payments.gst_invoice_url".

## Naming

- File prefix: `NNNN_short_slug.py` where `NNNN` is monotonic 4-digit (`0001_init`,
  `0002_identity_and_consent`, ...). Alembic's revision hashes are still used internally.
- One logical concern per migration. Splitting `0006_clinical_core` and `0007_prescriptions`
  is correct; bundling them is hard to review and hard to revert.

## Patterns to enforce

- **Add nullable or default.** Every new column is nullable OR has a server_default. Backfill
  nulls in a separate migration if a NOT NULL constraint is needed later.
- **Indexes concurrent in production.** `op.create_index(..., postgresql_concurrently=True)`
  inside `with op.get_context().autocommit_block():`. CONCURRENTLY cannot be in a transaction.
- **Foreign keys with explicit `ON DELETE`.** `CASCADE`, `RESTRICT`, or `SET NULL` — never the
  default. The choice is a clinical-safety decision.
- **Enum value changes are additive only.** `ALTER TYPE <name> ADD VALUE IF NOT EXISTS '<v>'`.
  Renaming or removing requires a multi-step migration; plan it as multi-deploy.
- **Validate constraints late.** New FKs against potentially-null target columns use
  `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT` in a follow-up migration. Avoids
  long table locks.

## Append-only tables

`ad_audit_log` has no UPDATE/DELETE path. The Postgres trigger blocking modification is
created in the initial audit-log migration:

```python
op.execute("""
    CREATE OR REPLACE FUNCTION prevent_audit_log_modification() RETURNS TRIGGER AS $$
    BEGIN
      RAISE EXCEPTION 'ad_audit_log is append-only';
    END;
    $$ LANGUAGE plpgsql;
""")
op.execute("""
    CREATE TRIGGER prevent_audit_log_update
      BEFORE UPDATE OR DELETE ON ad_audit_log
      FOR EACH ROW
      EXECUTE FUNCTION prevent_audit_log_modification();
""")
```

## Partitioning

`wn_health_datapoints` and `ad_audit_log` are partitioned by RANGE on timestamp. The initial
migration creates the parent table and the first 6 months of partitions. A monthly Celery beat
task creates partitions 3 months ahead.

## downgrade()

Every migration has a working `downgrade()`. Production migrations are forward-only in
practice, but `downgrade` is what makes the migration testable round-trip in
`tests/migration/test_migrations_up_down.py`. CI runs that test.

If a migration is genuinely not reversible (data loss, type collapse), `downgrade()` raises
`NotImplementedError` with a clear message. This is rare and requires explicit acknowledgement
in the PR description.

## Schema-head sanity check

The backend's lifespan startup verifies the applied migration head matches the code's head.
If you add a migration but the app starts in an environment where it wasn't applied, the app
refuses to start with a clear "schema version mismatch — run `alembic upgrade head`" message.

Do NOT bypass this by removing the check.

## What to read

- `docs/strategy/backend-strategy.md` §5 (Postgres strategy)
- `docs/strategy/backend-strategy.md` §10 (schema implementation)
- `docs/strategy/backend-strategy.md` §16 (zero-downtime migration patterns)
