# Security Non-Negotiables

These twenty rules are inviolable. Code that violates them does not merge. They apply to every
file in this repository regardless of language or surface.

## PHI and access control

1. **Cross-user PHI access returns 404, never 403.** A patient probing for another patient's
   resources must not be able to enumerate by status code. Filtering happens at the SQL layer
   in repository functions, not at the response-shaping layer.

2. **Draft prescriptions are never visible to patients by any path.** Repository-level filter
   excludes `status='draft'` for patient queries. Signed-URL generation refuses for drafts.

3. **Coordinators never see lab values, prescription contents, or doctor notes — at the schema
   layer.** Coordinator-scoped Pydantic schemas omit clinical fields. A coordinator-routed
   endpoint that uses a non-coordinator schema is a code review reject.

4. **Doctor-only fields are physically separated from patient-visible content by repository
   function.** Patients never query `kc_doctor_notes` directly; doctor-visible views project
   explicit fields.

5. **Every authorization decision is audit-logged.** Both `allowed=true` and `allowed=false`
   write to `ad_audit_log`. The audit log is the artifact of compliance, not a debugging tool.

## Encryption, secrets, transport

6. **All PHI in S3 is encrypted with SSE-KMS, and S3 objects are never public.** Bucket
   policies enforce `aws:SecureTransport` and deny `s3:GetObject` to `principal: "*"`.

7. **All inbound API traffic terminates at TLS 1.3.** HTTP redirects to HTTPS. HSTS with
   preload. Mobile app pins certificates.

8. **JWT secrets and OTP secrets are minimum 32 characters and validated at startup.**
   Production refuses to start with default placeholder values.

9. **Pre-signed S3 URLs have maximum 15-minute TTL.** Long-lived signed URLs are a liability.
   UIs needing longer access re-request.

10. **No PHI in application logs, ever.** Patient names, phone numbers, lab values, prescription
    contents are never logged. structlog and Sentry have PHI scrubbers. Reviews enforce this.

## Data discipline

11. **All money is stored in paise as integers.** No `float`, no `Decimal` at the storage
    boundary. Display conversion to rupees is presentation-layer.

12. **Audit log entries are immutable.** Postgres trigger blocks UPDATE/DELETE on
    `ad_audit_log`. A daily integrity hash check validates the chain.

13. **Redis is never the source of truth for any business state.** OTPs, rate limits,
    idempotency keys, and locks live in Redis with TTLs. Anything durable lives in Postgres.

14. **Data residency: every byte of PHI lives in `ap-south-1` (Mumbai) or the India region of
    the third-party service.** No cross-region replication outside India. No third-party tools
    without India residency.

## Operational discipline

15. **Migrations never run implicitly on application boot.** A new deploy with a pending
    migration is a failed deploy. The schema-head check at startup is the safety net.

16. **Webhook handlers are idempotent and verify HMAC signatures.** No webhook handler trusts
    its body without signature verification. Replay of the same event ID is a no-op.

17. **OCR retry logic is idempotent.** A task that runs twice on the same lab report produces
    the same result and updates the row at most once.

18. **Refresh tokens rotate on use, with reuse detection.** A reused refresh token revokes the
    entire session family. Implementation per OAuth 2.0 BCP.

## Patient-facing flows

19. **Patient profile changes require re-verification of contact info.** Email changes require
    email OTP. Phone changes require SMS OTP. Both at once require both.

20. **Doctor consent for recording is captured per consultation, before the call starts.**
    Stored in `ad_consent_records` with the consent text hash. No blanket recording.

---

## When in doubt

If you cannot tell whether an implementation choice violates one of these twenty rules, stop
and ask the user. A delayed PR is recoverable; a PHI leak is a 72-hour breach notification
under DPDP.

For the full reasoning behind these rules, read `docs/strategy/backend-strategy.md` section 17.
