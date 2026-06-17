# P36 — Schedule-Aware Drug Module (backend only)

> Build prompt for the **staff-RBAC track**, hand-authored from `docs/strategy/staff-rbac-spec.md`
> §3 (Doctor (RMP) prescription surface — "Schedule-aware drug module").

> **Sequence note.** This is step 6 of the staff-RBAC track, building on **P31–P35**. Scoped
> **backend only** (confirmed with user) — doctor-portal UI (drug search autocomplete, schedule
> badge display) is deferred to a follow-up. It deliberately does **not**:
> - Make `kc_drug_catalogue` an exhaustive ICD formulary or an FK/validation target for
>   `kc_prescription_items.drug_generic_name` — it is a curated enforcement-and-autocomplete aid
>   (~55 drugs). Drugs not in the catalogue pass through with `drug_schedule=NULL`.
> - Add a FK from `kc_prescription_items.drug_schedule` to the catalogue.
> - Perform drug interaction checking (separate future concern).
> - Change the PDF template or `kc_prescriptions.diagnosis_note`.
> - Change anything patient- or coordinator-facing.

## Required reading

- `docs/strategy/staff-rbac-spec.md` §3 (Doctor prescription surface — schedule-aware drug module)
- `.claude/rules/security.md` — rule 5 (no PHI in logs), rule 3 (coordinators never see
  clinical content)
- `.claude/rules/migrations.md` — additive/nullable columns, working `downgrade()`
- Current code reconciled against (purely additive):
  - `backend/app/models/clinic.py` — `PrescriptionItem` (existing columns)
  - `backend/app/services/prescription_service.py` — `create_draft`/`update_draft` (service layer)
  - `backend/app/repositories/prescriptions.py` — item constructor pattern
  - `backend/app/api/v1/doctor/prescriptions.py` — existing `_audit_ctx`/`write_audit`/
    404-then-error pattern

## Acceptance gates

- One new migration (`0025_drug_catalogue_and_schedule.py`): `kc_drug_catalogue` table (seeded
  with ~55 drugs); nullable `drug_schedule VARCHAR(10)` on `kc_prescription_items`. Working
  `downgrade()`.
- Pure `check_drug_entry` function in `prescription_service.py` (no async/DB) enforces: blocked
  drugs (`is_prohibited` → 422 `drug_prohibited`); Schedule X → 422
  `schedule_x_not_prescribable`; Schedule H1 → 422
  `schedule_h1_not_prescribable_via_telemedicine`; vertical restriction → 422
  `drug_requires_specialist_vertical`. Schedule H and NONE pass through.
- `_check_refill_gate` raises `refill_requires_prior_consultation` (422) when any item has
  `refill_allowed=True` and the patient has no prior COMPLETED consultation.
- Exception handler in `create_prescription` / `update_prescription` splits:
  ownership errors → 404; schedule/refill errors → 422 with machine-readable `detail`.
- `GET /v1/doctor/drugs?q=...` returns Schedule H / NONE drugs only (blocks X/H1/prohibited
  from autocomplete). Role-gated by `get_doctor_user`. No audit write.
- `ruff check` and `mypy --no-incremental` pass on every changed file.
- 8 pure unit tests (no DB) pass for `check_drug_entry`.
- Integration tests cover: catalogue search, Schedule X/H1/prohibited rejection, GLP-1 vertical
  enforcement, unknown-drug passthrough, refill gate (blocked and allowed). RBAC matrix gains
  `/v1/doctor/drugs` entries.

## Original prompt

### 1. Migration `0025_drug_catalogue_and_schedule.py`

New `kc_drug_catalogue`:
- `drug_generic_name VARCHAR(255) PK` (lowercase INN)
- `drug_schedule VARCHAR(10) NOT NULL` ('NONE', 'H', 'H1', 'X')
- `is_prohibited BOOLEAN NOT NULL DEFAULT false` (CDSCO-banned)
- `requires_vertical VARCHAR(50) NULL` (e.g. 'weight' for GLP-1s)
- Index on `drug_schedule`
- Seeded with ~55 drugs across Kyros verticals + common comorbidities + blocked drugs (Schedule X:
  alprazolam/diazepam/nitrazepam/clonazepam/lorazepam/zolpidem/tramadol/codeine/buprenorphine;
  Schedule H1: isotretinoin/ceftriaxone/meropenem; prohibited: sibutramine/phenformin/rofecoxib/
  cisapride)

