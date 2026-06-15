# P34 — Consultation State Machine + TPG Consent/Identity Hard Gate

> Build prompt for the **staff-RBAC track**, hand-authored from `docs/strategy/staff-rbac-spec.md`
> §5 (Cross-Cutting Concerns — explicit state machines with allowed-actor transitions), §3 (Doctor
> (RMP) — consent + identity-verification as a TPG hard gate on opening a consult), and §2 (Admin —
> an `unverified` doctor cannot be assigned a consult, enforced as a state precondition). This
> track is NOT part of the P1–P30 build-spec queue and is not produced by
> `scripts/extract-build-prompts.py`. Treat this file as the working brief.

> **Sequence note.** This is step 4 of the staff-RBAC track, building on **P31 — Staff RBAC:
> Permission Model + Role-Context Stamping**, **P32 — Staff Auth Plane Hardening**, and **P33 —
> PHI-Access Audit Middleware**. It deliberately does **not**:
> - Rename `ConsultationStatus.SCHEDULED` to `booked`, or add `prescription_issued` / `follow_up`
>   / `closed` states — those conflate the consultation lifecycle with the already-separately-
>   tracked `PrescriptionStatus` and are deferred (no decision needed yet).
> - Retrofit `_assert_transition` into the existing `confirm_payment`, `cancel_consultation`,
>   `admin_cancel_consultation`, or `admin_mark_no_show` paths — those already encode equivalent
>   checks ad-hoc and were verified consistent with the new table. Only the two **new**
>   transitions (open/complete) consult it.
> - Add any migration, Postgres enum value, or model column. `in_progress` / `completed` already
>   exist in the `consultation_status` Postgres type (migration 0008, never previously set by any
>   code path); `ConsentType.TELEMEDICINE` already exists (migration 0002); `User.phone_verified`
>   and `ad_consent_records` already exist.
> Do not pull P35 scope (SOAP notes + ICD-10) forward.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/staff-rbac-spec.md` — §5 (Cross-Cutting Concerns — state machines), §3 (Doctor
  (RMP) — TPG consent/identity hard gate), §2 (Admin — unverified-doctor precondition)
- `.claude/rules/security.md` — rule 1 (cross-user PHI access returns 404), rule 5 (no PHI in
  logs)
- `.claude/rules/backend.md` — audit log discipline (denial rows commit before raising)
- Current code to reconcile against (do not skip — this prompt is purely additive):
  - `backend/app/db/enums.py` — `ConsultationStatus` (scheduled/confirmed/in_progress/completed/
    cancelled/no_show), `DoctorStatus`, `ConsentType.TELEMEDICINE`
  - `backend/app/services/consultation_service.py` — `book_consultation`, `confirm_payment`,
    `cancel_consultation`, `admin_cancel_consultation`, `admin_reassign_consultation`,
    `admin_mark_no_show` (existing ad-hoc transition checks to reconcile against, not rewrite)
  - `backend/app/repositories/consultations.py` — `get_consultation_for_doctor`,
    `update_consultation`, `get_patient_record`
  - `backend/app/repositories/coordinator_portal.py` — `book_consultation_for_patient`
  - `backend/app/repositories/consent.py` — `get_active_consent`
  - `backend/app/models/identity.py` — `User.phone_verified` (TPG identity-verification proxy)
  - `backend/app/api/v1/doctor/video.py` — `doctor_join_consultation` (where the TPG gate fires,
    before the `video_room_id` readiness check)
  - `backend/app/api/v1/doctor/consultations.py` — existing `_audit_ctx` / `write_audit` /
    404-then-409 pattern to follow for the new `complete` endpoint
  - `backend/app/api/v1/clinic/consultations.py` — `book_consultation` error-mapping block

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- No new migration, no new Postgres enum values, no model column changes. If you find a genuine
  need for one, stop and flag it — it likely means the scope has drifted from this prompt.
- `_ALLOWED_TRANSITIONS` / `_assert_transition` is added as the canonical state-machine
  reference (spec §5) but only governs the two **new** transitions (open → in_progress,
  in_progress → complete). Existing transition checks are left untouched.
- The TPG consent/identity gate fires on the **doctor's** join endpoint only — the patient's own
  `/join` endpoint is unchanged (TPG places the verification obligation on the RMP, not the
  patient).
- Every new denial path (`doctor_not_available`, `identity_not_verified`,
  `telemedicine_consent_missing`, `consultation_not_open_eligible`,
  `consultation_not_in_progress`, cross-doctor 404 on `complete`) writes an `ad_audit_log` row
  via `write_audit(..., allowed=False, reason=<code>)` before raising.
- `ruff check` and `mypy --no-incremental` pass on every changed file.
- New unit tests for `_assert_transition` / `_ALLOWED_TRANSITIONS` require no DB.
- New/updated integration tests cover both the happy path and every new denial code, plus RBAC
  matrix entries (401/403/404) for the new `complete` endpoint.

## Original prompt

### 1. Explicit transition table (`app/services/consultation_service.py`)

Add a small table + helper as the canonical reference for spec §5:

```python
_ALLOWED_TRANSITIONS: dict[ConsultationStatus, frozenset[ConsultationStatus]] = {
    ConsultationStatus.SCHEDULED: frozenset(
        {ConsultationStatus.CONFIRMED, ConsultationStatus.CANCELLED, ConsultationStatus.NO_SHOW}
    ),
    ConsultationStatus.CONFIRMED: frozenset(
        {ConsultationStatus.IN_PROGRESS, ConsultationStatus.CANCELLED, ConsultationStatus.NO_SHOW}
    ),
    ConsultationStatus.IN_PROGRESS: frozenset({ConsultationStatus.COMPLETED}),
    ConsultationStatus.COMPLETED: frozenset(),
    ConsultationStatus.CANCELLED: frozenset(),
    ConsultationStatus.NO_SHOW: frozenset(),
}

