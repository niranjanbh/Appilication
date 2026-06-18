# Kyros Patient Mobile — Screen Flow Spec (for wireframing)

> Source of truth: the expo-router route tree under `mobile/app/`. Because routing is
> file-based, the directory structure *is* the navigation map. This document is derived
> from those routes and is intended as a brief for wireframing/design.
>
> Last derived: 2026-06-18 (dev branch).

---

## 0. Design context (apply to every screen)

- **Typography:** Cormorant Garamond (display/headings), DM Sans (body/UI), Tiro Devanagari Hindi (Hindi content).
- **Themes:** Light + Dark, fully tokenized (no hard-coded colors). Light = sky-mist background / navy accents; Dark = forest-ink background / jade accents.
- **Signature UI:** floating **frosted-glass tab dock** (rounded, detached from the bottom edge), **neumorphic cards**, **ambient gradient backgrounds**.
- **Global overlays:** Offline banner (top), "Open in app" banner (web only), **Privacy Shield** (blurs PHI when the app is backgrounded), screenshot **CaptureGuard** on clinical screens (e.g. prescription detail).
- **Healthcare UX rules:** no PHI in screen titles or tab labels; explicit loading states for clinical data; reassuring empty states; confirmation modals on destructive actions.
- **Two form factors:** phone (bottom tab dock) and **desktop web** (same code renders a left `WebSidebar` instead of the dock) — wireframe both.

---

## 1. App entry & gating (`index.tsx`)

A silent router (spinner while loading), then redirects:

- **Not authenticated →** Login
- **Authenticated, onboarding incomplete →** Onboarding / Welcome
- **Authenticated + onboarded →** Home (tabs)

```
Launch ─▶ [Auth check]
            ├─ unauthenticated ─▶ AUTH FLOW
            ├─ no onboarding ───▶ ONBOARDING FLOW
            └─ ready ───────────▶ MAIN APP (tabs)
```

---

## 2. AUTH flow `(auth)/` — no tab bar, standalone stack

| Screen | Route | Purpose | Key elements |
|---|---|---|---|
| **Login** | `(auth)/login` | Phone/email + password sign-in | Logo/wordmark, phone or email field, password field, "Forgot password?" link, primary "Log in" button, secondary "Create account" link, (optional Google sign-in if enabled) |
| **Signup** | `(auth)/signup` | New patient registration | Name, phone, email, password; consent-to-terms checkbox; "Continue" → OTP |
| **Verify OTP** | `(auth)/verify-otp` | Confirm phone/email via OTP | 6-digit OTP input (auto-advance), resend timer, "Verify" button |
| **Forgot password** | `(auth)/forgot-password` | Request reset code | Phone/email field, "Send code" button, helper text on channel |
| **Reset password** | `(auth)/reset-password` | Set a new password | OTP/code field, new password, confirm password, "Reset" button |

```
login ─▶ signup ─▶ verify-otp ─▶ (onboarding)
  │
  └─▶ forgot-password ─▶ reset-password ─▶ login
```

---

## 3. ONBOARDING flow `(onboarding)/` — sequential, progress-driven

