# DPDP Breach Response Runbook

**Regulation:** Digital Personal Data Protection Act, 2023 (India)  
**Last reviewed:** 2026-06-04  
**DPO:** [Name], dpo@kyrosclinic.com  
**Legal counsel:** [Name], legal@kyrosclinic.com  

> **72-hour clock starts when Kyros becomes aware of the breach**, not when the breach occurred.

---

## Table of Contents

1. [What Constitutes a Reportable Breach](#1-what-constitutes-a-reportable-breach)
2. [Breach Assessment Checklist](#2-breach-assessment-checklist)
3. [72-Hour Response Timeline](#3-72-hour-response-timeline)
4. [Notification to Data Protection Board of India](#4-notification-to-data-protection-board-of-india)
5. [Notification to Affected Data Principals](#5-notification-to-affected-data-principals)
6. [Post-Incident Obligations](#6-post-incident-obligations)
7. [Internal Communication Protocol](#7-internal-communication-protocol)
8. [Evidence Preservation](#8-evidence-preservation)

---

## 1. What Constitutes a Reportable Breach

Under DPDP 2023, a **personal data breach** is any accidental or unauthorized breach of security leading to:
- Destruction of personal data
- Loss of personal data
- Alteration of personal data
- Unauthorized disclosure of personal data
- Unauthorized access to personal data

**Always report** (regardless of scope):
- Any unauthorized access to patient PHI (health data, lab results, prescriptions)
- Any unauthorized access to payment card data or UPI references
- Any disclosure of ABHA IDs or linked health records
- Bulk export or download of patient records without authorization
- Ransomware or malicious encryption of patient data
- Loss of a device containing unencrypted PHI

**Assess before reporting** (may not require notification):
- Internal system errors that exposed anonymized/aggregated data only
- Unsuccessful intrusion attempts with no confirmed data access
- Loss of encrypted data where keys are intact and uncompromised

**When in doubt, treat as reportable.** The cost of over-reporting is low; the cost of under-reporting is high (penalties under DPDP).

---

## 2. Breach Assessment Checklist

Complete within **4 hours of awareness:**

- [ ] Identify the nature of the breach (unauthorized access / disclosure / loss / alteration)
- [ ] Identify the data category affected:
  - [ ] Patient health data (lab values, prescriptions, doctor notes)
  - [ ] Contact information (phone, email, address)
  - [ ] ABHA / ABDM health ID
  - [ ] Financial data (payment references, bank details)
  - [ ] Authentication credentials (hashed passwords, OTP logs)
- [ ] Estimate scope: number of data principals (patients) potentially affected
- [ ] Determine the likely start time of the breach
- [ ] Determine whether the breach is ongoing (if yes, containment is priority 1)
- [ ] Identify whether any data left the `ap-south-1` region
- [ ] Check `ad_audit_log` for anomalous access patterns
- [ ] Check CloudWatch logs for unusual API call patterns
- [ ] Check S3 access logs for unauthorized object reads
- [ ] Preserve all relevant evidence (§8)

---

## 3. 72-Hour Response Timeline

### Hour 0–4: Contain and assess

1. **Contain the breach.** If breach is ongoing:
   - Revoke compromised API keys / JWT tokens immediately.
   - Block source IPs at WAF level.
   - If storage is compromised: rotate S3 bucket policy, revoke KMS key grants.
   - If database is compromised: force-disconnect sessions, rotate DB password via Secrets Manager.

2. **Assemble the incident team:**
   - Incident commander: CTO or Engineering Lead
   - DPO (mandatory from hour 0)
   - Legal counsel
   - Backend on-call engineer

3. **Open incident channel** in Slack: `#breach-YYYY-MM-DD`  
   (Private channel — invite only, do NOT post breach details in public channels.)

4. **Complete the breach assessment checklist** (§2).

### Hour 4–24: Document and decide

5. **Draft the breach notification** to the Data Protection Board of India (§4).

6. **Identify all affected data principals** (patients). Run the SQL query in §5.

7. **Draft the notification to affected data principals** (§5).

8. **Legal review** of both notification drafts.

9. **Document root cause** and interim mitigation steps.

### Hour 24–72: Notify

10. **Submit notification to Data Protection Board of India** via the official portal. Deadline: T+72h from awareness.

11. **Notify affected data principals** via registered mobile (WhatsApp + SMS) and email. Deadline: as prescribed by the DPBI on a case-by-case basis, but aim for T+72h.

12. **Document the notification** (timestamp, channel, content hash) in `ad_audit_log`.

---

## 4. Notification to Data Protection Board of India

**Portal:** https://www.meity.gov.in/data-protection-board (or as updated by MeitY)  
**Submission format:** As prescribed by DPBI rules. Submit via online portal with:

```
NOTIFICATION OF PERSONAL DATA BREACH
Data Fiduciary: Kyros Health Technologies Private Limited
CIN: [CIN]
DPO: [Name], dpo@kyrosclinic.com, +91 XXXXXXXXXX

1. Date and time of breach discovery: YYYY-MM-DD HH:MM IST

2. Nature of the breach:
   [Unauthorized access / Disclosure / Loss / Alteration — describe specifically]

3. Categories of personal data affected:
   [List: health data, contact info, ABHA ID, financial data, etc.]

4. Approximate number of data principals affected: [N]

5. Likely consequences of the breach:
   [Describe potential harm: identity fraud, medical misuse, financial loss, etc.]

6. Measures taken or proposed to address the breach:
   [Technical: key rotation, IP blocks, WAF rules]
   [Organizational: password resets, access reviews]
   [Notification: patient notifications planned for YYYY-MM-DD]

7. Contact for further information:
   DPO: [Name]
   Email: dpo@kyrosclinic.com
   Phone: +91 XXXXXXXXXX
```

**Retain a copy** of the submitted notification and the submission acknowledgment in `docs/postmortems/YYYY-MM-DD-breach-notification.pdf`.

---

## 5. Notification to Affected Data Principals

### Identify affected patients

```sql
-- Substitute the actual breach condition (e.g., IP range, time window, resource IDs)
SELECT DISTINCT u.id, u.phone, u.email, u.name
FROM ad_audit_log al
JOIN users u ON al.actor_user_id = u.id
WHERE al.created_at BETWEEN '<breach_start>' AND '<breach_end>'
  AND al.resource_type = '<affected_resource>'
  AND al.allowed = true
  -- Filter to patient actors or affected resource owners
ORDER BY u.id;
```

### Notification message template

**WhatsApp / SMS (Hindi + English):**

```
[KYROS HEALTH — SECURITY NOTICE]

Dear [Patient Name],

We are writing to inform you that Kyros Health experienced a security incident on [DATE] that may have affected your personal health data.

What happened: [Brief, plain-language description — no technical jargon]

What information was involved: [Specific categories — e.g., "your contact details and appointment history"]

What we are doing: We have [list containment measures]. We have notified the Data Protection Board of India.

What you should do:
• Be cautious of calls or messages claiming to be from Kyros asking for OTPs or passwords
• Contact us if you notice unusual activity

Contact: privacy@kyrosclinic.com | 1800-XXX-XXXX (toll-free)

We sincerely apologize for this incident and are committed to protecting your data.

— Kyros Health Team
```

### Notification delivery checklist

- [ ] Draft reviewed by DPO and legal counsel
- [ ] Sent via MSG91 (SMS) to all affected phone numbers
- [ ] Sent via AiSensy (WhatsApp) to all affected phone numbers
- [ ] Sent via SendGrid (email) to all affected email addresses
- [ ] Delivery status logged in `ad_audit_log` with `action=breach_notification_sent`
- [ ] Undeliverable contacts escalated manually

---

## 6. Post-Incident Obligations

**Within 7 days of breach closure:**
- [ ] Post-mortem completed and filed in `docs/postmortems/`
- [ ] Root cause analysis documented
- [ ] Remediation action items assigned with owners and due dates
- [ ] DPIA updated if the breach reveals new risks (§`docs/dpia-v1.md`)

**Within 30 days:**
- [ ] Follow-up report to DPBI if requested
- [ ] Security controls improved based on root cause
- [ ] Staff training updated if breach involved human error

**Ongoing:**
- Retain breach notification records for 7 years
- Include breach in annual DPIA review cycle

---

## 7. Internal Communication Protocol

**What to say internally:**
- Use `#breach-YYYY-MM-DD` (private channel only)
- Never post PHI or breach details in general channels
- Updates to board/investors via email from CEO only, after legal review

**What NOT to say:**
- Do not post on public social media until legal review
- Do not confirm or deny breach to press without legal sign-off
- Do not share patient names or data counts outside the incident team

---

## 8. Evidence Preservation

Preserve the following immediately (before any remediation steps that might overwrite):

```bash
# Export relevant CloudWatch logs
aws logs export-task \
  --log-group-name /kyros/backend-api \
  --from <epoch_ms_start> \
  --to <epoch_ms_end> \
  --destination s3://kyros-prod-evidence/breach-YYYY-MM-DD/ \
  --destination-prefix cloudwatch-api-logs/ \
  --region ap-south-1

# Export WAF logs
aws logs export-task \
  --log-group-name aws-waf-logs-kyros-production \
  --from <epoch_ms_start> \
  --to <epoch_ms_end> \
  --destination s3://kyros-prod-evidence/breach-YYYY-MM-DD/ \
  --destination-prefix waf-logs/ \
  --region ap-south-1

# Export audit log rows for the period
make shell-db
\COPY (SELECT * FROM ad_audit_log
       WHERE created_at BETWEEN '<start>' AND '<end>'
       ORDER BY created_at)
TO '/tmp/audit_log_breach.csv' CSV HEADER;
```

Store all evidence in `s3://kyros-prod-evidence/breach-YYYY-MM-DD/` (private, no public access). Tag with `DataCategory=BreachEvidence`, `RetentionYears=7`.

---

*For general operational incidents (non-breach), see `docs/runbook-prod.md`.*
