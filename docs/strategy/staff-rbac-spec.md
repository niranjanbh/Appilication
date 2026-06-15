---
name: kyros-staff-rbac-spec
description: Target design for the Kyros staff-side access model — Admin, Doctor (RMP), and Care Coordinator. Defines the permission model, per-role feature sets, and cross-cutting backend concerns (audit, state machines, sign-off service, retention vs. erasure). This is a build-spec, not a skill. Reconcile against the current backend before implementing.
status: design source — DO NOT implement wholesale; sequence into P-prompts first
related: kyros-clinical-compliance (regulatory rules), kyros-business-strategy (operating principle, honest state)
---

# Kyros Staff RBAC — Build Spec

**How to use this file (for Claude Code):** This is the *target design* for the staff-facing access model. Do **not** implement it wholesale. First reconcile it against the current backend — report what already exists, what conflicts, and what is missing. Then propose a sequenced build plan as separate P-prompts (one concern per prompt), starting with RBAC + audit scaffolding, then the doctor consult + prescription surface. Wait for "go" before writing code.

The three roles are **not three dashboards** — they are three permission boundaries over the same patient and consultation data, governed by TPG 2020, NMC ethics, and DPDP. The access model is decided before features.

---

## 1. Access Model (decide before features)

RBAC for *what* + row-level ABAC for *whose data*. A flat role-to-screen map fails audit.

- **Roles are permission bundles, not identities.** Define granular `resource:action` permissions (`prescription:create`, `patient:read:assigned`, `patient:read:redacted`, `audit:read`, `payout:compute`) and compose roles from them. At pre-launch, founders/first doctors hold multiple roles — permissions resolve as the **union**, but every action is stamped with the **role-context it was taken under** (a doctor-admin writes a prescription *as the RMP*, for clinical liability).
- **Row-level scoping is separate from role.** Doctor sees only assigned patients; coordinator sees the ops queue with a redacted projection; admin sees all. Enforce at the query + serialization layer with **per-role Pydantic response models**, not in the UI. The coordinator must not be able to deserialize a clinical note.
- **Staff auth is a separate plane from patient auth** — provisioned accounts (no self-signup), mandatory MFA, short idle-timeout sessions, admin-forced session revocation, different token audience from the patient app.

---

## 2. Admin

- **Identity & access:** create/update/suspend/deactivate staff; assign/revoke roles; force MFA/password reset and session kill.
- **Doctor credentialing (gate that blocks consults):** onboarding intake (NMC reg number, qualification, specialty, ID, signature specimen); NMC verification-status tracking; vertical assignment (which of the 7); capacity caps. An `unverified` doctor cannot be assigned a consult — enforce as a state precondition, not a UI hide.
- **Content publication control:** publish-side of the universal sign-off gate — review queue across condition pages, articles, social, ad copy, with version history and an immutable "who approved + published, when" trail. **Doctor approves, admin publishes** — separate actions for separation of duties.
- **Compliance & data rights:** immutable audit-log viewer; consent registry; DPDP data-principal request handling (access/erasure/correction); retention-policy enforcement.
- **Financial/ops:** Razorpay settlement reconciliation; refund approval; doctor payout computation; **pricing as config** (₹500–700 / ₹400–600 never hardcoded); coupon management (constrained by DMR Act).
- **Platform config:** vertical enable/disable, feature flags, partner-integration credentials/webhooks (Orange Health, Truemeds, MSG91, authkey, Razorpay), DLT-registered notification templates.
- **Analytics:** consult volume, conversion, doctor utilization, CAC by channel, and the lead metric — **doctor-supply health**.

---

## 3. Doctor (RMP)

- **Clinical readiness:** own profile, NMC reg, digital signature, availability calendar, capacity.
- **Consultation workflow:** scoped patient queue; pre-consult view (intake, history, prior consults, uploaded reports, **and consent + identity-verification status as a hard gate** per TPG — cannot open consult without it); live surface (async/chat Phase 1, 100ms video Phase 2); structured clinical notes (SOAP); diagnosis capture with ICD-10.
- **Prescription (heaviest compliance lift):** IMC-format e-prescription with digital signature; **Schedule-aware** drug module — Schedule X blocked outright, Schedule H/H1 with TPG conditions, prohibited-list enforced at the rules layer; GLP-1 supervision handling for the weight vertical; repeat/refill behind a re-evaluation gate, never auto.
- **Orders/referrals:** structured lab order to Orange Health; prescription routing — patient chooses the pharmacy, system must not present Truemeds as mandated; referral **decoupled from any commercial settlement** (NMC fee-splitting prohibition).
- **Approval action:** sign-off queue for content in their vertical; approve/reject with comments producing an immutable sign-off record (signer NMC reg + timestamp + artifact hash).
- **Communication:** audited async patient messaging inside consultation context; non-clinical hand-off to coordinator.

---

## 4. Care Coordinator (non-clinical ops)

The defining backend fact about this role is its **deny list** — it is a PHI surface staffed by non-clinicians.

**Can do:** intake/document-upload assistance; booking/reschedule/no-show management; **doctor-matching** (vertical + availability — the routing brain); template-driven outbound comms (reminders, follow-up nudges, re-engagement); non-clinical inbound triage with escalation to doctor; diagnostics + pharmacy fulfilment coordination (sample collection scheduled, results returned to doctor, delivery tracked); failed-payment follow-up; non-clinical adherence tracking (e.g., thyroid retest at 6 weeks overdue → flag to doctor).

**Cannot do (enforce server-side):** create/edit prescriptions; view or edit clinical notes; make clinical recommendations; access full medical history. Coordinator gets a **redacted patient projection** limited to coordination-relevant fields.

---

## 5. Cross-Cutting Concerns (where this is won or lost)

- **Audit is middleware, not per-endpoint.** Every PHI access — who, what, when, source — to an append-only `kc_audit_log`. DPDP + TPG both require it; bolting it on later means re-instrumenting every route.
- **Model lifecycles as explicit state machines** with allowed-actor transitions:
  - consultation: `booked → consent_pending → in_progress → completed → prescription_issued → follow_up/closed`
  - prescription: `draft → signed → dispensed`
  - content: `draft → pending_review → approved/rejected → published`
  This makes "who can do what when" enforceable and testable rather than scattered across handlers.
- **One generic sign-off service** stamps both content *and* clinical artifacts — same immutable approval primitive, since the universal doctor gate spans media and prescriptions.
- **Retention vs. erasure conflict must be encoded now.** DPDP grants erasure; TPG/medical-record rules mandate retention. Medical records are a statutory-retention exception — implement "erasure with legal hold": anonymize ancillary PII, retain the clinical record under the retention obligation. An erasure request must never hard-delete a consult.

---

## 6. Build Sequencing (respects the rate-limiter)

Per the operating principle (doctor recruitment before everything; zero patients today), build order is:

1. **RBAC + audit scaffolding** — permissions, role-context stamping, staff auth plane, `kc_audit_log` middleware.
2. **Doctor consult + prescription surface** — the actual rate-limiter for taking a first paying patient (pre-consult consent gate, SOAP notes, IMC e-prescription, Schedule-aware drug module).
3. **Admin credentialing + sign-off/publish** — unblocks doctor onboarding and content publication.
4. **Care Coordinator** — modeled in the permission system now, but ship as a **thin queue**, not an elaborate ops console, until there is real coordination volume. Over-building coordinator tooling pre-first-patient is the same premature-expansion trap on the ops side.
