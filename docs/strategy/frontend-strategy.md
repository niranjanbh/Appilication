# Kyros Clinic — Patient App and Portal UI/UX Design Strategy

**Version:** 1.0 · Implementation-grade reference document
**Audience:** Founder, product designer, frontend engineering, clinical reviewer
**Scope:** Patient-facing mobile app (primary) + responsive web portal (secondary)
**Anchor documents:** kyros-design-system, kyros-business-strategy, kyros-clinical-compliance

This document defines the visual and interaction operating system for Kyros Clinic's patient experience. It honours the locked brand system rather than reinventing it. Every recommendation should be readable by a designer in Figma and a frontend engineer in Tailwind/React without further translation.

---

## Table of contents

1. Product design north star
2. User psychology and trust model
3. Information architecture
4. Full screen inventory
5. Dashboard design system
6. Consultation UX
7. Lab reports UX
8. Prescription UX
9. Reminders and adherence UX
10. Education UX
11. Privacy and trust UX
12. Visual system
13. Imagery and illustration direction
14. Motion and interaction design
15. UX writing system
16. Accessibility and healthcare usability
17. Component library
18. State design
19. Mobile vs web portal adaptation
20. Top recommendations and non-negotiables

---

## 1. Product design north star

### 1.1 The four jobs of the app

Most health apps confuse themselves by trying to be one thing. Kyros holds four jobs simultaneously, in tension. Naming the tension is how the design stays coherent.

**The emotional job.** Hormonal-health patients arrive with a backlog of being dismissed — by parents, by previous doctors, by partners, by themselves. The app's emotional job is to feel like the first interaction that takes them seriously. This is not warmth as decoration; it is warmth as evidence of seriousness. A patient should sense, by the second screen, that someone competent has thought carefully about what they are about to feel. The opposite failure mode — "cheerful health buddy" — patronises the same audience that hormonal-health patients have spent years escaping.

**The trust job.** The app must read as clinically credible before it reads as well-designed. This is the inversion of the consumer-app instinct, where craft is the credential. In healthcare, craft *is* the credential, but only if it does not announce itself. The trust job is delivered by: visible doctor identity (real name, NMC registration, specialty), restrained colour, clinical-density information surfaces (white cards, tabular precision), accurate medical vocabulary used responsibly, and the absence of marketing language inside the product surface. Every gimmick costs trust. Every honest detail earns it.

**The behaviour change job.** Hormonal conditions are managed across months and years, not single visits. The app's behaviour change job is to make the next correct action — book the follow-up, log the dose, take the lab test, read the doctor's note — feel like the obvious next thing, not a chore the app is asking for. This is done by reducing the action's surface area to a single one-tap affordance in the right place at the right time, not by streaks, badges, or notifications that nag.

**The continuity-of-care job.** "One doctor, one place, one platform" is the brand promise. The app is the place. Every artifact of care — labs, prescriptions, dosage changes, consultation notes, education — must accumulate visibly into a single thread the patient (and their doctor) can read backwards through time. A new patient sees a beginning. A six-month patient sees a journey. A two-year patient sees a record they would never give up.

### 1.2 What "premium-warm clinical" means inside a product

The brand visual lane was defined for marketing surfaces at a 50/50 ratio. Inside the product, the ratio shifts to **60/40 — sixty per cent clinical clarity, forty per cent warmth.** This shift is the operative design decision. It means:

- **Backgrounds default to Ivory or White**, not Peach Mist. Peach Mist appears only in welcome strips, empty states, education sections, and bottom CTA cards.
- **Cards default to White on Ivory** for clinical density. Cards on Peach Mist only for emotional moments — a welcome strip, an empty-state hero, an "all clear" confirmation.
- **Saffron is used as accent punctuation**, not as background. Three to five saffron moments per screen, no more.
- **Terracotta appears once per screen at most**, and only in genuinely emotional contexts (a reflective close on an education article, an empty-state for a sensitive vertical's first consultation prompt).
- **Cormorant Garamond appears in display moments only** — page-level hero titles, large display numerals on dashboard stat blocks, pull-quotes inside education articles, the post-consultation thank-you screen. Not on every screen. Not in cards. Not in form labels.
- **DM Sans does the structural work** of every other surface — navigation, lab tables, prescription rows, form labels, body copy, metadata.

The mental check: if a screen looks like it could appear in *Cleveland Clinic's app refreshed with editorial warmth*, it is in the right lane. If it looks like *a wellness app with a serif headline*, it has drifted.

### 1.3 The product's relationship to the patient

The app is not the doctor. The app is the room around the doctor. Think of it as the calm, well-lit consulting space where preparation, follow-up, and continuity happen, with the doctor stepping in at scheduled moments. Several consequences fall out of this framing:

- **The app does not "answer questions"** with chatbot interfaces, AI symptom checkers, or generative wellness coaches. It surfaces the doctor's words and the doctor's plan. AI may quietly assist behind the scenes (OCR, trend computation, search) but never wears the white coat.
- **The app does not perform expertise** through dramatic data visualisations, dashboards full of moving parts, or "your score is 78" gamified composites. It presents facts and the doctor's reading of them.
- **The app makes the doctor visible without making the doctor a face on a poster.** Doctor names appear with credentials. Doctor commentary appears as a quoted block, formatted distinctly. The doctor is present in the product the way a senior consultant is present in a hospital — through their handwriting, not their photograph.

### 1.4 Why this matters for sensitive categories

A patient opening the app for the first time about ED, premature ejaculation, hair loss, weight, or fertility carries shame they have not articulated even to themselves. The design either accelerates the dropout or quiets the shame. Three principles govern this:

1. **Never show what the patient is most afraid will appear on their screen in public.** Condition names, dosage names, lab abnormality labels — every one of these is hidden behind a tap by default in shoulder-surfing-vulnerable views (lock screen previews, app switcher, notification body). The patient's home screen card does not say "PCOS plan"; it says "Your plan" with a forest icon. The condition appears only after the patient is inside.
2. **Never use empathy as content.** "We know this is hard" written inside the app is performative. Empathy is delivered structurally: by the absence of stigmatising language, by progress visible without comparison to others, by reminders worded like a colleague's not a coach's.
3. **Never frame sensitive categories around aspirational outcomes.** No "regain your confidence," no "feel like yourself again." The promise is medical: a doctor who measures, a plan that adjusts, a record that accumulates. Outcomes belong to the patient, not the product.

### 1.5 How the product feels for both men and women without coding gender

Many Indian health apps either feminise everything (pastel pink for PCOS, lifestyle stock of women) or masculinise everything (carbon black for TRT, gym imagery). Kyros must not. The patient population is mixed-gender across most verticals, and gender-coding the surface alienates the cross-population on every vertical. The solution is in the locked palette: **Forest as the spine, Saffron and Terracotta as accents** are gender-neutral, warmth-coded rather than gender-coded. The same dashboard chrome serves a TRT patient and a PCOS patient. The only thing that changes is the content — the doctor, the conditions, the labs, the plan.

### 1.6 Balancing "serious medicine" with "gentle care"

The balance is achieved at the level of **visual register**, not at the level of separate "serious" and "gentle" zones. A single screen should read as serious in its structure and gentle in its texture. Concretely:

- Serious in structure: clinical hierarchy, reference ranges visible, doctor attribution, timestamps, units, source labs named.
- Gentle in texture: Ivory backgrounds with warm undertone, Cormorant in a display title or pull-quote, generous whitespace (16/24/32px rhythm), restrained motion, microcopy that explains without instructing.

A screen that is serious in structure but cold in texture reads as a hospital portal. A screen that is gentle in texture but loose in structure reads as a wellness app. Both fail. The Kyros register is both, on every screen.

---

## 2. User psychology and trust model

### 2.1 Six patient archetypes

Six archetypes cover roughly 90% of patient-app interactions. Each has a different emotional state, different cognitive load, and different visual cues that build or destroy trust.

#### Archetype A — The curious-but-anxious first-time patient

The largest archetype on signup. Has read about their symptoms on Reddit and r/PCOS_India / r/AskDocs / r/Indian_Academia for weeks. Suspects a condition, fears a worse diagnosis, has been dismissed before. Arrives with hope and dread held in unstable balance.

- **Emotional state:** anxious, alert, simultaneously hopeful and braced for disappointment.
- **Cognitive load:** high. Cannot absorb dense onboarding; can absorb one decision at a time.
- **Trust barriers:** "Is this a real clinic?" "Is there a real doctor?" "Will I be sold something?" "Will my family find out?"
- **Fears:** dismissal, judgement, hidden costs, data leak to family devices, being told the symptoms are imagined.
- **What they need to see immediately:** evidence of a real doctor (name, NMC reg, specialty); a clear price (₹400-600 consultation fee, no asterisks); a privacy assurance that is structural, not promotional; a single primary action ("Book a consultation").
- **UX patterns that reduce friction:** single-question onboarding screens with progress visible; condition selection by symptom rather than by diagnosis ("I've been tired for months" rather than "Hypothyroidism"); ability to delay intake forms until after booking.
- **Visual patterns that increase trust:** real doctor names with credentials; restrained colour (no celebratory confetti); ivory and white backgrounds without gradient noise; Cormorant in the welcome title delivering a single warm sentence followed by plain DM Sans body.
- **What feels wrong:** chatbot greeting them; symptom-checker quizzes that feel like marketing; testimonial carousels on the home screen; "X people booked today" social proof; any AI-coded primary action.

#### Archetype B — The lab-report-heavy returning patient

Has been managing thyroid or PCOS or TRT for two to five years. Has a folder of lab PDFs, often spread across labs (Dr Lal PathLabs, Thyrocare, Metropolis, Apollo Diagnostics). Wants to centralise. Will judge the app by how it handles a complex history.

- **Emotional state:** competent, mildly impatient, low-drama. Knows their own data.
- **Cognitive load:** low for general use, high tolerance for clinical depth.
- **Trust barriers:** "Will the app butcher my historical labs?" "Can the doctor actually see what I see?"
- **Fears:** OCR misreading values, app dumbing down data they understand, losing their existing PDFs in some new ecosystem.
- **What they need to see immediately:** an upload affordance prominent on the labs tab; a trend chart that shows TSH (or testosterone, or HbA1c) over time with reference range bands; the ability to export everything as PDF; their existing PDFs preserved as originals alongside the structured data.
- **UX patterns that reduce friction:** bulk PDF upload; OCR with editable confirmation; biomarker view that groups by panel (thyroid panel, lipid panel, metabolic panel) not alphabetically.
- **Visual patterns that increase trust:** restrained chart design (sage reference band, ink line, saffron callout for the latest value); units always visible; source lab named on every result; date of test prominent.
- **What feels wrong:** charts that smooth out true variation into "trends"; AI-generated "interpretation" overlaid on raw data; gamified "your thyroid score is improving"; pastel chart palettes.

#### Archetype C — The sensitive-condition patient seeking privacy

ED, premature ejaculation, fertility, AGA at a young age, sexual health, PCOS where family awareness is itself a stressor. The patient is here because telehealth offers what an in-person visit cannot: discretion.

- **Emotional state:** vulnerable, hyper-vigilant about exposure, often using the app late at night in shared spaces.
- **Cognitive load:** medium. Wants to move through quickly without lingering on anything embarrassing.
- **Trust barriers:** "Will notifications show this on my lock screen?" "Will the app icon give it away?" "If my partner picks up the phone, what shows?"
- **Fears:** lock-screen previews of "Your ED consultation is in 10 minutes"; family member opening the app from notification preview; data shared with insurance; data shared with employer.
- **What they need to see immediately:** privacy controls during onboarding ("Use generic notifications" toggle); the option to set a passcode on the app itself; doctor identity confirming this is a real clinical relationship, not an anonymous chat service.
- **UX patterns that reduce friction:** generic notification text by default ("Your consultation is in 10 minutes" not "Your TRT consultation is in 10 minutes"); biometric app lock available at signup, not buried in settings; quick consultation-without-history option.
- **Visual patterns that increase trust:** the app icon and name in the OS app switcher reads as a clinic, not as the condition; no condition labels in any thumbnail surface (notification preview, widget, app switcher card).
- **What feels wrong:** any UI that announces the condition; "celebrate your first consultation" success state; shareable referral cards; community features.

#### Archetype D — The busy working professional booking quickly

Tier-1 city, 30s-40s, time-constrained, will abandon any flow longer than three taps. May be booking for themselves or for a parent. Treats the app like a Uber for healthcare — they want a doctor, soon, with a credible promise of competence.

- **Emotional state:** transactional, optimising for speed, willing to pay for efficiency.
- **Cognitive load:** medium, but split — they are doing this between meetings.
- **Trust barriers:** "Is this faster than my regular doctor?" "Will I get someone competent or a randomly assigned junior?"
- **Fears:** waiting 45 minutes for a consultation; getting bounced between people; being asked to repeat information already provided.
- **What they need to see immediately:** next available slot (today, this evening, tomorrow morning); the assigned doctor's name and credentials, not "a doctor will be assigned"; a fee they can pay in under 30 seconds.
- **UX patterns that reduce friction:** persistent "Book consultation" CTA at the bottom of the home tab; saved payment method; "rebook with Dr X" as one-tap from past consultations.
- **Visual patterns that increase trust:** clean slot picker (no scarcity theatrics, no "only 1 slot left!" pressure); doctor card with photo or initial monogram on placeholder, name, NMC reg, specialty, languages.
- **What feels wrong:** mandatory intake form before being shown slots; multi-step onboarding before the home screen; "we'll get back to you in 24 hours" patterns.

#### Archetype E — The longitudinal-care patient tracking improvements

Six to twenty-four months in. Has settled into a rhythm with a specific doctor. Comes back to the app to log adherence, glance at next reminder, and check their three-month TSH/free-T/HbA1c trend before their next consult. This is the patient whose lifetime value depends entirely on whether the app feels like home or feels like a billing system.

- **Emotional state:** settled, mildly invested, occasionally curious.
- **Cognitive load:** low. Uses the app in sub-30-second sessions.
- **Trust barriers:** "Will my doctor still be here in six months?" "Will the app remember everything?"
- **Fears:** their doctor leaving the panel; the app being acquired and changing; old data being lost in a redesign.
- **What they need to see immediately:** today's plan (reminders, today's water/medication/supplement log); the relationship — their doctor by name with the next consultation date; a quiet sense of progress without a celebratory tone.
- **UX patterns that reduce friction:** one-tap adherence logging from a notification or the home screen; rebooking with the same doctor as one action; trend chart accessible in two taps from anywhere.
- **Visual patterns that increase trust:** the doctor's name persistently visible somewhere on the home screen; the dashboard's evolution over time (more data accumulated, but the chrome unchanged); subtle continuity rather than visible "you've achieved X" celebration.
- **What feels wrong:** redesign churn that resets their muscle memory; streak language ("you're on a 47-day streak!"); promotional banners about other verticals or new features cluttering their home.

#### Archetype F — The patient with low trust due to previous dismissive doctors

Disproportionately women with PCOS, hypothyroidism, fibromyalgia-adjacent presentations; or men with hormonal symptoms dismissed as "stress" by a previous GP. Has been told their symptoms are imagined, exaggerated, or psychosomatic. Will be looking for evidence the doctor is different.

- **Emotional state:** guarded, alert for dismissal cues, ready to leave at the first sign of condescension.
- **Cognitive load:** high during onboarding (they are reading every word); low after relationship establishes.
- **Trust barriers:** "Will this doctor actually read what I write?" "Will my symptoms be taken seriously?"
- **Fears:** intake form being too brief to capture their history; doctor spending five minutes; being told to "manage stress."
- **What they need to see immediately:** an intake form long enough to feel taken seriously (but structured, not overwhelming); the option to add free-text history; doctor credentials and clinical interest areas, not generic "GP."
- **UX patterns that reduce friction:** intake forms with optional free-text "Tell us anything else" fields after structured questions; pre-consult notes the patient can see their doctor has read.
- **Visual patterns that increase trust:** the patient's own words appearing back in the consultation summary; doctor commentary that quotes and responds to specifics, not generic recommendations.
- **What feels wrong:** intake forms that feel like checkboxes; consultation summaries that read as templates; "we hear you" microcopy without backing structural evidence.

### 2.2 The trust ladder

Trust accumulates and resets, predictably, across known events. Designing the app means designing for each rung.

| Rung | What earns it | What destroys it |
|---|---|---|
| 1. Initial credibility | Real doctor names visible before signup, fee clarity, privacy framing | "Get started" buttons before doctor identity, hidden fees, generic privacy text |
| 2. First-session trust | Onboarding that ends in a sensible state, fast slot picker, payment confirmation that names the doctor | Long forms, payment screen ambiguity, no confirmation of slot |
| 3. Pre-consultation trust | Intake form feels purposeful, doctor's specialty matches need, waiting room communicates the doctor is preparing | Generic intake, mismatched specialty, blank waiting room |
| 4. Consultation trust | Doctor was on time, listened, prescribed sensibly, gave a plan | Doctor late without communication, hurried call, vague plan |
| 5. Post-consultation trust | Prescription arrives quickly, doctor's note is readable, follow-up clearly scheduled | Delayed prescription, jargon-only note, no follow-up clarity |
| 6. Longitudinal trust | Continuity (same doctor), labs flow back into dashboard, doctor commentary on new labs within 48h | Doctor swap without explanation, labs orphaned in a "documents" pile, no commentary |
| 7. Brand trust | The app changes slowly, respects existing muscle memory, never sells third-party products | Frequent redesign, in-app ads, supplement upsells |

The seventh rung is the one that converts patients to advocates — and the one that competitor health apps reliably destroy.

### 2.3 Universal trust signals to apply on every surface

These are non-negotiable cues to recur across the product:

- **Doctor identity is visible:** name + NMC registration + specialty, on every doctor-attributable artifact (consultation card, prescription, lab commentary, education byline).
- **Timestamps are precise:** "Today, 4:32 PM" not "a few hours ago." Patients sharing screens with doctors need exact times.
- **Units are explicit:** TSH 2.4 mIU/L, not TSH 2.4. Testosterone 412 ng/dL, not Testosterone 412. Always the unit, always reading-grade legible.
- **Source labs are named:** every uploaded report identifies the lab. The patient has a folder; the app preserves origin.
- **Reference ranges are present:** for every biomarker, alongside the value, with a sage band for in-range and a saffron edge for out-of-range. Never red until clinically warranted.
- **No marketing language inside the product surface:** no "amazing," no "best," no "trusted by thousands." These are marketing-page words. Inside the app they corrode trust.
- **Privacy controls are visible, not buried:** the privacy and data settings are reachable in two taps from anywhere via the Profile tab. The notification-privacy toggle is offered during onboarding, not hidden in a settings sub-page.

---

## 3. Information architecture

### 3.1 Top-level navigation: five bottom tabs

The bottom tab bar is the patient's permanent reference frame. It must hold the five most-used destinations and nothing else. Recommended structure:

```
Home  ·  Consults  ·  Labs  ·  Plan  ·  Profile
```

Why these five, and why not others:

- **Home** is the dashboard — the patient's daily-use surface. Most sessions start and end here.
- **Consults** is the consultation hub: upcoming, past, history, post-consult notes. Separating consults from home means the patient can navigate consultation-specific actions without scrolling past dashboard widgets.
- **Labs** is the longitudinal record. This is a flagship surface and gets its own tab because the labs experience is a primary product moat (per business strategy: "Lab results, prescriptions, dosage history, wearable trends — all in your dashboard"). Burying labs inside a "Records" pile destroys the trust-of-continuity job.
- **Plan** is the action surface: today's reminders, prescriptions, supplements, water/medication adherence, education assigned by the doctor. "Plan" is the right word because it reflects the doctor-authored plan rather than the patient's habits. Calling it "Habits" or "Tracker" cedes the framing to the consumer wellness lane.
- **Profile** is the trust and identity surface: account, privacy, consent, data export, DPDP rights, notification preferences, ABHA linking, settings.

What does *not* belong in the tab bar:
- **Education** is reached from Home, from Plan (assigned content), and from the Consult detail screen — it does not need a top-level tab. A dedicated education tab encourages the patient to treat the app as a content destination, which is the wrong primary relationship.
- **Search** is a global icon in the top-right of the Home screen, not a tab. Patients rarely search a clinic.
- **Notifications** is a bell icon in the top-right, opening a notifications sheet. Not a tab.
- **Chat** is intentionally absent at v1. If chat with the care team is added later, it lives inside the Consult detail screen as "Message the care team" with bounded availability (not 24/7) — never a persistent tab that implies instant doctor access.

### 3.2 Full IA tree

```
Kyros Patient App
│
├── (Pre-auth)
│   ├── Splash / app open
│   ├── Sign in
│   │   ├── Phone OTP
│   │   └── Email + password (fallback)
│   ├── Sign up
│   │   ├── Phone OTP
│   │   ├── Basic profile (name, DOB, sex assigned at birth, city)
│   │   └── Notification privacy preference (generic vs detailed)
│   ├── Forgot password / recover account
│   └── App-store landing equivalent (web only)
│
├── Onboarding (post-signup, pre-home)
│   ├── Welcome (warm hello)
│   ├── What brings you in (condition selection by symptom cluster)
│   ├── Brief intake (4–6 quick questions, condition-routed)
│   ├── Consent (privacy, telemedicine, data use)
│   ├── Optional: ABHA linking
│   ├── Optional: Health data sync (Apple Health / Health Connect)
│   ├── Optional: App passcode / biometric lock
│   └── Ready (you can book whenever you're ready — no forced booking)
│
├── HOME (tab 1)
│   ├── Top app bar (search icon, notification bell, profile avatar)
│   ├── Hero / welcome strip (contextual: morning/afternoon/evening + name)
│   ├── Next-best-action card (varies by state)
│   ├── Upcoming consultation card (if any)
│   ├── Today's plan strip (medications, supplements, reminders due today)
│   ├── Recent lab insight card (if recent labs)
│   ├── Doctor's recent commentary (if any)
│   ├── Assigned education card (if any)
│   ├── Quick actions row (Book, Upload, Refill, Help)
│   └── Trust / support footer (Contact care team)
│
├── CONSULTS (tab 2)
│   ├── Upcoming
│   │   └── Consultation detail
│   │       ├── Doctor card
│   │       ├── Pre-consult checklist
│   │       ├── Time + countdown
│   │       ├── Join button (active near time)
│   │       ├── Reschedule / cancel
│   │       └── Pre-consult notes (free-text "anything you want the doctor to know")
│   ├── Past
│   │   └── Past consultation detail
│   │       ├── Doctor's summary note
│   │       ├── Prescription issued (link)
│   │       ├── Labs ordered (link)
│   │       ├── Education assigned (link)
│   │       └── Follow-up scheduled (link or "book follow-up")
│   ├── Book new consultation
│   │   ├── Choose specialty / vertical
│   │   ├── Choose doctor (or "any available")
│   │   ├── Choose slot
│   │   ├── Fee summary
│   │   ├── Payment
│   │   └── Confirmation
│   └── In-call experience
│       ├── Waiting room (pre-call)
│       ├── Video consultation surface
│       └── Post-call summary
│
├── LABS (tab 3)
│   ├── Lab timeline / list (most recent first)
│   ├── Upload report
│   │   ├── Camera capture
│   │   ├── PDF / file upload
│   │   ├── Multiple report bulk upload
│   │   ├── OCR processing
│   │   └── Confirm extracted values (correction UI)
│   ├── Lab report detail
│   │   ├── Source lab + date
│   │   ├── Biomarker rows (with reference range)
│   │   ├── Flagged values summary
│   │   ├── Doctor commentary (if any)
│   │   ├── Original PDF (view / download)
│   │   └── Compare with previous
│   ├── Biomarkers (longitudinal)
│   │   ├── Biomarker list
│   │   └── Biomarker detail (trend chart, history table)
│   └── Empty state (no labs yet)
│
├── PLAN (tab 4)
│   ├── Today (default tab)
│   │   ├── Medications due
│   │   ├── Supplements due
│   │   ├── Water / hydration
│   │   ├── Movement / activity (if doctor-prescribed)
│   │   └── Education assigned
│   ├── Medications
│   │   ├── Current medications list
│   │   ├── Medication detail (dosage, instructions, history)
│   │   └── Refill request
│   ├── Adherence (history)
│   │   ├── Last 7 days
│   │   ├── Last 30 days
│   │   └── Per-medication adherence
│   ├── Education (assigned + browsable)
│   │   ├── Assigned by your doctor (priority list)
│   │   ├── Library (browsable, by vertical)
│   │   └── Article / video viewer
│   └── Reminders settings
│
├── PROFILE (tab 5)
│   ├── Personal details (name, DOB, contact)
│   ├── Health profile (sex assigned at birth, conditions, allergies, family history)
│   ├── Insurance / TPA (optional)
│   ├── ABHA (optional)
│   ├── Privacy & data
│   │   ├── My consents (with timestamps)
│   │   ├── My data (download, export)
│   │   ├── Delete my account / data
│   │   ├── Linked devices / health sync sources
│   │   └── DPDP rights (export, correct, delete, withdraw)
│   ├── Notifications
│   │   ├── Generic vs detailed preview
│   │   ├── Channel preferences (push, SMS, email, WhatsApp)
│   │   └── Quiet hours
│   ├── Security
│   │   ├── App passcode / biometric
│   │   ├── Active sessions
│   │   └── Change password
│   ├── Payments
│   │   ├── Payment methods
│   │   └── Receipts / billing history
│   ├── Help & support
│   ├── About Kyros
│   ├── Terms & policies
│   └── Sign out
│
└── Global modals / sheets
    ├── Notification sheet (bell icon)
    ├── Search sheet (search icon)
    ├── Emergency banner (Alert color, in-person referral)
    └── In-call mini-window (when navigating away during a consultation)
```

### 3.3 Architectural rationale

**Why Home, not "Today."** "Today" is a habit-tracker frame. "Home" is the patient's address. The dashboard does include today's actions, but it is not a today screen — it is also where the doctor's recent commentary, the latest lab insight, and the next-best-action card live. Home holds the relationship; Plan holds today.

**Why Consults and Plan are separate tabs.** Consultations are episodic, often-anticipated, time-bounded events. Plan is daily, routine, habitual. Combining them ("Care") muddles the patient's mental model and forces every glance through extra navigation. Two tabs cost nothing structurally and clarify the model.

**Why Labs is a top-level tab, not under Records.** This is a strategic decision tied to the business positioning. "One place, where your health lives" makes labs and longitudinal biomarker tracking a flagship — not a document repository. Burying labs inside a generic "Records" or "Documents" section signals labs are not central. They are.

**Why Profile holds Privacy.** Privacy and trust live together with identity. The patient who is anxious about data exposure should find privacy controls one tap from their profile. Spreading privacy across Settings, Account, and Security creates the impression of obfuscation — exactly the opposite of what the brand promises.

### 3.4 What is one-tap reachable from anywhere

From any tab, the patient must reach the following in one or two taps:

| Destination | From | Taps |
|---|---|---|
| Book consultation | Home → Quick actions row | 1 |
| Upcoming consultation detail | Home → upcoming consultation card | 1 |
| Upload a lab report | Labs → Upload button (top right) | 1 (after switching tab) |
| Latest lab report | Home → recent lab insight card OR Labs → first item | 1–2 |
| Mark medication taken | Plan → Today → tap the row | 1 (after switching tab) |
| Doctor's last note | Consults → Past → top item | 2 |
| Privacy & data | Profile → Privacy & data | 1 |
| Emergency / "this is urgent" | Banner in Home + Help & support in Profile | 1–2 |

