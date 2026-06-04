# Data Protection Impact Assessment — v1

**Document reference:** DPIA-KYROS-001  
**Version:** 1.0  
**Date:** 2026-06-04  
**Review due:** 2027-06-04 (annual)  
**Prepared by:** Engineering + DPO  
**Approved by:** CTO  

---

## Table of Contents

1. [Controller Identity and DPO](#1-controller-identity-and-dpo)
2. [Purpose and Scope](#2-purpose-and-scope)
3. [Data Flows and Processing Activities](#3-data-flows-and-processing-activities)
4. [Categories of Personal Data Processed](#4-categories-of-personal-data-processed)
5. [Legal Bases for Processing](#5-legal-bases-for-processing)
6. [Retention Periods](#6-retention-periods)
7. [Third-Party Processors](#7-third-party-processors)
8. [Risk Assessment](#8-risk-assessment)
9. [Controls and Residual Risk Acceptance](#9-controls-and-residual-risk-acceptance)
10. [Review and Update Schedule](#10-review-and-update-schedule)

---

## 1. Controller Identity and DPO

| Field | Detail |
|---|---|
| **Data Fiduciary (Controller)** | Kyros Health Technologies Private Limited |
| **CIN** | [Insert CIN] |
| **Registered address** | [Insert address], India |
| **Contact** | privacy@kyros.clinic |
| **Data Protection Officer (DPO)** | [Name] |
| **DPO email** | dpo@kyros.clinic |
| **DPO phone** | +91 XXXXXXXXXX |
| **DPO appointment date** | 2026-06-04 |

The DPO is independent, reports directly to the board, and has no conflict of interest with processing activities.

---

## 2. Purpose and Scope

**Platform:** Kyros Clinic — India-first telemedicine platform covering hormonal health, PCOS, thyroid, weight management, skin/hair, men's intimate health, TRT, and longevity support.

**Processing purposes:**
1. Patient registration, authentication, and identity verification
2. Booking and conducting telemedicine consultations
3. Clinical care: lab report upload, OCR processing, biomarker tracking, prescription management
4. Health data synchronization from Apple Health / Google Health Connect (with explicit consent)
5. Payment processing for consultations
6. ABHA (Ayushman Bharat Health Account) linking and health record sharing
7. Patient education and content delivery
8. Platform operations, analytics, and compliance (audit logging, DPDP request handling)
9. Notifications (appointment reminders, prescription alerts, wellness reminders)

**Data principals:** Patients of Kyros Clinic platform. Approximately [N] registered as of DPIA date.

**Necessity assessment:** All processing is necessary for the delivery of telemedicine services. Health data processing specifically is necessary to provide clinical care; no alternatives exist that would achieve the same clinical outcome without processing health data.

---

## 3. Data Flows and Processing Activities

```
Data Principal (Patient)
        │
        ▼
[Mobile App / Web Portal]
        │  HTTPS/TLS 1.3
        ▼
[AWS ALB → FastAPI Backend]  ←→  [Redis (OTP, sessions, rate limits)]
        │
   ┌────┴─────────────────┐
   │                       │
   ▼                       ▼
[RDS PostgreSQL]      [S3 (encrypted)]
[PHI: patient data,   [PHI: lab reports,
 consultations,        prescriptions,
 lab results]          recordings]
        │
        ▼
[Celery Workers]  →  Third-party integrations (see §7)
```

**Data residency:** All data is stored and processed in AWS `ap-south-1` (Mumbai). No data replication outside India. S3 objects are encrypted with SSE-KMS using a key in `ap-south-1`. RDS encrypted at rest with AWS KMS.

**Third-party flows:** See §7.

---

## 4. Categories of Personal Data Processed

| Category | Specific Data | Sensitivity |
|---|---|---|
| **Identity** | Full name, date of birth, gender | Standard personal data |
| **Contact** | Mobile phone, email address | Standard personal data |
| **Authentication** | Argon2id password hash, OTP (TTL 5 min), JWT tokens | Security-sensitive |
| **Health (Special Category)** | Lab report files (PDF/image), extracted biomarkers (glucose, TSH, hormones, etc.), prescriptions, doctor notes, consultation transcripts, ABHA ID | Sensitive personal data — highest protection |
| **Health Sync** | Steps, heart rate, HRV, sleep, weight, blood pressure, blood glucose (synced from Apple Health / Google Health Connect with explicit consent) | Sensitive personal data |
| **Financial** | Razorpay order/payment IDs, GST invoice metadata, UPI reference numbers. **No full card data is stored.** | Financial data — no PCI scope (Razorpay is PCI DSS compliant) |
| **Device / Technical** | IP address, user agent, device OS, push notification token | Technical metadata |
| **Usage** | Consultation booking patterns, app feature usage (aggregated for analytics, no individual tracking) | Low sensitivity |
| **Consent records** | Consent text hash, timestamp, version, consent type (telemedicine, data_processing, health_sync, recording) | Legal compliance data |

---

## 5. Legal Bases for Processing

| Processing Activity | Legal Basis (DPDP 2023) |
|---|---|
| Account registration and authentication | Consent (explicit, granular) |
| Telemedicine consultation delivery | Consent + contractual necessity (service delivery) |
| Lab report OCR and biomarker extraction | Consent (health_sync or data_processing consent) |
| Prescription generation and storage | Consent + legal obligation (Telemedicine Practice Guidelines, 2020) |
| Health data sync (Apple/Google Health) | Explicit consent (separate, withdrawable) |
| ABHA linking | Explicit consent (ABDM framework) |
| Payment processing | Contractual necessity |
| Audit logging (ad_audit_log) | Legal obligation (healthcare compliance) |
| Analytics (aggregated, no individual PHI) | Legitimate interest in platform operation |
| Marketing communications | Consent (marketing consent, separate from service consent) |
| DPDP data subject requests | Legal obligation |

**Children:** Platform is not directed at minors under 18. Age verification is performed at registration. If a minor account is identified, it is deactivated and data deleted under parental request.

---

## 6. Retention Periods

| Data Category | Retention Period | Basis |
|---|---|---|
| Patient account (active) | Duration of account + 7 years post-deletion request | Medical Records Act, Telemedicine Guidelines |
| Consultation records | 7 years from consultation date | MCI/NMC guidelines |
| Prescriptions | 7 years | Medical Records Act |
| Lab reports | 7 years | Medical Records Act |
| Audit log (`ad_audit_log`) | 7 years | Legal compliance / DPDP accountability |
| Consent records | 7 years from withdrawal | DPDP 2023 accountability |
| Payment records | 7 years | GST and financial record-keeping |
| Health sync data (`wn_health_datapoints`) | 3 years from sync date, or account deletion | Minimal necessary for care continuity |
| OTP (Redis) | 5 minutes (TTL) | Authentication security |
| JWT access tokens | 60 minutes (expiry) | Authentication security |
| JWT refresh tokens | 30 days (expiry), invalidated on use | Authentication security |
| Pre-signed S3 URLs | 15 minutes (TTL) | Security (short-lived access) |
| Analytics aggregates (ad_daily_metrics) | 3 years | Business analytics |
| DPDP erasure requests | Records retained 3 years post-completion (without PHI) | DPDP accountability |

**Data deletion:** On confirmed DPDP erasure request, PHI is deleted from Postgres, S3 objects deleted, Sentry events purged. Anonymized audit records (no PHI in `metadata`) are retained for the audit log retention period.

---

## 7. Third-Party Processors

All third-party processors are bound by data processing agreements. PHI is not shared with processors unless necessary for service delivery.

| Processor | Purpose | Data Shared | India Residency |
|---|---|---|---|
| **AWS** (ap-south-1) | Infrastructure (RDS, S3, ElastiCache, ECR, Secrets Manager, CloudWatch) | All categories | Yes — ap-south-1 |
| **MSG91** | SMS OTP delivery | Phone number + OTP only | Yes — India operations |
| **AiSensy** | WhatsApp utility messages | Phone number + templated message content | Yes — India operations |
| **SendGrid** | Transactional email | Email address + notification content | Confirm India data processing terms before production |
| **Razorpay** | Payment processing | Payment metadata (no PHI) | Yes — PCI DSS, India |
| **100ms (HMS)** | Video consultation infrastructure | Consultation room metadata, recording storage | Confirm ap-south-1 recording storage |
| **Google Document AI** | Lab report OCR | Lab report images (processing only, no storage) | Confirm asia-south1 residency |
| **Sentry** | Error monitoring | Stack traces (PHI scrubbed before send) | Review Sentry India data residency |
| **ElevenLabs** | Content voice synthesis | Article text (no PHI) | Review residency |
| **Expo** | Mobile push notifications | Push notification token + notification content | Review |

**Action items:**
- [ ] Obtain DPA from SendGrid confirming India data processing or migrate to a DPDP-compliant alternative.
- [ ] Confirm 100ms (HMS) stores recordings exclusively in ap-south-1.
- [ ] Confirm Sentry EU region is acceptable under DPDP or migrate to Sentry US (note: DPDP may require India residency — legal review needed).
- [ ] Obtain DPAs from all processors before production launch.

---

## 8. Risk Assessment

### Risk 1: Unauthorized access to patient PHI

| | |
|---|---|
| **Description** | Attacker gains API access to patient health records, lab results, or prescriptions belonging to other patients. |
| **Threat** | Compromised JWT token, IDOR/authorization bypass, compromised admin account. |
| **Likelihood** | Low (cross-user 404 pattern, scoped repository queries, JWT expiry 60 min) |
| **Impact** | High (health data disclosure, DPDP reportable) |
| **Inherent risk** | Medium-High |
| **Controls** | Cross-user 404 (not 403) at SQL layer; JWT short expiry + refresh rotation; WAF + rate limiting; MFA for admin; audit logging every access decision; PHI scrubbing in Sentry/logs. |
| **Residual risk** | Low |

### Risk 2: Unauthorized access to S3 lab reports or prescriptions

| | |
|---|---|
| **Description** | Direct access to S3-stored PHI files (lab PDFs, prescription PDFs). |
| **Threat** | Misconfigured bucket policy, leaked pre-signed URL, compromised IAM role. |
| **Likelihood** | Low |
| **Impact** | High |
| **Inherent risk** | Medium |
| **Controls** | Bucket policy blocks public access; SSE-KMS encryption; pre-signed URLs expire in 15 min; IAM least-privilege (ECS task role); no S3 object ACLs; S3 access logging enabled; `aws:SecureTransport` condition on bucket policy. |
| **Residual risk** | Low |

### Risk 3: Data breach via third-party processor

| | |
|---|---|
| **Description** | Third-party processor (SMS provider, video platform, OCR service) experiences a breach that exposes Kyros patient data. |
| **Threat** | Processor security incident. |
| **Likelihood** | Low-Medium (supply chain risk) |
| **Impact** | High (if PHI was involved) |
| **Inherent risk** | Medium |
| **Controls** | Minimal PHI shared (only what is necessary); PHI scrubbed from Sentry before send; DPAs with all processors; annual processor review; processor contracts require breach notification within 24 hours. |
| **Residual risk** | Low-Medium (dependent on processor security posture) |

### Risk 4: Insider threat (compromised coordinator or admin account)

| | |
|---|---|
| **Description** | Coordinator or admin account compromised; used to exfiltrate patient records or alter clinical data. |
| **Threat** | Phishing, weak password, social engineering. |
| **Likelihood** | Low-Medium |
| **Impact** | High |
| **Inherent risk** | Medium |
| **Controls** | Coordinator schema strips clinical fields (lab values, prescriptions, doctor notes); audit log on every access decision; anomaly detection (>20 denials/hour per actor fires Sentry warning); admin accounts require strong passwords + 2FA; session timeout; IP allowlist for admin portal (production). |
| **Residual risk** | Low |

### Risk 5: Violation of data retention obligations

| | |
|---|---|
| **Description** | Patient data retained longer than necessary, or deleted before legally required retention period expires. |
| **Threat** | Missing automated deletion, incorrect retention policy. |
| **Likelihood** | Low-Medium |
| **Impact** | Medium (regulatory) |
| **Inherent risk** | Medium |
| **Controls** | Documented retention periods (§6); DPDP erasure Celery task with audit trail; DPO reviews retention policy annually; no ad-hoc data deletion without DPDP request process. |
| **Residual risk** | Low |

---

## 9. Controls and Residual Risk Acceptance

**Overall residual risk: LOW — acceptable for production operation.**

The following conditions must remain true for this acceptance to hold:
1. DPAs are in place with all processors in §7 before processing begins.
2. The PHI scrubbing filters in Sentry and structlog are maintained and tested with each release.
3. The audit log trigger blocking UPDATE/DELETE on `ad_audit_log` is not disabled.
4. Pre-signed URL TTL of 15 minutes is not increased without DPO approval.
5. The DPDP erasure task is tested quarterly.
6. Admin portal is IP-allowlisted in production.
7. DPO reviews this DPIA annually and after any significant change to processing scope.

**Significant changes requiring DPIA update:**
- Adding a new category of sensitive data processing
- Integrating a new third-party processor that receives PHI
- Expanding to a new country or jurisdiction
- Introducing AI-based clinical decision support
- Enabling cross-patient aggregate analytics that could re-identify individuals
- Any security incident that changes the risk landscape

---

## 10. Review and Update Schedule

| Review trigger | Action |
|---|---|
| Annual (due 2027-06-04) | Full DPIA review — update all sections |
| New processor receiving PHI | Add to §7, re-assess §8 |
| New data category | Add to §4, update §5 and §6 |
| Security incident | Review and update affected risk in §8 |
| Regulatory change (DPDP rules update) | Legal review, update §5 |
| Significant feature addition | Assess new processing, amend document |

**Version history:**

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-04 | Engineering + DPO | Initial DPIA for P30 production readiness |

---

*For breach response procedure, see `docs/dpdp-breach-runbook.md`.*  
*For production operational procedures, see `docs/runbook-prod.md`.*
