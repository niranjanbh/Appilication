---
name: kyros-clinical-compliance
description: Clinical compliance rules and regulatory context for the Kyros platform.
---
---
name: kyros-clinical-compliance
description: The single canonical home for ALL Kyros regulatory rules, vocabulary, clinical facts, and the doctor approval gate. Use this skill whenever producing, reviewing, or editing content that touches medical claims, symptoms, conditions, diagnostics, treatments, or patient communication — anywhere "is this line legally publishable" applies. Other skills reference operational facts from here (doctor sign-off required, RMP must be NMC-registered) but do NOT restate the regulatory rationale. This is also the single home for the cloned founder voice policy and per-vertical clinical facts.
sequence: 2 of 5 skills — read AFTER kyros-business-strategy
---

# Kyros Clinical Compliance

This skill is the **single source of truth** for what Kyros can and cannot say under Indian law, the doctor approval workflow that gates every clinical claim, the cloned founder voice policy with its documented risk, and the verified clinical facts that every other skill draws on.

**Isolation policy:** Other skills may reference operational facts from this skill ("this content needs doctor sign-off", "RMP must be NMC-registered", "use approved vocabulary per clinical-compliance") but do NOT restate the regulatory rationale or duplicate the rule lists below. The regulatory why lives here. The operational what lives in the consuming skills.

## Skill Read Order

1. kyros-business-strategy — positioning, model, unit economics
2. **kyros-clinical-compliance** (this file)
3. kyros-design-system — visual register, production stack
4. kyros-customer-acquisition — D2C channel mix
5. kyros-b2b2c-partnerships — B2B partnership playbook
6. kyros-build-spec (product spec) — technical architecture + Claude Code prompts P1–P30
---

## Hard Stops (Non-Negotiable)

Before reading anything else in this file, internalize these. Every other rule is an elaboration of one of these:

1. **No before/after imagery.** Any condition. Any framing. DMR Act + ASCI.
2. **No fabricated patient testimonials, names, ratings, or outcomes.** Including "users say" framings.
3. **No specific medication brand names** in public content (Mounjaro, Wegovy, Cialis, Viagra). Generic/INN molecule names allowed in educational mechanism framing only, doctor-attributed.
4. **No dosage information** in public content. Schedule H/J prohibition.
5. **No "cure," "reverse," "guarantee," "miracle," "FDA-approved," "natural alternative"** in any vertical.
6. **No engagement-bait questions** ("Comment below if this is you 👇") or fear-based hooks ("the silent killer in your kitchen").
7. **No clinical content without RMP credit on screen.** Pinned-comment credits don't count. Description credits don't count. On-screen at the start, prominent.
8. **No cloned founder face delivering clinical content.** Even with doctor credit. ASCI virtual influencer rule.
9. **Cloned founder VOICE is permitted only for non-clinical brand storytelling.** Clinical content uses the "Kyros Clinical Editor" generic voice + doctor sign-off + AI voice disclosure. See Cloned Voice Policy section below for full rationale.
10. **No music in clinical content.** Voiceover only. Warmth comes from color and pace, not soundtrack.
11. **No "treatment for [condition]" promotional framing** as headline or hook. Use "what your doctor evaluates for [condition]" or "the pathway for [condition]."
12. **No promises of specific symptom resolution timelines.** "Feel better in 14 days" is an outcome guarantee.
13. **No advisory board members or doctors named who haven't publicly committed in writing.**
14. **No Twitter/X account openings** at this phase. Revisit at Phase 2.
---

## The Doctor Approval Gate

Every public-facing clinical claim — every condition page, every social post mentioning a condition or treatment, every video script, every email touching mechanism — passes through one workflow:

```
Draft → Vocabulary check → RMP sign-off → AI disclosure check → Publish
```

**Roles:**
- **Drafter:** content creator (writer, designer, founder). Uses approved vocabulary; reads this file before drafting.
- **Reviewer:** NMC-registered RMP on Kyros panel with specialty match for the vertical. Reviews clinical accuracy, signs off in writing (Slack message, email, signed PDF, doctor portal approval — any of these works as long as the doctor is real and the sign-off is recorded).
- **Publisher:** founder or coordinator. Publishes only after reviewer sign-off is recorded.
  **Audit log:** every published clinical asset stores reviewer name, NMC reg number, sign-off timestamp, asset URL. Build-spec lays this out at the database level (`ad_consent_records` and `kc_doctor_notes` patterns).