| Step | Screen | Route | Purpose | Key elements |
|---|---|---|---|---|
| 1 | **Welcome** | `(onboarding)/welcome` | Brand intro + value prop | Hero illustration, headline, "Get started" |
| 2 | **Consent** | `(onboarding)/consent` | DPDP consents (data processing, telemedicine, health-sync) | Consent cards with expandable text, individual toggles/checkboxes, "Agree & continue" (records consent hash) |
| 3 | **Conditions** | `(onboarding)/conditions` | Pick health areas of interest | Multi-select chips per vertical (thyroid, PCOS, weight, skin/hair, men's health, TRT, longevity) |
| 4 | **Intake form** | `(onboarding)/intake-form` | Baseline health questionnaire | Grouped question cards, inputs/selects, progress indicator, "Continue" |
| 5 | **Health sync** | `(onboarding)/health-sync` | Connect HealthKit / Health Connect | Explainer, permission CTA, "Connect" / "Skip for now" |
| 6 | **ABHA link** | `(onboarding)/abha-link` | (Optional) Link ABHA/ABDM health ID | ABHA number/address field, verify flow, "Link" / "Skip" |

→ On completion: redirect to **Home**.

```
welcome ▶ consent ▶ conditions ▶ intake-form ▶ health-sync ▶ abha-link ▶ HOME
                                                   (skip)        (skip)
```

---

## 4. MAIN APP — Tab bar (6 tabs, floating glass dock)

Order: **Home · Plan · Reports · Reminders · Inbox · Profile**

### Tab 1 — Home `(tabs)/home`
The dashboard / launchpad.
- Greeting (time-based) + avatar with initials
- **Quick actions** grid (4): Consult, Reminders, Reports, My Notes
- Plan / next-step cards (upcoming consult, today's reminders, latest report) on neumorphic cards
- Ambient gradient background

### Tab 2 — Plan / Consultations `(tabs)/consultations`
- List of consultations grouped by status (requested / upcoming / completed)
- Each item: condition, date-time (IST), doctor (once assigned), status pill
- Primary CTA: "Request a consultation"
- Empty state: reassuring copy + CTA

### Tab 3 — Reports `(tabs)/reports`
- List of lab reports (status: processing / ready)
- Upload CTA
- Each item → report detail

### Tab 4 — Reminders `(tabs)/reminders`
- Today's medication/adherence reminders with check-off
- Adherence streak/summary
- Add-reminder CTA; local notifications

### Tab 5 — Inbox / Notifications `(tabs)/notifications`
- Notification list (consult, report-ready, reminders, system)
- Read/unread states
- Link to notification preferences

### Tab 6 — Profile `(tabs)/profile`
- Profile header (name, patient ID)
- Settings list → routes to sub-screens (see §6)

---

## 5. Clinical detail flows (pushed over tabs as stack screens)

### Consultations

| Screen | Route | Purpose | Key elements |
|---|---|---|---|
| **Request a consult** | `consultations/book` | Coordinator-assigned model — *no doctor picking* | Condition select, requirement notes, preferred time window, "Submit request". A coordinator later assigns doctor+slot, then the patient pays. |
| **Consultation detail** | `consultations/[id]` | Status + actions | Status timeline, doctor info (once assigned), payment CTA (when priced), join button (when live), pre-consult report link, prescription link |
| **Pre-consult report** | `consultations/pre-consult-report` | Read-only prep summary the doctor sees | Lab summary, intake answers, flags — read-only cards |
| **Video call** | `consultations/join/[id]` | 100ms video room | Recording-consent gate before join, video layout, controls, elapsed timer |

```
Plan tab ─▶ book ─▶ (request submitted)
Plan tab ─▶ [id] ─▶ pay ─▶ join/[id] (video)
                  ├─▶ pre-consult-report
                  └─▶ prescriptions/[id]
```

### Reports & Biomarkers

| Screen | Route | Purpose | Key elements |
|---|---|---|---|
| **Upload report** | `reports/upload` | Upload a lab report (PDF/image) | Drag/drop or pick file, condition tag, "Upload" → OCR processing state |
| **Report detail** | `reports/[id]` | Parsed results | Biomarker values w/ reference ranges, OCR-confidence indicators, link to trends |
| **Biomarker trend** | `biomarkers/[name]` | Single biomarker over time | Line chart (Victory Native), time-series points, reference band |

### Prescriptions

| Screen | Route | Purpose | Key elements |
|---|---|---|---|
| **Prescriptions list** | `prescriptions/index` | Signed prescriptions | Cards: doctor, date, # meds, status; empty state |
| **Prescription detail** | `prescriptions/[id]` | Read-only (CaptureGuard) | Header (doctor + NMC, signed date); **per-medication cards**: drug name, form, **Dose / Duration chips**, **"How to take" row** (composed timing, e.g. "Twice daily · Morning, Night · after food"), instructions, refill flag; **Download PDF** button (15-min signed URL) |

### Education, Notes & Insights

| Screen | Route | Purpose |
|---|---|---|
| **Education library** | `education/index` | Assigned/curated content (articles, video, PDF) |
| **Content viewer** | `education/[id]` | Read/watch a piece of content |
| **My Notes** | `notes/index` | Patient's personal notes |
| **Insights** | `insights` | Aggregated health insights view |

---

## 6. Profile & account management (stack screens off Profile)

| Screen | Route | Purpose | Key elements |
|---|---|---|---|
| **Privacy & security** | `privacy-security` | Security settings | Biometric lock, session settings, security info |
| **Notification preferences** | `notification-preferences` | Channel toggles | Push / WhatsApp / email / SMS per notification type |
| **ABHA settings** | `abha-settings` | Manage linked ABHA ID | Linked status, unlink |
| **Download data** | `download-data` | DPDP data export | Explainer, "Request export", confirmation |
| **Delete account** | `delete-account` | DPDP erasure | Warning copy, consequences, **confirmation modal**, "Delete account" |

```
Profile ─┬─▶ privacy-security
         ├─▶ notification-preferences
         ├─▶ abha-settings
         ├─▶ download-data        (confirm)
         └─▶ delete-account       (destructive confirm)
```

---

## 7. Master flow map

```
                         ┌──────── AUTH ────────┐
   Launch ─▶ index ─────▶│ login / signup / otp │
                         │ forgot / reset       │
                         └──────────┬───────────┘
                                    ▼
                         ┌──── ONBOARDING ──────┐
                         │ welcome ▶ consent ▶   │
                         │ conditions ▶ intake ▶ │
                         │ health-sync ▶ abha    │
                         └──────────┬───────────┘
                                    ▼
   ┌──────────────────── MAIN APP (tab dock) ───────────────────────┐
   │ Home   Plan      Reports     Reminders   Inbox     Profile      │
   │  │      │          │            │          │          │         │
   │  │      ▼          ▼            ▼          ▼          ▼         │
   │  │   book        upload      (check-off)  prefs   privacy-sec   │
   │  │   [id]        [id]                              notif-prefs   │
   │  │    ├ pay      biomarker/[name]                  abha-settings │
   │  │    ├ join (video)                               download-data │
   │  │    ├ pre-consult-report                         delete-account│
   │  │    └ prescriptions/[id] ◀── prescriptions/index │            │
   │  └─ quick actions: Consult · Reminders · Reports · My Notes      │
   │     education/index ▶ [id]    insights    notes/index           │
   └─────────────────────────────────────────────────────────────────┘
```

---

## Notes for the designer

- **Two breakpoints:** phone (bottom tab dock) and **desktop web** (left `WebSidebar`). Wireframe both.
- `mobile/app/design.tsx` is an internal component showcase, **not** a user screen — exclude from wireframes.
- Every clinical screen needs explicit **loading** and **empty** state wireframes, plus the **backgrounded / Privacy-Shield** state for PHI screens.

---

## Appendix — full route inventory

```
app/index.tsx                          entry redirect (auth/onboarding/tabs)
app/_layout.tsx                        root stack + providers + global overlays

app/(auth)/login.tsx
app/(auth)/signup.tsx
app/(auth)/verify-otp.tsx
app/(auth)/forgot-password.tsx
app/(auth)/reset-password.tsx

app/(onboarding)/welcome.tsx
app/(onboarding)/consent.tsx
app/(onboarding)/conditions.tsx
app/(onboarding)/intake-form.tsx
app/(onboarding)/health-sync.tsx
app/(onboarding)/abha-link.tsx

app/(tabs)/home.tsx
app/(tabs)/consultations.tsx
app/(tabs)/reports.tsx
app/(tabs)/reminders.tsx
app/(tabs)/notifications.tsx
app/(tabs)/profile.tsx

app/consultations/book.tsx
app/consultations/[id].tsx
app/consultations/pre-consult-report.tsx
app/consultations/join/[id].tsx          (+ .web.tsx variant)

app/reports/upload.tsx
app/reports/[id].tsx
app/biomarkers/[name].tsx                (+ .web.tsx variant)

app/prescriptions/index.tsx
app/prescriptions/[id].tsx

app/education/index.tsx
app/education/[id].tsx
app/notes/index.tsx
app/insights.tsx

app/notification-preferences.tsx
app/abha-settings.tsx
app/privacy-security.tsx
app/download-data.tsx
app/delete-account.tsx

app/design.tsx                          internal showcase (not a user screen)
```