def _assert_transition(
    current: ConsultationStatus,
    new: ConsultationStatus,
    *,
    error_code: str = "invalid_transition",
) -> None:
    if new not in _ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise ConsultationError(error_code)
```

Used by the two **new** transitions below (open/complete). Existing functions
(`confirm_payment`, `admin_cancel_consultation`, `cancel_consultation`, `admin_mark_no_show`)
already encode equivalent checks ad-hoc and are left untouched — verified consistent with the
table, not retrofitted (keeps the diff focused).

### 2. Doctor-verified precondition at booking (spec §2)

- `consultation_service.book_consultation`: after resolving `patient`, fetch
  `db.get(Doctor, doctor_id)`. If `None` or `doctor.status != DoctorStatus.ACTIVE` →
  `ConsultationError("doctor_not_available")`.
- Router `app/api/v1/clinic/consultations.py::book_consultation`: map
  `doctor_not_available` → **409** (alongside the existing `slot_not_available` → 409 mapping).
- `app/repositories/coordinator_portal.py::book_consultation_for_patient`: after the slot lock
  succeeds, fetch the `Doctor` via `slot.doctor_id`; if not `ACTIVE`, return `None` (same
  generic "slot unavailable" path the coordinator UI already handles — no new error surface
  needed there).
- All existing test fixtures create doctors with `status=DoctorStatus.ACTIVE`, so this is
  non-breaking.

### 3. TPG consent + identity-verification hard gate on doctor "open consult"

New service function `consultation_service.open_consultation(db, *, consultation_id, doctor_id)`:

1. `consultations_repo.get_consultation_for_doctor(...)` → `None` →
   `ConsultationError("consultation_not_found")`.
2. If `status == IN_PROGRESS` → return as-is (idempotent reconnect — re-joining an already-open
   consult must not error or re-stamp `actual_start_at`).
3. `_assert_transition(status, IN_PROGRESS, error_code="consultation_not_open_eligible")` —
   rejects opening a `SCHEDULED` (unpaid), `COMPLETED`, `CANCELLED`, or `NO_SHOW` consult.
4. New repo helper `consultations_repo.get_patient_user_for_consultation(db, patient_id=...)`
   → joins `kc_patients` → `users`. If `None` or `not user.phone_verified` →
   `ConsultationError("identity_not_verified")` (TPG identity-verification proxy: phone OTP
   verification at registration).
5. `consent_repo.get_active_consent(db, user_id=patient_user.id, consent_type=ConsentType.TELEMEDICINE)`
   → `None` → `ConsultationError("telemedicine_consent_missing")`.
6. `consultations_repo.update_consultation(..., status=IN_PROGRESS, actual_start_at=now())`.

Router `app/api/v1/doctor/video.py::doctor_join_consultation`: after the existing
`get_doctor_record`/cross-doctor-404 checks, call `open_consultation` **before** the
`video_room_id` check (TPG gate takes precedence over infra readiness). Map errors → audit +
HTTP:

- `consultation_not_found` → existing 404 path (unchanged; theoretically unreachable here since
  the same `(consultation_id, doctor_id)` lookup already succeeded in this transaction).
- `consultation_not_open_eligible` / `identity_not_verified` / `telemedicine_consent_missing`
  → **409**, `write_audit(..., allowed=False, reason=<code>)`.
- On success, proceed to the existing room-provisioned check + HMS token generation as today.

Patient's own `/join` endpoint is **unchanged** — TPG places the verification obligation on the
RMP, not the patient; patients can wait in the room before the doctor "opens" it.

### 4. End-consultation transition (IN_PROGRESS → COMPLETED)

New service function `consultation_service.complete_consultation(db, *, consultation_id, doctor_id)`:

- `get_consultation_for_doctor` → `None` → `consultation_not_found`.
- `_assert_transition(status, COMPLETED, error_code="consultation_not_in_progress")`.
- `update_consultation(..., status=COMPLETED, actual_end_at=now())`.

New endpoint `POST /v1/doctor/consultations/{consultation_id}/complete` in
`app/api/v1/doctor/consultations.py`, doctor-only (`get_doctor_user`), following the existing
`_audit_ctx`/`write_audit`/404-then-409 pattern in that file. Response schema
`ConsultationCompleteResponse(id, status, actual_end_at)`.

## Acceptance

- `POST /v1/clinic/patient/consultations` against a doctor with `status=DoctorStatus.INACTIVE`
  returns **409** `{"detail": "doctor_not_available"}`.
- A doctor `POST`-ing `/v1/doctor/consultations/{id}/join` (video join) on their own
  `CONFIRMED` consult, where the patient has `phone_verified=True` and an active `TELEMEDICINE`
  consent, returns **200**, the consultation transitions to `IN_PROGRESS` with `actual_start_at`
  set, and re-joining (now `IN_PROGRESS`) is idempotent — still **200**, `actual_start_at`
  unchanged.
- The same join, with `phone_verified=False`, returns **409** `identity_not_verified`; the
  consultation stays `CONFIRMED`; an `ad_audit_log` row with `reason="identity_not_verified"`
  exists.
- The same join, with `phone_verified=True` but no `TELEMEDICINE` consent, returns **409**
  `telemedicine_consent_missing`; the consultation stays `CONFIRMED`.
- The same join against a `SCHEDULED` (unpaid) consult returns **409**
  `consultation_not_open_eligible`.
- `POST /v1/doctor/consultations/{id}/complete` on an `IN_PROGRESS` consult owned by the calling
  doctor returns **200**, status `COMPLETED`, `actual_end_at` set.
- The same `complete` call on a `CONFIRMED` (never opened) consult returns **409**
  `consultation_not_in_progress`; status stays `CONFIRMED`.
- The same `complete` call on another doctor's consultation returns **404** (cross-user
  pattern — rule 1).
- `tests/integration/api/test_rbac_matrix.py` gains entries for
  `/v1/doctor/consultations/{id}/complete`: no-auth → 401, patient → 403, coordinator → 403,
  doctor on unowned resource → 404.
- `tests/unit/test_consultation_state_machine.py` exercises `_ALLOWED_TRANSITIONS` /
  `_assert_transition` with no DB.
- `ruff check` and `mypy --no-incremental` pass on all changed `app/` and test files.
- `make test` — run if Docker is available; otherwise note as not-run, consistent with
  P31–P33.

---

*To execute: tell Claude Code `Execute P34. Read docs/build-prompts/P34-consultation-state-machine-tpg-gate.md, then plan before editing.`*