**No shortcuts.** If volume pressure tempts a shortcut on doctor review, cut volume. Never shortcut review. This is the single point of regulatory failure most likely to bring an ASCI complaint or an NMC inquiry, and both are existential at Kyros's scale.
 
---

## Regulatory Framework Map

Five binding instruments. Each is summarized below with operational implications.

### 1. Drugs and Magic Remedies (Objectionable Advertisements) Act 1954

**What it prohibits:** advertising any drug as treatment/prevention/cure for the diseases enumerated in the Schedule to the Act and in Rule 6 of the DMR Rules 1955.

**Why it matters:** Six of Kyros's seven verticals contain DMR-listed conditions. Casually-worded content can violate without anyone intending to.

**Operational rule:** never advertise a drug or molecule by name as treatment/prevention/cure for any DMR-listed condition. Use mechanism framing under doctor attribution instead.

### 2. Schedule J of the Drugs and Cosmetics Rules 1945

Per G.S.R. 21(E) dated 11 January 1996, Schedule J prohibits any drug from claiming to prevent or cure 51 specific diseases. Rule 106 of the D&C Rules states:

> *"No drug may purport or claim to prevent or cure or may convey to the intending user thereof any idea that it may prevent or cure, one or more of the diseases or ailments specified in Schedule J."*

**The full 51-entry list:**

| # | Disease / Ailment |
|---|---|
| 1 | AIDS |
| 2 | Angina pectoris |
| 3 | Appendicitis |
| 4 | Arteriosclerosis |
| 5 | Baldness |
| 6 | Blindness |
| 7 | Bronchial asthma |
| 8 | Cancer and benign tumours |
| 9 | Cataract |
| 10 | Change in colour of the hair and growth of new hair |
| 11 | Change of foetal sex by drugs |
| 12 | Congenital malformations |
| 13 | Deafness |
| 14 | Diabetes |
| 15 | Diseases and disorders of uterus |
| 16 | Encephalitis |
| 17 | Epileptic fits and psychiatric disorders |
| 18 | Erysipelas |
| 19 | Fairness of the skin |
| 20 | Form, structure of breast |
| 21 | Gangrene |
| 22 | Genetic disorders |
| 23 | Goitre |
| 24 | Glaucoma |
| 25 | Hernia |
| 26 | High/Low Blood Pressure |
| 27 | Hydrocele |
| 28 | Insanity |
| 29 | Increase in brain capacity and improvement of memory |
| 30 | Improvement in size and shape of the sexual organ and in duration of sexual performance |
| 31 | Improvement in the strength of the natural teeth |
| 32 | Improvement in vision |
| 33 | Jaundice/Hepatitis/Liver disorders |
| 34 | Leukaemia |
| 35 | Leucoderma |
| 36 | Maintenance or improvement of the capacity of the human being for sexual pleasure |
| 37 | Mental retardation, subnormalities and growth |
| 38 | Myocardial infarction |
| 39 | Obesity |
| 40 | Paralysis |
| 41 | Parkinsonism |
| 42 | Plague |
| 43 | Power to rejuvinate |
| 44 | Premature ageing |
| 45 | Premature greying of hair |
| 46 | Rheumatic Heart diseases |
| 47 | Sexual impotence, premature ejaculation, spermatorrhoea |
| 48 | Stammering |
| 49 | Stones in gall-bladder, kidney and bladder |
| 50 | Tuberculosis |
| 51 | Varicose veins |

**Vertical-by-vertical implications:**