What should *never* be one tap (deliberately): account deletion, data export confirmation, ABHA linking changes, payment method changes. These should require explicit, friction-bearing confirmation steps.

### 3.5 Progressive disclosure principles

Information that lives behind a tap, not at the surface:

- **Onboarding intake details.** Surface the symptom cluster; reveal the deeper history form only after the patient indicates they want to share more.
- **Reference range explanations.** Surface the value and band; reveal the "what does this range mean" body inside a sheet from the chip.
- **Doctor credentials beyond name + specialty.** Surface name, NMC reg, specialty; reveal full CV (training, languages, clinical interest) on tap.
- **Consent text.** Surface the summary in one line ("You're agreeing to..."); reveal the full text below a "Read full text" affordance.

Information that does *not* live behind a tap (must be surface-visible):

- The patient's own name and the morning/afternoon greeting on Home.
- The assigned doctor on every consultation card.
- The next due reminder on Plan → Today.
- The latest biomarker value with its reference range.
- The privacy and data link from Profile (not inside Settings → Account → Privacy three taps deep).

### 3.6 Mobile web portal differences

The web portal serves three primary use cases that the mobile app does not: (1) bulk-upload a year of lab PDFs at once, with drag-and-drop; (2) read a long doctor's note in a desktop-format reading view; (3) print or save a prescription as PDF.

Architectural differences:

- **Tab bar becomes a left rail** on desktop. Same five destinations. Same icons. The left rail is permanent; the active item has a Forest fill at 8% opacity and a Forest left border.
- **Two-column layouts** open up: on Home, the right column holds the doctor's commentary and recent education; the left column holds the upcoming consultation, today's plan, and lab insights. On Labs detail, biomarker rows render in two columns on screens above 1024px.
- **Drag-and-drop upload** is the primary upload affordance on the Labs tab in the web portal. Camera capture is absent.
- **Keyboard shortcuts** are introduced minimally: `cmd/ctrl+K` opens search; `g h` goes to Home; `g c` to Consults; `g l` to Labs; `g p` to Plan. Documented in a "Keyboard shortcuts" entry in Profile → Help & support.
- **Print stylesheet** for prescriptions and lab reports renders white-on-white with all warmth tints removed. Doctor name, NMC reg, prescription details, timestamps, and clinic identity remain.

What stays identical across native and web: information architecture; component visual style; copy; doctor identity placement; the visual register (60/40 clinical-to-warmth). Patients should not feel they are using a different product on different devices — only that the device has its own conveniences.

---

## 4. Full screen inventory

This section enumerates every screen the patient app must support, grouped by flow. For each screen: purpose, user intent, primary CTA, secondary CTA, critical information, emotional tone, UX risk if mishandled.

### 4.1 Auth and onboarding screens

| Screen | Purpose | User intent | Primary CTA | Secondary CTA | Critical info | Emotional tone | UX risk if mishandled |
|---|---|---|---|---|---|---|---|
| Splash | App-open frame; brand reassurance | None — passing through | None | None | Kyros wordmark on Ivory | Calm, brief (under 800ms) | Lingering splash reads as performance issue |
| Sign in | Return for existing patient | Sign back in | Continue with phone | Sign in with email | Phone field + privacy footnote | Quiet, no celebration | Phone-only is fastest; email shown if locked out |
| Sign up — phone | Begin account | Start | Send OTP | Sign in instead | Indian phone, country flag, T&C link | Calm welcome | T&C as wall of text destroys trust |
| OTP verify | Confirm number | Verify | Auto-detect OTP or paste | Resend OTP | OTP fields, resend timer | Brief, neutral | Resend hidden = retry friction |
| Welcome | First emotional moment | Receive a warm hello | Continue | None | Cormorant single sentence ("Welcome to your clinic") + DM Sans sub | Warm, restrained | Long welcome copy patronises |
| What brings you in | Capture intent without forcing diagnosis | Indicate primary concern | Continue | Skip for now | Symptom clusters as chips, not diagnoses | Non-judgemental | Diagnostic labels here shame the user |
| Intake (4–6 questions) | Capture clinical baseline | Answer honestly | Continue | Save and exit | One question per screen, progress dot | Quiet, professional | Long forms = abandonment |
| Consent | Legal + clinical permission | Read summary, agree | I agree | Read full text | Telemedicine + DPDP + data use summary | Calm, transparent | Walls of legalese = consent fatigue |
| ABHA linking (optional) | Optional national health ID | Link or skip | Link ABHA | Skip for now | "Optional" prominent; benefits in 2 lines | Neutral | Implying it's required violates the optional rule |
| Health data sync (optional) | Apple Health / Health Connect permission | Permit or skip | Allow | Skip | What we read, what we don't, who sees | Reassuring | Permission walls without explanation = denial |
| Notification privacy preference | Choose generic vs detailed | Pick lock-screen behavior | Use generic previews | Detailed previews | "Recommended: generic" microcopy | Warm but firm | Defaulting to detailed leaks |
| App passcode (optional) | Biometric / passcode lock | Set or skip | Set passcode | Skip for now | Face ID / fingerprint visual | Neutral | Hidden in settings = patients miss it |
| Ready | Onboarding complete | Land on Home | Go to my home | None | "You can book whenever you're ready" | Settled, no fanfare | Confetti or party celebration breaks register |

### 4.2 Home dashboard screens and states

| Screen / state | Purpose | UX risk |
|---|---|---|
| Home — first-time (no consultation, no data) | Warm hero + clear "Book your first consultation" CTA + tasteful explainer of how Kyros works | Looking empty / abandoned |
| Home — pre-first-consult (booked, awaiting) | Upcoming consultation card pinned at top; pre-consult checklist visible | Hiding the upcoming consult = anxious patient |
| Home — post-first-consult (active patient) | Today's plan, recent lab insight (if any), doctor's last commentary, assigned education | Information overload |
| Home — longitudinal (months in) | Calm card stack: doctor relationship visible, today's plan compact, trend snippets | Stale-looking dashboard if nothing new |
| Home — consultation today | Hero shifts to "Your consultation with Dr X is at 4:00 PM" with countdown closer to time | Hidden urgency = missed call |
| Home — overdue items (skipped doses, late labs) | Gentle prompt card, not red, not nagging | Punitive surfacing destroys trust |
| Home — loading | Skeleton placeholders matching final card shapes | Spinner over a blank screen feels broken |
| Home — offline / sync failed | Banner "Some data couldn't update. Showing last known." | Silent failure = stale data passed off as current |

### 4.3 Consultation screens

| Screen | Purpose | Primary CTA | Critical info | UX risk |
|---|---|---|---|---|
| Book — vertical select | Pick area of concern | Choose | Seven vertical tiles | Clinical jargon as labels |
| Book — doctor select | Choose specific doctor or "any available" | Choose | Name, NMC reg, specialty, languages, next slot | Photo-led card pushes into stock-doctor failure |
| Book — slot picker | Pick time | Confirm slot | Day rail + slot grid, doctor name persistent | Calendar overwhelm |
| Book — fee summary | Review what is being paid | Pay | Amount, what's included, refund policy | Hidden fees |
| Book — payment | Complete transaction | Pay ₹X | UPI/card/wallet options, secure-payment icon | Payment failure with no recovery path |
| Book — confirmation | Confirm booking and what happens next | View consultation | Doctor, time, calendar add, pre-consult notes | "Thank you" without next-step clarity |
| Upcoming consultation detail | Hold all info for the next session | Join (when active) | Doctor, time, pre-consult checklist, notes field | Countdown without join button when active |
| Pre-consult checklist | Quick prep tasks before the call | Mark done | "Have your last labs ready," "Quiet room" | Reading as a quiz instead of a checklist |
| Pre-consult notes (free-text) | Patient adds context the doctor will see | Save | "What would you like the doctor to know?" | Empty by default = patient assumes it's optional and skips |
| Waiting room | Hold the patient just before the call | Join now (when ready) | Doctor's prep status, expected time, "You're next" | Empty room with no acknowledgement |
| In-call surface | The video consultation | Camera toggle, mic toggle, end call | Doctor video, self video, time elapsed, chat fallback | Cluttered call UI |
| Connection issue mid-call | Recover from interruption | Reconnect | "Connection lost. Reconnecting…" + dial-in fallback | Silent dropout |
| Doctor is running late | Acknowledge delay honestly | Stay or reschedule | "Your doctor is running about 8 minutes late. Apologies." | Silence (worse than honest delay) |
| Post-call summary | Immediate post-consult anchor | View prescription / Book follow-up | What was discussed, prescription issued, labs ordered, follow-up date | Dropping the patient at a blank screen post-call |
| Consultation cancelled | Communicate cancellation, offer rebook | Reschedule | Reason (if any), refund status, alternate slots | Bureaucratic tone |
| Consultation history list | Browse past consults | Open a past consult | Doctor, date, primary concern, prescription/lab links | Treating past consults as inert records |
| Past consultation detail | Re-read the doctor's note | Book follow-up / View prescription | Doctor's summary, prescription, labs, education | Note feels templated |

### 4.4 Lab report screens

| Screen | Purpose | Primary CTA | UX risk |
|---|---|---|---|
| Labs — empty (no labs yet) | First-use prompt | Upload a report | "We need labs to begin" reads as gating |
| Labs — list (chronological) | Browse all reports | Open a report | Cluttered if many reports |
| Upload entry | Choose how to upload | Take a photo / Pick a file | Two equal CTAs without recommendation |
| Camera capture | Photograph a paper report | Capture | Bad framing UX |
| Multi-photo capture | Multiple pages | Add page / Done | No "review pages" step before submit |
| File picker | PDF or image from device | Confirm | iOS/Android picker behavior inconsistency |
| Upload progress | Show file uploading | Cancel | Progress percent disappears |
| OCR processing | Extracting values | None (waiting) | Spinner indefinitely |
| OCR confirm — high confidence | Review extracted values, confirm | Confirm and save | User skips, errors persist |
| OCR confirm — low confidence | Manual correction UI | Save | Error pattern unclear |
| OCR confirm — failed | Manual entry path | Enter manually | Dead-end if no manual fallback |
| Lab report detail | View full report | Compare with previous / View PDF | Wall of numbers without hierarchy |
| Lab report detail — doctor commentary pending | Set expectations | None | Implying doctor will read in 10 minutes |
| Lab report detail — with doctor commentary | Doctor's reading of the labs | Book follow-up if needed | Commentary buried below biomarkers |
| Biomarker list | All biomarkers tracked | Open a biomarker | Alphabetical sort defeats clinical grouping |
| Biomarker detail (trend) | Single biomarker over time | Toggle range, view history | Chart without reference range |
| Biomarker detail — single result | Just one data point | Add another lab | "Trend" word used for single point |
| Compare two reports | Side-by-side biomarker comparison | Switch reports | Tiny font on mobile |
| Flagged values summary | Aggregate of out-of-range values | Open biomarker | Red-everything alarm fatigue |
| Lab report shared with another doctor | Sharing audit | View who has access | No visible audit |
| No labs yet — onboarding card on Home | First-time prompt to upload | Upload first report | Implying patient cannot use the app without labs |
| Lab data sync failed | Connectivity issue | Retry | Silent failure |

### 4.5 Prescription screens

| Screen | Purpose | Primary CTA | UX risk |
|---|---|---|---|
| Prescriptions — empty | First-use prompt | None | "You have no prescriptions" reads as something is missing |
| Prescriptions — list | Browse all prescriptions | Open a prescription | Mixing active and inactive prescriptions without distinction |
| Prescription detail | Read a specific prescription | Download PDF / Set reminder | Treating prescription like a screenshot |
| Medication row | Single medication line | Tap to view detail | Generic / brand confusion |
| Dosage change history | When and why the dose changed | None | History as a flat list without context |
| Medication detail (clinical) | Drug, dose, frequency, duration, purpose | Set reminder / Refill | Pharma-commerce aesthetic |
| Refill request | Request refill from care team | Submit request | No status after submit |
| Prescription PDF | Original signed doctor document | Download / Share | PDF that looks unlike a real prescription |

### 4.6 Plan and reminders screens

| Screen | Purpose | Primary CTA | UX risk |
|---|---|---|---|
| Plan — Today | Today's scheduled actions | Mark done | Treating like a to-do list |
| Plan — Medications | Current meds | Open medication | Same as prescriptions tab — confused IA |
| Plan — Adherence (7d) | Recent adherence | Switch to 30d | Punitive missed-dose styling |
| Plan — Adherence (30d, 90d) | Longer adherence window | Switch range | Streak language |
| Plan — Education (assigned) | Doctor-assigned reading | Open article | Mixing assigned and library |
| Plan — Education (library) | Browsable | Open article | Library treats education as content marketing |
| Reminder due notification | Phone-level prompt | Mark taken / Snooze / Skip | Nagging notifications |
| Reminder — Mark taken | Quick log | Done | Long log path |
| Reminder — Snooze | Postpone | 15m / 1h / Tomorrow | Snooze defaults that feel arbitrary |
| Reminder — Skip | Skip this dose | Confirm | No reason capture (optional) |
| Reminder settings | Tune reminder behavior | Save | Buried in Settings rather than reachable from a row |

### 4.7 Education screens

| Screen | Purpose | UX risk |
|---|---|---|
| Education — assigned list | Reading the doctor recommended | Mixing with library |
| Education — library | Browsable, by vertical | Treating as a content site |
| Article viewer | Read an article | Wall of text |
| Video viewer | Watch a video | Autoplay surprises in public |
| Read progress | "You've read 3 of 5 assigned" | Gamified percentages |
| Doctor attribution on article | "Reviewed by Dr X, NMC reg 12345" | Generic byline |
| Reviewed date | "Reviewed January 2026" | Outdated content with no date |

### 4.8 Profile and privacy screens

| Screen | Purpose | UX risk |
|---|---|---|
| Profile — landing | Identity and account at a glance | Mixing health profile with payment screens |
| Personal details | Edit name, contact | Asking for too much |
| Health profile | Edit conditions, allergies, family history | Treating like a generic health profile |
| Insurance / TPA | Optional insurance details | Required-by-default |
| ABHA linking | Optional national health ID | Re-asking on every login |
| Privacy & data — landing | DPDP rights and data controls | Hidden under Settings sub-pages |
| My consents | Past consent records with timestamps | Listing nothing visible |
| Download my data | Export request | "Will email you in 30 days" feels lazy |
| Delete account | Destructive action with confirmation | Single-click delete |
| Linked devices | Health sync sources visible | No revocation path |
| Notifications | Preferences, channels, quiet hours, generic vs detailed | Hidden behind a sub-tab |
| Security | Passcode, sessions, password change | Sessions never shown |
| Payments | Methods, billing | Storing card details visibly |
| Help & support | Contact care team, FAQ | Generic FAQ that doesn't address sensitive questions |
| About Kyros | Brand, licences, doctor panel summary | Marketing copy inside the product |
| Terms & policies | Legal documents | Walls of legalese |
| Sign out | Sign out | Easy to hit accidentally |

### 4.9 Edge-case and system screens

These often get neglected; they are the difference between a polished product and a brittle one.

| Screen / state | Treatment |
|---|---|
| First-launch loading | Skeleton on ivory background, no spinner |
| Connectivity warning | Subtle ivory-on-ivory banner at top of Home, "Showing offline data" |
| Sync in progress | Sage tint chip near each affected card, "Syncing…" |
| Permission denied (camera, notifications, health data) | Explainer screen with link to OS settings, never blocked dead-end |
| Payment failed | Clear reason, retry button, alternate payment method, no consultation lost |
| OCR low confidence | Saffron edge on extracted values, "Please confirm these — we're not fully sure" |
| OCR failed entirely | Manual entry path, link to upload PDF for doctor manual review |
| No slots available | "No slots in the next 7 days for Dr X. View other doctors or join the waitlist." |
| Doctor running late | "Dr X is running about 8 minutes late. You'll be joined when she's ready." |
| Reminder already complete | "You've taken all of today's doses." Quiet, no celebration. |
| Doctor's note not yet posted | "Dr X is writing her note. Most notes arrive within 24 hours." With timestamp of expected. |
| Consultation cancelled (by patient) | Confirmation + refund window |
| Consultation cancelled (by clinic) | Apology + immediate rebooking + refund automatic |
| Pre-consultation intake incomplete | Soft nudge on consultation card, not a wall |
| Privacy request submitted | "We've received your request to delete your data. You'll hear from us within X days." |
| No historical labs | "Once you upload a lab report, it lives here permanently." Inviting, not blocked. |
| Cannot find your doctor (no panel match) | "We're matching you with the right doctor. Someone from the care team will reach out within X hours." |
| Doctor leaves the panel | "Dr X is no longer with our panel. Your records and history move with you. We've matched you with Dr Y." Honest, calm. |
| Server / maintenance | "We're doing a scheduled update. Back in X minutes." |
| Critical alert (rare) | Alert-color banner only; e.g. "Lab value flagged urgent — Dr X has been notified. Please call our care team." |

---

## 5. Dashboard design system

The dashboard (the Home tab) is the centre of gravity for the entire product. It is where every returning patient lands, where the doctor's care is felt, and where the brand's promise is either kept or quietly broken. This section specifies the dashboard in module-level detail.

### 5.1 The dashboard's job, stated precisely

The dashboard's job is to answer four questions before the patient asks them:

