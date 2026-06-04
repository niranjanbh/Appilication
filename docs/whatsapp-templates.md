# Kyros Clinic — WhatsApp Utility Templates

> Meta Business Manager submission documentation.
> All five templates are **UTILITY** category (transactional, not promotional).
> Language: `en` (English). WABA registered under Kyros Health Pvt. Ltd.
>
> Utility messages are free within the 24-hour customer service window.
> Outside the window they are charged at the utility rate (~₹0.115/msg as of 2024).
>
> Each template uses numbered positional parameters `{{1}}`, `{{2}}`, etc.
> The parameter list below maps to the `params` array passed by the AiSensy SDK.

---

## 1. `appointment_confirmation`

**Submission name:** `kyros_appointment_confirmation`  
**Category:** UTILITY  
**Language:** en  
**Header:** None  
**Footer:** "Kyros Clinic"

**Body text:**
```
Hi {{1}}, your Kyros appointment is confirmed for {{2}} at {{3}} IST. Your consultation link will be available 15 minutes before the call. Reply HELP for support.
```

**Parameters:**
| Position | Value | Example |
|---|---|---|
| `{{1}}` | Patient first name | `Priya` |
| `{{2}}` | Appointment date (DD Mon YYYY) | `15 Jun 2025` |
| `{{3}}` | Appointment time (HH:MM AM/PM) | `11:30 AM` |

**Buttons:** None (add deeplink button post-approval if needed)

**Sample message:**
> Hi Priya, your Kyros appointment is confirmed for 15 Jun 2025 at 11:30 AM IST. Your consultation link will be available 15 minutes before the call. Reply HELP for support.

---

## 2. `appointment_reminder`

**Submission name:** `kyros_appointment_reminder`  
**Category:** UTILITY  
**Language:** en  
**Header:** None  
**Footer:** "Kyros Clinic"

**Body text:**
```
Hi {{1}}, a reminder that your Kyros appointment is tomorrow at {{2}} IST. Please complete your pre-consultation questionnaire if you haven't already. Reply HELP for support.
```

**Parameters:**
| Position | Value | Example |
|---|---|---|
| `{{1}}` | Patient first name | `Arjun` |
| `{{2}}` | Appointment time (HH:MM AM/PM) | `03:00 PM` |

**Sample message:**
> Hi Arjun, a reminder that your Kyros appointment is tomorrow at 03:00 PM IST. Please complete your pre-consultation questionnaire if you haven't already. Reply HELP for support.

---

## 3. `lab_result_ready`

**Submission name:** `kyros_lab_result_ready`  
**Category:** UTILITY  
**Language:** en  
**Header:** None  
**Footer:** "Kyros Clinic"

**Body text:**
```
Hi {{1}}, your lab report has been processed and your results are ready to view in the Kyros app. Open the app to see your results. Reply HELP for support.
```

**Parameters:**
| Position | Value | Example |
|---|---|---|
| `{{1}}` | Patient first name | `Meera` |

**Note:** No lab values or condition names are mentioned. Generic language only — per PHI policy.

**Sample message:**
> Hi Meera, your lab report has been processed and your results are ready to view in the Kyros app. Open the app to see your results. Reply HELP for support.

---

## 4. `pre_consult_report_ready`

**Submission name:** `kyros_pre_consult_report_ready`  
**Category:** UTILITY  
**Language:** en  
**Header:** None  
**Footer:** "Kyros Clinic"

**Body text:**
```
Hi {{1}}, your pre-appointment health summary is ready. Your doctor will review it before your consultation at {{2}} IST. Open the Kyros app to view it. Reply HELP for support.
```

**Parameters:**
| Position | Value | Example |
|---|---|---|
| `{{1}}` | Patient first name | `Rahul` |
| `{{2}}` | Appointment time (HH:MM AM/PM) | `10:00 AM` |

**Sample message:**
> Hi Rahul, your pre-appointment health summary is ready. Your doctor will review it before your consultation at 10:00 AM IST. Open the Kyros app to view it. Reply HELP for support.

---

## 5. `medication_reminder`

**Submission name:** `kyros_medication_reminder`  
**Category:** UTILITY  
**Language:** en  
**Header:** None  
**Footer:** "Kyros Clinic"

**Body text:**
```
Hi {{1}}, time for your scheduled medication. Open the Kyros app to log it. Staying consistent helps you get the most from your treatment. Reply HELP for support.
```

**Parameters:**
| Position | Value | Example |
|---|---|---|
| `{{1}}` | Patient first name | `Sunita` |

**Note:** Medication name is intentionally omitted from the template text — PHI policy prohibits medication names in push/WhatsApp messages.

**Sample message:**
> Hi Sunita, time for your scheduled medication. Open the Kyros app to log it. Staying consistent helps you get the most from your treatment. Reply HELP for support.

---

## Submission checklist

- [ ] Meta Business Manager account verified (Kyros Health Pvt. Ltd.)
- [ ] WhatsApp Business Account (WABA) approved
- [ ] Phone number verified and registered to WABA
- [ ] AiSensy API key provisioned for WABA
- [ ] Each template submitted under "Message Templates" → "Create Template"
- [ ] Template name matches `kyros_<slug>` (lowercase, underscores)
- [ ] Category set to **UTILITY** (not MARKETING)
- [ ] Sample parameters provided at submission time (use sample values above)
- [ ] Approval typically takes 24–48 hours; monitor "Template Status" for APPROVED/REJECTED
- [ ] Update `app/integrations/aisensy.py` template name mapping after approval

## Opt-out compliance

All messages include "Reply HELP for support." AiSensy handles STOP / OPT-OUT replies
automatically. The `notification_preferences` column on the `users` table allows users to
disable WhatsApp notifications from the Kyros app without needing to text STOP.
