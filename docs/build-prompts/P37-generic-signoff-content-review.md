# P37 — Generic Sign-off + Content Review/Publish Split (backend only)

> Build prompt for the **staff-RBAC track**, hand-authored from `docs/strategy/staff-rbac-spec.md`
> §3 (Content sign-off — separation of duties) and §5 (Generic sign-off service).

> **Sequence note.** This is step 7 of the staff-RBAC track, building on **P31–P36**. Scoped
> **backend only** (confirmed with user) — admin UI content pipeline (Jinja2/HTMX) and
> doctor-portal UI deferred. It deliberately does **not**:
> - Change the Jinja2 admin content templates or HTMX endpoints.
> - Send email/WhatsApp notifications to doctors when content is submitted for review (P29
>   notification system already handles templates; wiring deferred).
> - Apply sign-off to clinical artifacts (prescriptions, SOAP notes) — that is P38+.
> - Retroactively migrate existing `PUBLISHED` content (they remain PUBLISHED, no backfill needed).

## Required reading

- `docs/strategy/staff-rbac-spec.md` §3 (content sign-off — "Doctor approves, admin publishes"),
  §5 (generic sign-off service)
- `.claude/rules/security.md` — rule 5 (no PHI in logs), rule 12 (audit log immutability)
- `.claude/rules/migrations.md` — additive-only, working `downgrade()`, enum values are additive
- Current code reconciled against:
  - `backend/app/db/enums.py` — `ContentStatus` (only DRAFT/PUBLISHED/ARCHIVED before this)
  - `backend/app/api/v1/admin/content.py` — collapsed `approve` endpoint
  - `backend/app/repositories/education.py` — `approve_content` bypasses state machine
  - `backend/app/core/permissions.py` — `CONTENT_APPROVE` (doctors) / `CONTENT_PUBLISH` (super_admin)

## Acceptance gates

- Migration `0026_content_review_publish_split.py`:
  - Adds `pending_review`, `approved`, `rejected` to `content_status` enum
  - Creates `ad_sign_off_records` table (append-only, Postgres trigger blocks UPDATE/DELETE)
  - Working `downgrade()` (drops table/trigger; leaves enum values — cannot remove from Postgres)
- `ContentStatus` enum has all six values: `DRAFT`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`,
  `PUBLISHED`, `ARCHIVED`
- `ad_sign_off_records` row created on every doctor review action (approve or reject)
- State machine enforced via conditional WHERE on status (returns None on mismatch → 409)
- `POST /v1/admin/content/{id}/submit-for-review`: DRAFT → PENDING_REVIEW, any admin level
- `POST /v1/doctor/content/{id}/review`: PENDING_REVIEW → APPROVED/REJECTED, CONTENT_APPROVE
- `POST /v1/admin/content/{id}/publish`: APPROVED → PUBLISHED, CONTENT_PUBLISH (super_admin)
- Old `POST /v1/admin/content/{id}/approve` removed; replaced by `publish`
- `reviewed_by_doctor_id` + `reviewed_at` on `kc_education_content` stamped at doctor-review
  step (not at publish step)
- `ruff check` and `mypy --no-incremental` pass on every changed file
- 4 pure unit tests (`tests/unit/test_sign_off_hash.py`) pass without DB
- Integration tests cover: state transitions, sign_off row creation, wrong-state 409, RBAC
- RBAC matrix gains 4 new sections (submit-for-review, publish, GET/POST doctor/content)

## Original prompt

### 1. Migration `0026_content_review_publish_split.py`

**Enum additions** (`ALTER TYPE content_status ADD VALUE IF NOT EXISTS ...`):
- `'pending_review'`, `'approved'`, `'rejected'`

**New table `ad_sign_off_records`** (append-only):
- `id UUID PK DEFAULT gen_random_uuid()`
- `content_id UUID NOT NULL REFERENCES kc_education_content(id) ON DELETE RESTRICT`
- `doctor_id UUID NOT NULL REFERENCES dr_doctors(id) ON DELETE RESTRICT`
- `nmc_registration_number VARCHAR(50) NOT NULL` — denormalized at sign-time for audit immutability
- `artifact_hash CHAR(64) NOT NULL` — SHA-256 hex of `title|body_md|content_url` at review time
- `action VARCHAR(20) NOT NULL` — `'approved'` or `'rejected'`
- `notes TEXT NULL`
- `signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- Index on `content_id`
- Postgres trigger blocks UPDATE/DELETE (same pattern as `ad_audit_log` in migration 0003)