1. **What is happening next in my care?** (Upcoming consultation, today's reminders, this week's plan)
2. **What is new since I last looked?** (Doctor's commentary, lab results, education assigned)
3. **What should I do right now, if anything?** (A single next-best-action)
4. **Am I still in this with someone competent?** (Doctor presence, brand presence, no marketing noise)

If a returning patient cannot answer all four within five seconds of opening Home, the dashboard has failed.

### 5.2 The first fold

The first fold is the visible area before any scroll. It is the most expensive real estate in the product. Cramming it ruins it; under-using it wastes it.

**Recommended composition (mobile, 393×852 reference frame, iPhone 14 Pro):**

```
┌─────────────────────────────────────────┐
│  Top app bar                            │  56px
│  ◯ Hi Niranjan       ⌕   🔔   ⓘ        │
├─────────────────────────────────────────┤
│                                         │
│  Welcome strip (peach mist field)       │  88–112px
│  "Good evening, Niranjan."              │
│  "Dr Mehta will see you tomorrow."      │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Upcoming consultation card             │  ~160px
│  ── doctor avatar ──                    │
│  Dr Anjali Mehta · Endocrinology        │
│  Tomorrow, 4:00 PM                      │
│  [ Join when ready ] (active near time) │
│  [ Pre-consult notes →                ] │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Today's plan strip (compact)           │  ~84px
│  ▢ 8 AM Levothyroxine 50mcg             │
│  ▢ 9 PM Vitamin D 60K                   │
│                                         │
└─────────────────────────────────────────┘
```

The first fold contains: greeting (warm), upcoming consultation (relational), today's plan (functional). Not more. The patient who needs nothing else just learned everything that matters. The patient who needs more keeps scrolling.

**The hero/welcome strip in detail:**

- **Background:** Peach Mist `#FCE4CC` field, ivory undertone preserved by leaving 16px ivory border on left and right (the strip is inset from the edges, not edge-to-edge).
- **Typography:** "Good evening, Niranjan." in DM Sans 18px Forest weight 500. "Dr Mehta will see you tomorrow." in DM Sans 14px Stone weight 400.
- **No Cormorant here** despite being a warm moment. Cormorant is reserved for *display* moments (the post-consultation thank-you, the empty-state heroes); the dashboard hero is a returning-patient greeting, and Cormorant on every load makes the serif theatrical.
- **Time-aware copy:** "Good morning" before noon, "Good afternoon" 12–5pm, "Good evening" after 5pm. Local device time. Always uses first name only.
- **Contextual second line:** if a consultation is today → "Dr Mehta will see you in 2 hours." If pending labs → "Your TSH from yesterday — Dr Mehta will read it tomorrow." If nothing notable → omit the second line entirely (do not pad with platitudes).

**The upcoming consultation card in detail:**

This is the single most important card on the entire dashboard. Specifications:

- **Background:** White card `#FFFFFF` on Ivory page background. 12px radius. 1px Forest 8% opacity border. No shadow (clinical-restrained, not skeuomorphic).
- **Anatomy:**
  - Top row: doctor avatar (40×40, circular, monogram fallback if no photo) + doctor name (DM Sans 16px Forest weight 600) + specialty chip (DM Sans 12px Stone).
  - Below: date and time (DM Sans 15px Ink). When the consultation is within 24h, a Saffron dot precedes the time.
  - Action row: primary CTA "Join when ready" (Forest fill, Ivory text, 44px tap target, full width) becomes active 5 minutes before scheduled time. Before active: "Joins at 4:00 PM" caption only.
  - Secondary action: text link "Pre-consult notes" in Forest, opens the notes sheet.
- **State variations:**
  - Booked, >24h away: full card with reschedule/cancel as overflow.
  - Booked, <24h away: Saffron dot, "Tomorrow" pinned, pre-consult checklist progress visible.
  - Active window (5 min before): "Join now" button in Saffron fill with Forest text (urgency without alarm).
  - In progress: card shifts to "You're in a consultation" with a tap-to-return CTA.
  - Just completed (within 24h): "Your consultation with Dr Mehta ended at 4:23 PM. Note expected within 24h."

**The today's plan strip in detail:**

A compact strip, not a full plan section, sized for the first fold:

- Maximum 3 items visible; "View all in Plan" link if there are more.
- Each item: checkbox (left), time (DM Sans 13px Stone), medication / supplement name (DM Sans 14px Ink), dose (DM Sans 13px Stone).
- Tap the checkbox: mark taken. The row animates softly (220ms ease-out fade) to a completed state — DM Sans Stone strikethrough, no celebration.
- Tap the row body: open medication detail. Not the same as tapping the checkbox.

### 5.3 Below the fold: contextual modules

Below the first fold, modules appear in a priority-ordered stack. Modules that have no content do not appear at all (no "no recent labs yet" placeholders cluttering the dashboard — empty states belong in tabs, not on Home).

Recommended order with rationale:

1. **Next-best-action card** (only if relevant)
2. **Recent lab insight card** (if a lab arrived in the last 7 days)
3. **Doctor's recent commentary card** (if a commentary arrived in the last 14 days)
4. **Assigned education card** (if unread doctor-assigned content exists)
5. **Quick actions row** (always present)
6. **Trust / support footer** (always present)

**The next-best-action card.**

This is the dashboard's most strategic surface. It surfaces the *one* thing the patient should do, not a list. It varies by state:

| Patient state | Next-best-action |
|---|---|
| Recently completed first consultation, prescription issued, no follow-up booked | "Book a 6-week follow-up with Dr Mehta" |
| Lab ordered, not yet uploaded | "Your TSH is due. Upload the report when you have it." |
| Lab uploaded, doctor commentary pending | (No card — the dashboard does not nag the doctor) |
| Adherence dropped below 60% in last 7 days | "Skipping doses? Tap to talk to your doctor." Soft tone, never punitive. |
| Six months in, no recent consultation | "It's been three months since you last saw Dr Mehta. Time for a check-in?" |
| No pending action | No card. Do not invent one. |

Visual: White card, Forest icon at top-left (16×16), Cormorant 20px Forest title line ("Time for a check-in?"), DM Sans 14px Stone body (one sentence), Forest text button at bottom-right ("Book follow-up").

**The recent lab insight card.**

- Background: White card on Ivory.
- Top: small Sage badge "New result" (DM Sans 11px Forest).
- Body: biomarker name (DM Sans 14px Stone) + value with unit (Cormorant 28px Forest, large) + reference range (DM Sans 12px Stone) + status chip (Sage "In range" or Saffron "Slightly off" or Terracotta with Alert escalation only for critical).
- Bottom: Forest text link "See full report".
- Always one biomarker per card, surfaced by clinical relevance not by recency alone. The TSH for a thyroid patient, not the random complete-blood-count value.

**The doctor's recent commentary card.**

This is the one place Cormorant appears in card body:

- Background: White card on Ivory, with a Saffron border-left 3px stroke.
- Doctor attribution at top: small avatar + "Dr Anjali Mehta · 2 days ago" in DM Sans 13px Stone.
- Quoted commentary in Cormorant 18px italic Ink ("Your TSH is responding well to 50mcg. Let's hold this dose and recheck in 8 weeks.")
- Forest text link "See full note".

**The assigned education card.**

- Background: White card on Ivory.
- Small Forest tag "Assigned by Dr Mehta" (DM Sans 11px).
- Article title in DM Sans 16px Forest weight 600 (not Cormorant — saves Cormorant for editorial-grade content where it earns its place).
- Estimated read time + reviewed date in DM Sans 12px Stone.
- Forest text link "Read" (or "Watch" for video).

**The quick actions row.**

Always present, at the bottom of the dashboard above the trust footer. Four actions max, in a horizontally scrolling row only if more than four. Recommended on Home:

```
[ Book ]   [ Upload report ]   [ Refill ]   [ Help ]
```

Each action: a tile, 88×72px, Ivory background, Forest icon, DM Sans 12px Forest label. On tap: subtle 120ms scale-down to 0.96, then navigate.

**The trust / support footer.**

A quiet, low-key footer that reinforces the relationship. Two lines:

- "Need help? The care team is reachable from 9 AM to 9 PM." (DM Sans 13px Stone)
- "Privacy and your data — manage anytime" with link arrow (DM Sans 13px Forest)

No marketing language. No "Rate us 5 stars!" No referral CTAs. The dashboard ends on care and privacy, not promotion.

### 5.4 Persistent vs contextual widgets

| Widget | Persistent or contextual? | Why |
|---|---|---|
| Welcome strip | Persistent | Greeting + day-context relationship anchor |
| Upcoming consultation card | Contextual (only if a consultation exists) | Becomes the patient's most-used module when active |
| Today's plan strip | Persistent (compact, even if zero items) | Habit anchor; compact when nothing due |
| Next-best-action | Contextual (only if relevant) | Avoiding invented prompts |
| Recent lab insight | Contextual (last 7 days only) | Past 7 days is the right freshness window |
| Doctor commentary | Contextual (last 14 days only) | Older commentary lives in past consultation detail |
| Assigned education | Contextual (only unread) | Read content moves to Plan → Education |
| Quick actions row | Persistent | Reachability anchor |
| Trust footer | Persistent | Brand presence + privacy reachability |

### 5.5 How warm vs clinical the dashboard should feel

The 60/40 ratio applied: **the dashboard is 60% clinical white on ivory, 40% warmth via Peach Mist welcome strip, Sage status chips, Saffron accent moments, and one Cormorant moment in the doctor commentary card.** Not more.

The wrong dashboard is one full of pastel cards with hand-drawn icons and motivational copy. The wrong dashboard is also one full of bare clinical tables with no warmth anywhere. The Kyros dashboard is white cards on ivory with restrained warm punctuation in three to five moments.

### 5.6 Empty state for first-time patients

A first-time patient (no booked consultation, no labs, no plan) should not see a wall of empty placeholders. The dashboard adapts:

```
┌─────────────────────────────────────────┐
│  Top app bar                            │
├─────────────────────────────────────────┤
│                                         │
│  Welcome hero (peach mist field)        │  ~200px
│                                         │
│  Cormorant 28px Forest:                 │
│  "Welcome to Kyros, Niranjan."          │
│                                         │
│  DM Sans 15px Stone:                    │
│  "Begin with a doctor. The first        │
│  consultation is ₹400."                 │
│                                         │
│  [ Book your first consultation ]       │
│  (Forest fill button)                   │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  How Kyros works                        │  ~280px
│  (3-step quiet list, no illustration)   │
│                                         │
│  1. A doctor who stays with you.        │
│  2. A place where your health lives.    │
│  3. A platform where privacy is the     │
│     point.                              │
│                                         │
├─────────────────────────────────────────┤
│  Quick actions row                      │
│  Trust footer                           │
└─────────────────────────────────────────┘
```

The three-pillar copy here is the locked brand copy from business strategy. It earns its place here because this is the moment the patient is choosing whether to invest.

### 5.7 Dashboard interactions

- **Pull to refresh:** subtle. A small Forest-tint ring appears under the welcome strip. Refresh completes in <800ms. No bounce overshoot.
- **Module entry:** each module fades in (220ms ease-out) on first load, in DOM order. No staggered slide-ups (too theatrical).
- **Tap on a card:** subtle 120ms scale-down to 0.98, then navigate. Tap target is the entire card surface for primary actions.
- **Long-press on a card:** no context menu. Long-press is reserved for OS-level menus the patient is unlikely to want here.
- **Card dismissal:** never. Cards reflect state, not notifications. They appear and disappear based on data, not on user dismissal.

### 5.8 What the dashboard must never become

- A widget dump. More than seven visible modules on first load is a failure.
- A marketing surface. Banners promoting other verticals, supplements, or partner products are banned.
- A coaching app. No "you're 3 days into your streak!" No motivational quotes. The dashboard is care continuity, not behaviour theatre.
- A symptom checker. No "How are you feeling today?" with mood emojis. If symptom check-ins are valuable, the doctor orders them as a structured task on Plan; the dashboard does not lead with them.
- A chat surface. No persistent chat module on the dashboard. Chat with the care team, if it exists, lives inside Consult detail and Help & support.

---

## 6. Consultation UX

The consultation is the single most important act in the entire product. Everything else in the app exists to make consultations more competent, more continuous, and more trusted. This section designs the complete consultation experience from booking to follow-up.

### 6.1 The booking flow — three screens, not seven

Most telemedicine apps build seven-screen booking funnels and lose 40% of patients to abandonment. The Kyros booking flow is three screens, with intake deferred to *after* booking confirmation.

```
Screen 1 — Choose your concern (vertical)
Screen 2 — Choose your slot (doctor + time, combined)
Screen 3 — Pay and confirm
```

This compression is intentional. The deciding action — "am I going to book a consultation today?" — happens in the first 30 seconds. Every screen between intent and confirmation is an opportunity for abandonment.

**Screen 1 — Choose your concern.**

- Header: "What brings you in?" (DM Sans 18px Forest weight 600).
- A grid of seven vertical tiles (Thyroid, Weight, PCOS, Skin & hair, Men's intimate, Hormones, Longevity). Each tile: Ivory background, Forest icon (24×24 line icon, no fill), Forest title (DM Sans 14px weight 600), Stone subtitle (DM Sans 12px) describing the vertical in patient language ("Hair loss, adult acne, melasma" rather than "Dermatology").
- One tile selected at a time; selected tile gets a 2px Forest border.
- Persistent footer "Not sure? Tap here." opens a short symptom-to-vertical routing sheet.
- Primary CTA "Continue" (Forest fill, full-width, 44px, anchored to bottom).

**Screen 2 — Choose your slot.**

This is where most apps fail. The Kyros approach combines doctor and time into a single decision rather than forcing two screens. Default behaviour:

- **Top of screen:** "Any available doctor, soonest slot" (Saffron-bordered card). Tapping reveals the soonest 3 slots in the next 48h with the doctors who hold them, named. Selecting confirms doctor + time in one action.
- **Below:** "Choose a specific doctor" expanded list of available doctors in the chosen vertical, each with their next 3 slots. Doctor row anatomy: avatar (or monogram), DM Sans 16px Forest name, DM Sans 12px Stone NMC reg + specialty + languages, three slot chips horizontally.
- A "Show more slots from Dr Mehta" affordance opens a calendar-and-time picker sheet for that specific doctor.

**Day rail vs calendar.** For specific-doctor slot picking inside the sheet, a **day rail** (horizontal scrolling chips of dates, 7 days visible) beats a full-month calendar. Patients booking medical care think in terms of "the next 3-4 days," not "May 14th." The day rail surfaces the soonest dates first; a calendar picker is available behind a "Pick a date" button for >7-day-out booking.

**Time slot grid.** Once a date is chosen, time slots render in a 3-column grid: morning, afternoon, evening sections. Available slots in Forest text on White card; unavailable in Stone text on Ivory chip; selected in Ivory text on Forest fill.

**Doctor detail.** From either doctor selection surface, tapping the doctor's name (not the slot chip) opens a sheet with full doctor detail: photo or monogram, name, NMC reg, specialty, training (one line: "MBBS, MD Endocrinology, AIIMS Delhi"), languages, clinical interests, years of experience, brief calm bio (2 sentences, plain, no marketing). No reviews, no star ratings, no patient testimonials inside this sheet (those belong on the marketing site, not in-product where they corrode trust).

**Screen 3 — Pay and confirm.**

- Summary block: doctor (avatar + name + NMC reg), date and time, fee. No upsells. No "add a lab test" cross-sell. No supplement attachments.
- Fee in DM Sans 18px Ink with breakdown in DM Sans 13px Stone ("₹400 consultation · no platform fee, no GST hidden").
- Payment method selector: UPI as primary, card and wallet as alternatives. Saved payment method (if returning patient) selected by default.
- Primary CTA "Pay ₹400 and book" (Forest fill, full-width, 48px). The amount is in the button so the patient confirms the price as they confirm the booking.

**Confirmation.**

After payment success, the screen transitions (450ms ease-in-out) to a confirmation:

- Cormorant 24px Forest: "You're booked with Dr Anjali Mehta."
- DM Sans 15px Ink: "Tomorrow at 4:00 PM. We'll send a reminder an hour before."
- DM Sans 14px Forest text link: "Add to calendar"
- Card: Pre-consult checklist (4 quick items) preview. Forest text link "Open pre-consult notes →" — strongly nudged but not required.
- Primary CTA "Done" (Forest fill).

The confirmation does not say "Congratulations!" It does not animate confetti. It treats the booking as routine and important — the register the doctor would use.

### 6.2 Pre-consultation experience

The 24 hours before a consultation are an opportunity to make the call more useful. The patient prepares; the doctor receives that preparation; the consultation begins from a richer baseline.

**Pre-consult checklist** (4 items recommended):

1. **Add to your story** — free-text "What would you like Dr Mehta to know?" Soft prompt, not required. Persists if the patient returns.
2. **Recent labs uploaded?** — if labs are required for the consultation context, this nudges upload. If no labs are needed, omit this entirely.
3. **A quiet 15 minutes** — gentle reminder to find privacy and stable connectivity.
4. **Your phone charged** — practical, briefly stated.

The checklist appears on the upcoming consultation detail screen. Items can be marked done. Marking everything done is *not* a requirement to join the call. The checklist is a tool, not a gate.

**Pre-consult notes.** Free-text field with placeholder "What would you like Dr Mehta to know about your story, recent symptoms, or what you're hoping to discuss?" Patients with low-trust archetypes (F) need this space most. The field accepts up to ~1500 characters. Word counter not shown until 1300 (no premature gating signal). Notes are visible to the doctor before and during the consultation, indicated by a small "Dr Mehta has read your notes" indicator that turns Sage when read.

**Reminders.** 24h before: gentle SMS or push ("Your consultation with Dr Mehta is tomorrow at 4 PM."). 1h before: more prominent ("In 1 hour. Pre-consult notes →"). 10 minutes before: "Join when you're ready." All respecting the notification-privacy preference (generic vs detailed).

### 6.3 Waiting room

The waiting room is the 5-minute pre-call surface, the most under-designed area in most telemedicine apps. The Kyros waiting room:

- **Background:** Ivory with a Peach Mist top-strip.
- **Content:**
  - Doctor avatar (64×64), name, specialty.
  - Status line in DM Sans 16px Forest: "Dr Mehta is preparing for your consultation." (Updates as state changes.)
  - Secondary line: "She has read your pre-consult notes." (Sage tone — quietly reassuring.)
  - Camera/mic check tile: small video preview of the patient's camera, mic level meter, "Adjust settings" Forest text link.
  - Primary CTA "Join when ready" — disabled (Stone) until the doctor is ready (Saffron fill, Forest text), then becomes the active button.
  - Bottom-right small text "Need help? Contact care team" Forest link.
- **State transitions:**
  - Doctor not yet in room: "Dr Mehta is preparing for your consultation."
  - Doctor ready, patient not: "Dr Mehta is ready when you are."
  - Doctor running late: "Dr Mehta is running about 8 minutes late. Apologies." (Saffron text on Ivory. Never red.)
  - Doctor in another consultation: "Dr Mehta is finishing another consultation. She'll be with you shortly."

The waiting room is the surface that handles delays with honesty. The wrong waiting room shows a static screen and lets the patient wonder. The right one explains.

### 6.4 The in-call surface

Designed to look like the consultation room, not a video conference. Specifications:

- **Background:** Forest 95% with a slight Ivory tint visible at the edges. (Dark surface for video, but not pure black — preserves brand presence.)
- **Doctor video:** large, top-center, with a small DM Sans 12px Ivory caption with the doctor's name persistently visible. (Real consultation rooms have a name plate; the digital equivalent.)
- **Patient self-video:** picture-in-picture, top-right corner, 96×128. Can be tapped to swap to large.
- **Controls:** bottom strip, three primary actions — Mic toggle, Camera toggle, End call (Alert red, last, separated by extra spacing). Two secondary actions — Chat toggle (opens a side panel for typing if audio fails), Share file (for the doctor to push an article or for the patient to share a photo of a symptom).
- **Time elapsed:** small DM Sans 12px Ivory in top-left.
- **No filters, no backgrounds, no AR effects.** The doctor and patient are in a clinical conversation.

**Connection issues.** If the call drops mid-session: "Connection lost. Reconnecting…" overlay with a Saffron progress indicator. If reconnection fails within 20s: "We couldn't reconnect. Dr Mehta will call you on your phone at +91 ••••• 56789. (Tap to dial Kyros care team if needed.)" Phone fallback is critical because consultations should not be lost to wifi failure.

**Doctor mid-call sharing.** Doctors may push a document (an article, a prescription preview, an anatomical diagram) to the patient's screen during the call. The pushed document appears as a small Forest-bordered card at the bottom of the patient's screen, tappable to expand. The patient's video remains primary.

### 6.5 Post-call experience

The post-call window is where many telemedicine apps drop the patient on a "Thank you for your consultation" dead-end. The Kyros approach treats post-call as the most useful moment:

- **Immediate post-call screen (within 5 seconds of call end):**
  - Cormorant 22px Forest: "Your consultation with Dr Mehta has ended."
  - DM Sans 15px Stone: "She'll add her note within 24 hours. Here's what happens next."
  - Card 1: "Prescription issued" — Forest fill button "View prescription" (immediately available if the doctor prescribed during the call).
  - Card 2: "Labs ordered" — Forest fill button "View lab orders" (with a "Where to get these tests" link).
  - Card 3: "Follow-up scheduled" — Forest fill button "View follow-up booking" or "Book follow-up" if the doctor recommended one but did not schedule.
  - Card 4: "Education assigned" — link to articles the doctor wanted the patient to read.
  - Bottom: "We'll send a survey shortly. Your feedback shapes the panel." (Optional NPS, not blocking.)

The post-call structure is itself an artifact of care: it tells the patient that things happen *after* the conversation, and the app holds the continuity.

### 6.6 Doctor's note arrival

Within 24 hours, the doctor adds a written note. The patient receives:

- Push notification (respecting privacy preference): "Dr Mehta has added a note from your consultation." (generic) or "Dr Mehta has added her consultation note." (detailed).
- The note appears on Home as a "Doctor's recent commentary" card (described in §5.3) for 14 days.
- The note lives permanently inside the past consultation detail.

The doctor's note is rendered in DM Sans 15px Ink with selective Cormorant 18px italic Forest pull-quotes if the doctor uses a "highlight this" annotation tool. The note structure is doctor-authored, not template-locked — but Kyros provides a recommended structure (Assessment, Plan, Next steps) that doctors can use.

### 6.7 Following up

If the doctor recommended a follow-up in 6 weeks:

- A "Book follow-up with Dr Mehta" card persists on Home for 14 days post-consultation.
- A reminder fires 7 days before the recommended follow-up window.
- Rebooking is one-tap: the slot picker pre-selects the recommended doctor and surfaces slots in the recommended window.

This is where continuity of care becomes visible: the same doctor, the next consultation, accumulating into a relationship.

### 6.8 Booking abandonment minimisation

The booking flow's primary failure mode is abandonment after slot selection but before payment. Mitigations:

- **No new fields requested at payment.** Phone number, name, and basic profile are captured at signup, not at booking.
- **Saved payment method** for returning patients (with explicit consent recorded at first save).
- **Apparent commitment device:** the slot is held for 10 minutes after selection, visible to the patient ("This slot is held for you for 9:47.") rather than vague urgency. Honest hold, not pressure tactic.
- **Refund clarity:** "Cancel up to 2 hours before for a full refund" stated next to the pay button. Removes the "what if I have to cancel?" cognitive load.

### 6.9 Slot picking decisions

**Calendar-first or time-first?** Time-first, by default. The patient's primary question is "How soon can I see a doctor?" not "What's the calendar look like?" The "soonest slot" surface (described in §6.1) answers the primary question in one screen. A full calendar exists for patients who want to schedule further out.

**How much doctor detail to show before booking?** Just enough: photo or monogram, name, NMC reg, specialty, languages, next 3 slots. Full doctor profile is one tap behind the name. Showing the full CV at this stage adds cognitive load to a decision that is primarily about "is this a real doctor?" — a question answered by name + NMC reg.

**Trust signals that matter most before booking:** NMC registration number, named specialty (not "general physician" for a hormonal consultation), explicit fee, the existence of a follow-up policy. Trust signals that *do not* matter (and shouldn't be shown): star ratings, "X patients booked this week," "satisfaction guaranteed."

### 6.10 What happens next

The phrase "what happens next" is repeated through the consultation flow because uncertainty is the patient's biggest source of friction. The app should answer "what happens next" before the patient asks it, at every transition:

- After booking → "Dr Mehta will see you tomorrow at 4. We'll remind you an hour before."
- After joining the waiting room → "Dr Mehta is preparing. You'll join in a moment."
- After the call ends → "Her note will arrive within 24 hours. Here's what was issued."
- After the note arrives → "Read the note. Book your follow-up when you're ready."
- After follow-up booked → "We'll see you in 6 weeks."

The presence of this answer at every step is what makes the product feel like continuous care, not a transaction stack.

---

## 7. Lab reports UX

This is the flagship surface. The lab report experience is where Kyros's "One place, where your health lives" promise becomes evident or evaporates. Most telemedicine apps treat lab reports as PDF attachments. The Kyros approach is to make labs the longitudinal spine of the patient's record.

### 7.1 The lab experience's job

The lab experience must do four things:

1. **Ingest labs accurately**, from any source (Dr Lal PathLabs, Thyrocare, Metropolis, Apollo Diagnostics, smaller local labs), in any format (PDF, photo, scan), with OCR that the patient can correct without feeling the app is broken.
2. **Render labs intelligibly** for a patient who is not a clinician, without dumbing down what a clinician would understand.
3. **Track biomarkers longitudinally** with charts that show real change without manufacturing drama from noise.
4. **Surface the doctor's reading** of the labs — not algorithmic interpretation, but the actual doctor's commentary.

If the lab experience does these four things well, it is the single feature most likely to make a patient stay with Kyros for years.

### 7.2 Upload flow

**Entry points to upload:**
- Labs tab → "Upload report" button (top right of the labs list).
- Home → Quick actions row → "Upload report".
- After a doctor orders labs → Consultation detail → "Upload your TSH when you have it" card.

**The upload entry screen:**

- Header: "Upload a lab report" (DM Sans 18px Forest weight 600).
- Two primary options as equal cards (not buttons in a row, full-width cards stacked):
  1. **Take a photo** — for paper reports. Forest icon, "Capture your report" subtitle.
  2. **Pick a file** — for PDFs from email or labs' apps. Forest icon, "PDF or image from your phone" subtitle.
- Below: small Stone caption "We accept reports from any lab. Original files are preserved."

The wording matters. "We accept reports from any lab" reassures the patient that the upload is not gated by a partner list. "Original files are preserved" addresses the lab-report-heavy patient's fear of losing data.

**Camera capture flow:**

- Standard camera surface with capture button. Forest tint on the capture button.
- After capture: full-frame preview with two actions: "Add another page" (for multi-page reports) and "Use this".
- Multi-page reports show a small bottom strip of captured pages, reorderable by drag.
- Final review screen: "Ready to upload?" with all pages thumbnailed in a vertical scroll. Primary CTA "Upload N pages" (Forest fill).

**File picker flow:**

- Native iOS / Android picker (Files app, Photos, Recent files).
- After selection: review screen with file name, size, type. Primary CTA "Upload" (Forest fill).

### 7.3 OCR processing

OCR happens server-side, takes ~5–15 seconds for a standard one-page report. During processing:

- Full-screen state with Ivory background.
- DM Sans 16px Forest: "Reading your report…" (do not say "Analyzing" or "Processing" — these are AI words; "Reading" sounds like a human task, which matches the warmth.)
- Subtle Forest dot animation (three dots fading in sequence, 800ms total cycle, no bounce, no spring).
- DM Sans 13px Stone caption: "We're extracting values so they appear on your trend charts."
- No estimated time (estimates that prove wrong destroy trust more than uncertainty).

**Edge case: OCR taking longer than 15 seconds.** After 15s, the caption updates: "Taking a moment longer than usual. We'll let you know when it's ready." The patient can navigate away — a notification will fire when complete.

### 7.4 OCR correction UI

This is the single most important screen in the labs experience. OCR fails sometimes. The patient must be able to correct it without feeling the app is unreliable.

**High confidence (>90% confidence on all extracted values):**

- Header: "We extracted your report. Take a quick look." (DM Sans 18px Forest weight 600). Tone is calm, not asking for laborious review.
- Each biomarker row: Sage tick icon (12×12), biomarker name (DM Sans 14px Ink), value with unit (DM Sans 15px Ink, monospace numerals), reference range (DM Sans 12px Stone).
- Tap any row to edit; tapping reveals an inline edit field.
- Primary CTA at bottom: "Looks right" (Forest fill, full-width).
- Secondary text link: "Something wrong? Edit values".

**Low confidence (any value <80% confidence):**

- Header: "We extracted your report, but we're not fully sure on a few values."
- High-confidence rows: Sage tick, as above.
- Low-confidence rows: Saffron edge (3px left border on the row), Saffron warning chip in the value field "Confirm".
- Tapping a low-confidence row expands to show the original PDF region highlighted (a small inset thumbnail of the relevant section) alongside the editable field. The patient sees what the OCR read and what was in the source.
- Primary CTA: "Confirm values" (Forest fill, full-width, disabled until all low-confidence rows are confirmed).
- Secondary text link: "Skip OCR — let the doctor read it manually" (for low-confidence reports the patient doesn't want to correct).

**Failed OCR (the report could not be parsed):**

- DM Sans 16px Forest: "We couldn't read this report automatically."
- DM Sans 14px Stone: "Your original file is saved. Dr Mehta will read it during your next consultation."
- Primary CTA: "Add values manually" (Forest outline button) — for patients who want their biomarkers tracked.
- Secondary: "That's fine, just keep the PDF" (Forest text link) — for patients who only want the report archived.

### 7.5 Lab report detail screen

The flagship surface. Designed to render a complete report intelligibly on a mobile screen.

**Composition (top to bottom):**

1. **Header strip.** Source lab name (DM Sans 16px Forest weight 600), test date (DM Sans 13px Stone), report number if available (DM Sans 12px Stone).
2. **Doctor commentary card** (if commentary exists). White card with Saffron border-left. Doctor avatar + name + date. Commentary in DM Sans 15px Ink, with optional Cormorant italic pull-quotes for emphasis the doctor adds.
3. **Doctor commentary pending state** (if no commentary yet, lab is <48h old): Sage tint card, "Dr Mehta will read these results within 24 hours of arrival." DM Sans 14px Stone. No more.
4. **Flagged values summary** (if any out-of-range): a single card listing biomarkers outside their reference range. Each row: biomarker name, value, range, status chip. Maximum 5 visible; "View all flagged →" if more.
5. **All biomarkers, grouped by clinical panel.** Each panel (Thyroid, Lipid, Metabolic, Liver, Kidney, Hormonal, etc.) is a section with a DM Sans 13px uppercase Forest header. Within each panel, biomarker rows.
6. **Original report PDF.** A card with the PDF preview thumbnail and "View original PDF" Forest text link. Also "Download" affordance.
7. **Compare with previous** Forest text button at the bottom, opens the comparison view.

**Biomarker row anatomy:**

```
┌──────────────────────────────────────────────┐
│  TSH                              2.4 mIU/L  │
│  Thyroid stimulating hormone      0.4–4.0    │
│                                              │
│  ─────────●──────────────  ✓ In range       │
└──────────────────────────────────────────────┘
```

- **Biomarker name** (DM Sans 14px Ink weight 600) and **abbreviation** in cell, full name in DM Sans 12px Stone below.
- **Value** (DM Sans 16px Ink, monospace numerals for legibility) with **unit** (DM Sans 13px Stone).
- **Reference range** as DM Sans 12px Stone "0.4–4.0".
- **Range bar:** a thin horizontal bar (4px height, Sage tint for in-range zone, Saffron tint for borderline zones at the edges, the patient's value marked by a Forest dot). On tap: expands to the biomarker detail screen.
- **Status chip:** Sage "In range" / Saffron "Slightly off" / Terracotta with Alert escalation "Outside range — speak with your doctor". Never red unless clinically critical.
- Tap target: the entire row.

**Visual hierarchy for abnormal values.** Three tiers, with restraint:

1. **In range** — Sage chip, no emphasis. The value is just a fact.
2. **Slightly off** (within ~20% of the range boundary, clinically often-fine) — Saffron edge on the value, Saffron chip "Slightly off". The row reads as informational, not alarming. Saffron is curiosity colour, not warning colour.
3. **Outside range, clinically relevant** — Terracotta edge, Terracotta chip "Outside range". The row is more visually distinct but still not red. Red is reserved for genuine critical values.
4. **Critical** — Alert (`#B53A2B`) chip "Urgent — call care team", with an inline Forest banner above the row "This value requires attention. Dr Mehta has been notified." Used only when clinically warranted (e.g. potassium >6, hemoglobin <7, glucose >400). This treatment may appear once or twice in a patient's entire history.

The key principle: **most labs are not red.** A patient who opens their report and sees three different shades of warning learns to distrust the colour system. Saffron is for "look here," not "be alarmed." Restraint earns the rare alert.

### 7.6 Biomarker trend screens

The trend view is where the lab data becomes a relationship. Most patients will tap into TSH (or testosterone, or HbA1c, depending on their condition) and see how it has moved over months.

**Biomarker detail screen composition:**

1. **Header:** biomarker name in Cormorant 28px Forest ("TSH"). Below: full name (DM Sans 13px Stone "Thyroid stimulating hormone").
2. **Current value block:** large display numeral in Cormorant 56px Forest with unit in DM Sans 16px Stone. Status chip below.
3. **Trend chart** (described in detail below).
4. **History table:** chronological list of all values for this biomarker, with source lab, date, value, reference range used at the time. DM Sans throughout, monospace numerals.
5. **What's normal for this** explainer (collapsible). DM Sans 14px Ink body, plain language. No marketing.
6. **Last doctor commentary on this biomarker** (if any). Same card style as elsewhere.

**Chart specifications:**

- **Plot type:** line chart with reference range as a sage-tinted band.
- **X-axis:** time, labeled as "Today / 7 days ago / 30 days ago / 90 days ago / 1 year ago" depending on selected range. Not raw dates on x-axis — too dense.
- **Y-axis:** biomarker units. Range auto-scaled to encompass both data and reference range. Labels in DM Sans 12px Stone.
- **Reference range band:** Sage `#8FA88E` at 25% opacity, behind the line.
- **Out-of-range zones:** Saffron at 15% opacity above and below the reference band.
- **Critical zones (rare):** Alert at 12% opacity at extreme values; only rendered if those zones are relevant to this biomarker.
- **Data line:** 2px stroke, Forest `#0F3D2E`. Slightly desaturated if more than 90 days range is shown (to prevent visual aggression on long ranges).
- **Data points:** 6px Forest dots; if a value is out-of-range, the dot is Saffron with a Forest border 1px.
- **Latest point:** larger (10px), with a Forest leader line down to the x-axis and a small DM Sans 13px Forest label "Today" or the latest date.
- **No grid lines** except a soft Stone 10% horizontal line at each reference range boundary.
- **Range selector:** segmented control above the chart: 7d / 30d / 90d / 1y / All. Selected: Forest fill, Ivory text. Unselected: Forest text on Ivory. 14px DM Sans.
- **Touch interactions:**
  - Tap on a data point: tooltip appears with date, value, source lab, status. Persists until tapped away.
  - Drag along the line: a vertical Forest line follows the finger, with a callout showing the value at that point (interpolated or actual). Releases the line on release.
  - Pinch-zoom: disabled. Range selector handles zoom — pinch on touchscreens reads as clumsy on health data.
- **Loading state:** chart skeleton with sage reference band visible, line absent, "Loading trend…" caption in DM Sans 13px Stone.
- **Empty state:** "Only one TSH value so far. Trends become useful with three or more readings." Sage tone, not blocking.

**Comparison overlays.** A toggle below the chart: "Compare with [Cholesterol / HbA1c / etc.]" — adds a second biomarker as a dotted Forest line, on its own secondary y-axis. Comparison is opt-in, not default. Most patients want to read one biomarker at a time.

### 7.7 Flagged markers summary

When a report has multiple out-of-range values, the patient needs an at-a-glance read. The flagged markers summary card on the report detail surface:

- Header: "Flagged for attention" (DM Sans 14px Forest weight 600). Saffron icon next to it (warning, not alarm).
- A short list of biomarkers outside their reference range. Each row: biomarker name (DM Sans 14px Ink), value, range, status chip.
- Bottom: "Dr Mehta will read these in her commentary." (DM Sans 13px Stone). Or, if commentary exists, "See Dr Mehta's reading above" with Forest text link.

The card does *not* tell the patient what to do. It tells them what to notice. The doctor tells them what to do.

### 7.8 Compare across reports

A two-report side-by-side comparison surface:

- Top: two report headers (lab, date) with a swap-affordance.
- Below: biomarker rows showing the value from each report side-by-side, with a small Forest arrow indicating direction of change (up, down, unchanged). The arrow is a glyph, not a colour — direction is information, not necessarily good or bad.
- Each row: biomarker, value 1, value 2, delta (e.g. "−12%").
- Sticky bottom: "View doctor's commentary on this comparison" if a comparison-specific note exists.

On mobile, the two-column view is genuinely tight. The compromise: scrollable horizontal section per row, with the biomarker name pinned on the left.

### 7.9 OCR low-confidence indicators

When values in the saved report came from a low-confidence OCR pass that the patient confirmed but the system still wants to flag for posterity:

- A small Saffron dot beside the value (4px), with a tooltip "This value was confirmed by you from a low-confidence read. Tap to verify against original."
- The original PDF is always accessible. The trust principle: never let extracted data hide the source.

### 7.10 Connecting labs to consultation readiness

When a patient has new labs and a consultation in the next 7 days:

- On the upcoming consultation card (Home + Consults), a small Sage chip appears: "New labs ready for review."
- The pre-consult checklist updates with "Recent labs uploaded — Dr Mehta will see them."
- After the consultation, the doctor's note typically references the labs; the labs detail screen surfaces a "Discussed in your consultation on [date]" link.

This is what continuity feels like: labs and consultations are not separate; they are arms of the same record.

### 7.11 What the labs experience must avoid

- **Red as the dominant out-of-range colour.** Saffron is the warning colour for routine variation. Terracotta for clinically meaningful variation. Red (Alert) for the rare critical value.
- **Algorithmic interpretation pretending to be clinical advice.** "Your cholesterol indicates a 14% risk of cardiac event in 10 years." This is the wrong product. The doctor reads. The patient reads the doctor's reading.
- **Gamified health scores.** "Your thyroid score is 78/100." Composite scores reduce clinical information; they look proprietary but they obscure rather than reveal.
- **Smoothed trend lines that hide noise.** TSH varies between days, and the variation matters clinically. Showing a polynomial fit makes the chart look prettier and the data less true.
- **Pastel chart palettes.** Light blue lines on light grey backgrounds — common in wellness apps, wrong for clinical data.
- **Charts without reference ranges.** A TSH value of 2.4 is meaningless without the range. Always show the range, always.
- **Charts without units.** Forgetting units is the single most common chart failure in health apps. Always show units.


---

## 8. Prescription UX

The prescription experience must read as clinical and trustworthy, not as e-commerce. A prescription is a clinical document; the app surfaces it as such. The wrong reference is Amazon Pharmacy. The right reference is the doctor's actual prescription pad — typed, legible, signed.

### 8.1 The prescription list

The prescriptions list is reached from Plan → Medications, and from past consultation detail. It is *not* a separate tab (medications and prescriptions overlap conceptually; separate tabs would split the patient's mental model).

**Composition:**

- **Header:** "Your prescriptions" (DM Sans 18px Forest weight 600).
- **Segmented control:** "Active · Past" (DM Sans 14px). "Active" by default.
- **Active list:** white cards, one per prescription. Each card:
  - Top row: "Issued [date]" (DM Sans 12px Stone) + Sage chip "Active" (DM Sans 11px Forest).
  - Body: doctor name + NMC reg + specialty (DM Sans 14px Forest).
  - Medications listed (max 3 visible, "+N more" if more): DM Sans 14px Ink + dose + frequency.
  - Footer: "View prescription" Forest text link + "Download PDF" Forest text link.
- **Past list:** same anatomy, "Active" chip replaced by Stone chip "Past" (no longer prescribed).
- **Empty state:** Cormorant 20px Forest "Your prescriptions will live here." DM Sans 14px Stone "Once your doctor issues a prescription, it stays accessible permanently." Not blocking.

### 8.2 Prescription detail screen

The clinical document surface. Designed to feel like a real prescription, not a screenshot:

**Composition:**

1. **Clinic header strip.** Kyros wordmark (small, top-left), clinic registration details (right-justified, DM Sans 11px Stone). This is identical to what would appear on a printed prescription pad. Crucial for the patient when they need to show this prescription to a pharmacist.
2. **Doctor block.** Doctor name (DM Sans 16px Forest weight 600), NMC registration number (DM Sans 13px Stone), specialty + qualifications (DM Sans 13px Stone). Signed-by-doctor indication: a small Sage "Signed" chip with timestamp.
3. **Patient block.** Patient name (DM Sans 15px Ink), DOB (DM Sans 13px Stone), gender, weight if recorded. Prescription ID (DM Sans 12px Stone, monospace).
4. **Date issued.** DM Sans 14px Forest.
5. **Diagnosis (if disclosed).** Small section, DM Sans 14px Ink. Often deliberately omitted on prescriptions for sensitive conditions.
6. **Medications.** Each medication as a structured row (see below).
7. **Instructions block.** Doctor's free-text instructions in DM Sans 15px Ink. ("Take levothyroxine on empty stomach, 30 minutes before breakfast. Avoid taking with calcium or iron supplements.")
8. **Refill / duration info.** DM Sans 14px Forest "Valid for 30 days" + Forest text link "Request refill".
9. **Footer.** "Original digital prescription. Verify at kyrosclinic.com/verify/[ID]" (DM Sans 12px Stone). This is the public verification surface for pharmacists.

### 8.3 Medication row anatomy

Each medication on the prescription:

```
┌──────────────────────────────────────────────┐
│  Levothyroxine 50 mcg                        │
│  Levothyroxine sodium · Tablet               │
│                                              │
│  Take 1 tablet · Once daily · Morning        │
│  Empty stomach, 30 minutes before breakfast  │
│                                              │
│  Duration: 90 days (continues)               │
└──────────────────────────────────────────────┘
```

- **Drug name** (DM Sans 16px Ink weight 600) — brand or generic as the doctor wrote it. **Below it, the alternative** in DM Sans 13px Stone — if the doctor wrote a brand, the generic name appears below; if the doctor wrote generic, the common brand(s) appear below. This prevents the pharmacy substitution confusion that bedevils Indian retail pharmacies.
- **Form** ("Tablet", "Capsule", "Injection", "Cream") DM Sans 13px Stone.
- **Dose schedule** in plain language: "Take 1 tablet · Once daily · Morning". Not "OD" or "1-0-0".
- **Specific instructions** (DM Sans 14px Ink): "Empty stomach, 30 minutes before breakfast." Doctor-authored.
- **Duration** (DM Sans 14px Forest): "Duration: 90 days (continues)" — for ongoing meds, "(continues)" makes it clear refills are part of the plan.
- **Caution / interaction note** if the doctor added one: small Saffron edge, "Avoid: calcium and iron supplements within 4 hours."

### 8.4 Dosage change history

For ongoing medications, the dose may change. The history is critical clinical context — for the patient, the next doctor, and the pharmacist.

**Dosage timeline view:**

A vertical timeline showing dose over time, with consultation context attached:

```
50 mcg — 6 weeks ago
└── Started after consultation with Dr Mehta on May 14

25 mcg — 3 months ago
└── Started after consultation with Dr Mehta on March 12

(Initial dose, no prior history)
```

Each entry:
- Dose change (DM Sans 16px Forest weight 600).
- Date (DM Sans 13px Stone).
- Context line ("Started after consultation with Dr Mehta on [date]") with Forest text link to the consultation detail.
- Optional doctor note ("Increased because TSH plateaued at 4.2") in DM Sans 14px Stone italic — appears if the doctor annotated the change.

The timeline rendering uses simple Stone-tinted vertical line on the left margin, Forest dots at each event, DM Sans throughout. No animation, no fancy transitions.

### 8.5 PDF access

Every prescription has a downloadable PDF. The PDF is the legally-formatted clinical document. The in-app rendering is a *companion* to the PDF, not a replacement.

- Forest text button "Download PDF" prominently visible at the top and bottom of the prescription detail screen.
- The PDF is generated server-side, with: Kyros letterhead, doctor signature (digital, with timestamp), all prescription detail, and a verification URL+QR code at the bottom.
- "Share PDF" affordance — opens the OS share sheet. The patient can share with pharmacy, with their primary doctor, with a family member.

### 8.6 Refill workflow

For ongoing prescriptions, refill is a structured workflow:

- **Refill request CTA** on prescription detail: Forest text link "Request refill from Dr Mehta".
- Tapping opens a sheet: "Request refill of [medication name]"
  - Reason (chips): "Running low" / "Need 30 days more" / "Dose working well" / "Other"
  - Optional free-text "Anything else?" (max 500 chars)
  - "Submit refill request" (Forest fill)
- After submit: "Request submitted to Dr Mehta. Most refill requests are answered within 24 hours." Status appears on the prescription card.
- When the doctor responds: push notification, and the prescription updates with the renewed PDF.

Refill is not auto-approved. A doctor reviews every refill request, because that is the doctor-first principle in action. The product makes the workflow fast, not automatic.

### 8.7 Medication interactions

If a patient is on multiple prescriptions across multiple doctors, the system can surface interaction warnings — but cautiously. The principle: **flag for the doctor, not for the patient.**

- If a new prescription contains an interaction risk with an existing medication, the patient sees a small Saffron caption on the prescription detail: "Dr Mehta has noted this interacts with your levothyroxine. Take them 4 hours apart."
- The patient is *not* given a generic interaction database warning. Algorithmic interaction warnings make patients anxious and don't help them.
- The interaction is the doctor's annotation, not the algorithm's.

### 8.8 What the prescription UX must avoid

- **Pharma e-commerce aesthetic.** Big "Buy now" buttons, partner pharmacy logos, "Save 20%" copy. This is poison to clinical trust.
- **Generic vs brand confusion.** Always show both names. Pharmacy substitution is a real problem; the patient needs to know what they were prescribed and what is acceptable to substitute.
- **Dosage schedule jargon.** "BD," "TDS," "OD," "1-0-1" — doctors write these; the app translates. "Twice daily · Morning and evening." Patients shouldn't decode.
- **Hiding the PDF.** The PDF is the legal artifact. It should be one tap away, always.
- **Hiding dosage change history.** This is critical clinical context, especially for hormones, thyroid, and chronic conditions.
- **Auto-refill workflows.** A doctor reviews every refill. The product makes the workflow fast, not autonomous.
- **Medication shopping.** Showing alternative brand prices, partner pharmacy availability, or supplement upsells alongside a prescription. The prescription surface is a clinical document, not a marketplace.

---

## 9. Reminders and adherence UX

Reminders are the most-corrupted surface in consumer health apps. They become nagging, gamified, streak-driven, anxiety-producing. The Kyros approach treats reminders as a tool the doctor's plan uses, not as a habit-tracking app embedded inside a clinic.

### 9.1 The framing: care continuity, not habit tracking

The mental model is: **the doctor wrote a plan. The reminders are how the plan reaches the patient on the right day, at the right time. Adherence data is information the doctor uses to adjust the plan.**

This is the inversion of habit-tracking apps. There, the patient *is* the habit-system. Here, the doctor is, and the patient executes. The product's job is to make execution effortless and to surface adherence to the doctor without judgment.

Consequences:

- No streaks. No "37-day streak" celebrations.
- No badges, trophies, or gamification.
- No leaderboards, social comparison, or shareable adherence reports.
- No public-facing "I took my medication today" achievements.
- No motivational quotes triggered by completion.

What replaces these: a quiet, accurate record. The doctor sees a heatmap of adherence; the patient sees a clean, non-judgmental log.

### 9.2 Reminder types and where they originate

| Reminder type | Source | Frequency setting |
|---|---|---|
| Medication | Doctor-prescribed | Doctor sets in prescription; patient can adjust times within prescribed window |
| Supplement (doctor-recommended) | Doctor's plan | Same |
| Hydration / water | Doctor's plan (specific conditions) | Doctor sets target, patient logs |
| Movement (when prescribed) | Doctor's plan | Doctor sets target |
| Glucose log (diabetes / weight management) | Doctor's plan | Patient logs, doctor sees the log |
| Symptom check-in (specific to vertical) | Doctor's plan | Optional, doctor can request |

**Patient-set reminders** are not the default. The product does not encourage patients to invent their own care plans. If a patient wants to add a self-prescribed supplement, they can — but it appears in a "Self-tracked" section, visually distinguished from doctor-prescribed items (slightly different chip styling, "Self-tracked" label).

### 9.3 Reminder row design

In Plan → Today, each due item is a row:

```
┌──────────────────────────────────────────────┐
│  ⏰ 8:00 AM                                  │
│  ▢  Levothyroxine 50 mcg                     │
│      Empty stomach, 30 min before breakfast  │
└──────────────────────────────────────────────┘
```

- **Time** (DM Sans 13px Forest weight 600).
- **Checkbox** (left, 24×24 tap target, larger touch area).
- **Medication / supplement name + dose** (DM Sans 15px Ink).
- **Instructions** (DM Sans 13px Stone).
- Tap the checkbox: marks taken. 220ms fade animation, the row becomes Stone-toned with strikethrough on the name. No celebration sound, no animation flourish.
- Tap the row body: opens the medication detail (history, dosage timeline, etc.).
- Long-press is reserved for OS actions (none defined here).

### 9.4 The three actions: taken, skipped, snoozed

When a reminder notification fires, the patient has three options:

- **Taken** — the most common action. One tap, in-notification or in-app.
- **Skipped** — for missed doses. Tap "Skip" opens a small sheet: "Skipping this dose?" with reason chips (Forgot, Felt unwell, Out of supply, Other), all optional. Reasons are *helpful* (the doctor sees them), not required.
- **Snoozed** — postpone the reminder. Options: 15 min, 1 hour, "Skip and remind tomorrow." Snooze does not punish or visually flag; it just defers.

**Visual treatment of skipped vs taken:**

- Taken: Sage tick beside the row, strikethrough on the name, Stone-toned. Settled.
- Skipped: empty box, Stone-toned strikethrough, small Stone caption "Skipped — Felt unwell" if reason given. No red, no "missed" label. Skipped is information, not failure.
- Snoozed: Saffron dot beside the time, "Reminding at 9:00 AM" caption. Active state, not punitive.

The principle: a missed dose is a clinical event the doctor reads. It is not a moral failing the app needs to call out.

### 9.5 Notification behavior

**Default times.** Medication reminders fire at the prescribed time. For ongoing doses, the patient can adjust the time within the doctor-permitted window (e.g., morning dose: 7–9 AM range).

**Notification copy** (respecting privacy preference):

- **Generic preview:** "It's time for your morning medication."
- **Detailed preview:** "Levothyroxine 50 mcg — empty stomach, before breakfast."
- The "generic" wording does not reveal what the patient is taking. Crucial for sensitive medications (TRT, ED meds, PCOS treatments) on lock screens visible to family members.

**Quiet hours.** Patient sets a quiet window in Settings → Notifications. Reminders during quiet hours are batched and surfaced when quiet hours end. Critical medications (e.g., certain emergency-relevant doses) can override quiet hours, but the doctor flags this at prescription time — the patient doesn't have to think about it.

**Notification fatigue prevention.**

- Maximum 3 reminders per medication per day.
- "Missed dose" follow-up notifications: maximum 1, sent 30 min after the original. Then nothing. No "you've missed your dose!" guilt-trips.
- Daily summary notifications are opt-in, not default.
- Educational content notifications: maximum 2 per week.

### 9.6 Adherence visualization

The adherence view is in Plan → Adherence. It shows the patient their pattern; it shows the doctor their pattern more thoroughly.

**Patient view (last 7 days, default):**

A heatmap row per medication, columns being days. Each cell:
- Sage fill (slight tint) = taken
- Ivory fill = skipped (no negative colour)
- Saffron edge = snoozed (rare)
- Stone outline (faint) = scheduled but not yet due

```
Levothyroxine 50 mcg

Mon  Tue  Wed  Thu  Fri  Sat  Sun
[●]  [●]  [●]  [○]  [●]  [●]  [●]
```

A small numeric line below: "6 of 7 doses taken in the last week."

No percentages. No "adherence score." The doctor sees a more detailed view in the doctor portal; the patient sees a quiet record.

**30d and 90d views:** the heatmap compresses (smaller cells, multi-row), same colour scheme. Useful for the patient who wants to see their pattern; not optimised for granularity.

**Per-medication detail:** opens a calendar view of that specific medication with every dose marked. Lets the patient see "I missed three doses last weekend."

### 9.7 Microcopy tone

Reminders are where microcopy carries the most weight. The wrong word here makes the app feel like a parent. The right word makes it feel like a colleague.

| Context | Wrong | Right |
|---|---|---|
| Notification (medication due) | "Don't forget your medication!" | "Levothyroxine — 8:00 AM" |
| Missed dose follow-up | "You missed your medication." | "Still time for your morning dose if you want." |
| Skip confirmation | "Are you sure you want to skip?" | "Skip this dose? You can add a reason." |
| All caught up | "You're doing great!" | "All of today's doses are logged." |
| Streak begin | "You've started a streak!" | (no streak language at all) |
| Low adherence | "Your adherence is dropping." | "It looks like a few doses were missed this week. Want to mention this in your next consultation?" |
| Successful 30 days | "30-day streak! 🎉" | (no celebration; the next consultation reads as the milestone) |

### 9.8 When subtle encouragement is appropriate

There are moments — rare — when a calm acknowledgment lands well. They are *not* streak celebrations. Examples:

- After the first successful week of a new medication: a small in-app card on Home, "First week on levothyroxine. Talk to Dr Mehta if anything feels off." — pure care-team tone, no celebration.
- After the patient logs a particularly long stretch of consistent adherence (say, 90 days), if and only if the doctor's plan involves a review at that point: "Time for your 3-month check-in with Dr Mehta." — converts the milestone into the next clinical event, not a self-congratulatory moment.

The encouragement is functional. It points to the next correct action.

### 9.9 When *not* to gamify

The product is structurally non-gamified. No streaks, no badges, no levels, no points, no leaderboards, no shareable cards. This is not a stylistic choice; it is a clinical-trust choice. Gamification reframes care as performance. Patients who treat care as performance over-disclose to the app and under-disclose to the doctor (because the app rewards completion and the doctor rewards honesty).

---

## 10. Education UX

The education surface is where the doctor extends the conversation beyond the consultation. Done well, it reinforces the clinical relationship and supports adherence. Done badly, it becomes content marketing inside the product — corrosive to trust.

### 10.1 Two kinds of education content

The product distinguishes two categories that look superficially similar but serve different purposes:

1. **Doctor-assigned content** — a specific article or video the doctor wants this patient to read after a consultation. Appears in Plan → Education → Assigned. High priority, surfaced on Home until read.
2. **Library content** — browsable resources for patients who want to learn more about their condition. Lives in Plan → Education → Library. Browsable, not pushed.

Doctor-assigned has priority in every surface. The library is a quiet repository, not the home page of the product.

### 10.2 Assigned content surfacing

When a doctor assigns content during or after a consultation:

- The patient receives a notification (respecting privacy preference): "Dr Mehta has shared an article with you." (generic) or "Dr Mehta has shared 'Understanding TSH ranges' with you." (detailed).
- The article appears on Home as an "Assigned by Dr Mehta" card for 14 days or until read.
- The article appears at the top of Plan → Education → Assigned.

### 10.3 Article and video cards

**Card anatomy:**

```
┌──────────────────────────────────────────────┐
│  ASSIGNED BY DR MEHTA                        │  Forest tag, DM Sans 11px
├──────────────────────────────────────────────┤
│                                              │
│  Understanding your TSH range                │  DM Sans 16px Forest 600
│                                              │
│  A 5-minute read on what TSH values mean,    │  DM Sans 13px Stone
│  why ranges vary, and what 'in range'        │
│  actually tells us.                          │
│                                              │
│  Reviewed by Dr Anjali Mehta · January 2026  │  DM Sans 12px Stone
│  5 min read                                  │
│                                              │
│  [ Read ]                                    │  Forest text link
└──────────────────────────────────────────────┘
```

**Trust signals on every card:**

- Reviewer doctor name + NMC reg + review date.
- Estimated read or watch time.
- Category tag (Thyroid / PCOS / etc.) for library content.
- "Reviewed [month year]" — currency matters; medical content older than a year should be flagged for review.

### 10.4 Article reading layout

**Composition:**

1. **Top app bar** with Forest back-arrow, article title (truncated), bookmark icon (saves to "saved" — optional, not gamified).
2. **Hero section.** Cormorant 28px Forest title, DM Sans 14px Stone subtitle (one sentence).
3. **Doctor attribution block.** Doctor avatar + name + NMC reg + review date.
4. **Article body.** DM Sans 16px Ink, 1.6 line-height, 1-column at mobile, max 680px width on desktop. Generous spacing.
5. **Inline elements:** subheads (Cormorant 22px Forest), pull-quotes (Cormorant 20px italic Forest with Saffron border-left 3px), simple line illustrations (no 3D, no stock photography).
6. **References / sources** at the bottom in DM Sans 13px Stone, numbered. Health content needs citations; the absence of citations is itself a trust signal in the wrong direction.
7. **Reviewed date** repeated at the bottom for clarity.
8. **"Talk to Dr Mehta about this"** Forest text link, deeply contextual — connects reading to action.

### 10.5 Video viewing layout

For doctor-explanation videos (mostly Mode B/C from the design system's voice policy — line animation with Kyros Clinical Editor voice, doctor sign-off visible):

- Video player full-width at top.
- Below: same attribution block (reviewer doctor + NMC reg + review date).
- Below: chapter markers if the video is longer than 5 minutes.
- Transcript expandable below — accessible by default, served as an alternative to watching.

**Critical:** the AI voice / cloned voice disclosure (per kyros-design-system's voice policy) must be visible in the first 3 seconds of any video using cloned founder voice or Kyros Clinical Editor voice. This is a regulatory and trust requirement.

### 10.6 Read tracking

Whether and how to track that a patient has read a piece of content:

- **Implicit:** scrolled to bottom of article = "read." Watched to >80% of video = "watched."
- **Explicit:** "I've read this" button at the bottom of articles, optional. Some patients prefer to explicitly close the loop.
- **Doctor visibility:** the doctor sees in the patient's record whether assigned content was read. Not as judgement — as context. ("Dr Mehta knows you read the TSH article, so she can build on it in the next conversation.")
- **Patient visibility:** in Plan → Education → Assigned, read items move to a small "Read" sub-list below "To read." No badges, no completion percentages, no celebrations.

### 10.7 Library browsing

The library is reached from Plan → Education → Library. It is not the front door of the product; it is a quiet repository.

**Composition:**

- Top: search bar (DM Sans, Forest text on Ivory input).
- Below: vertical filters as chips: "All / Thyroid / PCOS / Weight / Skin & hair / Men's intimate / Hormones / Longevity / Privacy & care."
- Article and video cards in a vertical list.
- No "trending" or "most popular" sorting. The library is curated by the clinical team; popularity is not the right ranking.

### 10.8 What education must avoid

- **Content marketing aesthetic.** Big magazine-style hero images, "5 ways to..." listicle titles, "Discover the secret to..." headlines. The library reads as medical reference, not as a blog.
- **Generic wellness content.** "10 superfoods for thyroid health" is the wrong content. "Understanding TSH ranges and when to discuss them with your doctor" is the right content.
- **Content without attribution.** Every article and video carries a reviewer's name and NMC registration. The absence of attribution is itself a credibility breach.
- **Content older than 12–18 months without re-review.** Medical guidance shifts. A "Reviewed January 2026" line that hasn't been re-confirmed in 18 months silently corrodes the trust of patients who read review dates.
- **Treating education as a primary product surface.** No "Education" tab in the bottom bar. Education is a tool inside care continuity, not the destination.

---

## 11. Privacy and trust UX

Privacy is the third pillar of the brand — "One platform, where privacy is the point." This section designs how that pillar becomes visible inside the product, not as legal compliance, but as an experience.

### 11.1 The privacy framing

Most apps treat privacy as a settings sub-page buried under three taps. Kyros treats privacy as a *visible thread* through the entire product. The patient sees privacy decisions made for them, can change them, and feels them honoured.

Five places privacy becomes visible:

1. **At signup.** The notification-privacy preference (generic vs detailed previews) is set during onboarding, not buried.
2. **At consent.** Each clinical interaction or data sharing event surfaces the specific consent being given, in plain language.
3. **On Home.** A "Privacy and your data — manage anytime" link in the trust footer, persistently visible.
4. **In Profile.** A "Privacy & data" section, not buried under Settings.
5. **At every sensitive data-handling moment.** When labs are uploaded, when notes are written, when video is recorded — short reassurance moments confirm what is happening.

### 11.2 The profile screen composition

**Profile landing screen (Profile tab):**

```
┌──────────────────────────────────────────────┐
│  Top app bar                                 │
├──────────────────────────────────────────────┤
│  Avatar  Niranjan Reddy                      │  64×64 avatar
│          niranjan@example.com                │  DM Sans
│          +91 ••••• 56789                     │  Masked
│                                              │
│  [Edit profile]                              │  Forest text link
├──────────────────────────────────────────────┤
│                                              │
│  PERSONAL                                    │  Section header, DM Sans 12px uppercase Stone
│  ─ Personal details                          │
│  ─ Health profile                            │
│  ─ Insurance / TPA            (Optional)     │
│  ─ ABHA                       (Optional)     │
│                                              │
│  PRIVACY & DATA                              │
│  ─ My consents                               │
│  ─ Download my data                          │
│  ─ Delete my account                         │
│  ─ Linked devices                            │
│  ─ DPDP rights                               │
│                                              │
│  PREFERENCES                                 │
│  ─ Notifications                             │
│  ─ Quiet hours                               │
│  ─ App passcode / biometric                  │
│                                              │
│  ACCOUNT                                     │
│  ─ Payments & receipts                       │
│  ─ Active sessions                           │
│  ─ Change password                           │
│                                              │
│  ─ Help & support                            │
│  ─ About Kyros                               │
│  ─ Terms & policies                          │
│  ─ Sign out                                  │
│                                              │
└──────────────────────────────────────────────┘
```

Note: **Privacy & data is its own section, prominently positioned above Preferences.** Most apps hide it under Settings → Account → Privacy. Kyros surfaces it.

### 11.3 PII masking patterns

Sensitive personal information appears masked by default in any public-facing surface inside the product:

- **Phone number:** "+91 ••••• 56789" (last 5 digits visible). Tap to reveal full number, with a brief Forest hint "Tap to view".
- **Email:** "n••••••@example.com". Tap to reveal.
- **ABHA ID (if linked):** "•••• •••• ••12 3456" — last 6 visible. Tap to reveal.
- **Insurance / TPA member ID:** masked similarly.

Why: shoulder-surfing protection. The patient using the app on a Mumbai local train or a Bangalore Uber should not have their PII visible to a glance.

### 11.4 Consent records

The "My consents" screen lists every consent the patient has given, with timestamps and current status:

```
┌──────────────────────────────────────────────┐
│  Your consents                               │  Header
│                                              │
│  Telemedicine consent                        │  DM Sans 14px Forest 600
│  Active · Granted 14 Jan 2026                │  DM Sans 12px Stone
│  [View full text]      [Withdraw]            │
│                                              │
│  Data processing (DPDP)                      │
│  Active · Granted 14 Jan 2026                │
│  [View full text]      [Withdraw]            │
│                                              │
│  Health data sync — Apple Health             │
│  Active · Granted 18 Jan 2026                │
│  [View full text]      [Withdraw]            │
│                                              │
│  Marketing communications                    │
│  Not granted                                 │
│  [View options]                              │
│                                              │
└──────────────────────────────────────────────┘
```

Each consent: name, status, grant date, view-full-text link, withdraw link. The withdraw flow is honest: it explains what happens if the patient withdraws (e.g., "Withdrawing telemedicine consent will prevent future consultations until renewed").

### 11.5 Download my data

DPDP rights require accessible data export. The Kyros approach:

- **Forest fill button** "Request your data" — explicit action.
- After tap: a sheet "We'll prepare a complete export of your data, including consultations, labs, prescriptions, and your records. This usually takes 24 hours. We'll email you the download link."
- "Send to: [email on file]" with an option to send to a different email.
- "Confirm request" → confirmation screen, request appears in a "Past requests" list.

The export contains: profile, consultations (with notes), prescriptions, labs (structured + original PDFs), education history, consent records, audit log of data access. Provided as a structured zip with a human-readable index and machine-readable JSON for portability.

### 11.6 Delete my account

The most destructive action. Designed with friction in the right places, but not so much friction that it feels like the company is hiding it.

**The flow:**

1. Profile → Privacy & data → Delete my account.
2. Screen 1: "We're sorry to see you go." Plain explanation of what deletion means: which data is removed immediately, which is retained for medical record regulatory minimums (DPDP carve-outs for healthcare records), how long that retention is.
3. Screen 2: "Type 'delete my account' to confirm." (Friction step.)
4. Screen 3: Identity confirmation via OTP.
5. Confirmation: "Your account is scheduled for deletion. You have 30 days to recover it. After 30 days, all non-regulatory-required data is removed permanently."

The 30-day grace period is honest, not a trap. The patient can sign in and cancel deletion within 30 days. After that, deletion is permanent.

### 11.7 Linked devices and data sources

The patient sees, in plain list, every data source linked to their Kyros record:

```
Apple Health      Connected 18 Jan 2026   [Disconnect]
Health Connect    Not connected           [Connect]
Active sessions:
  iPhone 14       Last seen 2 minutes ago [End session]
  iPad            Last seen 3 days ago    [End session]
```

Disconnecting a health data source halts further sync immediately. Previously synced data remains (clinical record), unless the patient also requests its deletion.

### 11.8 DPDP rights

A dedicated DPDP rights surface explains the four rights granted under the Digital Personal Data Protection Act:

1. **Right to access** — already exercised via "Download my data."
2. **Right to correction** — a form to request correction of any specific personal data point.
3. **Right to erasure** — exercised via "Delete my account" or a more granular partial erasure request.
4. **Right to withdraw consent** — exercised on the consent records screen.

Each right has a plain explanation, an "Exercise this right" affordance, and a "What happens when you exercise this" expectation-setting paragraph. DPDP rights are visible, exercisable, and acknowledged — not buried in terms-of-service text.

### 11.9 Audit trail (optional, advanced)

For patients who want transparency on data access:

- Profile → Privacy & data → Data access log.
- A chronological list of who accessed what, when:
  - "Dr Anjali Mehta viewed your TSH report — 14 May 2026, 4:18 PM (during consultation)."
  - "Care team member [name] viewed your phone number — 18 May 2026, 11:02 AM (for appointment reminder call)."
- Audit entries are kept for 12 months by default; longer retention available on request.

Most patients will never look at this surface. Its existence builds trust with the small minority who care intensely about transparency — and they often turn into advocates.

### 11.10 Security reassurance moments

Throughout the product, brief reassurance lines appear at sensitive moments:

- Uploading a lab: "Your report is encrypted and visible only to your doctor and care team." DM Sans 12px Stone, below the upload progress.
- Joining a video consultation: "Your call is end-to-end encrypted and not recorded." DM Sans 12px Stone, in the waiting room.
- Sharing data with insurance / TPA (when applicable): "Sharing TSH report with [TPA name] for [reason]. You can review what was shared in My consents." Inline, before the action.

These are not legal disclaimers. They are reassurance moments that build felt safety. They are short, specific, and accurate.

### 11.11 What privacy UX must avoid

- **Wall-of-text consent screens.** Plain summary in 2 sentences, "Read full text" expandable. Always.
- **Pre-checked consent boxes for non-essential consents.** Marketing consent must be opt-in, never opt-out.
- **Dark patterns in deletion.** Deletion must be findable, executable, and honest. No "Are you really sure? Are you really *really* sure?" guilt loops beyond the necessary friction steps.
- **Cryptic data settings.** "Anonymous data sharing for research" — patients can't evaluate this. Replace with: "We share de-identified data — your name, phone, and email removed — with research partners studying [specific conditions]. You can opt out at any time. View full policy." Plain, specific, opt-out-accessible.
- **Vague "we take privacy seriously" microcopy.** Replace with concrete: "Your data is stored on Indian servers, encrypted, and accessible only to your assigned care team and you."

---

## 12. Visual system

This section specifies the complete UI visual system for the app, building on the locked design system. It is the document the frontend team should reference when implementing Tailwind tokens, component variants, and CSS variables.

### 12.1 Colour usage system (in-product application)

The locked palette has eleven tokens. This section specifies how each plays inside the product, not in marketing.

**Forest `#0F3D2E` — the spine.**

- Primary CTA fills (e.g. "Book consultation," "Pay ₹400 and book," "Confirm values").
- Primary text on Ivory and Peach Mist backgrounds (over body 14–16px, headlines 18px+).
- Tab bar icon active state.
- Top app bar wordmark.
- Doctor name display.
- Section header text on Profile and Plan screens.
- Forest fill: appears on at most ~25% of any screen's pixel area. The dashboard is white-on-ivory with Forest text and CTAs, not Forest-as-background.

**Jade `#2D7A5F` — saturated companion.**

- Hover states on Forest CTAs (desktop only — mobile has no hover).
- Secondary CTAs on warm-background pages (e.g. inside an empty state hero on Peach Mist).
- Illustration fills inside line drawings (per the design system's line-animation pattern).
- **Never:** body text, primary CTA fills, status indicators.

**Sage `#8FA88E` — calm support tint.**

- "In range" status chips and dots in labs.
- Reference range bands in trend charts (at 25% opacity).
- Soft confirmation states ("Saved," "Synced").
- Adherence "taken" cell fills (at slight tint).
- Section field backgrounds on Profile sub-pages (very sparingly, at 8–12% opacity, never full saturation).

**Saffron `#E08E3C` — primary accent for emphasis.**

- "Slightly off" status chips in labs.
- "Join now" CTA when a consultation is active (urgency without alarm).
- Border-left accent on doctor commentary cards.
- Step number circles in checklists (number is white, circle is Saffron).
- New-item dots / chips ("New result," "New note from Dr Mehta").
- Saffron edges on low-confidence OCR rows.
- **Never:** background fields larger than ~15% of a screen, body text, primary action fills on neutral pages.

**Terracotta `#C25A4A` — emotional warmth accent.**

- Out-of-range (non-critical) status on lab reports.
- Empty state hero accents on sensitive-condition first-use screens (e.g. PCOS first consultation prompt) — sparingly.
- Reflective close pull-quote borders on long-form education articles.
- **Strict rule:** at most one Terracotta moment per screen. Never combined with Alert.

**Ivory `#FAF1E4` — default warm background.**

- Default page background for most screens (Home, Consults, Labs, Plan, Profile).
- Tab bar background.
- Top app bar background.
- Card background variant for empty states and warmth-mode sections.

**Peach Mist `#FCE4CC` — warm section tint.**

- Welcome strip on Home.
- Empty-state hero backgrounds.
- Education library top section.
- Confirmation screens immediately after a positive event (booking confirmation, refill request submitted).
- **Never:** main page background for clinical surfaces (labs detail, prescription detail, biomarker trend).

**White `#FFFFFF` — clinical density.**

- Card backgrounds on clinical surfaces (lab report rows, prescription detail, biomarker rows, consultation cards).
- Form input fields (inside the card).
- Tables (the lab biomarker grid).
- The dashboard's upcoming consultation card, recent lab insight card, doctor commentary card — all White on Ivory.

**Ink `#1A1A1A` — body text.**

- All body copy (DM Sans 14–16px).
- Form input text.
- Values in lab biomarker rows.
- Quoted doctor commentary (in italic Cormorant when used).
- **Never compromised:** body text on warm backgrounds remains Ink. Not Forest. Not Stone. Readability first.

**Stone `#6B6B68` — secondary text.**

- Captions, metadata, timestamps, reference ranges (alongside values).
- Doctor specialty and NMC reg lines on doctor cards.
- Placeholder text in form inputs (DM Sans 14px Stone, 60% opacity).
- "Past" / "Skipped" state text.

**Alert `#B53A2B` — danger only.**

- Critical lab value chips (rare).
- Emergency banners ("Lab value flagged urgent — Dr X has been notified.").
- "End call" button on the in-call surface.
- Account deletion confirmation accents.
- **Never:** out-of-range labs that aren't clinically critical, missed-dose styling, "warning" copy that isn't life-safety relevant. The alert colour is reserved for actual alerts.

### 12.2 Colour density per surface type

The 60/40 dashboard ratio expressed numerically:

| Surface | Approx. pixel-area split |
|---|---|
| Home dashboard | White cards 55% · Ivory page 25% · Peach Mist welcome 10% · Forest CTAs / text 7% · Saffron/Sage accents 3% |
| Labs list | Ivory page 50% · White cards 40% · Forest text 5% · Sage / Saffron accents 5% |
| Lab report detail | White surface 70% · Ivory page 18% · Forest text 7% · Status colours 5% |
| Biomarker trend | White card 60% · Ivory page 25% · Sage reference band 10% · Forest line + Saffron/Terracotta callouts 5% |
| Prescription detail | White surface 80% · Ivory page 12% · Forest text 6% · Sage signed-chip 2% |
| Consultation booking | Ivory page 55% · White cards 30% · Forest CTA fill 10% · Saffron accent 5% |
| Education library | Ivory page 50% · Peach Mist hero 20% · White cards 25% · Forest text 5% |
| Profile | Ivory page 75% · Forest text 15% · Stone secondary 10% |
| Empty state (first-time Home) | Ivory page 50% · Peach Mist hero 35% · Forest CTA + text 15% |
| In-call surface | Forest 95% background 70% · Ivory tint at edges 5% · Doctor video 20% · Controls 5% |

These numbers are illustrative, not enforceable. They communicate the rhythm — most clinical surfaces are White-on-Ivory, with Forest doing structural work and the warm accents punctuating sparingly.

### 12.3 Typography system in detail

**The display vs body split, reasserted:**

- **Cormorant Garamond:** display-only. Page-level hero titles, large display numerals (lab biomarker current values), pull-quotes inside education articles, post-consultation thank-you screen, empty-state heroes.
- **DM Sans:** all structural work. Navigation, body copy, form labels, button labels, table content, metadata, timestamps, lab biomarker rows (except the large numeral on biomarker detail).

**Why Cormorant must not creep into structural surfaces:** Cormorant at 14–15px (body size) loses legibility. Cormorant on a button label looks ornamental, not premium. Cormorant on a form label slows reading. The premium feel comes from Cormorant being *rare and earned*, not omnipresent.

**Practical type scale (mobile):**

| Token | Family | Size | Weight | Color | Use |
|---|---|---|---|---|---|
| display-hero | Cormorant Garamond | 32–42 | 500 | Forest | Empty-state hero, welcome screen |
| display-numeral | Cormorant Garamond | 48–64 | 500 | Forest / Saffron | Biomarker current value |
| display-thanks | Cormorant Garamond | 24 | 500 | Forest | Post-consultation thank you |
| pull-quote | Cormorant Garamond italic | 18–22 | 400 | Ink / Forest | Inside doctor commentary, education articles |
| h1 | DM Sans | 22 | 600 | Forest | Major page header (rare; most pages use h2) |
| h2 | DM Sans | 18 | 600 | Forest | Section header on most screens |
| h3 | DM Sans | 16 | 600 | Forest | Card title, sub-section |
| body-lg | DM Sans | 16 | 400 | Ink | Primary body copy on educational and emotional surfaces |
| body | DM Sans | 14–15 | 400 | Ink | Default body, table content |
| body-sm | DM Sans | 13 | 400 | Stone | Captions, secondary text |
| label | DM Sans | 12 | 500 | Stone uppercase | Section labels, metadata categories |
| caption | DM Sans | 11–12 | 400 | Stone | Fine print, timestamps |
| button | DM Sans | 14–15 | 500 | Ivory / Forest | CTA labels |
| tab | DM Sans | 11–12 | 500 | Stone (inactive) / Forest (active) | Bottom tab labels |

**Numerals:** all numeric values in clinical contexts (lab values, doses, timestamps) use DM Sans with `tabular-nums` and `lining-nums` enabled. This is non-negotiable on lab biomarker rows where alignment matters.

**Chart text:** DM Sans 12px Stone for axis labels, DM Sans 13px Forest for callouts. Cormorant never appears in charts; serif numerals in charts read as ornate rather than precise.

### 12.4 Spacing and layout

**Base grid:** 4px. All spacing values are multiples of 4.

**Spacing scale:** `4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64`.

**Standard spacings:**

- **Page horizontal padding (mobile):** 16px (small screens) / 20px (default) / 24px (large mobile, 414px+).
- **Card padding internal:** 16px or 20px depending on density. Clinical cards (lab rows): 16px. Emotional cards (welcome strip, hero): 20–24px.
- **Section vertical spacing:** 24px between sections on dense surfaces (labs, prescriptions). 32px between sections on emotional surfaces (Home, empty states).
- **Card vertical gap:** 12px between cards in a vertical list. 16px on Home (slightly more breathing room).
- **Form field gap:** 16px between fields. 20px between field groups.
- **Bottom safe area:** always respected. CTAs anchored to the bottom sit 16px above the safe-area inset.

**Rhythm principle:** dense clinical surfaces (lab report detail, biomarker trends, prescription detail) use tighter rhythm (12–16px). Emotional surfaces (Home welcome strip, post-consultation, empty states) use generous rhythm (24–32px). The same screen never mixes tight and generous — it commits to one rhythm.

**Bottom sheet spacing:** 24px top padding, 20px horizontal, 16px between sheet sections, 16px above the bottom safe-area. Bottom sheets have a Stone 4×40px drag handle at the top centre.

**Desktop portal spacing:** larger. Page horizontal padding 32–48px. Card padding 24–32px. Two-column layouts use 24px column gap.

### 12.5 Shape language

**Border radius:**

- **Buttons:** 8px (slightly soft, not aggressive, not pill-shaped).
- **Cards:** 12px (slightly more relaxed for content).
- **Inputs:** 8px.
- **Bottom sheets:** 16px top corners only.
- **Modals:** 16px all corners.
- **Avatars:** fully circular.
- **Chips:** 6px (smaller, denser).
- **Image thumbnails (PDF previews, articles):** 8px.

**Borders:**

- **Cards:** 1px Forest at 8% opacity. This subtle border replaces shadow for clinical credibility. Shadows imply skeuomorphic depth; thin borders imply documentation.
- **Inputs:** 1px Stone at 60% opacity (default), 2px Forest (focused), 2px Alert (error).
- **Dividers:** 1px Stone at 12% opacity, never thicker.

**Shadows:**

- **Default cards:** no shadow. Border-only.
- **Floating elements (bottom-sheet over content, modal):** subtle shadow `0 4px 24px rgba(15, 61, 46, 0.08)`. Forest-tinted, not black.
- **Active card press state:** subtle scale to 0.98, no shadow change.

**Elevation language:** the product has three elevation levels, not five.

1. **Surface (most things)** — flat on the page, border-only.
2. **Floating (bottom sheets, modals, dropdowns)** — subtle Forest-tinted shadow.
3. **Critical (the rare in-call mini window when navigating away)** — slightly stronger shadow with a Forest border.

The product feels tactile through proportion and rhythm, not through stacked depth.

### 12.6 Iconography

**Icon library:** Lucide React (referenced in the design system) for the base set, with custom icons added when Lucide doesn't have a clinical-appropriate option.

**Style:**

- **Line icons** (stroke-only), never filled. Stroke weight 1.5px at 24×24, 1.25px at 16×16.
- **Forest** stroke for active or default. **Stone** stroke for inactive.
- **No mixed line/fill icons.** Consistency is more important than visual variety.
- **No coloured icons** as primary navigation. Tab bar icons are Stone (inactive) / Forest (active). Status icons (Sage tick, Saffron warning) are exceptions and use colour.

**Icon + text rules:**

- Tab bar: icon + text label always (accessibility, recognition).
- Top app bar icons: icon only (with accessible labels via ARIA / VoiceOver).
- Primary CTA buttons: text only (icons inside buttons add visual noise).
- Secondary text links: icon (a small arrow) only when navigation is implied.
- Empty states: a single illustrative icon (60×60) above the hero text. Forest stroke.

**Where icons help vs add noise:**

- **Helpful:** tab bar (5 icons), top app bar (search, notifications, profile), section dividers (no — these are noise), status chips (Sage tick, Saffron warning).
- **Noise:** decorative icons inside body copy, icon every list-row indicator (rows don't need icons; they need clear text).

### 12.7 Component visual variants (high-level)

A few key components in their variant matrix:

**Buttons:**

- **Forest fill** — primary. Forest background, Ivory text, 44–48px height, 8px radius, 16–24px horizontal padding. Pressed state: Forest 90% opacity.
- **Saffron fill** — urgency primary (used sparingly: "Join now" when consultation is active, time-sensitive CTAs). Saffron background, Forest text.
- **Forest outline** — secondary. Transparent background, 1.5px Forest border, Forest text.
- **Forest text** — tertiary. No background, no border, Forest text, optional small Forest arrow.
- **Alert fill** — destructive (account deletion confirm, end call). Alert background, Ivory text.

**Cards:**

- **Clinical card** — White on Ivory, 1px Forest 8% border, 12px radius, no shadow.
- **Warm card** — Ivory on Ivory page (subtle differentiation) or White on Peach Mist field, slightly more padding.
- **Doctor commentary card** — White, 3px Saffron border-left, otherwise clinical.
- **Empty state card** — Peach Mist background, no border, more generous padding.

**Chips:**

- **Sage status chip** — Sage 15% background, Forest text, 11–12px DM Sans, 6px radius.
- **Saffron status chip** — Saffron 15% background, Forest text.
- **Terracotta status chip** — Terracotta 15% background, Ink text.
- **Alert chip** — Alert background, Ivory text. Rare.

### 12.8 Colour density per screen type — quick reference

| Screen | Mood | Background | Card backgrounds | Accents allowed |
|---|---|---|---|---|
| Home (active patient) | Calm, relational | Ivory | White + 1 Peach Mist (welcome strip) | Sage chips, 1 Saffron CTA, 1 Cormorant moment |
| Home (first-time) | Welcoming, inviting | Ivory | Peach Mist hero | 1 Forest CTA, 1 Cormorant moment |
| Lab report detail | Clinical, precise | Ivory | Mostly White | Sage / Saffron / Terracotta status chips |
| Biomarker trend | Clinical, attentive | Ivory | White | Sage reference band, Forest line, sparse Saffron callouts |
| Prescription detail | Document-formal | Ivory (or near-White) | White | Sage signed chip, Forest doctor signature line |
| Consultation booking | Direct, structured | Ivory | White cards | Saffron "soonest slot" border, Forest CTAs |
| In-call | Dark, focused | Forest 95% | (none) | Ivory tint, Alert end-call only |
| Education library | Calm, browsable | Ivory + Peach Mist hero | White | Forest tags, Cormorant in article body |
| Empty states | Warm, inviting | Ivory + Peach Mist | (rarely card-bordered) | Forest CTA, Cormorant headline, single illustration |
| Profile | Quiet, structural | Ivory | Ivory (no cards on Profile landing — list rows) | Forest text, Stone secondary |

---

## 13. Imagery and illustration direction

The brief asks whether the product should use photography at all. Mostly: no. The product is image-light by design, because every image is an opportunity for stock-photography drift, gender coding, or wellness-aesthetic creep. This section defines exactly where imagery appears and what kind.

### 13.1 Photography inside the product: very sparingly

The product surface is overwhelmingly typographic and structural. Photography appears in three places only:

1. **Doctor avatar.** Real photographs of real Kyros panel doctors, taken to a consistent specification: neutral background, head-and-shoulders, no white coat (white coat is a stock trope; doctor identity is established by name and NMC reg, not costume), warm-but-restrained lighting matching the design system's "north-light still life" direction. If a doctor's photo is not yet available, a monogram fallback in Forest fill with Ivory initials.
2. **Educational article hero images** (selectively). When an article needs an anchoring image, the image is a warm architectural still life from the design system's photography direction (chai cup, marigold, leather notebook, copper vessel, window plant) — not anatomical, not lifestyle, not stock health. Most articles work better with no hero image at all; if in doubt, omit.
3. **The about screen** (Profile → About Kyros). A small Kyros logo, perhaps a single warm architectural image. Not a brand reel.

**No patient photography.** Ever. No before-and-after. No "patient testimonials with photos." No lifestyle shots of people taking medications, exercising, eating. The product is about the patient, not about other patients.

**No app-screenshot-in-product.** No marketing-style "here's what the dashboard looks like" inside the dashboard. The product should not advertise itself to itself.

### 13.2 Illustrations: line drawings, restrained

The design system specifies 2D line illustrations with Forest strokes and optional Sage/Peach Mist fills at low opacity. The product applies this principle in:

**Anatomical line drawings** in education articles only. Thyroid gland, reproductive system, skin layers, hair follicle structure — rendered in the design system's anatomical style. Forest strokes, optional fills, no realistic shading, no 3D, no glossy organs. Animated line-drawn-reveal (per design system motion tokens) when first scrolled into view.

**Empty state illustrations** — a single Forest-line icon at 60×60 above the empty-state hero text. Simple, often a single symbol (a leaf for a fresh start, a clipboard for an empty record, a calendar for an unbooked first consultation). Not characters, not full scenes, not playful.

**Iconography** is already covered in §12.6. Icons are not illustrations; they are functional indicators.

**No 3D blob illustrations.** No "friendly health buddy" character. No mascot. No avatar that isn't a doctor or the patient themselves.

### 13.3 Banned imagery (re-stating from the design system, applied to product)

- **No stock smiling-doctor cliché.** No white-coat-with-stethoscope smiling at the camera. Even if it's a real Kyros doctor, the photograph should not look like stock.
- **No athleisure wellness visuals.** No women in yoga poses, no men in gym wear.
- **No pseudo-Ayurveda cues.** No mandalas, paisley, "ancient wisdom" visual coding.
- **No pill bottles, pill organisers, syringes.** Medical paraphernalia photography reads as clinical-cold or as ad-pharma.
- **No before-and-after.** Outcome theatre is the wrong contract.
- **No app-in-hand marketing shots.** Inside the product. Reserved for marketing site only.
- **No 3D blob characters or mascots.**
- **No glossy CGI organs.** Anatomy is line-drawn, not rendered.
- **No exaggerated red-warning anatomy diagrams.** Health diagrams use the locked palette: Forest stroke, Sage / Peach Mist fills, occasional Saffron leader lines. Never red anatomy.
- **No pseudo-data visualisations** (i.e. fake bar charts as decoration). Charts only render real data.

### 13.4 Where the product is image-light vs image-rich

- **Image-light:** Home, Consults, Labs, Plan, Profile, all detail surfaces. Typography and structure carry the experience. The visual richness comes from rhythm, colour use, and the doctor's words — not images.
- **Image-rich (selectively):** education articles (one anatomical illustration, one architectural still life, one pull-quote per article maximum), the marketing-equivalent surfaces (About Kyros, terms pages).

### 13.5 How imagery should support trust, not distract

When an image appears, it should answer a question or set a tone — never decorate.

- **Doctor avatar** answers "Is this a real doctor?" — a real photograph of the named doctor.
- **Educational anatomical illustration** answers "What does the thyroid look like?" — a precise, beautifully drawn line illustration.
- **Architectural still life on an article** answers "Is this serious content or marketing?" — a warm Indian-context photograph sets a register that says "this is medical reading, not magazine fluff."

If an image is being added for visual interest alone, it should be removed. The visual interest in this product comes from typography, colour discipline, and Cormorant moments.


---

## 14. Motion & interaction design

### 14.1 Interaction philosophy

The Kyros app should feel **composed under the user's hand**. Things respond, but they don't perform. The motion register is closer to a luxury automobile dashboard or a hospital chart application than to a consumer social app. Every animation answers one question: *what just happened, and where did it go?* — not *isn't this delightful?*

The locked design-system motion register is restrained: subtle fades, soft reveals, measured number transitions, graceful state changes. Translated to the product surface, that means:

- **Instant** for everything the user did on purpose (tap a button, switch a tab, open a card the user just decided to open). No "satisfying" 200ms lag to make it feel "premium" — premium feels fast.
- **Restrained transitions** between contexts (one screen to another, a sheet opening, a chart loading) — 220ms entrance, 200ms exit, soft curve.
- **Slower, deliberate** for narrative moments (a biomarker chart line drawing in, a number counting up on first reveal, an article hero coming into view). These earn 600–1800ms because they have something to say.
- **No spring, no bounce, no overshoot, no rotating loading spinners shaped like swirling mandalas, no confetti, no haptic celebrations.** Healthcare composure means no celebration theatre.

### 14.2 Motion tokens (from design system, applied to product)

| Token | Duration | Easing | When to use |
|---|---|---|---|
| Instant | 0ms | — | Button press visual feedback (color shift), tab switch, tap-state change |
| Micro | 120ms | ease-out | Toggle, checkbox check, chip select, small color/icon swap |
| Entrance | 220ms | ease-out | Sheet opens, card appears, dropdown reveal, modal in |
| Exit | 200ms | ease-in | Sheet dismisses, modal out, toast leaves |
| Section transition | 450ms | ease-in-out | Screen-to-screen navigation, dashboard section expansion |
| Pull-quote / Cormorant reveal | 600ms | ease-out | Doctor commentary first appearance, three-pillar copy fade |
| Numeral count-up | 800ms | ease-out | First reveal of a biomarker value, adherence summary numeral |
| Photo crossfade | 1000ms | ease-in-out | Doctor avatar load-in, article hero appearance |
| Line-draw | 1200–1800ms | ease-out | Anatomical illustration first reveal, chart line draw on first paint |

Anything longer than 1800ms is too long. Anything shorter than 120ms either uses Instant (0ms) or Micro (120ms) — never an arbitrary 60ms or 90ms.

### 14.3 Where things should be instant

- **Tab bar switching.** The user moved their thumb decisively; the system should not make them wait. New tab content appears instantly; if data is still loading, the loading state appears instantly (skeleton) rather than the screen staying on the previous tab for 200ms.
- **Button visual state.** Pressed state is immediate. No "press-and-release-and-then-it-darkens-half-a-second-later."
- **Form input focus.** Border colour to Forest the instant the user taps a field.
- **Chip selection.** Immediate.
- **Checkbox / radio.** Immediate.
- **Tab/segmented control.** Immediate.

### 14.4 Where things should be 220ms (entrance)

- **Bottom sheets** opening (slot picker, edit field sheet, prescription quick-view, doctor note sheet, consent sheet).
- **Modals** appearing (rare — modals are reserved for destructive confirmations and high-stakes consent).
- **Cards revealing** when scrolled into view on first paint of a screen (not on every scroll — only first paint).
- **Dropdown menus** (the rare ones — most pickers are sheets, not dropdowns).
- **Toast notifications** sliding into view.

### 14.5 Where things should be 450ms (section transition)

- **Screen-to-screen native navigation.** Push transitions on iOS, fragment transitions on Android — using platform defaults at 450ms with the platform's easing curve. Don't customise the push transition to add personality; the platform default is already correct.
- **Dashboard section expansion** when a user taps "View all" on a Plan summary or "See all consults" on an upcoming list — the section animates open at 450ms with easing.

### 14.6 Where things should be 600–1800ms (deliberate)

- **Cormorant pull-quote on doctor commentary** — when a doctor commentary card first comes into view on the dashboard or lab report, the Cormorant pull-quote fades up at 600ms. Body text and metadata are already visible; only the Cormorant moment is staged. This makes the doctor's words feel like a considered statement.
- **Biomarker chart line draw** on first paint of a lab report detail screen — the line draws from left to right over 1200ms, dots appear with 50ms staggered fade-ins after the line completes. Only on first paint; subsequent visits show the chart already drawn.
- **Numeral count-up** on a single hero metric (e.g., adherence percentage if shown, or a biomarker hero value on a comparison screen) — 800ms count from 0 to value with ease-out. Only on first paint. Subsequent visits show the final number.
- **Anatomical illustration draw-in** on education article hero — 1200–1800ms line-draw on first scroll into view. This is one of the few moments the product allows itself a small piece of visual storytelling.

### 14.7 Where motion is banned outright

- **Bounce / overshoot / spring.** No iOS-style rubber band on cards. No Material-style ripple-and-bounce. The animation arrives, settles, stops.
- **Confetti / celebration animations.** Not when a patient marks a medication as taken. Not when an adherence streak hits a milestone (and there are no streaks anyway). Not when a consultation is booked. Confetti is for fintech onboarding; medicine doesn't celebrate compliance.
- **Loading spinners shaped like anything other than a quiet indeterminate progress.** No swirling brand logos. No animated mandala-shaped loaders. The locked loading pattern is: skeleton placeholders on dense surfaces (Stone 8% bg, 4px border-radius blocks matching the destination layout) and a 1.5px Forest indeterminate spinner only when no structure can be shown (e.g., during OCR processing, on the upload progress sheet).
- **Parallax scrolling.** Adds nothing, adds motion sickness risk, distracts from clinical clarity.
- **Hero photo zoom-on-scroll.** Same reason.
- **Auto-play looping videos.** No background video on the home screen, on any screen.
- **Haptic celebration patterns.** Standard tap haptic on iOS buttons is fine; success haptic patterns are banned. A medication marked as taken does not earn a triple-pulse haptic.
- **Rotating gradients, animated noise textures, particle effects.** Treat them as banned by default.

### 14.8 How sheets and modals should behave

**Bottom sheets** are the primary disclosure pattern. They appear with a 220ms upward slide and a simultaneous 220ms fade-in of the dimmed Forest 60% backdrop. Dismiss with a 200ms slide down and backdrop fade. The sheet has a 16px top border-radius (locked). A drag-to-dismiss gesture works on iOS and Android, but the gesture should feel weighted — it should resist briefly, not flick away. (No precise spring constants; the platform default with no custom override.)

**Modals** appear with a 220ms fade + 4% scale-up from 96% to 100%. Backdrop is Forest 60%, no blur (no glassmorphism). The modal sits centred, 24px margins on small screens, max 480px wide. Used only for: destructive confirmations (delete account, cancel consultation), high-stakes consent moments, and irreversible privacy actions. Most things people instinctively reach for modals to do should be sheets instead.

### 14.9 How charts behave

The lab biomarker chart was specified in §7.5; motion specifics:

- **First paint:** Reference range band fades in at 220ms. Then the trend line draws from left to right at 1200ms with ease-out. Then the dots appear with 50ms stagger between dots, each at 120ms fade-in. The most recent dot stays on its tap-target highlight ring (Forest 8% fill, 16px diameter) at the end of the sequence. Total first-paint sequence: ~1500ms.
- **Subsequent paints (re-entering the chart from a back-navigation):** Chart is already drawn. No re-animation. The user has seen this before; respect that.
- **Range-switch (7d / 30d / 90d / 1y / All):** The line redraws at 220ms with a fade-cross — old line fades out at 200ms while new line fades in at 220ms with a 50ms overlap. No left-to-right re-draw — that's an "I'm showing you this for the first time" gesture and the user has just changed range, not opened the chart.
- **Tap-drag on chart:** A vertical Stone 30% line follows the user's finger with no easing — it moves at the speed the finger moves. The callout above shows date and value, updating instantly. When the finger lifts, the callout stays for 1500ms then fades out at 200ms.

### 14.10 How status changes animate

Healthcare status changes are emotionally significant — a biomarker moving from "out of range" to "in range," a consultation moving from "scheduled" to "completed," a medication moving from "active" to "discontinued." These changes deserve a small motion moment, but not celebration.

- **Biomarker status change** (e.g., previously Terracotta, now Sage): On the lab report detail when a new report supersedes an older one, the biomarker row crossfades its colour token over 600ms. No bouncing, no party. A simultaneous small comment slot below the row appears with the doctor's note about the change if one exists.
- **Consultation completed** (transitioning from "Upcoming" to "Past" on Consults): The card crossfades its top-edge colour (Saffron 4px → Stone 4px) over 600ms when the user returns to the Consults tab after a completed consultation. No "Completed!" toast. The user knows.
- **Medication marked as taken on a reminder:** The reminder row's left edge changes from Stone 1px to Sage 2px in 220ms. The status chip text shifts from "Due now" to "Taken" with a 120ms text crossfade. No checkmark animation, no celebratory haptic.

### 14.11 How numbers update

When a numeric value updates (an adherence percentage week-over-week, a biomarker comparison), the number does not snap. It counts from old value to new value over 600ms with ease-out — but only on a first reveal or a user-triggered change (e.g., user tapped "Compare to last month"). Background updates do not animate; they show the new number on next paint.

Use tabular-nums (locked from §12) so the digits don't shift width as they count.

### 14.12 Reduced motion handling

When `prefers-reduced-motion` is set at the OS level, the app respects it strictly:

- **All entrance / exit transitions** become instant (0ms).
- **Chart line-draw on first paint** becomes instant — the full chart appears immediately.
- **Numeral count-up** becomes instant — the final number appears.
- **Cormorant pull-quote reveal** becomes instant — the Cormorant appears at full opacity from the first frame.
- **Bottom sheets and modals** become instant cross-fades (0ms slide, 120ms opacity).

Reduced motion users are not getting a degraded experience — they're getting a more efficient one. The product still feels Kyros; it just doesn't perform any of the deliberate motion moments.

### 14.13 Continuity across steps

In multi-step flows (booking, intake, lab upload), each step should feel like it continues from the previous one rather than starting over. The technique is:

- **Stable header.** The progress stepper at the top of a multi-step flow stays in place across step changes — only the active step indicator moves. The header doesn't transition.
- **Content area transitions at 220ms.** The previous step's content fades out at 200ms (ease-in) while the next step's content slides in 12px from the right and fades in at 220ms (ease-out). Backward navigation slides 12px from the left.
- **CTA position is constant.** The "Next" or "Continue" CTA sits at the same screen position across all steps so the user's thumb doesn't have to relocate.

### 14.14 Loading specifics

Three loading registers:

1. **Skeleton.** When the system knows the structure of what's coming (lab report list, consultation history, dashboard cards). Skeletons are Stone 8% blocks with 4px border-radius matching the destination layout's geometry. They do NOT shimmer — shimmer is a wellness/SaaS reflex. They appear instantly and the real content swaps in at 220ms fade.
2. **Indeterminate spinner.** Used only when no structural placeholder is possible — during OCR processing, during a video call connection handshake, during a long server operation. A 24px Forest 1.5px-stroke circular indeterminate spinner, centred, with a status line below it ("Reading your report" / "Connecting to Dr Mehra" / "Encrypting upload"). The spinner rotates continuously at a slow 1200ms-per-revolution pace. No pulse, no breath effect.
3. **Progress bar.** Used only for known-duration operations (upload progress, video processing). 4px-tall Forest fill on Stone 12% background, rounded ends. No animation beyond the actual progress fill. No indeterminate progress bars.

### 14.15 Edge-case interactions

- **Pull-to-refresh:** Yes, on Home and Labs (where new data might arrive between sessions). Forest 1.5px circular spinner, no custom illustration, no brand mark. Standard platform pattern.
- **Swipe-to-delete on rows:** Only on Linked Devices (revoke a device), and on a draft prescription draft if any. Never on medications, lab reports, or consultations — destructive actions on clinical records require an explicit confirmation, not a gesture.
- **Long-press menus:** Available on biomarker rows (to access "View history" / "Compare reports" / "Add manual entry") and on lab reports (to access "Share with another doctor" / "Download PDF" / "Remove from record"). The menu appears as a sheet, not a hover-style popover.
- **Double-tap:** No double-tap interactions anywhere. Double-tap to like is a social-app idiom and doesn't belong here.

---

## 15. UX writing & microcopy

### 15.1 Voice principles

The Kyros product voice is **the voice of the doctor's room, written down**. It speaks in complete sentences, uses precise medical vocabulary without unnecessary jargon, never patronises, never alarms unnecessarily, and never tries to be cute. It is warm because the people writing it actually care, not because they're trying to sound warm.

Five voice principles:

1. **Plain medical language, not dumbed-down language.** "Your TSH is slightly elevated" is right. "Your thyroid number is a bit high!" is wrong. Patients are intelligent adults; respect that. Where a medical term needs explanation, explain it inline once and then use the term.
2. **Calm specificity, not vague reassurance.** "Your report has been added to your record. Dr Mehra will review it before your next consultation." is right. "All good! We've got it!" is wrong.
3. **Doctor-first attribution.** When a recommendation, plan, or insight is from a doctor, name the doctor. When it's from the system, don't pretend it's from a person.
4. **No fear-mongering. No urgency theatre.** No "URGENT — your test results are in!" No "Don't miss your dose!" No "You haven't logged today." The product does not pressure.
5. **Quietly warm at the right moments.** A welcome strip can say "Good morning, Niranjan." A doctor's note can read like a doctor. But the warmth lives in moments, not in every label.

### 15.2 Voice in action — wrong vs right

| Surface | Wrong (avoid) | Right |
|---|---|---|
| Welcome strip | "Hey there! Ready to crush your health goals today? 💪" | "Good morning, Niranjan." |
| Reminder due | "Time to take your meds! Let's do this 🎉" | "Levothyroxine 50mcg. Take with water on an empty stomach." |
| Reminder snoozed | "No worries! We'll bug you again later 😊" | "Snoozed. We'll remind you again in 15 minutes." |
| Upload progress | "Cooking up your report... ✨" | "Reading your report. This usually takes 30–60 seconds." |
| OCR low-confidence | "Oops! We need your help!" | "We couldn't read a few values clearly. Tap to review and correct." |
| Out-of-range biomarker | "Uh oh — looks like your TSH is high! 🚨" | "TSH 6.8 — slightly above the reference range (0.4–4.5)." |
| Doctor delay | "Sorry! Doctor running late 😞" | "Dr Mehra is running about 8 minutes behind. Please stay on this screen — we'll connect you as soon as she's ready." |
| Empty consultations | "No appointments yet! Book your first one!" | "You haven't booked a consultation yet. When you're ready, choose a focus area to begin." |
| Adherence summary | "You're a rockstar! 7-day streak! 🔥" | "You've taken 19 of 21 doses this week." |
| Critical alert | "DANGER! Critical value detected!" | "Potassium 6.2 mmol/L. This is above the safe range. Dr Mehra has been notified and will reach out shortly." |
| Privacy consent | "We need your permission to use cookies 🍪" | "We'd like to securely share your lab record with Dr Mehra so she can review it before your consultation. You can revoke this access anytime in Profile → My consents." |
| Delete account confirmation | "Are you really sure?! This is permanent! 😱" | "Deleting your account removes all your records, prescriptions, and lab history. After 30 days this cannot be undone. Type DELETE to confirm." |

### 15.3 Button language

Buttons describe the action, not the system's reaction. Active voice. No exclamation marks. No "Let's" framing.

- **Primary CTAs:** "Book consultation" — not "Let's book!" "Upload report" — not "Add a report." "Save changes" — not "Save!"
- **Secondary CTAs:** "View report" "Edit profile" "See history" "Cancel" "Snooze 15 minutes."
- **Destructive CTAs:** "Delete account" — never "Bye bye!" "Cancel consultation" — never "I changed my mind."
- **One-word CTAs are fine** when context is unambiguous: "Continue" "Done" "Submit" "Send."
- **Loading state on a CTA:** Inline spinner left of the label. Label text stays unchanged. Do not change "Submit" to "Submitting…" — the spinner says that.

### 15.4 Form labels and placeholders

- **Labels** are above the field, DM Sans 13px Stone, sentence case. "Mobile number." "Email address." "Date of birth."
- **Placeholders** show *example* values, not instructions. "+91 98765 43210" not "Enter your mobile number." "you@example.com" not "Type your email here."
- **Helper text** below the field, Stone 12px, only when needed. "We'll only use this to share your prescription PDFs." Helper text disappears once a value is entered.
- **Optional fields** are labeled "(optional)" — not "*" for required. The required state is the default; optional is the exception.
- **Required field with no value at submit:** "Please enter your date of birth." (Not "This field is required.")
- **Invalid value:** Specific. "This doesn't look like a valid Indian mobile number." Not "Invalid input."

### 15.5 Upload instructions

The lab report upload sheet (covered in §7.3) needs four lines of microcopy that set expectations and reduce friction:

- **Sheet title:** "Upload a lab report."
- **Sheet body:** "Take a photo or upload a PDF. We'll read it and add it to your record."
- **Hint below the primary CTA:** "Most reports work — even older paper ones."
- **Privacy line at the bottom of the sheet:** "Your report is encrypted before it leaves your device."

After upload starts:
- **Title shifts to:** "Reading your report."
- **Status line:** "This usually takes 30 to 60 seconds. You can leave this screen and we'll notify you when it's ready."

After successful OCR:
- **Title shifts to:** "Report added."
- **Body:** "20 biomarkers extracted. Tap to review."

After low-confidence OCR:
- **Title:** "We need your help on a few values."
- **Body:** "We couldn't read some readings clearly. Please review and correct them — this only takes a minute."

After OCR failure:
- **Title:** "We couldn't read this report automatically."
- **Body:** "You can enter the values manually, or try uploading again with better lighting."
- **Primary CTA:** "Enter values manually."
- **Secondary CTA:** "Upload again."

### 15.6 Consent screens

Consent should read like a Kyros letter, not like a terms-of-service dump. Each consent moment uses a structured pattern:

- **One-sentence purpose** (what we want to do).
- **One-sentence reason** (why).
- **One sentence on revocation** (how to undo).
- **Two CTAs** (Allow / Not now).

Example — lab sharing consent:
> "Share your latest lab report with Dr Mehra?
> She'll review it before your consultation on Thursday.
> You can revoke this access anytime in Profile → My consents.
> [ Allow ] [ Not now ]"

Example — Apple Health sync consent (after the OS-level permission):
> "Connected to Apple Health.
> Kyros will read steps, heart rate, weight, and sleep — only the metrics you choose. Nothing is shared without your permission.
> Manage which metrics sync in Profile → Linked health data.
> [ Done ]"

Long legal disclosure is collapsed behind "Read the full consent text" — available, but not the first thing the user sees.

### 15.7 Reminder microcopy

Reminders are the doctor speaking, not the system speaking. They use plain medication names and dosing, omit emojis, omit motivation, omit streak language.

| Context | Copy |
|---|---|
| 8am dose due | "Levothyroxine 50mcg. Take with water on an empty stomach." |
| Repeat reminder after 15 minutes (if not actioned) | "Reminder: Levothyroxine 50mcg." |
| Missed dose (4 hours after due, only sent once) | "You haven't logged this morning's Levothyroxine. If you've taken it, you can mark it taken now." |
| Marked as taken | (No copy — silent state change; row updates visually only.) |
| Marked as skipped | "Skipped. We'll let Dr Mehra know if this happens often." (Shown as a 2-second toast only.) |
| Marked as snoozed | "Snoozed for 15 minutes." (Toast only.) |

Privacy-sensitive reminders (TRT, intimate health) use a generic label by default per the user's preference: "Daily reminder." The detailed label appears only when the user opens the app — never on lock screen unless the user opted in.

### 15.8 Error states

Errors are explained in human language with a path forward. Three components: what happened, why it might have happened, what the user can do.

| Error | Copy |
|---|---|
| No internet on consultation start | "We can't reach the video service. Check your internet connection and tap Retry." |
| Payment failed | "Your payment didn't go through. Your card was not charged. You can try again, or use a different method." |
| Slot just taken | "This slot was just taken by another patient. Please choose a different time — these are still available today." |
| OCR upload too blurry | "We couldn't read this image. Try taking the photo again in better lighting, or upload as a PDF if you have one." |
| Doctor disconnected mid-call | "Dr Mehra has been disconnected. Please wait — we're reconnecting her now. This usually takes under a minute." |
| Account deletion grace period not yet expired | "Your account is scheduled for deletion on 20 June. You can cancel deletion until then by tapping Restore." |
| App update required (clinical safety-critical) | "A required update is available. Please update Kyros to continue. This update includes a fix to medication reminders." |

Never:
- "Something went wrong." (Be specific.)
- "Oops!" (No exclamation theatre.)
- "Please try again later." (When? Why?)
- "Error code 0x4f8a." (User-facing copy never shows error codes; they go to a Stone 12px line below the human message if support is asked.)

### 15.9 Empty states

Empty states explain why it's empty and what to do next — without trying to be cute about it.

| Surface | Empty-state copy |
|---|---|
| Labs (first visit, no reports yet) | "Your lab reports will appear here. Upload your first report to start building your record." |
| Consultations (none yet) | "You haven't booked a consultation yet. When you're ready, choose a focus area to begin." |
| Plan (no medications yet) | "Your medications and reminders will appear here after your first consultation." |
| Education (none assigned yet) | "Articles your doctor recommends will appear here. You can also browse the library." |
| Doctor commentary (waiting on note after first consultation) | "Dr Mehra's note from your consultation will appear here within 24 hours." |
| Trends (only one data point) | "We'll show trends here once you have at least two reports. Upload your next one when you have it." |
| Linked devices (only this one) | "Only this device is signed in to your Kyros account." |

### 15.10 Delay and waiting copy

Waiting states are where the product earns trust. Be honest about time, be specific about cause.

- **Doctor running late in waiting room:** "Dr Mehra is running about 8 minutes behind. Please stay on this screen — we'll connect you as soon as she's ready. You can also keep this tab open and we'll notify you."
- **OCR processing taking longer than usual:** (After 90 seconds.) "This is taking a little longer than usual. We're still working on it — feel free to leave this screen and we'll notify you when it's ready."
- **Doctor's note pending (more than 24h):** "Your consultation note hasn't arrived yet. Dr Mehra usually shares notes within 24 hours. If it's been longer than that, you can [message support]." (Only shown after 36 hours.)
- **Refill review in progress:** "Dr Mehra is reviewing your refill request. We'll let you know within 24 hours."

### 15.11 Educational content labels

Education labels respect that the user is reading something a doctor reviewed. Trust signals are typographic, not iconographic.

- **Article kicker (above title):** "Reviewed by Dr Mehra · NMC 47829 · Updated Nov 2025." DM Sans 12px Stone. Never "Trusted!" "Vetted!"
- **Body type for articles:** DM Sans 16px Ink, 1.6 line-height, max 65 characters per line. Cormorant only for the article hero title (28px) and one pull-quote per article maximum.
- **Inline citations:** "[1]" in DM Sans 13px, Forest, with the full citation list at the bottom of the article in DM Sans 12px Stone. Citations link to source (peer-reviewed journals, WHO/ICMR/MOHFW guidelines, named professional society guidelines).
- **End-of-article CTA:** "Have questions? Talk to Dr Mehra about this." Forest text button linking to a pre-filled consultation booking with this article noted in the intake.

### 15.12 Biomarker explanations (the hardest copy task)

Each biomarker on the lab report detail can be tapped to expand a short explanation. These are the most-read pieces of copy in the product. Structure:

- **What it is.** One sentence in plain language. "TSH (thyroid stimulating hormone) tells your thyroid how much hormone to make."
- **What this value means for you.** One or two sentences referencing the user's specific value, the reference range, and whether the result is in range, slightly off, or out of range. "Yours is 6.8 mIU/L — slightly above the reference range of 0.4–4.5. This often suggests an underactive thyroid."
- **What happens next.** One sentence about what Dr Mehra is doing or what the user should do. "Dr Mehra will review this and discuss it with you at your next consultation." Or: "Dr Mehra has already noted this — see her commentary below."
- **A "Learn more" link** to the relevant education article if one exists.

Banned phrases: "abnormal," "deficiency!" (with exclamation), "concerning," "alarming," "shocking," anything that introduces fear without specifying what to do about it.

### 15.13 Doctor commentary copy (when shown system-side)

Doctor commentary is *the doctor's own words*. The system never paraphrases. But the system does provide three pieces of supporting copy around the commentary:

- **The label above the commentary block:** "Dr Mehra's note from your consultation on 12 Nov 2025." DM Sans 13px Stone.
- **The Cormorant pull-quote treatment** is reserved for when the doctor's note contains a single line that summarises the plan — pulled out at 20px Cormorant italic Forest, indented 12px with a Saffron 2px left border. This treatment is applied editorially by the clinical team when writing the note, not auto-extracted.
- **The "Read full note" link** if the note is longer than the visible preview — Forest text button, opens the full note in a sheet.

### 15.14 Tone calibration across surfaces

Different surfaces warrant different amounts of warmth. A quick reference:

| Surface | Warmth dial | Why |
|---|---|---|
| Welcome strip on Home | Warm | First touch of the day, sets register |
| Doctor commentary | Warm | The doctor's voice, by definition |
| Education article body | Composed-warm | The doctor educating |
| Lab report values | Cool / clinical | Data should not be emotionally narrated |
| Prescription detail | Cool / clinical | Reads like a paper prescription |
| Consent screens | Composed, plain | Trust is built through clarity, not warmth |
| Error states | Composed, factual | Warmth here reads as evasion |
| Critical alert | Composed, urgent, factual | No "Oh no!" — direct facts and a path |
| Privacy actions (delete, export) | Composed, factual | Respect the gravity of the action |
| Reminder notifications | Plain, factual | Notification fatigue is real |

The product is composed-warm-clinical on average, but the dial slides per surface. The dashboard welcome strip can carry warmth that would be inappropriate on a critical alert screen.

---

## 16. Accessibility & healthcare-specific usability

### 16.1 Why healthcare accessibility is not generic accessibility

Generic SaaS accessibility focuses on screen readers, contrast, and tab order. Healthcare accessibility additionally accounts for:

- **Anxious users with reduced cognitive bandwidth** — a patient with newly-diagnosed PCOS reading her first lab report has 30–50% less working memory than her baseline.
- **Tired users** — patients with hypothyroidism, chronic fatigue, or chronic illness often interact with the product while tired.
- **Older users** — many patients are 40+ for hormone-related care; many TRT and longevity users are 50+. Default font sizes for a 25-year-old SaaS user are unreadable for many of these users.
- **One-handed users** — patients are often holding a child, a coffee, a cane, or are lying down.
- **Public-space users** — a TRT patient does not want a notification preview reading "Testosterone enanthate 0.5ml — IM injection — Tuesday" on a lock screen on the metro.
- **Pre-consultation users** — anxious, possibly upset, possibly recently received a difficult diagnosis. UI should not require fine motor precision or rapid recall.

The product must work for users at their worst day, not their best.

### 16.2 Tap targets

- **Minimum tap target:** 48×48px. No exceptions. (Smaller visual elements are fine if the tappable area extends to 48px.)
- **Primary CTAs:** 56px height, with comfortable horizontal padding (24px each side minimum).
- **Tab bar items:** Each tab is 56px tall × full-width-divided-by-5. The visual icon is 24px; the tap target is the entire tab cell.
- **Inline action chips:** 36px tall × at minimum 64px wide. Smaller visual chip is acceptable if its tap target extends past visible bounds.
- **Spacing between tap targets:** 8px minimum (12px preferred) so users with motor difficulty don't accidentally hit adjacent targets.
- **Edge-of-screen tap targets:** Avoid placing critical actions in the bottom 8px or the side 8px of the screen — gesture-area conflicts on iOS.

### 16.3 Font sizing

- **Body default:** 16px DM Sans, Ink. Smaller body sizes are unacceptable on patient-facing surfaces.
- **Metadata / labels:** 13px Stone — used for date stamps, secondary info. Never falls below 12px.
- **Captions / micro:** 12px Stone — used sparingly, only for legal-style fine print, footnote-equivalent details. Never for primary information.
- **iOS Dynamic Type / Android font scaling:** Supported up to 200%. The layout reflows; cards stretch vertically; no information is clipped. At 200% scale the dashboard becomes a vertical scroll of single-column cards.
- **Cormorant Garamond at small sizes:** Banned. Cormorant only appears at 20px+ for pull-quotes, 28px+ for article hero titles. Below 20px, Cormorant lacks the contrast needed for accessible reading.
- **Numeric values on lab biomarkers:** 22px DM Sans Tabular Forest semibold. Specifically chosen larger than body so values remain legible to tired/anxious eyes.

### 16.4 Contrast

All token pairs verified per the design system. WCAG AA minimum across the product; AAA where achievable. Reference (from design system):

| Foreground / Background | Contrast | WCAG |
|---|---|---|
| Ink #1A1A1A / Ivory #FAF1E4 | 15.8 : 1 | AAA |
| Ink #1A1A1A / White #FFFFFF | 19.3 : 1 | AAA |
| Forest #0F3D2E / Ivory | 12.4 : 1 | AAA |
| Forest #0F3D2E / White | 14.9 : 1 | AAA |
| Stone #6B6B68 / Ivory | 5.2 : 1 | AA |
| Stone #6B6B68 / White | 6.0 : 1 | AA |
| Saffron #E08E3C / Ivory | 2.8 : 1 | Decorative only — never body text |
| Saffron on Forest button | Ivory text used; passes AAA on Forest fill | AAA |
| Terracotta on Ivory | 4.8 : 1 (large/heading only) | AA Large |
| Alert #B53A2B on Ivory | 6.2 : 1 | AAA |

**Critical rule:** Saffron and Terracotta are never used as body text or as a colour for small UI text. Where they appear, they appear as backgrounds (with Ivory text), borders (1–2px), or large numerals (20px+).

### 16.5 Colour is never the only signal

For every status (in-range, out-of-range, critical, due, skipped), the visual encoding combines colour and shape or text:

- **In-range biomarker:** Sage chip + the word "In range" + (optional) a small filled dot.
- **Slightly off:** Saffron chip + the word "Slightly above range" or "Slightly below range" + an upward/downward arrow.
- **Out of range:** Terracotta chip + the word "Above range" (or "Below range") + a clear arrow.
- **Critical:** Alert chip + the word "Above safe range" + a solid square indicator + the doctor's name attached ("Dr Mehra has been notified").

A colour-blind user (any flavour) can distinguish all four statuses by text and shape alone.

### 16.6 Low-light usability

The default Kyros UI is light-mode on Ivory. Dark mode is a planned addition (not in MVP), but the light-mode UI is engineered to be legible in low light:

- **Ivory** is not bright white — it's a warm muted off-white that doesn't blast the eyes in a dark bedroom.
- **Body text on Ivory** has 15.8:1 contrast — readable at any reasonable screen brightness.
- **Critical surfaces** (lab report detail, reminder notifications) use White instead of Ivory specifically because White's higher contrast aids data parsing — at the cost of a more clinical feel.
- **Auto-brightness adaptation:** The OS handles this; the product doesn't override or interfere.

When dark mode ships, it should be a true dark mode (deep dark grey, not Forest — Forest as a dark mode background loses too much contrast against Forest text accents). Saffron and Terracotta remain warm; Sage and Peach Mist are replaced with dark-mode-appropriate companions.

### 16.7 One-handed usability

The thumb zone matters. The Kyros app is engineered for right- and left-handed one-handed use:

- **Bottom tab bar** is reachable in any grip.
- **Primary CTAs** sit in the bottom third of the screen — never at the top.
- **The "X" close button on sheets** is on the top-right (the natural top-corner thumb arc for one-handed reach) and is 44×44px tappable.
- **The back chevron** on screens sits in the top-left (platform standard), and is reachable on most phones via thumb stretch — but critical screens (lab report detail, consultation detail) also support edge-swipe-back (iOS gesture; Android system back).
- **No critical action requires reaching the top-centre of the screen.** Headers can hold non-critical actions (search, filter), but the primary task always lives in the lower half.

### 16.8 Older / tired / anxious users

- **Default font size 16px** is large enough for users 50+. Combined with Ivory + Ink, contrast is comfortable for older eyes.
- **No information is hidden behind hover** (on mobile this isn't relevant; on web portal, hover-only states are banned — all info is visible or tap/click revealed).
- **No critical action requires more than one sequential tap to confirm.** "Tap to view your prescription" is fine. "Tap, then long-press, then choose" is not.
- **Loading states show time estimates** where possible. "This usually takes 30–60 seconds" reassures the tired user that nothing is broken.
- **All long lists support large-step navigation** (e.g., jump-to-month on consultation history, year-jumper on lab trend chart).

### 16.9 Medical terminology handling

The product uses plain language as the default, but never strips out medical terms — patients need them to communicate with doctors, search for information, and read paper reports.

- **First mention of a term** includes a brief gloss. "TSH (thyroid stimulating hormone) is..."
- **Subsequent mentions** use the term alone.
- **Tappable glossary:** Any underlined-on-tap medical term opens a short definition sheet. The glossary entries are written by the clinical team.
- **Acronyms in lab reports** are preserved exactly as the lab reported them (e.g., the lab says "FT4" — Kyros shows "FT4" with a tap-to-expand gloss).
- **No "easy mode" toggle.** The product does not have a "simplify" switch. The complexity is calibrated to be approachable by default.

### 16.10 Form fatigue mitigation

Forms in the product (intake, payment, profile editing) follow the same rules:

- **One concept per screen** for the intake flow. The patient enters age on one screen, sex assigned at birth on the next, current symptoms on the next. Each screen is fast; the total is the same length as a wall-of-form, but the cognitive load is much lower.
- **Auto-advance** where possible. After tapping a single-select radio, the screen advances at 220ms. The user does not need to tap "Next" for a single-tap question.
- **Save-on-exit.** The form state persists if the user leaves the app. Reopening returns to the same step.
- **Progress visibility.** A simple "Step 3 of 7" indicator at the top, with previous steps tappable to revisit.
- **Skip-able sections:** Non-clinical questions (preferred name, communication preferences) are marked clearly optional and can be skipped.

### 16.11 Multi-step flow fatigue

The longest flows in the product are: initial intake (7–10 steps), lab upload + correction (2–3 steps), and booking + payment + consent (3–4 steps). Mitigations:

- **No more than 10 steps in any single flow.** If a flow trends longer, it's split or restructured.
- **Persistent save** on intake — the patient can pause and resume. The dashboard surfaces "Continue your intake" until complete.
- **Reduced visual variety** across steps — the same layout, same CTA position, same step indicator. Visual sameness reduces cognitive shifting.
- **End-of-flow summary** showing what's about to be submitted, so the user can scan once before committing.

### 16.12 Chart accessibility

Lab biomarker charts are the most data-dense surface in the product. Accessibility requirements:

- **Each biomarker chart has an accessible-table fallback** reachable by a "View as table" link below the chart. The table lists each data point's date and value in DM Sans, screen-readable.
- **The chart's reference range is announced** in alt-text: "Trend chart. Reference range 0.4 to 4.5 mIU per litre. Five data points from January to November 2025. Most recent value: 6.8, above range."
- **Tap+drag interactions** are mirrored by left-arrow / right-arrow keyboard equivalents on the web portal — and on the mobile app, by accessibility focus-and-swipe with VoiceOver / TalkBack.
- **Colour-blind alternative encoding:** The trend line is Forest 2px; data points are Forest filled circles; reference range band is Sage 12% with a Forest 1px top/bottom guideline. Out-of-range dots are encoded by position (above/below the band) in addition to colour. A user who can't perceive the Sage band can still see that the dot is positioned outside two horizontal guidelines.

### 16.13 Screen reader semantics

- **All interactive elements have accessible labels** that describe what tapping does, not what the element looks like. "Book consultation" not "Saffron button."
- **Sections have heading hierarchy** (H1 for screen title, H2 for sections, H3 for cards). VoiceOver / TalkBack can navigate by heading.
- **Lab values are read in a useful order:** "TSH. 6.8. mIU per litre. Slightly above reference range. Reference range 0.4 to 4.5. Tap for explanation."
- **Decorative elements have empty alt-text** or are marked `aria-hidden`. The Cormorant pull-quote on doctor commentary has its full text as the heading; the visual treatment is not announced as "image."
- **Status changes are announced** via `aria-live="polite"` regions. When a reminder marks as taken, the screen reader announces "Levothyroxine marked as taken at 8:14am."
- **Toasts and banners** use `aria-live="assertive"` only when truly critical (a connection lost during a video call); otherwise `polite`.

### 16.14 Privacy in public spaces

- **Lock-screen notification text** defaults to generic ("Daily reminder" / "New message from Kyros") unless the user opted into detailed previews.
- **Sensitive-condition labels** are short and non-revealing on Home cards seen at glance: "Plan for today" not "Testosterone replacement plan."
- **Lab report titles** on the Labs list default to "Lab report — 12 Nov 2025" not "PCOS panel — 12 Nov 2025." The category is visible inside the report, not on the list.
- **Doctor names on lock-screen** are visible (patients want to know who's contacting them); category context is not.
- **Privacy mode toggle** in Profile lets the user enable an extra layer: when active, any biomarker values on the Home dashboard are masked behind "Tap to reveal" tiles. Useful for patients reviewing their dashboard on a shared family device or during a commute.

### 16.15 Masked sensitive data patterns

- **Phone number masked:** "+91 ••••• 56789" with a "Show" toggle.
- **Email masked:** "n••••••@example.com" with a "Show" toggle.
- **ABHA ID:** Always masked except in a dedicated "ABHA details" sheet.
- **Date of birth:** Visible to the patient in their own profile (no need to mask self from self), but never appears as a passive label on Home or Consults.
- **Address:** Never appears in the product UI at all. It exists in the patient record but is not surfaced in patient-facing screens.


---

## 17. Component library

This section enumerates the primary product components, their anatomy, states, and use rules. Every component honours the locked visual system (§12) — no new tokens, no new colors, no new typography weights are introduced here.

### 17.1 Buttons

**Purpose:** Primary user actions, secondary confirmations, destructive operations.

**Variants:**

- **Primary (Forest fill):** Forest #0F3D2E background, Ivory text, 56px tall, 24px horizontal padding, 8px border-radius. The default for the most important action on any screen.
- **Primary (Saffron fill):** Saffron #E08E3C background, Forest text, 56px tall, 8px border-radius. Used sparingly — only when the action is the warm "next step in care" (e.g., "Book follow-up consultation," "Continue with intake"). Maximum one Saffron primary per screen.
- **Secondary (Forest outline):** Ivory background, Forest 1.5px border, Forest text, 56px tall, 8px border-radius. Used for the alternative action when a primary exists.
- **Tertiary (text button):** Forest text, no border, no fill, 16px DM Sans semibold, 48px tap-target. Used for low-emphasis actions ("View history," "See all").
- **Destructive (Alert outline):** Ivory background, Alert 1.5px border, Alert text. Used for destructive confirmations (delete account, cancel consultation) — only inside the confirmation dialog itself, never on listing surfaces.

**States:**
- Default, Pressed (Forest button → darker Forest #0A2C20; Saffron → darker Saffron #C77929), Disabled (Stone 30% fill, Stone 60% text), Loading (inline spinner left of label, label retained).

**When NOT to use:**
- As a heading. Buttons are actions, not decoration.
- Stacked vertically more than two times. If three CTAs are needed, the screen is doing too much.
- With emoji. Ever.

### 17.2 Chips

**Purpose:** Compact category/status indicators or selectable filters.

**Variants:**

- **Status chip (Sage / Saffron / Terracotta / Alert):** 24px tall, 6px border-radius, 12px horizontal padding, 13px DM Sans Forest on tinted bg. Used for biomarker statuses, consultation states ("Upcoming" / "Past"), and similar.
- **Filter chip (selectable):** 32px tall, 6px border-radius, Forest 1px border, transparent fill when inactive, Forest fill + Ivory text when active. Used on lab filters, consultation history filters.
- **Read-only metadata chip:** No border, just tinted bg (Peach Mist or White on Ivory). 24px tall, 6px border-radius.

**States:**
Default, Selected, Hover (web only, very subtle bg shift).

**When NOT to use:**
As a CTA. Chips are descriptors, not actions. A chip with an arrow icon is wrong — that's a button or a tile.

### 17.3 Badges

**Purpose:** Small notification indicators or counts.

**Anatomy:** 16px diameter circle (or pill if a count of 2+ digits). Saffron fill with Forest text. Placed top-right of an icon or item.

**Where used:** Tab bar items with pending state (e.g., a new doctor note on Consults), notification bell. Used sparingly — three or more simultaneous badges create alarm.

**When NOT to use:** As a permanent label. Badges represent transient, action-required state. If a badge is always there, it's a label and should be designed as a chip instead.

### 17.4 Tabs and segmented controls

**Bottom tab bar:**
- 5 items: Home, Consults, Labs, Plan, Profile.
- 56px tall, Ivory bg, Forest 1px top border.
- Active tab: 24px Lucide icon Forest filled-stroke (line-only style retained, weight visually heavier via stroke), 12px DM Sans Forest label below.
- Inactive tab: 24px Lucide icon Stone, 12px DM Sans Stone label.
- No active-indicator pill behind the icon (too SaaS). The colour change carries the state.

**Segmented control:**
- Used inside screens for view switches (Active / Past on Prescriptions, 7d / 30d / 90d / 1y / All on chart range).
- 36px tall, Ivory bg, Forest 1px border, 8px outer radius.
- Active segment: Forest fill, Ivory text.
- Inactive segment: transparent fill, Stone text.

**Top tabs:** Used rarely — only on the Consults screen (Upcoming / Past). 48px tall, Forest 2px bottom indicator under active label.

### 17.5 Navigation bar (per-screen header)

**Purpose:** Screen title, back navigation, and at most one trailing action.

**Anatomy:** 56px tall on mobile (88px including safe area on iPhones with notch). Ivory bg. Forest 1px bottom border on scroll, no border at top of screen. Forest back chevron 24px on left (24px tap-target, 44×44 effective). Forest 16px semibold DM Sans title centred. Optional trailing action (16px DM Sans Forest text button) on right.

**When NOT to use:**
- With multiple trailing actions. If a screen needs 3+ actions, they belong in a sheet or a "..." overflow menu (which itself opens a sheet).
- With centred logos. The logo lives in the splash and About, not on every screen.

### 17.6 Cards

**Purpose:** Group related information into a tappable surface.

**Anatomy:** White or Ivory background, Forest 8% (rgba(15, 61, 46, 0.08)) 1px border, 12px border-radius, 16px internal padding. No box-shadow. Tappable cards have an entire-card hit area; the user can tap anywhere on the card to activate the primary action.

**Variants:**
- **Information card:** Default. Shows data, doesn't directly invoke an action when tapped (taps may open a detail sheet, but the card itself is informational).
- **Action card:** A card that wraps a primary action (e.g., the upcoming consultation card on Home). Distinguished by an arrow chevron on the right edge and a slightly more prominent primary CTA inside the card body.
- **Doctor commentary card:** Saffron 2px left border, otherwise standard card. Cormorant 20px italic pull-quote in the card body.
- **Critical-state card:** Replaces the Forest 8% border with Alert 1.5px border. Used only on critical lab values and similar.

**Internal anatomy (typical):**
- Optional kicker (DM Sans 12px Stone, sentence case)
- Card title (DM Sans 16px Ink semibold)
- Card body (DM Sans 14–16px Ink)
- Optional metadata row (DM Sans 12px Stone)
- Optional CTA row (text button or chip)

**When NOT to use:**
- Nested cards. A card inside a card is structural noise. Use sections inside a card instead.
- For decorative purposes. Every card holds a real piece of information.

### 17.7 Accordions

**Purpose:** Disclose detail without leaving the current screen.

**Anatomy:** A row with a title (16px DM Sans Ink), a chevron indicator (Stone 16px), and an expanded content area below. 56px tall collapsed, content extending tall when expanded. Forest 8% 1px bottom border.

**Used for:**
- Long doctor commentary on the lab report detail (collapsed by default to "Read note," expanded inline).
- FAQ sections in Profile → Help and About.
- Detailed consent disclosure ("Read full consent text").

**Animation:** 220ms expand/collapse with ease-in-out. Content fades in over the last 120ms of expansion.

**When NOT to use:** As the primary navigation for a screen. If a screen consists entirely of accordions, restructure into a list with detail pages.

### 17.8 Form inputs

**Single-line text input:**
- 56px tall, 8px border-radius, Forest 1px border (default), Ivory fill (or White on Ivory backgrounds — uses the lower-warmth fill to read as a data-entry field).
- Label above the input, DM Sans 13px Stone.
- Placeholder DM Sans 16px Stone 60%.
- Focused state: Forest 1.5px border, no glow.
- Error state: Alert 1.5px border, helper text below in Alert 12px.

**Textarea (multi-line):** Same as input but min-height 96px, max-height 256px before scrolling.

**Radio / checkbox:** 24px target, Forest border, Forest fill when selected, Ivory dot/check inside the fill. 12px label gap.

**Toggle (switch):** 32×20px. Stone fill when off, Forest fill when on, Ivory thumb. 220ms ease-in-out.

**Select / picker:** Always opens as a bottom sheet, not as a dropdown. The visible input field looks like a text input with a chevron on the right.

### 17.9 Date and time pickers

**Date picker:** Bottom sheet, month-grid view, Forest highlight on selected date. Confirm CTA at the bottom of the sheet.

**Time picker:** For consultation slots, NOT a generic time picker — instead a custom day-rail + slot-list pattern (see §6.3). Time is selected from available slots, not free-form.

**Date-of-birth pattern:** Three rolling pickers (day, month, year) in a sheet, to mirror common Indian form patterns. Direct keyboard entry also supported for power users.

### 17.10 Progress steppers

**Purpose:** Show progress through a multi-step flow.

**Anatomy:** Horizontal row of dots or short bars connected by lines. Active step Forest fill, completed steps Forest 50% fill, pending steps Stone 30% fill. Step label DM Sans 12px below.

**Variant for intake (7+ steps):** "Step 3 of 7" text + horizontal Forest fill bar showing 3/7 progress. Reduces visual clutter at high step counts.

**When NOT to use:** For flows of ≤2 steps. A single confirm screen doesn't need a stepper.

### 17.11 Upload areas

**Purpose:** Lab report upload (the highest-traffic upload in the product).

**Anatomy (sheet variant):**
- Sheet title: "Upload a lab report."
- Two large action tiles (full-width, 96px tall each, stacked):
  - "Take a photo" — Forest fill, Ivory text + Lucide Camera icon
  - "Choose a PDF" — Forest 1.5px outline, Forest text + Lucide File icon
- Bottom helper text: "Most reports work — even older paper ones."
- Privacy line: "Your report is encrypted before it leaves your device."

**Progress state:**
- Sheet remains open. Title shifts to "Reading your report." Indeterminate spinner. Status updates inline.

**Upload-area on web portal:** Adds a third option — drag-and-drop area (Forest dashed 2px border, Forest text "or drag a file here"). Drag-over state changes border to Forest solid + Saffron 4% bg.

### 17.12 Biomarker rows

**Purpose:** Display a single biomarker value within a lab report or trend list.

**Anatomy (collapsed row):**
- Status indicator: 4px vertical bar on the left edge of the row, coloured by status (Sage / Saffron / Terracotta / Alert).
- Biomarker label: DM Sans 16px Ink semibold.
- Reference range: DM Sans 12px Stone (right-aligned or below the label).
- Value: DM Sans 22px Tabular Forest semibold (right side of the row).
- Unit: DM Sans 12px Stone, below the value.
- Status chip: 24px tall, on the row's right edge or in a second line for narrow screens.

**Tap behaviour:** Opens an inline expansion below the row (60% of biomarker tap interactions stay on the same screen). Expansion shows: brief explanation, mini-trend chart (small horizontal trend, last 5 readings), doctor commentary if any, "View full chart" link.

**See §7.5 for full row anatomy.**

### 17.13 Chart legends

**Purpose:** Identify trend lines on multi-series charts (e.g., comparing two biomarkers).

**Anatomy:** Small inline chips below the chart. Coloured dot 8px + label in DM Sans 12px.

**When used:** Only on multi-series charts. Single-series charts have no legend (the title says what the line is).

### 17.14 Info callouts

**Purpose:** Surface a single piece of supporting information without making it look like an action.

**Anatomy:** Peach Mist or Sage 12% bg, Forest 1.5px left border, 12px padding, 8px right radius. DM Sans 14px Ink body text. Optional Lucide Info icon 16px Forest at the top-left of the callout.

**Used for:** "Take this on an empty stomach" instructions on a medication detail, "This lab report has been shared with Dr Mehra" notes on a lab.

**When NOT to use:** For errors or critical info. Those use the alert pattern, not a callout.

### 17.15 Doctor commentary cards

**Purpose:** Surface the doctor's voice as a distinct, recognisable piece of UI.

**Anatomy:**
- White bg, Saffron 2px left border, 12px border-radius (right side), 16px padding.
- Header: "Dr Mehra's note · 12 Nov 2025" — DM Sans 13px Stone.
- Body: Cormorant Garamond 20px italic Forest pull-quote (one sentence, the headline of the note).
- Continued body: DM Sans 16px Ink (the rest of the note).
- Footer (if longer): "Read full note" text button + Forest text.

**Where used:** Home dashboard (when a recent note is available), Lab report detail (under the biomarkers), Consultation history (in the post-consultation card).

**When NOT to use:** For system-generated text. Only used when a real doctor wrote a real note.

### 17.16 Reminder rows

**Purpose:** A single reminder within the Plan view or notification log.

**Anatomy:**
- Status indicator: 4px vertical bar on left edge (Stone for due, Sage for taken, Stone dashed for skipped, Saffron for snoozed).
- Time stamp: DM Sans 13px Stone (e.g., "8:00 AM").
- Reminder label: DM Sans 16px Ink semibold (medication name + dose).
- Instruction line: DM Sans 13px Stone (e.g., "Take on empty stomach with water").
- Action chips (when due): "Taken" / "Skip" / "Snooze 15m" — 36px tall, side-by-side.

### 17.17 Medication timeline rows

**Purpose:** Show dose changes over time on a single medication.

**Anatomy:** Vertical timeline with Forest 1px line, Forest filled dots at each change event, dates in DM Sans 12px Stone on the left, dose-change description in DM Sans 14px Ink on the right.

Each entry: "12 Nov 2025 — Dose increased from 25mcg to 50mcg by Dr Mehra."

**When NOT to use:** For active dose only (use the regular medication card). The timeline is for history.

### 17.18 Educational article cards

**Purpose:** Surface an assigned or browseable article on Home or Education library.

**Anatomy:**
- White bg, Forest 8% 1px border, 12px border-radius, 16px padding.
- Optional small Lucide-style icon top-left (Stone 16px, e.g., a book outline).
- Kicker: "Recommended by Dr Mehra" or "Library" — DM Sans 12px Stone.
- Title: DM Sans 16px Ink semibold, max 2 lines.
- Reviewer line: "Reviewed by Dr Mehra · NMC 47829 · Updated Nov 2025" — DM Sans 11px Stone.
- Optional 4-minute read indicator: "4 min read" — DM Sans 12px Stone.

**See §10.3 for full card spec.**

### 17.19 Privacy action rows

**Purpose:** A single privacy or data-rights action on the Profile → Privacy & data screen.

**Anatomy:**
- White bg, Forest 8% 1px bottom border (rows separated, no individual card framing).
- 56px tall.
- Lucide icon 20px Forest on the left.
- Label DM Sans 16px Ink.
- Optional description below DM Sans 13px Stone (e.g., for "Delete my account": "Removes all your records after a 30-day grace period.").
- Chevron 16px Stone right.

**Variants:**
- Default privacy action (export, download, delete a record).
- Destructive privacy action (Delete account): label is Alert text instead of Ink.

### 17.20 Toasts, banners, inline alerts, sheets, modals

**Toasts:**
- Small floating notifications, appear at the bottom-centre (above the tab bar), 200ms fade-in, auto-dismiss after 2.5 seconds (3.5s if action-bearing).
- Forest fill bg, Ivory text, 8px border-radius.
- Used for: ephemeral confirmations ("Reminder marked as taken," "Snoozed for 15 minutes").
- Never used for errors that require action (those are inline alerts).

**Banners:**
- Wide, full-width-of-content alerts pinned to the top of a screen or section.
- Sage tint bg + Forest text for informational ("This report was shared with Dr Mehra on 14 Nov").
- Saffron tint bg + Forest text for action-requested ("Complete your intake to enable booking").
- Alert tint bg + Alert text for system-critical ("Connection lost. Trying to reconnect…").
- Dismissible (X on the right) unless the banner is conveying a non-dismissable system state.

**Inline alerts:**
- Below a specific field or section. 12px helper-text-style. Alert colour for errors.

**Bottom sheets:**
- Primary disclosure pattern. See §14.8 for behaviour.
- Anatomy: 16px top radius, Ivory bg, sheet handle 32×4px Stone 30% at the top-centre (decorative, signals drag-to-dismiss), sheet title DM Sans 18px Forest semibold below the handle, content below the title, primary CTA pinned to the bottom of the sheet.

**Modals:**
- Reserved for irreversible / destructive / consent. See §14.8.
- Two CTAs always: confirm (destructive variant if destructive) and cancel.
- Cancel is on the left; confirm is on the right (platform convention).

---

## 18. State design

Every screen lives in multiple states. Healthcare apps that handle states well retain trust during the worst moments — connection loss, OCR failure, an empty record. Apps that handle them poorly look broken, and a broken-looking health app is one a patient won't trust with their next lab report.

### 18.1 First-use state

**The first time a user opens the app after signup.** Before any consultation, any lab report, any medication.

**Design pattern:** The Home dashboard shows a single hero card with the three pillars ("One doctor, who knows your story. One place, where your health lives. One platform, where privacy is the point.") in DM Sans 16px Ink (not Cormorant — too premature emotionally for a brand-new user). Below it, a primary CTA: "Book your first consultation." Below that, a quiet secondary path: "Or upload a lab report you already have." No fake metrics. No "Welcome aboard 🎉" toast. The product reads as composed and ready.

**What appears in each tab:**
- Home: hero card + the two paths above.
- Consults: empty state ("You haven't booked a consultation yet…") + the same primary CTA.
- Labs: empty state ("Your lab reports will appear here…") + an "Upload a report" CTA.
- Plan: empty state ("Your medications and reminders will appear here after your first consultation.").
- Profile: full profile — this is the one tab that's complete from day one.

### 18.2 Empty state

For any list or area where data has not yet been created. Pattern:

- 60×60 Forest line icon, centred (a different icon per surface — calendar for consultations, document for labs, list for plan, book for education).
- DM Sans 18px Ink semibold one-line headline ("No lab reports yet").
- DM Sans 14px Stone explanation ("Upload your first report to start building your record.").
- DM Sans Forest text button or Forest filled CTA ("Upload a report" / "Browse the library").

Empty states never use Cormorant. They never use illustration beyond the single line icon. They never apologise ("Sorry, no reports here!"). They explain and offer.

### 18.3 Loading state

Two patterns (per §14.14):

- **Skeleton placeholders** for structured content. Stone 8% rectangles matching the destination layout. No shimmer. Appear instantly on screen entry; real content swaps in at 220ms fade.
- **Indeterminate spinner** for unstructured operations. 24px Forest 1.5px-stroke ring, centred, with a status line below.

For partial loads (Home dashboard where some sections load before others): each card shows its own skeleton independently. Cards that load first appear immediately; later cards arrive without re-arranging the layout above them.

### 18.4 Syncing state

For background data syncs (Apple Health, lab report processing, doctor's note arrival):

- A small Forest 1.5px-stroke sync icon (Lucide RefreshCw) appears next to the relevant card title, spinning at 1200ms-per-revolution.
- Status line beneath the card: "Syncing with Apple Health…" or "Reading your report…"
- No full-screen sync overlay. The patient should be able to keep using the app while background work happens.

When sync completes: the icon fades out at 220ms. A subtle Forest 1px top border appears briefly on the affected card (220ms appear, 600ms hold, 220ms fade) to direct attention to the change without alarming.

### 18.5 Success state

Healthcare success is muted by design. The app does not celebrate.

- **Form submit success:** The screen advances to the next step (or back to the dashboard) at 220ms. A small toast confirms: "Profile updated" / "Report uploaded" / "Consultation booked."
- **Action success on a card:** The card's status updates inline (e.g., reminder row becomes Sage). No checkmark animation, no haptic celebration.
- **Booking success:** A dedicated confirmation screen — DM Sans 28px Forest headline "You're booked," DM Sans 16px Ink body with date, time, doctor, NMC reg, and link to add to calendar. No confetti. The headline borrows the directness of an airline ticket confirmation.

### 18.6 Warning state

Used for situations that need user attention but are not critical. The biomarker chip / row colour token Saffron is the visual lead.

- **Examples:** A lab value slightly out of range, a payment about to expire, a refill due soon.
- **Pattern:** Inline within the relevant card, not a full-screen modal. Saffron tint background or 4px left border, DM Sans 14px Ink body, optional Forest text button for the recommended action.
- **Tone:** Specific, calm, with a clear next step. "Your refill window opens in 3 days. Dr Mehra will review your request when you submit it."

### 18.7 Critical state

Reserved for true clinical concern. Visually loud, but composed.

- **Pattern:** A dedicated card with Alert 1.5px border on the lab report detail or, in the most severe cases, a banner pinned to the top of the Home dashboard.
- **Body:** "Potassium 6.2 mmol/L — above the safe range. Dr Mehra has been notified and will reach out by phone. If you experience [symptom list], please go to the nearest emergency room."
- **Phone CTA:** A "Call clinic" button in Alert outline below the body. (See §6.10 for the clinic phone number always being accessible.)

A critical state is the one place the product allows itself to be visually loud — and even then, the language remains specific and the doctor remains named.

### 18.8 Error state

Per §15.8 — every error names what happened, why it might have happened, and what to do.

- **Network errors:** Banner at the top of the affected surface, Alert tint bg. "Connection lost. Trying to reconnect…" Auto-dismisses when reconnected.
- **Form submission errors:** Inline below the field that caused the error. Alert helper text 12px.
- **Server errors:** Full-screen error card, Forest icon, DM Sans headline ("Something on our side broke."), DM Sans body ("This isn't your fault. We've already been notified. Please try again in a few minutes."), retry button.
- **Critical workflow errors** (e.g., payment processed but booking didn't go through): Persistent banner on Home until resolved, with the clinic's phone number for immediate help.

### 18.9 Permission denied

When the user denies an OS-level permission (camera, photos, notifications, Apple Health):

- **Pattern:** A composed card explaining what the permission was for, why it was requested, and how to enable it later. "Camera access lets you take photos of lab reports. You can enable it in Settings → Kyros → Camera if you change your mind."
- **No nagging.** The product does not re-request the permission after denial. The Upload screen instead shows "Choose from your gallery" or "Choose a PDF" as the primary options.

### 18.10 No results

For search or filtered views (consultation history filtered by year, lab reports filtered by category):

- **Pattern:** Inline below the filter chips. DM Sans 16px Ink ("No reports match these filters."). Below that, "Clear filters" text button.

### 18.11 Disconnected / offline

The app supports offline reading of cached data (last lab report, current prescription, plan for today) but cannot perform actions offline.

- **Offline banner:** Stone tint bg, "You're offline. Your latest reports and plan are available. Booking and uploads will resume when you're back online." Dismissible.
- **Disabled actions:** Booking CTA, upload CTA, and call CTAs are visibly disabled (Stone 30%) while offline. Tapping them shows a tooltip: "Connect to the internet to continue."

### 18.12 Partially complete profile

A common state — the patient signed up, started intake, but didn't finish.

- **Home banner:** Saffron tint, "Complete your intake to enable consultation booking." With a "Continue intake" CTA.
- **Intake screen:** Resumes at the last incomplete step.
- **No nag-modal on app open.** The banner is enough; full-screen interruption is overbearing.

### 18.13 No labs yet

- **Labs tab:** Empty state per §18.2.
- **Home dashboard:** The "Recent lab insight" card is replaced by a quiet promotional card: "Upload your first lab report to start tracking your biomarkers over time." Forest text button.

### 18.14 No education assigned yet

- **Home dashboard:** The "Recommended reading" card simply doesn't appear. The dashboard restructures without it. (See §5 — modules are conditional.)
- **Education tab:** Shows the library directly with no "Assigned" section.

### 18.15 No consultation booked yet

- **Home dashboard:** The "Upcoming consultation" card is replaced by a CTA card: "Book a consultation — choose a focus area to begin." Saffron primary CTA. (This is one of the few Saffron primary CTAs in the entire product — earned because it's the next step in care.)
- **Consults tab:** Empty state per §18.2.

### 18.16 The rule that ties them together

Across every state, three things are constant:

1. **The product never apologises for the user's situation** (no "Sorry, you don't have any reports!"). It explains and offers.
2. **The product never panics.** Even the critical state is composed, specific, and has a named doctor.
3. **The visual identity is consistent.** Forest spine, Ivory background, DM Sans body, Cormorant for the few earned moments. A user navigating from Home (full) to Labs (empty) to a critical alert does not feel they've left the app.

---

## 19. Mobile vs web portal adaptation

The same Kyros design language must work across mobile app (primary), mobile web portal, and desktop web portal. The visual system, voice, and component anatomy do not change — but layout, density, and interaction patterns adapt.

### 19.1 What stays identical across platforms

- **Colour palette** — all 11 tokens, used per the same rules.
- **Typography** — DM Sans for body/UI, Cormorant Garamond for display moments. Type scale identical.
- **Voice & microcopy** — every label, button, error message reads the same. A patient should not feel they're using a different product.
- **Information architecture** — the same surfaces exist (Home, Consults, Labs, Plan, Profile). The same content lives in each.
- **Trust elements** — doctor names with NMC reg, three pillars, privacy footers, consent flows.
- **Component anatomy** — a biomarker row is a biomarker row everywhere. A doctor commentary card is a doctor commentary card everywhere.

### 19.2 What adapts per platform

| Element | Mobile app | Mobile web | Desktop web |
|---|---|---|---|
| Primary navigation | Bottom tab bar | Bottom tab bar | Left sidebar (fixed, 240px wide) |
| Screen-to-screen | Native push transitions | Page navigation (fast, no spinner) | In-place section swap (left rail stays) |
| Card layouts | Single column | Single column | 2 or 3 columns where dense (dashboard, labs list) |
| Lab report detail | Full-screen, scroll-heavy | Same as mobile app | Two-column: biomarker list left, chart + doctor commentary right |
| Chart interactions | Tap+drag with finger | Tap+drag with finger | Hover-to-scrub + keyboard arrows |
| Form inputs | Native keyboards (numeric for phone, etc.) | Browser inputs | Browser inputs + keyboard shortcuts for submit |
| Upload | Camera + photo library + PDF picker | Camera (if browser supports) + PDF picker | Drag-and-drop area + file picker + paste-from-clipboard |
| Print | Not supported (PDF export only) | Not supported (PDF export only) | Optimised print stylesheets for prescription and lab report |
| Multi-window | Single full-screen | Single browser tab | Multi-tab support; specific deep links per record |

### 19.3 Mobile app specifics

The mobile app is the primary surface. Considerations already covered:

- One-handed reachability (bottom tabs, primary CTAs in bottom third).
- Bottom sheets as the dominant disclosure pattern.
- Native push transitions for screen navigation.
- Platform haptics for primary button feedback only.
- Lock-screen-aware notification copy (privacy in public).
- Native camera for lab report capture.
- iOS Apple Health / Android Health Connect for data sync.
- Biometric auth (Face ID, Touch ID, fingerprint) as the default re-auth method after the initial OTP.

### 19.4 Mobile web specifics

The mobile web portal exists for:
- Users who haven't installed the app yet (e.g., link shared via WhatsApp by Kyros).
- Quick read-only access to a lab report or prescription from a desktop session redirected to mobile.
- International access (where the app may not be available).

It mirrors the mobile app's information architecture but with these adaptations:

- **No biometric auth.** OTP-only login.
- **No background notifications** (browser doesn't support reliable push). Reminders are visible in the app only when open.
- **No camera capture in some browsers.** Falls back to "Choose a PDF" / "Choose from gallery."
- **No Apple Health / Health Connect integration.** Manual entry only.
- **Persistent "Open in app" banner** at the top of the screen (dismissible) for users who have the app installed but landed on web — Forest tint, "Open Kyros in the app for the full experience," Forest text button.

The mobile web should be capable of every read action and most write actions; the app is necessary only for biometric auth, push notifications, and live video consultation.

### 19.5 Desktop web specifics

The desktop web portal is **the doctor-replacement surface for the patient at their desk** — used most often by:
- Working professionals reviewing their record between meetings.
- Older users who prefer a larger screen.
- Patients sharing a record with a non-Kyros doctor (printing / PDF download).
- Patients reviewing comparison lab reports across years (where the larger screen actually helps).

**Layout fundamentals:**

- **Left sidebar** (fixed, 240px wide, Forest 8% right border, Ivory bg) contains the 5 navigation items, with a small Kyros wordmark at the top and the user's name + a chevron-down menu at the bottom (containing Profile, sign out).
- **Main content area** is 760px to 1080px wide depending on viewport, centred with comfortable margins. Never edge-to-edge on a 1440px screen.
- **Right rail (contextual)** appears on certain surfaces (lab report detail, consultation detail) at 320px wide containing related info (doctor commentary, related lab reports, link to book follow-up). Optional, can be collapsed.

**Specific desktop adaptations per surface:**

- **Home:** Two-column layout below the welcome strip. Left column: upcoming consultation, recent lab insight, doctor commentary. Right column: today's plan, recommended reading. The trust footer spans full-width at the bottom.
- **Consults:** Three-column where helpful — left a date jumper (year, then month), middle the list of consultations, right the selected consultation detail (no need to navigate to a separate page).
- **Labs:** Same three-column pattern — filters on the left, list of reports in the middle, selected report's biomarker overview on the right. Tapping a biomarker takes the right pane to that biomarker's trend chart.
- **Prescriptions:** Single full-width view. The prescription detail is best as a full document layout — it should look like a paper prescription on screen.
- **Plan:** Two-column. Left: today's reminders. Right: the active medications list with timeline view.
- **Profile:** Single column, narrow (max 640px). Profile is a settings surface; multi-column adds noise.

### 19.6 Hover behaviour on desktop

Hover is a real interaction on desktop, but the product uses it sparingly:

- **Cards:** Subtle hover state — Forest 4% bg shift over 120ms ease-out. No translate-up, no shadow-grow.
- **Buttons:** Slight darken (Forest button → 5% darker) over 120ms.
- **Text links:** Underline appears on hover (the default style is no underline; underline indicates "this is interactive right now").
- **Biomarker rows:** Slight Forest 4% bg shift on hover indicates the row is tappable.
- **Tooltips:** Used for icon-only buttons (e.g., the lab download icon on a list row). Forest fill, Ivory text, appears after 500ms hover, dismisses on mouse-leave. Brief — one or two words ("Download PDF").

What hover is NOT used for: revealing critical information that should always be visible. If a user needs to hover to find something important, the design is wrong.

### 19.7 Drag-and-drop for upload (desktop)

The desktop lab upload supports drag-and-drop as the primary interaction:

- **Default state:** A dashed Forest 2px-stroke rounded rectangle (300×200px on the upload page) with Lucide UploadCloud icon centred and DM Sans 16px Ink "Drag a file here or click to browse" text.
- **Drag-over state:** Border becomes solid Forest, background becomes Saffron 4% tint, text changes to "Drop to upload."
- **Drop:** File begins uploading immediately. Same OCR processing pipeline as mobile.

### 19.8 Print stylesheets

The web portal supports print for two surfaces:

- **Prescription:** A clean print layout — Kyros header (logo + NMC of clinic + GST), patient block, doctor block (name, NMC, signature placeholder), medication list, instructions, footer with Kyros contact. Black-on-white print. Avoids printing the entire chrome of the web portal.
- **Lab report:** Similar — clinic header, patient block, doctor block, biomarker table, doctor commentary, footer. Charts are printed as static SVG (no interactive elements). 

Both print views use specific CSS print stylesheets that hide the sidebar, navigation, and all interactive controls. The patient should be able to walk into a non-Kyros doctor's office with a printed Kyros document that looks professional.

### 19.9 Keyboard accessibility on web

Beyond the obvious tab-order and focus-ring (Forest 2px outline 2px offset), the desktop web portal supports useful keyboard shortcuts for power users:

- **/** (slash): Focus the search field on Labs or Education.
- **Esc:** Close any open sheet, modal, or dropdown.
- **Enter:** Activate the focused button.
- **Arrow keys:** Navigate between rows in lists; navigate the chart's data points when the chart is focused.
- **Cmd/Ctrl + P:** Print the current view (works only on print-eligible views).
- **Cmd/Ctrl + D:** Download the current PDF (lab report, prescription).

Shortcuts are documented in Profile → Keyboard shortcuts (a quiet, helpful screen for the users who want it).

### 19.10 Chart interaction differences

- **Mobile:** Tap+drag on the chart with a finger. Vertical Stone line follows the finger; callout shows date and value above.
- **Desktop:** Hover to scrub. Same vertical line follows the cursor. Click + drag selects a range (for advanced users who want to zoom into a specific period).
- **Keyboard on desktop:** When the chart is focused (tab into it), left/right arrows step through data points. Each step announces the date and value via aria-live for screen readers.

### 19.11 Larger-screen information density

Desktop has more pixels but does NOT use them to add more visual noise. The density rule is:

- **Whitespace expands** at larger sizes — the main content column does not stretch beyond 1080px even on a 1920px display. Margins absorb the excess.
- **More information becomes simultaneously visible** (e.g., the biomarker row's full inline detail can be visible without expansion on desktop), but the type sizes do not shrink.
- **Two-column layouts replace progressive disclosure** where appropriate. On mobile, tapping a consultation opens it as a new screen. On desktop, the consultation detail appears in the right pane while the list remains visible on the left.

### 19.12 What does NOT get added on desktop

A common temptation: "We have more screen real estate, let's add a fitness tracker widget / a wellness score / a community feed." None of these belong. The desktop surface is the same product, made comfortable for a larger screen. It is not an opportunity to add features that have no place on mobile.

The desktop dashboard is not denser than the mobile dashboard in terms of content. It is denser only in terms of simultaneous visibility (more cards visible at once because the screen is bigger). The cards themselves are the same cards.

---

## 20. Top recommendations & non-negotiables

### 20.1 The 10 most important design principles for Kyros

1. **Premium-warm clinical — and the order of those words is the order of importance.** Premium first (composure, restraint), warm second (Ivory base, Saffron accents, Cormorant moments), clinical third (Forest spine, named doctors, NMC visibility, real data hierarchy).
2. **One doctor, one place, one platform.** Every surface should reinforce continuity — the same doctor, the same record, the same private space. Never imply the patient is being handed between strangers.
3. **The doctor is the protagonist, the product is the room.** When the doctor speaks (commentary, prescription, note), the product steps back. The Cormorant treatment, the Saffron border, the named NMC — all of these exist to make the doctor's voice land. The system never tries to compete.
4. **Use Saffron and Terracotta the way a chef uses salt.** Three to five Saffron moments per screen, one Terracotta at most. They make the dish; they do not become the dish.
5. **Specific calm beats generic reassurance.** "Dr Mehra is running about 8 minutes behind" is calmer than "Doctor running late — please wait." Specificity is the trust-builder.
6. **The dashboard is continuity of care, not a widget dump.** Every module on Home answers the question "what does this patient need to do or know now?" — not "what could we possibly show them?"
7. **Labs are the flagship surface.** This is where Kyros earns its premium. The biomarker row, the trend chart, the doctor commentary cluster — these are the Apple-Health-grade interactions that define the product.
8. **Healthcare composure means no celebration theatre.** No confetti, no streaks, no badges. Marked-as-taken is a Sage colour shift, not a fireworks display.
9. **Privacy is visible at five points** — signup, consent moments, the Home trust footer, the Profile section, and every sensitive data touchpoint. Visibility builds the trust; burying privacy controls breaks it.
10. **The product never invents medical advice.** Every clinical statement, plan, dose, or interpretation is attributed to a named, NMC-registered doctor. The system surfaces; the doctor advises. This is non-negotiable.

### 20.2 The 10 most common design mistakes Kyros must avoid

1. **Wellness-aesthetic drift.** Pastels, gradients, mandalas, paisley, "ancient wisdom" iconography, lifestyle photography of women in athleisure or men with kettlebells. The product is a clinic, not a wellness brand.
2. **Hospital-cold drift in the other direction.** All Forest, no Ivory, no Cormorant, no Saffron warmth — the product becomes a database front-end. Kyros's lane is warmer than that.
3. **Saffron as a page fill.** Saffron is a punctuation colour. The moment a screen is majority-Saffron, the product reads as a takeaway-food app.
4. **Cormorant in dense surfaces.** Cormorant on a biomarker value, on a tab label, on a form field — reads as decorative serif inflation. Cormorant is reserved.
5. **Red as the colour of caution.** Reserve Alert for true clinical concern (potassium >6, hgb <7, similar). Saffron handles "slightly off" and Terracotta handles "out of range." A product that goes Alert at every slight deviation desensitises the user when something is actually critical.
6. **Gamification of adherence.** Streaks, badges, "you're on a 7-day roll!" Patients with chronic illness already feel the weight of their compliance; gamifying it adds shame, not motivation.
7. **Confetti, haptic celebrations, bounce animations.** Healthcare composure. These are banned outright.
8. **Stock smiling-doctor photography.** Real doctors only. White-coat-with-stethoscope is the visual signal of a fake clinic, not a real one.
9. **"Friendly" microcopy.** "Oops!" "No worries!" "We've got you!" None of this lives in the Kyros product. The voice is composed-warm, not coach-cute.
10. **Buried privacy controls.** If a patient can't find "Delete my account" or "Withdraw a consent" in fewer than three taps from Profile, the product has failed its trust contract under the DPDP Act and under the brand promise.

### 20.3 Recommended visual hierarchy model for the app

A three-tier hierarchy applies to every screen:

**Tier 1 — Spine (Forest, Ink, DM Sans semibold 16–18px).** The structural skeleton: navigation, screen titles, primary CTAs, card titles, body text. This is the 60% of every screen. It is composed and clinical.

**Tier 2 — Warmth (Ivory, Peach Mist, Cormorant, Saffron edges, Terracotta accents).** The 40% that makes the product feel like Kyros and not a generic SaaS clinical tool. Welcome strips, doctor commentary cards, three-pillar moments, gentle section tints.

**Tier 3 — Earned moments (Cormorant pull-quotes, Saffron CTAs, line-drawn anatomical reveals).** The deliberate, motion-staged, attention-rewarding moments. There are 3–5 of these per screen at most. Cormorant pull-quote on doctor commentary; Saffron primary CTA when next step in care; the chart line drawing in on first paint. These are the moments the user remembers.

If any of the three tiers is missing on a screen, the screen is incomplete. Spine alone is a hospital app. Warmth alone is a wellness app. Earned moments alone is a marketing site. All three is Kyros.

### 20.4 Recommended MVP screen set

To launch the product, these screens must exist and be production-grade. Anything beyond is incremental:

**Auth & onboarding (8 screens):**
1. Splash
2. Login (mobile + OTP)
3. OTP entry
4. Welcome / three-pillar intro
5. Focus area selection (vertical chooser)
6. Intake — basic profile (DOB, sex assigned at birth, location)
7. Consent screen
8. Intake — vertical-specific questions (collapsed to a single screen with conditional questions per vertical for MVP)

**Home dashboard (1 screen, with conditional modules):**
9. Home (welcome strip + conditional modules — empty state, partial state, full state all rendered from the same template)

**Consultations (4 screens):**
10. Consults list (Upcoming / Past)
11. Book consultation — vertical select (subset of step 5; can be reused)
12. Book consultation — slot picker
13. Consultation detail (upcoming / completed states)

**Labs (5 screens):**
14. Labs list
15. Upload sheet (lives as a sheet, not a screen — but counts as a distinct surface)
16. Lab report detail
17. Biomarker trend chart
18. OCR correction surface

**Prescriptions (2 screens):**
19. Prescriptions list (Active / Past)
20. Prescription detail

**Plan / Reminders (2 screens):**
21. Plan (today + medications)
22. Reminder detail (history of a single medication including dose timeline)

**Education (2 screens):**
23. Education library
24. Article reader

**Profile (5 screens):**
25. Profile main
26. Privacy & data (the meta-list of privacy actions)
27. My consents
28. Linked devices
29. About Kyros

**Edge & system states** are not screens per se — they are states of the screens above. They must all be designed (every state from §18) but they don't add screen count.

**29 distinct screens** is the production MVP. Three video consultation surfaces (waiting room, in-call, post-call) are technically additional screens but they live within the consultation detail flow.

### 20.5 The flagship "wow-but-calm" dashboard concept

The Kyros dashboard, at full-state for a returning patient with active care, in one paragraph:

> Open the app. A 60ms tap and the Home tab is live. The welcome strip says "Good morning, Niranjan" in DM Sans 18px Ink on Peach Mist, a single line, no greeting theatre. Below it, a White card with a Saffron 2px left border: "Tuesday, 3:00 PM with Dr Anjali Mehra — Thyroid & metabolic health. NMC 47829." A small Lucide chevron and "View details" on the right. Below that, on Ivory: "Your latest report — TSH is trending down. View biomarkers." The TSH word is underlined; a small Sage 8px dot signals in-range improvement. Below that, the doctor commentary card — White, Saffron 2px left border, Cormorant Garamond 20px italic Forest: *"You're responding well to the dose increase. Let's review your labs together on Tuesday."* Below the commentary, a quiet White card: "Today: Levothyroxine 50mcg at 8:00 AM — Taken." The Taken chip is Sage. Below that: a Recommended Reading card with one article — "Why TSH fluctuates with the seasons" — reviewed by Dr Mehra, NMC reg visible, 4 minutes. At the very bottom, a footer in 12px Stone: "Encrypted. DPDP-compliant. Doctor-led." Tap the Trust line and a sheet opens explaining what each word means.

That's the dashboard. Five cards, one welcome strip, one trust footer. Every word earns its place. The Cormorant pull-quote is the one earned moment. The Saffron borders are the punctuation. The Forest spine carries everything else. The patient feels seen by their doctor, oriented toward their day, and held by their record — all in three seconds of looking at the screen.

### 20.6 The flagship labs experience concept

The lab report detail screen, for a returning patient opening a new report:

> The screen loads instantly with a skeleton — five biomarker rows, a header, a commentary placeholder. Within 220ms the real content swaps in. The header: "Hormone & metabolic panel — uploaded 12 Nov 2025 from SRL Diagnostics, Hyderabad." Below: a summary chip cluster — "1 critical, 2 out of range, 8 slightly off, 9 in range" — each chip the colour of its tier, Alert / Terracotta / Saffron / Sage. Tap any chip to filter the rows below. The rows are the biomarker row anatomy: status bar on left edge, label and reference range, value in DM Sans 22px Tabular Forest semibold on the right. The TSH row at the top: Saffron 4px left edge, "TSH" label, "Reference 0.4–4.5 mIU/L" below, "6.8 mIU/L" on the right with a small Stone arrow indicating up vs the last reading. Tap the row, it expands inline: a mini-trend (last 5 values), one sentence of doctor commentary ("Higher than last month — likely a dose adjustment is needed; we'll discuss Tuesday"), and a "View full chart" Forest text button. Tap the full chart: a screen-filling biomarker trend, Sage reference range band, Forest 2px line drawing in over 1200ms from left to right, Forest dots fading in with 50ms stagger, the most recent point's tap-target highlighted. A 7d/30d/90d/1y/All segmented control above. The user taps 1y — the line redraws at 220ms with a fade-crossover. They drag their finger across the chart — a Stone vertical line follows, a callout above shows "8 Aug 2025 — 4.2 mIU/L." They lift their finger, the callout stays for 1500ms then fades. Below the chart, a Doctor Commentary card with the Saffron left border and a Cormorant pull-quote: *"This is the kind of trajectory I like to see — your body is responding."* The patient reads that and feels held. That is the labs experience.

This is where Kyros earns its position. Every other clinic surfaces lab reports as PDFs. Kyros surfaces them as a living conversation between the patient, their body, and their doctor — with the doctor's voice arriving at the exact moment it's needed.

### 20.7 Interaction philosophy in one paragraph

Kyros responds the way a thoughtful, composed person responds — quickly to what you ask, slowly to what it has to say. Buttons activate the instant your thumb presses. Tabs switch without lag. But when the chart line draws in for the first time, it takes 1200ms because it has something to show you. When the doctor's words appear in Cormorant italic, they fade up over 600ms because they deserve attention. Sheets open and close at 220ms because they are conversations, not announcements. Numbers count up over 800ms because they are quantities, not labels. Reduced-motion users get the same product without the theatre. Nothing bounces, nothing celebrates, nothing performs — every motion either acknowledges what the user did or stages what the system wants the user to notice. Composure is the through-line: the product is fast where speed serves the user and slow where slowness serves the meaning.

### 20.8 Practical handoff note for designers and frontend engineers

**For product designers:**

- Open the Figma library before designing any new screen. The 11 colour tokens, the type ramp, the component anatomy, the border-radius and elevation tokens — they're all there. Do not introduce new tokens. If a screen seems to need a new colour or a new radius, the screen is wrong, not the system.
- Design with the 60/40 ratio in mind: pixel-area-wise, the screen should be ~60% Ivory/White (the spine) and ~40% Peach Mist + Saffron-edged + Cormorant moments (the warmth). Test by squinting at a low-fidelity mock; if the warmth is invisible, add an earned moment. If the warmth is overwhelming, you've designed a marketing surface.
- Every screen needs at least one trust signal — a doctor's name with NMC reg, a privacy line, a doctor's note, or the trust footer. Trust is not a feature; it's a presence on every surface.
- Design every state for every screen — empty, loading, partial, error, critical, success. The state coverage matrix is part of the deliverable; "I'll figure out the error state later" is not acceptable in healthcare.
- Microcopy is part of the design. Do not hand off "[Error message]" as a placeholder. Write the exact words. The microcopy register is in §15 of this document.

**For frontend engineers:**

- The 11 tokens are CSS variables (`--forest`, `--ivory`, `--saffron`, `--peach-mist`, `--sage`, `--terracotta`, `--white`, `--ink`, `--stone`, `--alert`, `--jade`). Do not introduce new colour variables. If a Tailwind config or styled-components theme has more than 11 colours, fail the PR.
- Use `tabular-nums` for every numeric value in the product (lab values, dates, times, durations, dose counts, currency). The CSS is `font-variant-numeric: tabular-nums;`. This is a one-line change that prevents jittery layouts.
- The motion tokens (120ms, 220ms, 450ms, 600ms, 800ms, 1200ms, 1800ms) are CSS variables. Use them. A `transition: opacity 0.3s` in a PR should fail review — the closest token is 220ms or 450ms.
- Respect `prefers-reduced-motion: reduce` strictly. The entire app should have a single `@media (prefers-reduced-motion: reduce)` block that resets every transition duration to 0ms (except for indeterminate spinners, which remain). Test the entire app with reduced motion enabled.
- Accessibility is non-negotiable: tab order, focus rings, aria-labels, aria-live regions, semantic HTML headings. The desktop web portal especially must be keyboard-navigable end-to-end.
- Skeleton placeholders do not shimmer. Implement them as static Stone 8% blocks. The shimmer effect is a wellness/SaaS reflex; we explicitly do not want it.
- The biomarker chart is the most performance-sensitive component. Use SVG (not Canvas) so accessibility and print rendering work for free. The line-draw animation is `stroke-dasharray` + `stroke-dashoffset` transition over 1200ms — a 6-line CSS recipe.
- The print stylesheets for prescription and lab report are real CSS files. Test them by actually printing the page (or saving to PDF) — they should look like professional medical documents on plain white paper.
- Every form field has a corresponding state for: empty, focused, valid, invalid, disabled, loading-submission. Don't ship a field with three states and call it done.
- The DPDP-mandated user rights (download my data, delete my account, my consents, withdraw consent) are not optional. They are wired to real backend endpoints and have real timelines (24 hours for data export, 30 days for deletion grace). The frontend surfaces these honestly; do not show fake completion progress.

**For both:**

- The locked brand system is the spec. When in doubt, refer to the Kyros design system skill — not to general UX best-practice articles, not to other healthcare apps, not to "what other apps do." The Kyros lane is specific and deliberate; preserving it is the work.
- Read every doctor commentary card you ship out loud. If it sounds like marketing, rewrite it. If it sounds like a doctor, ship it.
- When something seems too plain — a quiet card, an unanimated success, a simple toast — that is usually correct. The product earns its premium not by adding visual flourish but by removing everything that isn't necessary, then composing what remains with care.

---

## Closing note

This document defines the visual and interaction operating system of Kyros Clinic. It is opinionated by design — not because the alternatives are wrong in every context, but because *they would be wrong here*. Kyros sits in a specific lane: premium-warm-clinical, doctor-led, longitudinally-attentive, privacy-visible, India-specific. Everything in this document descends from that positioning.

Use it as a working spec. Update it when the product teaches you something new. But before deviating from any locked element — the 11 colour tokens, the typography pairing, the 60/40 ratio, the motion register, the doctor-first attribution, the privacy-by-default microcopy — write down why. If the reason holds up against the three pillars ("One doctor, who knows your story. One place, where your health lives. One platform, where privacy is the point."), update the system. If it doesn't, the current system stays.

The product the patient opens at 7am to check their TSH trend, at 8am to mark their levothyroxine as taken, at 3pm to join their consultation, and at 11pm to read the article their doctor recommended — that product is the same product, composed across the day, attentive at every moment, and quietly, deliberately, premium.

That's the work. Build it carefully.
