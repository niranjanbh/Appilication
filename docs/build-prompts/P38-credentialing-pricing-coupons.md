# P38 — Admin Credentialing + Pricing-as-Config + Coupons

## Prompt

Implement three ops-critical backend items:

1. **Doctor credentialing REST API** — advance pipeline (APPLIED→DOCUMENTS_SUBMITTED→VERIFIED→ONBOARDING→ACTIVE), suspend, reactivate, credential document verification. Gate: `STAFF_MANAGE`.
2. **Pricing as config** — DB-backed `ad_pricing_config` table per `(condition_category, consultation_type)`. Settings fallback when no row exists. Gate: `PRICING_MANAGE`.
3. **Coupon management** — `ad_coupons` table + DMR-Act-constrained discount logic (≤50% for percent type) + optional `coupon_code` at patient booking. `kc_consultations` gains `coupon_id` FK + `discount_paise`.

Backend only — no Jinja2/HTMX admin UI changes.

## Required reading

- `docs/strategy/staff-rbac-spec.md` §2 (credentialing pipeline), §4 (pricing + coupons)
- `docs/strategy/backend-strategy.md` §11 (RBAC), §12 (API organization)

## Acceptance criteria

- [ ] Migration `0027_pricing_and_coupons.py` creates `ad_pricing_config`, `ad_coupons`, and adds `coupon_id`+`discount_paise` to `kc_consultations`
- [ ] `GET /v1/admin/doctors` and `GET /v1/admin/doctors/{id}` return doctor list/detail
- [ ] `POST /v1/admin/doctors/{id}/advance` enforces forward-only pipeline; 409 on invalid transition
- [ ] `POST /v1/admin/doctors/{id}/suspend` (ACTIVE/INACTIVE → SUSPENDED); 409 otherwise
- [ ] `POST /v1/admin/doctors/{id}/reactivate` (SUSPENDED/INACTIVE → ACTIVE); 409 otherwise
- [ ] `GET /v1/admin/doctors/{id}/credentials` lists credential docs
- [ ] `POST /v1/admin/doctors/{id}/credentials/{cid}/verify` stamps `verified_by_admin_id`
- [ ] `GET /v1/admin/pricing` returns current config list
- [ ] `PUT /v1/admin/pricing/{category}/{type}` upserts fee; 422 on invalid category/type/fee
- [ ] `GET /v1/admin/coupons`, `POST`, `PATCH /{id}`, `DELETE /{id}` — full CRUD
- [ ] `ConsultationBookRequest` accepts optional `coupon_code`; response includes `discount_paise`
- [ ] Razorpay order uses net amount (fee − discount)
- [ ] Pricing service is async with DB lookup + settings fallback
- [ ] `compute_discount` pure function enforces DMR Act ≤50% for percent coupons
- [ ] All 8 unit tests + 10+6+8+RBAC matrix sections pass

## What was built

### Migration

`alembic/versions/0027_pricing_and_coupons.py` — creates `ad_pricing_config` (UNIQUE on condition_category+consultation_type), `ad_coupons` (CHECK constraints for discount_type and discount_value), and ALTERs `kc_consultations` to add `coupon_id` FK and `discount_paise`.

### Models

- `app/models/pricing.py` — `PricingConfig` and `Coupon` ORM classes
- `app/models/clinic.py` — `Consultation` gains `coupon_id` + `discount_paise`

### Repositories

- `app/repositories/pricing_config.py` — `get_fee`, `list_all`, `upsert` (INSERT ON CONFLICT)
- `app/repositories/coupons.py` — `get_by_code`, `get_by_id`, `list_coupons`, `create_coupon`, `update_coupon`, `deactivate_coupon`, `increment_redemption` (atomic)
- `app/repositories/admin_portal.py` — added `get_credentials_for_doctor`, `verify_credential`
- `app/repositories/consultations.py` — `create_consultation` gains `coupon_id`, `discount_paise`

### Services

- `app/services/pricing_service.py` — made async; signature `get_consultation_fee_paise(db, *, condition_category, consultation_type) -> int`; DB-backed with settings fallback
- `app/services/coupon_service.py` — `CouponError`, `compute_discount` (pure), `validate_and_apply_coupon`
- `app/services/consultation_service.py` — updated to `await` pricing; optional `coupon_code` path
- `app/adminui/views/coord/scheduling.py` — updated to `await` pricing call

### API

- `app/api/v1/admin/doctors.py` — 7 endpoints (list, detail, advance, suspend, reactivate, list-credentials, verify-credential)
- `app/api/v1/admin/pricing.py` — 2 endpoints (list, upsert)
- `app/api/v1/admin/coupons.py` — 4 endpoints (list, create, patch, delete/deactivate)
- `app/api/v1/clinic/schemas.py` — `ConsultationBookRequest.coupon_code`, `ConsultationBookResponse.discount_paise`
- `app/api/v1/clinic/consultations.py` — coupon pass-through + error handling
- `app/api/v1/router.py` — registered 3 new admin routers

### Tests

- `tests/unit/test_compute_discount.py` — 8 pure unit tests (no DB)
- `tests/integration/api/test_credentialing.py` — 10 integration tests
- `tests/integration/api/test_pricing_config.py` — 6 integration tests
- `tests/integration/api/test_coupons.py` — 8 integration tests
- `tests/integration/api/test_rbac_matrix.py` — new sections for all 13 new endpoints

## Non-goals

- No Jinja2/HTMX admin UI for credentialing/pricing/coupons
- No coupon support in coordinator booking path
- No per-patient coupon redemption limit (one-per-patient)
- No partial refund logic for coupon-discounted cancelled consultations
- No retroactive DB pricing for existing consultations
