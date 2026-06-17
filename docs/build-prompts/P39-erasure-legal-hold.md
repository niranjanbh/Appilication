# P39 — Erasure with Legal Hold

## Prompt

Implement "erasure with legal hold" per DPDP §12 + NMC/TPG medical records retention rules:

1. The erasure Celery task must **anonymize PII** (name, email, phone, dob, city/state, etc.) rather than merely soft-deleting.
2. All consultations and prescriptions belonging to the erased user must be stamped with a **7-year legal hold** (`legal_hold_until`, `legal_hold_reason`).
3. A **Postgres trigger** must block hard DELETE on `kc_consultations` when the hold is active — encoding the invariant at the DB layer.
4. A minimal **admin REST API** for DSR management (`GET /v1/admin/dsr`, `PATCH /v1/admin/dsr/{id}/status`).

## Required reading

- `docs/strategy/staff-rbac-spec.md` §5 (retention vs. erasure conflict)
- `docs/strategy/build-spec.md` §15 (DPDP compliance architecture)
- `.claude/rules/security.md` rules 1, 5, 10

## Acceptance criteria

- [ ] Migration `0029_erasure_legal_hold` adds `erased_at` to `users`, `legal_hold_until` + `legal_hold_reason` to `kc_consultations` and `kc_prescriptions`, and the DELETE-blocking Postgres trigger
- [ ] `_process_erasure_async` anonymizes PII (not just soft-deletes) and sets legal hold on clinical records
- [ ] `anonymize_pii_values` is a pure function — unit-testable without DB
- [ ] Erasure task is idempotent (safe to run twice)
- [ ] `GET /v1/admin/dsr` + `PATCH /v1/admin/dsr/{id}/status` gated by `DSR_PROCESS` permission
- [ ] 5 unit tests + 9 integration tests pass; RBAC matrix sections for both DSR endpoints

## What was built

### Migration

`alembic/versions/0029_erasure_legal_hold.py` — `ALTER TABLE users ADD COLUMN erased_at`;
`ALTER TABLE kc_consultations ADD COLUMN legal_hold_until, legal_hold_reason`;
`ALTER TABLE kc_prescriptions ADD COLUMN legal_hold_until, legal_hold_reason`;
Postgres trigger `trg_prevent_consult_delete` + function `prevent_consult_delete_under_hold`.

### Models

- `app/models/identity.py` — `User.erased_at`
- `app/models/clinic.py` — `Consultation.legal_hold_until/reason`, `Prescription.legal_hold_until/reason`

### Repository

`app/repositories/erasure.py` — `anonymize_pii_values(user_id, now) -> dict` (pure) +
`apply_legal_hold(db, *, user_id, hold_until, reason) -> tuple[int, int]`.

### Task

`app/tasks/data_subject_request.py` — `_process_erasure_async` rewritten:
1. Anonymize PII (idempotent `erased_at IS NULL` guard)
2. Revoke all tokens
3. Apply 7-year NMC hold (`_NMC_RETENTION_YEARS = 7`)
4. Mark DSR COMPLETED with JSON audit notes

### API

- `app/api/v1/admin/dsr.py` — `GET /v1/admin/dsr` (paginated list + status filter), `PATCH /v1/admin/dsr/{id}/status` (status machine transitions, 409 on invalid, 404 if not found)
- `app/api/v1/router.py` — registered `admin_dsr_router`

### Tests

- `tests/unit/test_anonymize_pii.py` — 5 pure tests (no DB)
- `tests/integration/api/test_erasure_legal_hold.py` — 9 integration tests
- `tests/integration/api/test_rbac_matrix.py` — DSR list + patch sections

## Key design decisions

- **`erased_at` vs `deleted_at`**: `deleted_at` = soft-delete (recoverable in grace period); `erased_at` = PII anonymized (irreversible). Both are set by the erasure task for compatibility.
- **Legal hold at DB layer**: The Postgres trigger is the safety net — no application code can accidentally hard-delete a consultation under hold.
- **`_NMC_RETENTION_YEARS = 7`**: A legal constant in the task file. Changing it requires explicit code review and regulatory justification.
- **P38 migration conflict resolved**: `0027_patient_health_notes.py` already existed; P38's migration was renumbered from 0027 → 0028, and P39 is 0029.

## Non-goals

- No change to `POST /v1/users/me/delete` endpoint
- No Jinja2 admin UI changes (DSR queue at `/admin/dsr` already exists)
- No 30-day grace-period scheduler
- No per-field correction endpoint
