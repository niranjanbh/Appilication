# P35 — SOAP Notes + ICD-10 Diagnosis Capture (backend only)

> Build prompt for the **staff-RBAC track**, hand-authored from `docs/strategy/staff-rbac-spec.md`
> §3 (Doctor (RMP) consultation workflow — "structured clinical notes (SOAP); diagnosis capture
> with ICD-10"). This track is NOT part of the P1–P30 build-spec queue and is not produced by
> `scripts/extract-build-prompts.py`. Treat this file as the working brief.

> **Sequence note.** This is step 5 of the staff-RBAC track, building on **P31 — Staff RBAC:
> Permission Model**, **P32 — Staff Auth Plane Hardening**, **P33 — PHI-Access Audit Middleware**,
> and **P34 — Consultation State Machine + TPG Gate**. Scoped **backend only** (confirmed with
> user) — doctor-portal UI (NotesPanel SOAP form, diagnosis picker) is deferred to a follow-up.
> It deliberately does **not**:
> - Replace the existing free-text `kc_doctor_notes.content` column — SOAP fields are additive,
>   alongside it.
> - Make `kc_icd10_codes` an exhaustive ICD-10 catalog or an FK/validation target for
>   `kc_diagnoses.icd10_code` — it is a curated (~26-row) search aid for autocomplete only. A
>   doctor can record a code/description outside the catalog.
> - Add DB-level uniqueness on `(consultation_id, icd10_code)` — duplicate-diagnosis prevention
>   is a service-layer pre-check (`diagnosis_service.add_diagnosis`), avoiding
>   `IntegrityError`/savepoint handling mid-transaction.
> - Touch `kc_prescriptions.diagnosis_note` (separate, pre-existing free-text field).
> - Change anything patient- or coordinator-facing — coordinator schemas already omit
>   `kc_doctor_notes`/clinical content entirely (rule 3); this prompt does not add
>   `kc_diagnoses` to any coordinator-reachable code path.

## Required reading

- `docs/strategy/staff-rbac-spec.md` §3 (Doctor (RMP) — SOAP notes, ICD-10 diagnosis capture)
- `.claude/rules/security.md` — rule 1 (cross-user PHI access returns 404), rule 3 (coordinators
  never see clinical content), rule 5 (no PHI in logs)
- `.claude/rules/migrations.md` — additive/nullable columns, explicit `ON DELETE`, working
  `downgrade()`
- `.claude/rules/backend.md` — audit log discipline (denial rows commit before raising)
- Current code reconciled against (purely additive):
  - `backend/app/models/clinic.py` — `DoctorNote` (existing `content`/`note_type`/`version`/
    `superseded_by_id`)
  - `backend/app/repositories/doctor_portal.py` — `append_doctor_note`,
    `get_notes_for_consultation`, `get_doctor_consultation_detail` (cross-user 404 pattern)
  - `backend/app/api/v1/doctor/consultations.py` — existing `_audit_ctx`/`write_audit`/
    404-then-409 pattern for notes/lab-orders
  - `backend/app/api/v1/doctor/router.py` — router registration pattern

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- One new migration (`0024_soap_notes_and_icd10.py`), additive only: `kc_doctor_notes.content`
  becomes nullable + 4 new nullable TEXT columns + a CHECK constraint requiring at least one of
  the five populated; new `kc_icd10_codes` (curated catalog, seeded) and `kc_diagnoses` tables.
  Working `downgrade()`.
- `NoteCreate`'s `model_validator` mirrors the DB CHECK constraint (defense in depth): at least
  one of `content`/`subjective`/`objective`/`assessment`/`plan` must be non-empty after
  stripping whitespace.
- Every new diagnosis endpoint (`GET`/`POST .../diagnoses`, `DELETE .../diagnoses/{id}`) follows
  the existing `_audit_ctx`/`write_audit`/404-then-409 pattern, scoped via
  `dr_repo.get_doctor_consultation_detail(doctor_id=..., consultation_id=...)`.
- `GET /v1/doctor/icd10-codes` is gated by `get_doctor_user` only (role check, no
  resource-scoping decision) — deliberately does **not** write `ad_audit_log` (non-PHI static
  reference-catalog read).
- `ruff check` and `mypy --no-incremental` pass on every changed file.
- New unit tests for `NoteCreate`/`DiagnosisCreate` validators require no DB.
- New/updated integration tests cover SOAP-only notes, content-only notes (regression),
  diagnosis CRUD, duplicate-diagnosis 409, cross-doctor 404s, plus RBAC matrix entries for
  `/v1/doctor/icd10-codes` and the diagnosis endpoints.

## Original prompt

### 1. Migration `0024_soap_notes_and_icd10.py`

- `kc_doctor_notes`: `ALTER COLUMN content DROP NOT NULL`; add nullable `TEXT` columns
  `subjective`, `objective`, `assessment`, `plan`; `CHECK` constraint
  `ck_kc_doctor_notes_has_content` requiring at least one of the five non-null. Downgrade drops
  the constraint and columns, backfills `content = ''` where null, restores `NOT NULL`.
- New `kc_icd10_codes` (curated reference/lookup, NOT exhaustive, NOT an FK target):
  `code VARCHAR(10) PK`, `description VARCHAR(255)`, `category VARCHAR(50)`, indexed on
  `category`. Seed ~26 codes spanning Kyros's verticals (thyroid, weight, PCOS, skin/hair, men's
  intimate health, hormones/TRT, longevity) plus common comorbidities (vitamin D/iron
  deficiency, anxiety, depression, insomnia, hyperlipidemia, hypertension, type 2 diabetes).