`kc_prescription_items`: add nullable `drug_schedule VARCHAR(10)` (populated at write time).

### 2. Models (`app/models/clinic.py`)

- `PrescriptionItem.drug_schedule: Mapped[str | None]` (String(10), nullable)
- New `DrugCatalogue(Base)` (no mixins, static reference): `drug_generic_name`/`drug_schedule`/
  `is_prohibited`/`requires_vertical`

### 3. Repositories

New `app/repositories/drug_catalogue.py`:
- `lookup_drug(db, *, name)` — `func.lower()` case-insensitive match
- `search_drugs(db, *, query, limit=20)` — ILIKE, excludes `is_prohibited=True` and X/H1

`app/repositories/consultations.py`: add `has_prior_completed_consultation(db, *, patient_id,
exclude_consultation_id) -> bool` (`SELECT EXISTS` on `status='completed'`).

`app/repositories/prescriptions.py`: add `drug_schedule=item.get("drug_schedule")` to
`PrescriptionItem(...)` constructors in both `create_draft` and `update_draft`.

### 4. Service (`app/services/prescription_service.py`)

`PrescriptionError` upgraded with `.code` attribute (backward-compatible: `str(exc)` still
works). `_OWNERSHIP_CODES` frozenset distinguishes 404-worthy from 422-worthy codes.

Pure `check_drug_entry(*, drug_generic_name, entry: Any, doctor_verticals)` — no async/DB.

Async `_check_drug_items(db, items, doctor_verticals)` — calls `lookup_drug` per item, delegates
to `check_drug_entry`, mutates each item dict to add `"drug_schedule"` key.

Async `_check_refill_gate(db, items, *, patient_id, consultation_id)` — blocks refills without
a prior COMPLETED consultation.

`create_draft`: calls both checks (using `doctor.conditions_treated` as `doctor_verticals`).
`update_draft`: pre-fetches draft to get `patient_id`/`consultation_id`; calls both checks when
`items is not None`.

### 5. API (`app/api/v1/doctor/`)

New `drugs.py` — `GET /v1/doctor/drugs?q=...`, role-gated, no audit write.

`prescriptions.py`: `PrescriptionItemRead.drug_schedule: str | None`; error handlers use
`_prescription_http_error(exc)` (404 for ownership codes, 422 for schedule/refill codes).

`router.py`: register `drugs_router`.

## Acceptance

- `POST .../prescription` with alprazolam → 422 `schedule_x_not_prescribable`.
- `POST .../prescription` with isotretinoin → 422
  `schedule_h1_not_prescribable_via_telemedicine`.
- `POST .../prescription` with sibutramine → 422 `drug_prohibited`.
- `POST .../prescription` with semaglutide, thyroid-only doctor → 422
  `drug_requires_specialist_vertical`; weight doctor → 201.
- `POST .../prescription` with levothyroxine → 201; `GET` item shows `drug_schedule="H"`.
- `POST .../prescription` with unknown drug → 201; `GET` item shows `drug_schedule=null`.
- `POST .../prescription` with `refill_allowed=true` on first consultation → 422
  `refill_requires_prior_consultation`.
- `POST .../prescription` with `refill_allowed=true` when prior COMPLETED consult exists → 201.
- `GET /v1/doctor/drugs?q=alprazolam` → 200 but empty list (Schedule X excluded from results).
- 8/8 `tests/unit/test_drug_schedule_rules.py` pass (no DB).
- `make test` — note as not-run if Docker unavailable (consistent with P31–P35).
- `ruff check` and `mypy --no-incremental` pass on all changed files.

---

*To execute: tell Claude Code `Execute P36. Read docs/build-prompts/P36-drug-catalogue-and-schedule.md, then plan before editing.`*
