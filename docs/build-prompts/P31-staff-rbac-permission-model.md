# P31 — Staff RBAC: Permission Model + Role-Context Stamping

> Build prompt for the **staff-RBAC track**, hand-authored from `docs/strategy/staff-rbac-spec.md`
> §1 (Access Model) and §6 (Build Sequencing, step 1). This track is NOT part of the P1–P30
> build-spec queue and is not produced by `scripts/extract-build-prompts.py`. Treat this file as
> the working brief.

> **Sequence note.** This is step 1 of the staff-RBAC track and is the foundation every later
> prompt composes against. It deliberately does **not** include staff MFA / token-audience
> separation / forced session-kill (that is **P32 — Staff auth plane hardening**) nor the
> PHI-access audit *middleware* (that is **P33 — PHI-access audit middleware**). Keep this
> prompt to the permission model, multi-role union, the enforcement primitive, and role-context
> stamping. Do not pull P32/P33 scope forward.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/staff-rbac-spec.md` — §1 (Access Model — the whole basis for this prompt), §5 (audit + role-context), §6 (sequencing)
- `.claude/rules/security.md` — rules 1, 3, 5 (cross-user 404, audit-every-decision, no PHI in logs)
- `.claude/rules/backend.md` — three-layer architecture, RBAC and the cross-user 404 pattern, audit-log discipline
- `docs/strategy/backend-strategy.md` — §11 (auth and RBAC)
- Current code to reconcile against (do not skip — this prompt EXTENDS, it does not rewrite):
  - `backend/app/core/rbac.py` — existing `enforce_role`, `get_current_user`, `cross_user_404`
  - `backend/app/core/audit.py` + `backend/app/models/audit.py` — `AuditContext`, `write_audit`, `ad_audit_log`
  - `backend/app/db/enums.py` — `UserRole`, `ActorRole`
  - `backend/app/models/identity.py` — `User.role` (single primary role today)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations are reviewed before applying. Auto-generate where possible, then open the file. The
  `ad_audit_log` additions must be **nullable / additive** (the table is append-only with an
  immutability trigger and is partitioned monthly — no backfill, no rewrite).
- Tests added, including RBAC-matrix entries for any endpoint switched to permission enforcement.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged — both `allowed=true` and `allowed=false` — now also
  carrying the role-context and the permission exercised.
- No PHI in logs, fixtures, or error responses. Permission denials return 403; cross-user resource
  misses still return 404 (the existing `cross_user_404` pattern is unchanged).
- Back-compat: `enforce_role(...)` and the pre-built role deps keep working. This prompt adds a
  parallel permission layer; it does not delete the role layer in the same change.

## Original prompt

Establish the staff-side **permission model** the rest of the staff-RBAC track composes against.
Per `staff-rbac-spec.md` §1: roles are permission bundles, not identities; permissions resolve as
a **union** when a staff member holds multiple roles; and **every action is stamped with the
role-context it was taken under**.

In `backend/app/core/` and `backend/app/models/`:

1. **Permission catalog (code-defined, not a DB table).** Add `app/core/permissions.py` with a
   `Permission` `StrEnum` of granular `resource:action[:scope]` values. Cover at minimum the staff
   surface named in the spec (§2–§4), e.g.:
   `patient:read:assigned`, `patient:read:redacted`, `patient:read:all`,
   `consultation:read:assigned`, `consultation:transition`,
   `clinical_note:read`, `clinical_note:write`,
   `prescription:create`, `prescription:sign`,
   `content:approve`, `content:publish`,
   `audit:read`, `staff:manage`, `role:assign`, `payout:compute`, `pricing:manage`,
   `dsr:process`.
   Names are the contract later prompts import — choose them deliberately.

2. **Role → permission composition.** A `ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]]`
   mapping each role to its bundle. Encode the spec's boundaries precisely — the coordinator bundle
   gets `patient:read:redacted` and must **never** contain `clinical_note:read`,
   `clinical_note:write`, or `prescription:*` (this is the §4 deny-list, now expressed as the
   absence of those permissions, enforceable and testable).

3. **Multi-role union.** Introduce additive multi-role capability for **staff only** (patients are
   never multi-role). Add an `ad_staff_roles` table (`user_id` FK, `role`, `granted_by`,
   `granted_at`) for roles held in addition to `users.role` (the primary/identity role). Add a
   resolver `permissions_for(user) -> frozenset[Permission]` that unions the primary role's bundle
   with every additional staff role's bundle. `users.role` stays the primary role; do not migrate
   existing single-role users.

4. **Enforcement primitive.** Add `require_permission(*needed: Permission)` in `app/core/rbac.py`
   — a FastAPI dependency that loads the current user, computes `permissions_for(user)`, and raises
   403 (`detail="forbidden"`) if any required permission is absent. It lives alongside
   `enforce_role` (which is unchanged). Convert **one** representative staff endpoint per surface to
   `require_permission` as a reference migration (e.g. one doctor clinical endpoint and one admin
   endpoint) — full cutover of every route is later, not now.

5. **Role-context stamping.** Per §1/§5, every audited action records the role-context it was taken
   under (the doctor-admin signs a prescription *as the RMP*). Extend `AuditContext` and
   `write_audit` with a `role_context` field, and add `role_context` (and the `permission`
   exercised) as **nullable** columns on `ad_audit_log` via a reviewed, additive migration. The
   `require_permission` dependency determines the acting role — the role whose bundle granted the
   required permission — using a documented precedence when more than one role qualifies (clinical
   role wins for clinical permissions). It writes that role and the permission into the audit row.

Keep the three-layer architecture: the permission catalog and resolver are core/`app/core`; routers
depend on `require_permission`; services remain audience-agnostic and trust the router for authz.

**Acceptance:**

- `permissions_for` returns the correct union: a user holding both `doctor` and `super_admin` gets
  the union of both bundles; a single-role user gets exactly their bundle.
- `require_permission(Permission.PRESCRIPTION_CREATE)` permits a doctor, denies a coordinator with
  403, denies an unauthenticated request with 401 — asserted in the RBAC matrix.
- A coordinator's resolved permissions contain **no** `clinical_note:*` or `prescription:*` entry
  (explicit deny-list test).
- A clinical action taken by a multi-role doctor-admin writes an `ad_audit_log` row whose
  `role_context = 'doctor'` and `permission = 'prescription:create'`; an admin-only action by the
  same user stamps `role_context = 'super_admin'`.
- Both `allowed=true` and `allowed=false` decisions are audit-logged with the new fields populated.
- The reference-migrated endpoints behave identically to before for correctly-authorized callers
  (no regression in existing tests); `enforce_role` paths are untouched.

---

*To execute: tell Claude Code `Execute P31. Read docs/build-prompts/P31-staff-rbac-permission-model.md, then plan before editing.`*