| Kyros Vertical | Schedule J Entries That Apply | Practical Constraint |
|---|---|---|
| **Thyroid** | Only #23 "Goitre" | **Highest legal headroom.** Hypothyroidism/hyperthyroidism/Hashimoto's are NOT enumerated. Drug cure claims for visible goitre are prohibited, but most thyroid content discusses TSH/T3/T4/anti-TPO and lifestyle/medication management — fully permissible under doctor attribution. **This is why thyroid is the launch flagship.** |
| **Weight management** | #39 "Obesity" | Cannot claim any drug cures or prevents obesity. GLP-1 mechanism education permitted as doctor-attributed clinical explanation; specific brand promotion prohibited. Frame as "what your doctor evaluates," never "GLP-1s are changing weight loss." |
| **PCOS** | #15 "Diseases and disorders of uterus" | Cannot claim any drug cures PCOS. Lifestyle and metformin mechanism content permitted under doctor attribution. Frame as "managing PCOS," never "reversing PCOS." |
| **Skin & hair** | #5 "Baldness", #10 "Hair growth", #19 "Fairness of skin", #45 "Premature greying" | Cannot claim any drug regrows hair, cures baldness, or restores hair color. Minoxidil/finasteride mechanism content permitted under doctor attribution. |
| **Men's intimate** | #30 "Sexual organ size/shape/duration", #36 "Sexual pleasure capacity", #47 "Sexual impotence, PE, spermatorrhoea" | **Highest regulatory-risk vertical.** Every entry applies. ED/PE content must be educational under doctor attribution; no drug promotion; no outcome claims. |
| **Hormones / TRT** | #43 "Power to rejuvinate", #44 "Premature ageing" | Cannot claim TRT rejuvenates or reverses aging. Hypogonadism diagnosis + supervised TRT framed as endocrine medicine, not anti-aging. |
| **Longevity** | #43 "Power to rejuvinate", #44 "Premature ageing" | Cannot promise life extension or "anti-aging" outcomes. Frame as cardiometabolic risk reduction + biomarker management under doctor attribution. |

### 3. NMC Telemedicine Practice Guidelines 2020

Issued by the Board of Governors in supersession of MCI, 25 March 2020. Binding on every NMC-registered RMP delivering telemedicine.

**Key clauses:**

**Clause 3.7.1.4 (verbatim):** *"RMPs are not permitted to solicit patients for telemedicine through any advertisements or inducements."*

**Practical implication for Kyros:** doctors named or pictured in promotional content carry exposure on their own NMC license. The mitigation pattern: doctor appears as institutional voice ("Kyros's Medical Director, Dr. X") not personal solicitor ("Book with me!"). The brand solicits patients; the doctor does not.

**Clause 3.6.4 (verbatim):** *"An RMP providing consultation via telemedicine cannot prescribe medicines [in Schedule X]. These medicines have a high potential of abuse and could harm the patient or the society at large if used improperly. Medicines listed in Schedule X of Drug and Cosmetic Act and Rules or any Narcotic and Psychotropic substance listed in the Narcotic Drugs and Psychotropic Substances, Act, 1985."*

**Practical implication:** testosterone is Schedule H (NOT Schedule X) — can be prescribed via telemedicine subject to List A/B mode-of-consultation constraints. Anabolic steroids and most controlled performance hormones are off the table via telemedicine. The TRT vertical must be honest: hypogonadism management within Schedule H, not the "performance" framing grey-market clinics use.

**Drug categorization (operational):**
- **List O:** safe OTC drugs — prescribable at any consultation mode
- **List A:** prescribable after first video consultation
- **List B:** follow-up refills only (not new prescriptions via telemedicine)
- **Prohibited:** Schedule X + NDPS substances
  **AI disclosure:** Clause 3.5 prohibits AI from independently counseling patients or prescribing. AI may assist a doctor; clinical judgment must reside with the human RMP. Any AI-generated content surfacing to a patient must disclose AI involvement.

### 4. ASCI Influencer Guidelines Addendum 2 (effective 17 August 2023; clarified 7 April 2025)

**Verbatim:** *"For posts related to health and nutrition, the influencer must have relevant qualifications such as a medical degree, or be a certified nurse, nutritionist, dietician, physiotherapist, psychologist etc. depending on the specific advice being given."*

ASCI CEO Manisha Kapoor (April 28, 2025 press release): *"Influencer marketing has matured beyond simple endorsements and now often involves strategic partnerships for various aspects of brand communication. The updated guidelines bring in the required nuance for influencers operating in the BFSI and Health & Nutrition space."*

