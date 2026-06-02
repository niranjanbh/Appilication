---
paths:
  - "backend/tests/**"
---

# Backend Testing Rules

Tests are part of the deliverable, not a follow-up. Every PR that adds a route, model, or
service adds tests in the same PR.

## Pyramid

- Unit (≈60%): pure-function logic in `app/core/`, repository signatures, service orchestration
  with mocked repos.
- Integration (≈35%): async API tests against real Postgres + Redis (compose-test).
- End-to-end (≈5%): critical user journeys, run nightly.

## Async fixtures

- `db_session` fixture wraps each test in a transaction that is rolled back at the end. Fast,
  isolated. Defined in `tests/conftest.py`.
- `client` fixture wraps `httpx.AsyncClient` with the FastAPI app and a `get_db` override
  pointing at the wrapped session.
- Per-role fixtures: `patient_user`, `doctor_user`, `coordinator_user`, `admin_user`. Each
  has a `_auth_headers` variant that returns `{"Authorization": "Bearer ..."}`.

## RBAC matrix is mandatory

`tests/integration/api/test_rbac_matrix.py` enumerates every `/v1/*` endpoint and asserts
the expected status for every role. Adding a new endpoint requires adding a matrix entry.
**A CI lint fails if a route is missing from the matrix.**

The matrix has columns:

- `endpoint` (e.g., `/v1/clinic/patient/consultations/{id}`)
- `method` (e.g., `GET`, `POST`, `PATCH`, `DELETE`)
- `allowed_roles` (e.g., `[Role.PATIENT]`)
- `denied_roles_with_status` (e.g., `{Role.DOCTOR: 403, Role.COORDINATOR: 403, Role.SUPER_ADMIN: 403, None: 401}`)
- For resource-scoped endpoints: an own-resource fixture and a foreign-resource fixture, with
  the cross-user 404 assertion.

## Cross-user 404 tests

For every resource-scoped endpoint, write a dedicated test:

```python
async def test_patient_cannot_view_other_patient_<resource>(client, patient_user, ...):
    other = await create_user(...)
    foreign_resource = await create_<resource>(patient=other, ...)
    response = await client.get(f"/v1/clinic/patient/<resource>/{foreign_resource.id}",
                                headers=patient_auth_headers)
    assert response.status_code == 404
    # And the denial is audit-logged
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_user_id == patient_user.id,
            AuditLog.action == "view_<resource>",
            AuditLog.allowed == False,
        )
    )
    assert audit is not None
    assert audit.reason == "not_own_or_not_found"
```

## Synthetic data only

- Test data uses Faker. Never use real patient names, phone numbers, or any data that could
  be identifiable.
- Phone numbers in tests use the `+919000000XXX` range — clearly synthetic.
- Email addresses use `@test.kyros.local` — clearly synthetic.

## Celery task tests

- `celery_eager` fixture sets `task_always_eager=True` and `task_eager_propagates=True` so
  tasks execute synchronously in the test process.
- Test the underlying async function directly (`_parse_lab_report_async`), and separately
  test the Celery wrapper (`parse_lab_report.apply()`).

## Migration tests

`tests/migration/test_migrations_up_down.py` runs every migration forward and backward,
asserting they're reversible. CI runs this; broken `downgrade()` fails CI.

## Coverage and gates

- Line coverage ≥ 80% on `app/` (excluding `models/` and `integrations/`).
- Mypy strict mode passes.
- Ruff with full rule set passes.
- RBAC matrix complete.
- No skipped tests merged without an issue link.

CI fails on any of these.

## What not to do

- Don't mock SQLAlchemy. Use real Postgres in compose-test.
- Don't mock Redis. Use real Redis in compose-test.
- Don't mock the Celery broker. Use eager mode.
- Don't write tests that depend on test execution order.
- Don't share state across tests via module-level variables.

## What to read

- `docs/strategy/backend-strategy.md` §15 (testing strategy)
- `docs/strategy/backend-strategy.md` §11 (RBAC matrix discipline)
