# P32 — Staff Auth Plane Hardening

> Build prompt for the **staff-RBAC track**, hand-authored from `docs/strategy/staff-rbac-spec.md`
> §1 (Access Model). This track is NOT part of the P1–P30 build-spec queue and is not produced by
> `scripts/extract-build-prompts.py`. Treat this file as the working brief.

> **Sequence note.** This is step 2 of the staff-RBAC track, building on **P31 — Staff RBAC:
> Permission Model + Role-Context Stamping**. It covers the staff auth *plane*: JWT audience
> separation, mandatory TOTP MFA for staff with recovery codes, staff idle-timeout sessions, and
> admin-forced session revocation. It deliberately does **not** include the PHI-access audit
> *middleware* (that is **P33 — PHI-access audit middleware**) or any patient-facing / frontend MFA
> UI (doctor portal, mobile, super admin / coordinator login screens). Do not pull P33 scope
> forward, and do not build frontend MFA enrollment screens in this prompt — staff MFA is
> API-only for now, exercised via Postman/tests.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/staff-rbac-spec.md` — §1 (Access Model — "Staff auth is a separate plane from
  patient auth: provisioned accounts, mandatory MFA, short idle-timeout sessions, admin-forced
  session revocation, different token audience from the patient app.")
- `.claude/rules/security.md` — rules 5 (no PHI in logs), 8 (JWT/OTP secrets ≥32 chars, validated
  at startup), 18 (refresh-token rotation + reuse detection)
- `.claude/rules/migrations.md` — additive-only migrations, review before applying
- `.claude/rules/backend.md` — three-layer architecture, audit-log discipline
- Current code to reconcile against (do not skip — this prompt EXTENDS, it does not rewrite):
  - `backend/app/core/security.py` — existing `create_access_token` / `decode_access_token` /
    `TokenClaims`, refresh-token hashing, `hash_otp`
  - `backend/app/core/rbac.py` — existing `get_current_user`, `enforce_role`, `get_staff_user`
  - `backend/app/services/auth.py` — existing `login()` / `refresh()` flow, `_create_token_pair`,
    reuse-detection (`session_revoked`) branch
  - `backend/app/repositories/auth.py` — `create_refresh_token`, `revoke_all_for_user`,
    `revoke_session_family`
  - `backend/app/models/identity.py` — `User`, `RefreshToken`
  - `backend/app/adminui/deps.py` — admin/coordinator portal session-cookie helpers
    (`create_admin_session`, `create_coord_session`, `is_session_fresh`)
  - `backend/app/services/staff_service.py` — `reset_staff_password` (pattern to follow for the
    new session-revoke service function)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations are reviewed before applying. Auto-generate where possible, then open the file. New
  tables/columns are additive and nullable-or-defaulted — no backfill, no rewrite of
  `ad_audit_log` or `refresh_tokens` beyond a single defaulted boolean column.
- Tests added: unit tests for the new `app/core/security.py` primitives (audience mapping, TOTP
  helpers, recovery codes), integration tests for the MFA enrollment/login-challenge/verify/
  disable/re-enrollment flows, the staff idle-timeout refresh path, and admin-forced session-kill.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision remains audit-logged — both `allowed=true` and `allowed=false` —
  including the new MFA and session-revoke actions.
- No PHI in logs, fixtures, or error responses. TOTP secrets are encrypted at rest; recovery
  codes are hashed at rest and shown to the staff member exactly once (at `/mfa/confirm`).
- Back-compat: tokens minted before this change decode with `aud="patient"` and `mfa=False`
  defaults, which forces a re-login for staff accounts (audience mismatch) rather than erroring.
  Patient-facing flows (signup/login/refresh) are otherwise unchanged.

## Original prompt

Harden the staff auth plane per `staff-rbac-spec.md` §1: **provisioned accounts (no
self-signup — already true), mandatory MFA, short idle-timeout sessions, admin-forced session
revocation, and a different token audience from the patient app.**

In `backend/app/core/`, `backend/app/services/`, `backend/app/repositories/`,
`backend/app/api/v1/auth/`, and `backend/app/adminui/`:

1. **JWT audience separation.** Add `audience_for_role(role) -> Literal["patient", "staff"]` in
   `app/core/security.py` (doctor/coordinator/admin/super_admin → `"staff"`, patient →
   `"patient"`). `TokenClaims` gains `aud: str` and `mfa: bool`. `create_access_token` computes
   `aud` from the role, stamps `mfa` from a new `mfa_verified` flag, and selects the access-token
   TTL per audience: a new `jwt_staff_access_token_expire_minutes` setting (15) for staff,
   existing `jwt_access_token_expire_minutes` (60) for patients. `decode_access_token` reads
   `aud`/`mfa` with safe defaults (`"patient"` / `False`) so pre-existing tokens decode without
   error. `get_current_user` in `app/core/rbac.py` validates `claims.aud` against
   `audience_for_role(user.role)` — the user's **current** DB role, not just the stale claim —
   and raises 401 `detail="audience_mismatch"` on mismatch. It also sets
   `request.state.mfa_verified = claims.mfa` for downstream dependencies.

2. **TOTP-based MFA for staff.** New migration `0023_staff_mfa_and_session_audience.py`
   (`down_revision = "0022"`, additive): table `ad_staff_mfa` (`id`, `user_id` FK → `users.id`
   unique, `totp_secret_encrypted`, `recovery_codes` JSONB default `'[]'`, `enabled_at` nullable
   — NULL means "pending enrollment", `created_at`/`updated_at`); and
   `refresh_tokens.mfa_verified BOOLEAN NOT NULL DEFAULT false`. Add model `StaffMfa` in
   `app/models/admin.py` (pattern: `StaffRole` from P31).

   In `app/core/security.py` add MFA helpers built on `pyotp` (new dependency) and
   `cryptography.fernet.Fernet` (key derived from a new `mfa_encryption_key` setting, ≥32 chars,
   validated at startup like `jwt_secret`/`otp_secret`): `generate_totp_secret`,
   `encrypt_mfa_secret` / `decrypt_mfa_secret`, `totp_provisioning_uri` (issuer "Kyros Clinic"),
   `verify_totp_code` (window ±1 step), and `generate_recovery_codes(n)` — `n` codes formatted
   `XXXXX-XXXXX` from an unambiguous alphabet, hashed at rest with the existing `hash_otp()`.

   New repository `app/repositories/staff_mfa.py`: `get_for_user`, `upsert_pending`, `confirm`,
   `disable`, `consume_recovery_code`.

   New service functions in `app/services/auth.py`: `mfa_setup` (generates a pending secret +
   provisioning URI; re-enrollment on an already-enabled account requires an MFA-verified
   session), `mfa_confirm` (verifies the TOTP code, generates and returns recovery codes once,
   marks the row enabled), `mfa_disable` (requires password re-verification + an MFA-verified
   session), and `mfa_verify` (consumes a login challenge token, accepts a TOTP code or a
   single-use recovery code, returns a full `TokenPair` with `mfa_verified=True`). Each writes
   the appropriate `ad_audit_log` row (`mfa_setup_initiated`, `mfa_enabled`, `mfa_disabled`,
   `login`).

3. **Login challenge flow.** `login()` returns `TokenPair | MfaChallenge` (new dataclass:
   `challenge_token`, `expires_in`). If the user is staff and has MFA enabled
   (`ad_staff_mfa.enabled_at IS NOT NULL`), issue a Redis-backed challenge
   (`mfa_challenge:<token>` → user id, TTL `mfa_challenge_ttl_seconds` = 300) instead of minting
   tokens, and audit-log `login` with `allowed=true`, `log_metadata={"mfa_challenge": True}`.
   `POST /v1/auth/login` (`app/api/v1/auth/router.py`) returns either `TokenResponse` or a new
   `MfaChallengeResponse` (`mfa_required: bool = True`, `challenge_token`, `expires_in`). New
   endpoints: `POST /mfa/setup` and `POST /mfa/confirm` (both `get_any_staff_user` — the new
   role-dependency union of doctor/coordinator/admin/super_admin), `POST /mfa/disable` (204,
   requires `require_mfa` — a new dependency in `app/core/rbac.py` that 401s
   `detail="mfa_required"` if `request.state.mfa_verified` is falsy), and `POST /mfa/verify`
   (public, rate-limited, body = challenge token + code, returns `TokenResponse`).

4. **Staff idle-timeout on refresh.** In `refresh()`, for staff-audience sessions, compute
   `idle_for = now - stored_refresh_token.updated_at`. If it exceeds
   `jwt_staff_idle_timeout_minutes` (60), revoke the session family, write a `token_refresh`
   denial audit row (`reason="session_idle_timeout"`), commit, and raise
   `AuthenticationError("session_idle_timeout")` — mirroring the existing reuse-detection
   (`session_revoked`) branch immediately above it. Successful refreshes thread
   `stored.mfa_verified` through to the new access/refresh token pair so the `mfa` claim survives
   rotation.

5. **Admin-forced session-kill.** `app/adminui/deps.py`: track live admin/coordinator portal
   sessions per user in a Redis set `staff_sessions:<user_id>` (best-effort `sadd`/`expire`
   alongside the existing `create_admin_session`/`create_coord_session` writes). New
   `revoke_all_portal_sessions_for_user(user_id) -> int` deletes every tracked
   `session:admin:<id>` / `sessionfresh:admin:<id>` / `session:coord:<id>` key plus the set
   itself, fails open (returns 0) on Redis errors. `app/services/staff_service.py`: new
   `revoke_staff_sessions(db, ctx, *, user_id)` (pattern: `reset_staff_password`) — revokes all
   JWT refresh-token families via `auth_repo.revoke_all_for_user` AND all portal sessions via
   `revoke_all_portal_sessions_for_user`, writes a `force_session_revoke` audit row with
   `log_metadata={"jwt_sessions_revoked": ..., "portal_sessions_revoked": ...}`. New super-admin
   endpoint `POST /admin/users/{user_id}/revoke-sessions` in `app/adminui/views/users.py`
   (`require_fresh_super_admin`, same posture as `reset-password`), with a "Sessions" section on
   `user_detail.html` gated the same way as "Reset password".

Keep the three-layer architecture: routers depend on `get_current_user` / `get_any_staff_user` /
`require_mfa`; services remain audience-agnostic beyond what's needed for TTL/idle-timeout
branching; repositories take explicit scope parameters. Add `pyotp>=2.9.0` to
`backend/pyproject.toml` dependencies and to the mypy override list (no type stubs available).

**Acceptance:**

- `audience_for_role` maps patient → `"patient"`, doctor/coordinator/admin/super_admin →
  `"staff"`. A patient access token decodes with `aud="patient"`, `mfa=False`, and a 60-minute
  TTL; a staff access token decodes with `aud="staff"` and a 15-minute TTL.
- A staff account with MFA enabled returns `MfaChallengeResponse` (not tokens) from `/login`.
  `/mfa/verify` with a valid current TOTP code, or a valid unused recovery code, returns a
  `TokenResponse` whose decoded JWT has `aud="staff"`, `mfa=true`. A wrong code or a reused
  recovery code returns 401 `detail="mfa_invalid_code"`.
- `/mfa/disable` requires both the correct password and an MFA-verified session
  (`require_mfa`); a non-MFA-verified token gets 401 `detail="mfa_required"` even with the
  correct password. After disable, `/login` for that account returns tokens directly (no
  challenge). Re-enrolling via `/mfa/setup` on an already-enabled account without an
  MFA-verified session returns 401 `detail="mfa_required"`.
- A forged token whose `aud` doesn't match the user's current role returns 401
  `detail="audience_mismatch"` on any authenticated endpoint.
- A staff refresh token idle for longer than `jwt_staff_idle_timeout_minutes` is rejected on
  `/refresh` with 401 `detail="session_idle_timeout"`, the session family is revoked
  (`revoked_at IS NOT NULL`), and a `token_refresh` denial audit row is written.
- A super admin posting to `/admin/users/{user_id}/revoke-sessions` for a staff user revokes
  that user's JWT refresh-token family (`revoked_at IS NOT NULL`) AND deletes their live
  admin/coordinator portal session keys from Redis, redirects with `?revoke=ok`, and writes an
  `allowed=true` `force_session_revoke` audit row. The same call against a patient user redirects
  with `?revoke_error=not_a_staff_role` and makes no changes.
- Both `allowed=true` and `allowed=false` decisions for every new action above are audit-logged.
  Existing patient signup/login/refresh tests are unaffected.

---

*To execute: tell Claude Code `Execute P32. Read docs/build-prompts/P32-staff-auth-plane-hardening.md, then plan before editing.`*