**Practical implication:** influencers offering "advice on prevention, treatment, cure, or remedies for medical conditions must be certified professionals." Kyros has a **structural advantage** — every clinical claim flows through an RMP — but only if the doctor's qualification + NMC registration number is displayed prominently on every piece of clinical content. This locks out supplement-D2C competitors who don't have RMPs.

**Disclosure rules:** "Ad" / "Sponsored" / "Partnership" tag on paid promotion. Founder posting about Kyros is not an ad (it's the founder); founder posting about a partner is an ad and must disclose.

### 5. DPDP Act 2023 + Draft Rules 2025

**Operational requirements:**
- **Explicit consent** required for collecting and using patient health data. Blanket or implied consent invalid.
- **DPO (Data Protection Officer)** must be designated. For Kyros at launch scale, this can be the founder doubling as DPO with documented role description.
- **DPIA (Data Protection Impact Assessment)** mandatory for high-risk activities — health data qualifies as high-risk.
- **Breach reporting:** 72-hour window to Data Protection Board after detection.
- **Cross-border transfer:** patient health data cannot leave India without explicit informed consent. Affects every tech vendor choice. (Build-spec locks ap-south-1 residency.)
- **End-to-end encryption** for video consultations.
- **Data principal rights:** access, correction, erasure, grievance redressal — all surfaced as first-class actions in patient app/web.
  **Vendor implications:**
- **ElevenLabs voice cloning:** voice clone metadata processed cross-border. Mitigation: patient identifiers (name, condition, doctor name) never sent with voice synthesis requests. Voice clone is the founder's voice, not patient-attributable.
- **Google Document AI for OCR:** data residency configurable to ap-south-1. Set this explicitly during onboarding.
- **100ms for video:** Indian-origin provider with India-region data residency. Configured to ap-south-1 storage and processing.
---

## Cloned Founder Voice Policy

**Locked at user direction over flagged compliance risk.** This policy documents the risk in writing and the mitigation pattern. No shortcuts.

### Scope of cloned voice use

**Permitted:**
- Brand storytelling (why Kyros exists, founder narrative, company values)
- Non-clinical educational framing (how telehealth works, what to expect from a consultation flow)
- Process explainers (how to book, how the dashboard works, what's in the pre-consultation report)
  **Prohibited:**
- Any clinical claim (mechanism, treatment, dosage, prognosis, contraindication)
- Any condition-specific medical guidance
- Any face cloning — ASCI virtual influencer rule. Cloned-face delivery of clinical content is hard prohibited even with doctor credit.
### Clinical content voice protocol

For clinical content, use the **"Kyros Clinical Editor"** voice — a generic, professional, gender-neutral synthesized voice not modeled on the founder. The Clinical Editor voice:

- Is not associated with a real person
- Cannot be confused with founder personal solicitation
- Carries no NMC license exposure (it's not an RMP)
- Must still display the reviewing doctor's NMC registration number on-screen
### AI disclosure

Every piece using either cloned founder voice OR Kyros Clinical Editor voice must carry on-screen disclosure: **"AI voice"** or **"AI-generated voice"** in the first 3 seconds, visible for the duration of the asset. Captions or description-only disclosure does not count.

### Documented risk

The cloned founder voice policy carries documented legal exposure under:
- **NMC TPG 2020 Clause 3.7.1.4** (no RMP solicitation): mitigated because cloned voice is the founder (not an RMP), and clinical voice is the Kyros Clinical Editor (not a real person).
- **ASCI Addendum 2 qualification requirement:** mitigated because every clinical asset still gates through doctor approval; the voice is delivery, the clinical content traces to a qualified RMP.
- **IT Act §79 safe harbour:** Kyros operates as intermediary; cloned voice usage with disclosure does not forfeit safe harbour.
  **Required before launch:** written sign-off from a media-law counsel familiar with NMC + ASCI confirming the mitigation pattern is sufficient. This letter must exist before any cloned-voice asset publishes.

---

## Approved Vocabulary

### Use freely

Treatment plan, personalised protocol, certified doctor, clinically appropriate care, doctor-guided, evidence-based, health assessment, manage your condition, feel like yourself again, reclaim your energy, private consultation, discreet delivery, in your language, NMC-registered doctor, pathway, evaluation, what your doctor checks, supervised therapy, supervised initiation, mechanism, biomarker, baseline, titration, monitoring, longitudinal, ongoing care.

### Use in cinematic register only (hooks and closes, not body copy)

Boost, optimize, enhance, unlock. Permitted in hook and close moments where the visual register is warm-restrained (ivory or peach-mist field, saffron or terracotta single accent, single-line typography). Banned in plain-clinical body copy and in any register drifting toward D2C-health vocabulary or wellness-aesthetic framing.

### Hard-banned (any context)

| Word/Phrase | Why |
|---|---|
| Cure, reverse, eliminate, defeat | DMR Act + Schedule J — categorical disease-cure prohibition |
| Guaranteed, proven to treat, FDA-approved | DMR Act misleading-claim provisions |
| Quick fix, fast results, X kg in Y weeks | Outcome timing guarantee |
| Pill machine, prescription guaranteed | Schedule H/J + NMC TPG |
| Cure your PCOS, reverse your diabetes, regrow your hair, boost testosterone naturally | Schedule J explicit prohibitions per vertical |
| Drug, medicine, pill, injection (in promotional context) | Schedule H restrictions on public drug advertising |
| Specific brand names: Mounjaro, Wegovy, Cialis, Viagra, Saxenda, Liraglutide-Sun, etc. | Drug brand advertising prohibition |
| Anonymous (when referring to patient care) | Use "private" or "discreet" — DPDP requires identifiability for consent |
| Treatment for [condition] as headline | DMR Act framing prohibition |
| Wellness-aesthetic terms: holistic journey, ancient wisdom, natural healing, balance your chakras, root-cause cleanse, body-mind harmony | Lane drift — these read as wellness-aesthetic regardless of visual register |

### CTAs to use

- "Tell us a few basics"
- "Talk to a doctor"
- "Take the [condition] assessment"
- "See if treatment is right for you"
- "Talk to a specialist directly"
- "Browse conditions"
- "Start with a conversation"
- "Begin with a doctor"
### CTAs to avoid

- "Get your prescription"
- "Buy treatment now"
- "Order medicines"
- "Start your [drug name]"
- "Same-day prescription"
- "Add to cart"
- "Shop now"
---

## Clinical Facts Per Vertical

Indian primary sources tagged. These facts may be cited in customer-acquisition content under doctor sign-off. The customer-acquisition skill references this section but does not duplicate the facts.

### Thyroid

- **Adult prevalence:** 10.95% across 8 Indian cities (Unnikrishnan et al., Indian J Endocrinol Metab 2013, n=5,376). Inland > coastal: Kolkata 21.67%, Delhi 11.07%, Hyderabad 8.88%.
- **Sex distribution:** Female 15.86%, male 5.02%.
- **Subclinical hypothyroidism:** 8.02%.
- **Anti-TPO antibody positivity:** 21.85%.
- **South Indian urban cohort (45+):** 17.69% prevalence (Jessy et al., Brain Communications 2024, n=1,201).
- **Goitre is the only Schedule J–enumerated thyroid condition** — hypothyroidism, hyperthyroidism, Hashimoto's are not enumerated, giving thyroid vertical the highest legal headroom.
### Weight Management

- **Urban metropolitan obesity using Asian BMI cut-offs:** 30–40% (NFHS-5).
- **Forecast:** overweight reaching 30.5% (men), 27.4% (women) by 2040; obesity 9.5% / 13.9% (Luhar et al., PLOS ONE 2020).
- **Anti-obesity drug market:** grew from ₹87 Cr to nearly ₹1,000 Cr (MAT November 2025), tenfold expansion in 5 years per Pharmarack.
- **GLP-1 market:** Mounjaro became India's top-selling pharmaceutical brand by value at ₹1 billion in October 2025 sales (overtaking GSK's Augmentin at ₹800M), per Pharmarack/Reuters reporting.
- **Generic GLP-1 landed Q1 2026:** Sun Pharma semaglutide ₹3,400/month, Natco semaglutide ₹1,250/month after March 20, 2026 Novo Nordisk patent expiry.
- **Schedule J #39 "Obesity"** — cannot claim drug-based cure or prevention.
### PCOS

- **ICMR-PCOS national study:** 7.2% NIH-1990 criteria, 19.6% Rotterdam criteria (Ganie et al., JAMA Network Open 2024, n=9,824).
- **Phenotype distribution:** Phenotype C most prevalent (40.8%).
- **Comorbidities among PCOS patients:** obesity 43.2%, dyslipidemia 91.9%, NAFLD 32.9%, metabolic syndrome 24.9%.
- **Urban concentration:** Delhi NCR college cohort 17.4% (IJMPR 2025).
- **Schedule J #15 "Diseases and disorders of uterus"** applies — cannot claim cure.
### Skin & Hair

- **Androgenetic alopecia (male):** 58% in Indian males aged 30–50 (Sehgal consensus paper, PMC); up to 50% by age 50.
- **Adult acne:** 25–35% common in 25–35 age cohort.
- **Melasma:** high prevalence in Indian skin types IV–V.
- **Schedule J entries that apply:** #5 Baldness, #10 Hair growth, #19 Fairness of skin, #45 Premature greying. Highest density of Schedule J entries for any vertical.
### Men's Intimate Health

- **Symptomatic hypogonadism in working-age men:** 26.1% (Goel et al., Indian J Urol 2009).
- **ED prevalence in urban men 40+:** 30–40% per Apollo Hospitals andrology data.
- **Schedule J entries that apply:** #30 sexual organ size/shape/duration, #36 sexual pleasure capacity, #47 sexual impotence/PE/spermatorrhoea. Highest regulatory-risk vertical.
### Hormones / TRT

- **Age-associated testosterone deficiency syndrome:** 48.18% symptomatic, 28.99% biochemically confirmed in Indian men ≥40 (Yadav et al., Adv Urol 2019, Sir Ganga Ram Hospital).
- **Association:** strong with diabetes, hypertension, obesity, metabolic syndrome, vitamin D deficiency.
- **Testosterone is Schedule H** (not Schedule X) — prescribable via telemedicine subject to List A/B constraints.
- **Schedule J entries that apply:** #43 Power to rejuvinate, #44 Premature ageing.
### Longevity

- **Not a disease — a market construct.** Target cohort: top-decile urban Indians 30–50 with disposable income, biomarker awareness, wearable adoption.
- **Schedule J entries that apply:** #43 Power to rejuvinate, #44 Premature ageing. Frame as cardiometabolic risk reduction + biomarker management, never as life extension or anti-aging.
- **Indian context:** wearable adoption mature post-Huberman/Attia popularization; Apple Watch + Garmin + Whoop penetration high in target cohort.
---

## When to Refuse to Publish

If a draft requires any of the following, the publish decision is "no" — not "let's reword":

1. Claims a drug cures/prevents/treats any Schedule J–enumerated condition.
2. Names a specific RMP delivering personal solicitation ("Book with Dr. X now").
3. Uses before/after imagery for any condition.
4. Quotes a fabricated testimonial or patient outcome statistic that hasn't been published.
5. Promises symptom resolution in a specific timeframe.
6. Uses cloned founder face delivering clinical content.
7. Uses cloned founder voice delivering clinical content (Clinical Editor voice required).
8. Lacks reviewing doctor's NMC reg number on-screen.
9. Lacks AI disclosure when AI voice or AI imagery is used.
   Walking away from a draft is the cheapest possible loss. ASCI complaints, NMC inquiries, and DPDP breach findings are existential.

---

## Cross-References

- **kyros-business-strategy** — why the doctor-first model is strategically protected
- **kyros-design-system** — visual and voice register details (operational), including ElevenLabs voice settings and the AI-disclosure visual treatment
- **kyros-customer-acquisition** — how approved vocabulary applies per channel and per vertical
- **kyros-b2b2c-partnerships** — how the doctor approval gate applies to corporate content
- **kyros-build-spec** — how the doctor approval workflow is implemented at the data layer (audit log, sign-off tables, RBAC)
 