Downgrade: drop trigger + function + table; leave enum values.

### 2. Enum (`app/db/enums.py`)

Add to `ContentStatus`:
```python
PENDING_REVIEW = "pending_review"
APPROVED = "approved"
REJECTED = "rejected"
```

### 3. Model (`app/models/sign_off.py`)

`SignOffRecord(Base)` — follows `AuditLog` pattern (no UUIDMixin/TimestampMixin):
- `id`, `content_id`, `doctor_id`, `nmc_registration_number`, `artifact_hash`,
  `action`, `notes`, `signed_at`

### 4. Repositories

New `app/repositories/sign_off.py`:
- `create_sign_off(db, *, content_id, doctor_id, nmc_registration_number, artifact_hash,
  action, notes) -> SignOffRecord`
- `list_for_content(db, *, content_id) -> list[SignOffRecord]`

Updated `app/repositories/education.py` (additive):
- `submit_for_review(db, *, content_id)` — `UPDATE WHERE status='draft' SET 'pending_review'`
- `doctor_approve_content(db, *, content_id, doctor_id)` — stamps `reviewed_by_doctor_id` + sets `'approved'`
- `reject_content(db, *, content_id)` — `'pending_review'` → `'rejected'`
- `publish_content(db, *, content_id)` — `'approved'` → `'published'`
- `list_pending_review(db, *, page, page_size)` — doctor queue

All conditional-`WHERE` on status; returns `None` on mismatch.

### 5. Service (`app/services/sign_off_service.py`)

```python
class SignOffError(Exception): ...
_OWNERSHIP_CODES = frozenset({"content_not_found", "doctor_profile_not_found"})

def _artifact_hash(content: EducationContent) -> str: ...  # pure, SHA-256

async def submit_for_review(db, *, content_id) -> EducationContent
async def doctor_review(db, *, content_id, doctor_user_id, action, notes) -> EducationContent
async def publish_content(db, *, content_id) -> EducationContent
```

Error codes:
- `content_not_found` — not found or wrong state for transition
- `doctor_profile_not_found` — caller has no `dr_doctors` row
- `content_not_pending_review` — content not in PENDING_REVIEW at doctor review time
- `content_not_found_or_not_approved` — content not in APPROVED at publish time

### 6. API

**New `app/api/v1/doctor/content.py`**:
- `GET /v1/doctor/content` — pending-review queue, `require_permission(CONTENT_APPROVE)`
- `POST /v1/doctor/content/{id}/review` — approve/reject, `require_permission(CONTENT_APPROVE)`

**Updated `app/api/v1/admin/content.py`**:
- Added `POST /v1/admin/content/{id}/submit-for-review` — `get_admin_user`
- Renamed `POST .../approve` → `POST .../publish` — `require_permission(CONTENT_PUBLISH)`
- Removed the doctor-profile lookup from the publish step

Registered `content_router` in `app/api/v1/doctor/router.py`.

## Acceptance

- `POST /v1/admin/content/{id}/submit-for-review` on DRAFT → 200 `status=pending_review`
- `POST /v1/doctor/content/{id}/review` `{"action":"approved"}` → 200 `status=approved`
  + `ad_sign_off_records` row with `action='approved'`, 64-char `artifact_hash`
- `POST /v1/doctor/content/{id}/review` `{"action":"rejected"}` → 200 `status=rejected`
  + sign_off row with `action='rejected'`
- `POST /v1/admin/content/{id}/publish` → 200 `status=published`
- Any transition from wrong state → 409 with machine-readable `detail`
- Doctor without `dr_doctors` profile → 404 on review endpoint
- `GET /v1/doctor/content` → 200, doctor gets list; patient/coord → 403
- 4/4 `tests/unit/test_sign_off_hash.py` pass (no DB)
- `make test` — note as not-run if Docker unavailable (consistent with P31–P36)
- `ruff check` and `mypy --no-incremental` pass on all changed files

---

*To execute: tell Claude Code `Execute P37. Read docs/build-prompts/P37-generic-signoff-content-review.md, then plan before editing.`*