- New `kc_diagnoses`: `id UUID PK`, `consultation_id` FK → `kc_consultations` (`CASCADE`),
  `doctor_id` FK → `dr_doctors` (`RESTRICT`), `patient_id` FK → `kc_patients` (`RESTRICT`),
  `icd10_code VARCHAR(10)`, `icd10_description VARCHAR(255)` (denormalized, not validated
  against the catalog), `is_primary BOOLEAN DEFAULT false`, timestamps. Indexed on
  `consultation_id`. No uniqueness constraint on `(consultation_id, icd10_code)`.

### 2. Models (`app/models/clinic.py`)

- `DoctorNote.content` → `Mapped[str | None]` (nullable). Add `subjective`, `objective`,
  `assessment`, `plan` as `Mapped[str | None]` (`Text`, nullable).
- New `Icd10Code(Base)` — `kc_icd10_codes`, no mixins (static reference data).
- New `Diagnosis(Base, UUIDMixin, TimestampMixin)` — `kc_diagnoses`, FKs as above,
  `icd10_code`/`icd10_description`/`is_primary`.

### 3. Repository — new `app/repositories/diagnoses.py`

- `search_icd10_codes(db, *, query, limit=20)` — `ILIKE` on `code`/`description`, ordered by
  `code`.
- `list_diagnoses_for_consultation(db, *, doctor_id, consultation_id)` — scoped by `doctor_id`,
  ordered `is_primary DESC, created_at ASC`.
- `add_diagnosis(db, *, doctor_id, consultation_id, patient_id, icd10_code, icd10_description,
  is_primary)` — insert + flush.
- `delete_diagnosis(db, *, doctor_id, consultation_id, diagnosis_id)` — scoped `DELETE`, returns
  whether a row was deleted.

`app/repositories/doctor_portal.py::append_doctor_note` gains optional kwargs `content`,
`subjective`, `objective`, `assessment`, `plan` (all `str | None = None`).

### 4. Service — new `app/services/diagnosis_service.py`

`DiagnosisError(code, message="")`. `add_diagnosis(...)` lists existing diagnoses for the
consultation and raises `DiagnosisError("diagnosis_already_recorded")` if `icd10_code` already
present; otherwise delegates to the repo insert.

### 5. Schemas + endpoints (`app/api/v1/doctor/consultations.py`)

- `NoteCreate`: `content`/`subjective`/`objective`/`assessment`/`plan` all
  `str | None = Field(default=None, max_length=10_000)`, plus a `model_validator(mode="after")`
  requiring at least one non-empty-after-strip field.
- `NoteRead`: adds `content`, `subjective`, `objective`, `assessment`, `plan` (previously
  omitted `content` entirely).
- `add_consultation_note` / `list_consultation_notes` pass through and surface the new fields.
- New `DiagnosisCreate` (`icd10_code` regex `^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$`,
  `icd10_description`, `is_primary`) and `DiagnosisRead`.
- `GET/POST /consultations/{id}/diagnoses`, `DELETE /consultations/{id}/diagnoses/{diagnosis_id}`
  — doctor-only, `_audit_ctx`/`write_audit`/404-then-409 pattern (404 for not-own/not-found, 409
  `diagnosis_already_recorded` on duplicate).

### 6. New file `app/api/v1/doctor/icd10.py` + router registration

`GET /icd10-codes?q=...` → `list[Icd10CodeRead]`, gated by `get_doctor_user`, no audit write.
Registered in `app/api/v1/doctor/router.py`.

## Acceptance

- `POST /v1/doctor/consultations/{id}/notes` with only SOAP fields (no `content`) returns
  **201**; `GET` returns the note with `content: null` and the SOAP fields populated.
- The existing `content`-only flow still works (regression) — `GET` returns
  `subjective`/`objective`/`assessment`/`plan: null`.
- `POST .../notes` with all five fields empty/whitespace returns **422**.
- `GET /v1/doctor/icd10-codes?q=polycystic` returns **200** including `E28.2`.
- `POST /v1/doctor/consultations/{id}/diagnoses` happy path returns **201**; `GET` lists it,
  primary diagnoses ordered first.
- A duplicate `icd10_code` on the same consultation returns **409**
  `diagnosis_already_recorded`.
- Cross-doctor `GET`/`POST`/`DELETE` on `.../diagnoses` return **404**, with an `ad_audit_log`
  row `reason="not_own_or_not_found"`.
- `DELETE .../diagnoses/{id}` returns **204**; subsequent `GET` no longer includes it.
- `tests/integration/api/test_rbac_matrix.py` gains entries for `/v1/doctor/icd10-codes`
  (doctor=200, patient/coordinator=403, no-auth=401) and
  `/v1/doctor/consultations/{id}/diagnoses` GET/POST/DELETE (doctor=200/201/204 + 404 unowned,
  patient/coordinator=403, no-auth=401).
- `tests/unit/test_note_schema.py` and `tests/unit/test_diagnosis_schema.py` exercise the new
  validators with no DB.
- `ruff check` and `mypy --no-incremental` pass on all changed `app/` and test files.
- `make test` — run if Docker is available; otherwise note as not-run, consistent with
  P31–P34.

---

*To execute: tell Claude Code `Execute P35. Read docs/build-prompts/P35-soap-notes-icd10.md, then plan before editing.`*
