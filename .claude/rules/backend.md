---
paths:
  - "backend/**/*.py"
---

# Backend Implementation Rules

These rules apply to any change under `backend/`. For deeper context, read the referenced
sections of `docs/strategy/backend-strategy.md`.

## Three-layer architecture

- **Router** → **Service** → **Repository**. No exceptions.
- Routers handle: dependency injection, auth/role enforcement, request schema parsing, calling
  exactly one service function, response schema serialization, audit log writes for the
  authorization decision.
- Services handle: business logic, orchestration across repositories, calling integrations.
  Services never know which audience called them; they trust the router for auth.
- Repositories handle: async SQL via SQLAlchemy. One file per aggregate. Functions take scope
  parameters explicitly (`patient_user_id`, `doctor_id`, `coordinator_id`).

→ See backend-strategy §3 (FastAPI architecture), §10 (schema implementation).

## RBAC and the cross-user 404 pattern

- **Authentication** = JWT decode + DB lookup. Returns `User`.
- **Role authorization** = `enforce_role(Role.X)` dependency. Raises 403 on role mismatch.
- **Resource authorization** = repository function parameter. Returns None for "not yours OR
  not found." Router translates None → `HTTPException(404)`.

A patient hitting `/v1/clinic/patient/consultations/<other_patient_consult_id>` must receive
exactly the same response as for a non-existent UUID. Same status code (404), same body, same
timing characteristics if you can help it. Otherwise you've created an enumeration channel.

→ See backend-strategy §11 (auth and RBAC).

## Audit log discipline

Every authorization decision writes to `ad_audit_log` via `audit_repo.write()` — both allowed
and denied. Denials commit the audit row before raising the 4xx.

```python
if resource is None:
    await audit_repo.write(db, ctx, action="view_x", resource_type="x",
                           resource_id=x_id, allowed=False, reason="not_own_or_not_found")
    await db.commit()
    raise HTTPException(404, detail="not found")
```

The audit log is partitioned monthly, append-only (Postgres trigger blocks UPDATE/DELETE),
and never contains PHI in the metadata column.

## Pydantic schemas per audience

For the same underlying entity, maintain per-audience schemas:

- `PatientXxxRead` — patient view, scoped fields only.
- `DoctorXxxRead` — doctor view, clinical fields visible.
- `CoordinatorXxxView` — coordinator view, **clinical fields stripped**.
- `AdminXxxRead` — admin view, all fields.

Routers convert ORM → schema explicitly. Never `return orm_object` from a handler.

→ See backend-strategy §10 (schema implementation), §12 (API organization).

## Transactions

- One HTTP request = one transaction. The `get_db` dependency manages commit/rollback.
- Services never call `db.commit()` or `db.rollback()`. They flush if necessary.
- The exception: denial audit logs commit explicitly before raising (so denials are recorded
  even when the operation is rolled back).
- Celery tasks have their own session lifecycle (`task_db_session` context manager).

## Naming conventions

- ORM classes: `User`, `Consultation`, `Prescription` (PascalCase singular). `__tablename__`
  comes from build-spec (`users`, `kc_consultations`).
- Pydantic schemas: `XxxCreate` (inbound POST), `XxxUpdate` (inbound PATCH), `XxxRead`
  (outbound), `XxxAdminRead` (outbound with admin-only fields).
- Repository functions: verb + noun + scope. `get_consultation_for_patient(consult_id,
  patient_user_id)`, `list_consultations_for_doctor_panel(doctor_id, ...)`. Scope is a
  parameter, never an implicit context.
- Service functions: verb + noun, no scope suffix.
- Celery task names: `kyros.<domain>.<verb_noun>` for routing clarity.

## Money, time, IDs

- Money columns: `INTEGER` storing paise. Never `NUMERIC`, never `FLOAT`.
- Timestamps: `TIMESTAMPTZ`. Store UTC. Display conversion to IST is presentation-layer.
- UUIDs: server-generated via `gen_random_uuid()` from `pgcrypto`. Set
  `server_default=text("gen_random_uuid()")` on the model.

## Async correctness

- Every database call is `await`ed.
- `expire_on_commit=False` on the async session — required to avoid lazy-load failures.
- Celery tasks bridge to async via `run_async(coro)` helper, one `asyncio.run` per invocation.
- Never share an event loop across tasks.

## What to read for which task

| Task | Section in backend-strategy.md |
|---|---|
| Adding a model + migration | §5 (Postgres), §10 (schema strategy) |
| Adding a route | §3 (FastAPI), §12 (API organization), §11 (RBAC) |
| Adding a Celery task | §7 (Celery strategy) |
| Adding file upload/download | §13 (file storage) |
| Adding a webhook | §6 (Redis idempotency), §12 (API organization) |
| Adding config | §8 (configuration management) |
| Writing tests | §15 (testing strategy) |
