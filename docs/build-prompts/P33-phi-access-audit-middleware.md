# P33 — PHI-Access Audit Middleware

> Build prompt for the **staff-RBAC track**, hand-authored from `docs/strategy/staff-rbac-spec.md`
> §5 (Cross-Cutting Concerns — "Audit is middleware, not per-endpoint") and §6 (Build Sequencing,
> step 1). This track is NOT part of the P1–P30 build-spec queue and is not produced by
> `scripts/extract-build-prompts.py`. Treat this file as the working brief.

> **Sequence note.** This is step 3 of the staff-RBAC track, building on **P31 — Staff RBAC:
> Permission Model + Role-Context Stamping** (the `role_context`/`permission` columns and
> `request.state` stamping convention this prompt extends) and **P32 — Staff Auth Plane
> Hardening** (JWT audience separation, staff MFA). It deliberately does **not**:
> - Rewrite or remove any of the ~230 existing per-handler `write_audit()` calls — those remain
>   the source of truth for *allowed*-side PHI access (P31's reconciliation: "not a rewrite").
> - Add audit rows for *allowed* (2xx) responses — this prompt closes the **denied**-decision
>   gap only.
> - Add a new migration — `ad_audit_log.role_context`/`permission` (from migration 0022) and
>   every other column this prompt needs already exist, nullable.
> - Log 401s where the actor cannot be identified (missing/invalid/expired token) — no PHI was
>   reached, and writing one immutable row per scanner/bot request to a partitioned table is an
>   operational cost, not a compliance requirement. The access log already captures these.
> Do not pull P34 scope (consultation state machine, TPG consent/identity hard gate) forward.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/staff-rbac-spec.md` — §5 (Cross-Cutting Concerns — audit-as-middleware), §6
  (sequencing)
- `.claude/rules/security.md` — rule 3 (every authorization decision is audit-logged, allowed
  AND denied), rule 5 (no PHI in logs)
- `.claude/rules/backend.md` — audit log discipline (the `cross_user_404` pattern is the model
  for "commit a denial row before raising")
- Current code to reconcile against (do not skip — this prompt EXTENDS, it does not rewrite):
  - `backend/app/core/rbac.py` — `get_current_user` (audience-mismatch 401), `require_mfa`
    (mfa-required 401), `enforce_role` (403), `require_permission` (403 + existing
    `role_context`/`permission` stamping on the *allow* path), `cross_user_404`
  - `backend/app/adminui/deps.py` — `require_admin_session`, `require_coord_session`,
    `require_super_admin_session` (403 for admin-tier hitting a super-admin-only view),
    `require_fresh_super_admin` (302, out of scope)
  - `backend/app/observability/middleware.py` — `RequestIDMiddleware`, `AccessLogMiddleware`
    (the pure-ASGI pattern: mutate/read `scope["state"]` after `await self.app(...)` returns,
    since `scope` is a shared dict)
  - `backend/app/core/audit.py` + `backend/app/models/audit.py` — `AuditContext`, `write_audit`,
    `ad_audit_log` columns (all already present, all nullable except `actor_role`/`action`/
    `allowed`)
  - `backend/app/db/session.py` — `AsyncSessionLocal` (session factory usable outside FastAPI DI)
  - `backend/app/main.py` — middleware registration order
  - `backend/app/core/config.py` — `rate_limit_enabled` (pattern for an ops kill-switch flag)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- No new migration. If you find a genuine need for one, stop and flag it — it likely means the
  scope has drifted from this prompt.
- Tests added: unit tests for the new pure helper(s) (no DB), integration tests asserting
  `ad_audit_log` rows for the new denial paths.
- `make ruff && make mypy && make test` all pass.
- The middleware never raises and never alters the response body/status — a DB error while
  writing the audit row is caught and logged via `structlog`, not surfaced to the client.
- No PHI in the new audit rows: `action`/`resource_type`/`reason` are route/permission/string
  literals; `resource_id` is a UUID path param, never a name/phone/lab value.
- Existing tests (`test_rbac_matrix.py`, `test_permission_enforcement.py`) continue to pass
  unmodified — this middleware is response-transparent, it only adds rows to `ad_audit_log`.
- Gated by a new `settings.phi_audit_middleware_enabled` flag (default `true`) so ops can
  disable it without a redeploy if it misbehaves.

## Original prompt

Close the **denial-side** half of `staff-rbac-spec.md` §5: *"Audit is middleware, not
per-endpoint... every PHI access — who, what, when, source — to an append-only audit log."*
Today, `cross_user_404` (resource-level denial) writes+commits an audit row before raising —
but role/permission-level denials (`enforce_role` 403, `require_permission` 403,
audience-mismatch 401, mfa-required 401, admin-tier-vs-super-admin 403) write **nothing**. This
violates security rule 3 ("every authorization decision — allowed AND denied — is
audit-logged") and, being purely cross-cutting, is the part of the audit story that genuinely
belongs in middleware: P34+ endpoints get denial-audit coverage for free.

In `backend/app/core/`, `backend/app/adminui/`, and `backend/app/observability/`:

1. **Stamp actor identity + deny-reason on `request.state`.** This extends P31's existing
   `request.state.role_context`/`permission` stamping convention — same mechanism, same files.

   - `backend/app/core/rbac.py`:
     - `get_current_user`: immediately after resolving `user`, set
       `request.state.actor_user_id = user.id` and
       `request.state.actor_role = ActorRole(user.role.value)` (the five shared `UserRole` /
       `ActorRole` members have identical string values). Before raising the
       audience-mismatch 401, set `request.state.deny_reason = "audience_mismatch"`.
     - `require_mfa`: before raising its 401, set `request.state.deny_reason = "mfa_required"`.
     - `enforce_role`'s inner `dep`: before raising its 403, set
       `request.state.deny_reason = "forbidden"`.
     - `require_permission`'s inner `dep`: before raising its 403, set
       `request.state.permission = needed[0].value` and
       `request.state.deny_reason = "forbidden"` (leave `role_context` unset on denial — no
       held role grants the permission, so there is no acting role to record).

   - `backend/app/adminui/deps.py`:
     - `require_admin_session` and `require_coord_session`: immediately after resolving `user`,
       stamp `request.state.actor_user_id` / `request.state.actor_role` the same way (covers
       the downstream `require_super_admin_session` check). The existing 302 login-redirects
       for missing/invalid sessions are untouched — actor is unknown, middleware skips them
       naturally.
     - `require_super_admin_session`: before raising its 403, set
       `request.state.deny_reason = "super_admin_required"`.

2. **New `PHIAuditMiddleware`** in `backend/app/observability/middleware.py` — pure-ASGI, same
   style as `RequestIDMiddleware`/`AccessLogMiddleware` (mutate/read `scope["state"]` after
   `await self.app(...)` returns; capture the response status via the `_send` wrapper idiom).

   - Skip `scope["type"] != "http"`, and skip an exempt-prefix set: `/v1/auth`, `/v1/public`,
     `/v1/webhooks`, `/healthz`, `/readyz`, and the configured docs/openapi/redoc paths.
   - Skip entirely if `settings.phi_audit_middleware_enabled` is `False`.
   - After `await self.app(scope, receive, _send)` returns: if the captured status is `401` or
     `403` **and** `scope["state"]` has a non-`None` `actor_user_id` (i.e. the actor was
     identified — `get_current_user`/`require_admin_session`/`require_coord_session` ran far
     enough to resolve a user before something downstream denied access):
     - Build an `AuditContext` from `scope["state"]` (`actor_user_id`, `actor_role`,
       `role_context`, `permission`, all via `.get(...)` with `None` defaults) plus
       `ip_address`/`user_agent` from the request headers and `request_id` from
       `scope["state"]`.
     - Derive `resource_type`/`resource_id` via a small pure helper
       `_resource_from_path_params(path_params: Mapping[str, Any]) -> tuple[str | None, uuid.UUID | None]`:
       take the **last** key ending in `_id` from `scope.get("path_params", {})`; strip the
       suffix for `resource_type`; parse the value as a UUID for `resource_id` (`None` for
       either if no such key, or if the value doesn't parse as a UUID).
     - `action = f"{method} {path}"`, truncated to fit the `VARCHAR(100)` column.
     - Open a short-lived session via `AsyncSessionLocal()` (middleware has no request-scoped
       session), call `write_audit(db, ctx, action=..., resource_type=..., resource_id=...,
       allowed=False, reason=scope["state"].get("deny_reason", "access_denied"))`, commit,
       close.
     - Wrap the whole write in `try`/`except Exception`: log
       `logger.warning("phi_audit.write_failed", ...)` (no PHI, no token contents) and continue
       — never raise, never touch the response.

3. **Register the middleware** in `backend/app/main.py`
   (`app.add_middleware(PHIAuditMiddleware)`, alongside the existing observability middleware
   imports — exact ordering relative to `RequestIDMiddleware`/`AccessLogMiddleware` doesn't
   matter functionally since all read `scope["state"]` post-hoc, but group it with them for
   readability).

4. **Config flag.** Add `phi_audit_middleware_enabled: bool = True` to `app/core/config.py`
   (same pattern as `rate_limit_enabled`).

Keep the three-layer architecture in spirit: the middleware is the only new "handler" here, and
it calls the existing `write_audit`/`audit_repo.write` — no new repository code.

**Acceptance:**

- A coordinator calling a doctor-only `require_permission(Permission.PRESCRIPTION_CREATE)`
  endpoint still gets 403 `detail="forbidden"` (unchanged response), AND a new
  `ad_audit_log` row exists with `actor_user_id=<coordinator.id>`, `actor_role="coordinator"`,
  `allowed=False`, `reason="forbidden"`, `permission="prescription:create"`.
- A patient calling a doctor-only `enforce_role(UserRole.DOCTOR)` endpoint still gets 403
  (unchanged), AND a new `ad_audit_log` row exists with `actor_role="patient"`,
  `allowed=False`, `reason="forbidden"`.
- A logged-in `admin`-tier user hitting a `require_super_admin_session`-gated `/admin/*` view
  still gets 403 (unchanged), AND a new `ad_audit_log` row exists with `actor_role="admin"`,
  `allowed=False`, `reason="super_admin_required"`.
- A request with no/invalid/expired bearer token still gets 401 `detail="not_authenticated"` /
  `"user_not_found"` (unchanged), and **no** new `ad_audit_log` row is written by this
  middleware (actor unidentified).
- A bad-password request to `/v1/auth/login` still gets its existing response, and **no** new
  row is written by this middleware (`/v1/auth` is exempt).
- `resource_type`/`resource_id` are populated correctly for a denial on a parameterized route
  (e.g. `/v1/doctor/patients/{patient_id}/lab-reports/{report_id}/annotate` → `resource_type=
  "report"`, `resource_id=<report uuid>`) and both are `None` for a denial on a non-parameterized
  route (e.g. `/v1/doctor/patients`).
- Setting `settings.phi_audit_middleware_enabled = False` disables all of the above writes with
  no other behavior change.
- `test_rbac_matrix.py` and `test_permission_enforcement.py` pass unmodified.
- Both `allowed=true` (existing, per-handler) and `allowed=false` (new, via this middleware)
  decisions are now audit-logged for every permission-gated route.

---

*To execute: tell Claude Code `Execute P33. Read docs/build-prompts/P33-phi-access-audit-middleware.md, then plan before editing.`*
