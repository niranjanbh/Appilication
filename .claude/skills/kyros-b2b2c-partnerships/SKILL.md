---
name: kyros-b2b2c-partnerships
description: B2B2C partnership strategy, HRIS integrations, and marketplace context for the Kyros platform.
---
---
name: kyros-b2b2c-partnerships
description: The single canonical home for Kyros's B2B2C partnership playbook — corporate wellness pitch + pilot structure + pricing, insurance/TPA OPD-rider integration (MediBuddy, Medi Assist, Star Health, Niva Bupa, HDFC Ergo, Care Health, Aditya Birla), doctor association partnerships (FOGSI, IADVL, Indian Endocrine Society, Indian Thyroid Society), ekincare/Pazcare positioning analysis, per-vertical B2B angles, B2B sales cycle (9–18 months), ROI calculator structure, outbound sequence templates, the 90-day B2B2C operational plan. Treated as Phase 0 parallel pursuit, not deferred to Phase 1.
sequence: 5 of 5 skills — read AFTER all other skills
---

# Kyros B2B2C Partnerships

This skill owns **how Kyros sells to organizations who then sponsor care for individuals** — corporate wellness, insurance/TPA OPD-rider integration, doctor association partnerships, and platform-marketplace placements. Treated as a **Phase 0 parallel pursuit from Day 1**, not deferred.

## Skill Read Order

1. kyros-business-strategy — positioning, model, unit economics
2. kyros-clinical-compliance — regulatory rules, vocabulary, doctor approval gate
3. kyros-design-system — visual register, production stack
4. kyros-customer-acquisition — D2C channel mix
5. **kyros-b2b2c-partnerships** (this file)
6. kyros-build-spec (product spec) — technical architecture + Claude Code prompts P1–P30
---

## Why B2B2C Cannot Wait

The CAC ceiling math in kyros-business-strategy (₹300 at ₹400–600 pricing) shows the constraint. B2B2C **compresses CAC to near-zero per patient** because the employer/insurer pays acquisition; Kyros pays only the doctor-time cost.

Allara Health's 4× growth in 2024 was driven specifically by payer integration (Aetna, BCBS, Cigna, Humana, UnitedHealthcare). Payer integration was the 4× growth lever, not D2C scaling. The India equivalent is starting in Year 1, not Year 3.

**But** — the B2B sales cycle is 9–18 months. So Year 1 B2B2C is pipeline-building and credibility-building. D2C SEO + GBP + referral funds the business in Year 1. B2B2C revenue arrives Year 2.
 
---

## The Indian B2B2C Landscape (Verified May 2026)

### Market sizing

- **Corporate wellness market:** USD 2.60 Bn (2025) → USD 4.07 Bn by 2034 at 5.09% CAGR per IMARC Group. Grand View Research alternative: USD 2.08 Bn (2024) → USD 2.51 Bn by 2030 at 3.2% CAGR. Both materially higher than ekincare's previously-cited $1.6 Bn → $3.3 Bn figure.
- **More than 70% of Indian businesses** invest in some wellness program.
- **TPA OPD reimbursement is real and ₹500-capped on most policies.** Per Care Insurance documentation: "OPD Care for Care Supreme and Care Advantage offers reimbursement for 4 consultations in a year from 14 specified specialists, capped at ₹500 per consultation." **Kyros's ₹500 initial consultation is exactly at this ceiling — pricing strategy reflects this.**
### Key intermediaries (partner with or sell through)

| Player | Description | Kyros relationship |
|---|---|---|
| **ekincare** | 200+ corporate clients, 3.5L+ employees, 10,000+ service providers. MSD strategic investment via IDEA Studios Asia Pacific (April 2025). Aiming FY26 EBITDA breakeven. | Marketplace placement — Kyros as vertical-specialist provider on their flexi-care platform. Not competing for integrated-platform position. |
| **Pazcare** | 2,000+ corporate clients. "Treating insurance as a feature, healthcare as the core." | Marketplace placement opportunity. |
| **MediBuddy** | TPA service partner network; OPD claims processing. | **Primary TPA target** for paneling. |
| **Medi Assist** | Largest TPA in India; OPD claims processing. | **Primary TPA target** for paneling. |
| **Truworth Wellness** | Corporate wellness platform. | Marketplace placement. |
| **Onsurity** | Group health benefits platform. | Marketplace placement. |
| **Loop Health** | Employee health benefits + insurance. | Marketplace placement. |
| **Nova Benefits** | Group health + wellness. | Marketplace placement. |

### Insurance OPD-rider products (verified)

| Insurer | OPD Product | Sum Insured | Per-Consult Cap |
|---|---|---|---|
| Star Health | Star Outpatient Care (UIN SHAHLIP20064V011920) | ₹25,000–₹1,00,000 | Varies |
| Niva Bupa | ReAssure 2.0 OPD rider | Varies | Typically ₹500–₹750 |
| HDFC Ergo | Optima Restore OPD | Varies | Typically ₹500–₹1,000 |
| Care Health | Care Supreme / Care Advantage | ₹25,000+ | ₹500 (capped 4 consults/year, 14 specialist specialties) |
| Aditya Birla Health | Activ Health OPD | Varies | Varies |
 
---

## Track A: TPA OPD-Rider Integration

### The primary path

**MediBuddy and Medi Assist** are the largest TPAs handling OPD claims for corporate India. Empanelment with these two reaches the largest population of OPD-eligible employees through a single integration each.

**Process (binding under IRDAI Master Circular on Health Insurance Business, 29 May 2024):**

The IRDAI circular mandates:
- Cashless authorisation TAT capped at one hour
- Final authorisation within three hours of discharge request
- OPD/Day Care/Home Care coverage as standard
- 100% cashless aspiration
- Board-approved policy for empanelment
  **Empanelment timeline:** 6–12 months from initial conversation to live integration. Document requirements: NMC-registered doctor panel proof, infrastructure audit (telehealth platform, video consultation provider, prescription system), DPDP compliance documentation, insurance liability cover, registered medical clinic entity.

**Critical caveat:** Star Health and other insurers do **not** publish dedicated telehealth-provider empanelment tracks. Empanelment remains hospital/clinic-framed under the IRDAI 2024 circular. Kyros will likely need to register as a "registered medical clinic" entity to qualify. Plan this legal-structure work in Months 1–3.

### Outbound sequence: TPA empanelment

**5 touches over 8 weeks:**

1. **Week 1:** LinkedIn intro from founder to Head of Provider Network at MediBuddy (and Medi Assist). One paragraph: who Kyros is, what we do, why we'd be a paneled provider for chronic-condition specialty consultations at the ₹500 cap.
2. **Week 2:** Email follow-up with one-pager (Kyros brand position, vertical specialty depth, doctor panel snapshot with NMC reg numbers, geography coverage). Request 30-minute discovery call.
3. **Week 4:** First call. Listen more than pitch. Understand their network gaps in specialty chronic care.
4. **Week 6:** Submit empanelment application with all required documentation.
5. **Week 8:** Follow-up call to address questions and accelerate review.
   After Week 8, the timeline is theirs (typically 4–6 months for credentialing committee review and contracting). Kyros's job is to be responsive and have documentation ready.

### Secondary path: Insurer direct empanelment

Star Health, Niva Bupa, HDFC Ergo, Care Health, Aditya Birla Health — each has provider networks. Direct empanelment is slower (12–18 months) but higher-margin per consultation.

**8 touches over 12 weeks:**
1. Week 1: LinkedIn intro to Head of Provider Network at insurer
2. Week 2: One-pager email + meeting request
3. Week 4: Discovery call
4. Week 6: Reference call (introduce them to a panel doctor)
5. Week 8: Formal application with documentation
6. Week 10: Site/process audit (often remote for telehealth)
7. Week 12: Contracting
---

## Track B: Corporate Wellness Pilot Program

### Minimum viable offer

**₹X per employee per year for a Kyros "chronic condition concierge"** — 2 free specialist consultations/year across Kyros's 7 verticals + condition-specific webinars + discounted follow-ups for the employee + immediate family.

**Pricing tiers (per employee per year):**

| Company size | Per-employee/year | Conditions covered | Includes |
|---|---|---|---|
| 200–500 employees | ₹1,500–2,500 | Any 3 verticals | 2 consults + 1 follow-up + WhatsApp |
| 500–2,000 employees | ₹2,000–3,000 | All 7 verticals | 3 consults + 2 follow-ups + monthly webinar |
| 2,000+ employees | ₹2,500–4,000 | All 7 + executive longevity tier | 4 consults + 3 follow-ups + quarterly health checkup discount |

### Target list for Phase 0 (10-employer beta)

Indian unicorns and large enterprises with the right cohort fit:

| Company | Why fit |
|---|---|
| Adobe India | Premium IT cohort, female-skewed in research/design teams (PCOS, thyroid) |
| Microsoft India | Same |
| Razorpay | High-stress, executive cohort, BFSI-adjacent |
| Cred | Same |
| Swiggy | Mixed cohort, large employee base, comprehensive benefits |
| Zomato | Same |
| Flipkart | Large employee base, both engineering and operations |
| ThoughtWorks | Knowledge-worker cohort, strong wellness culture |
| Postman | Engineering, high-paying, strong benefits |
| Freshworks | Same |

### Pitch frame

"Allara closed the gender care gap in the US through employer + insurer integration. Kyros is the Indian doctor-first equivalent — and unlike Practo for Business / ekincare, we do specialty depth not GP breadth.

Per Ganie et al. (JAMA Network Open 2024, n=9,824): 7.2–19.6% of Indian women have PCOS depending on diagnostic criteria. 43.2% of women with PCOS have obesity, 91.9% have dyslipidemia. Per Shah et al. (Cureus October 2025): hypothyroidism prevalence in India is approximately 10.95%. These are measurable absenteeism costs employers will fund.

Pilot offer: 90 days, ₹X per employee, unlimited teleconsultations across 3 chosen verticals. Success criteria: utilization >8%, NPS >50, completion rate >60%. If pilot succeeds, annual contract."

### Outbound sequence: Corporate HR

**4 touches over 6 weeks:**

1. **Week 1:** LinkedIn intro from founder to Head of HR Wellness or Chief People Officer. Personalize with one company-specific data point (recent wellness announcement, ESG report mention, leadership statement).
2. **Week 2:** Email follow-up with pilot one-pager. Request 30-minute call.
3. **Week 4:** Discovery call. Understand their current wellness vendor stack (likely ekincare/Onsurity/Pazcare), gaps in specialty care coverage, employee feedback patterns.
4. **Week 6:** Proposal with 90-day pilot structure, success criteria, and post-pilot annual pricing.
   **Target: 3 pilot conversations booked by Day 30. First pilot signed by Day 60. 100 corporate-enrolled patients live by Day 90.**

### Pilot operational mechanics

**90-day pilot structure:**
- Week 0: Employer signs pilot agreement; Kyros onboards into their HR system (CSV upload, or HRIS integration if available)
- Week 1: Employee announcement via internal channels (Slack, Teams, intranet)
- Week 1–2: Onboarding webinar by Kyros founder + clinical lead
- Weeks 2–12: Active consultation period
- Week 13: Mid-pilot review (utilization, NPS, qualitative feedback)
- Week 13–25: Continued active period
- Week 25–26: Pilot review meeting + annual contract proposal
  **Pilot success criteria (the numbers you commit to):**
- Utilization: >8% of employees take at least one consultation in 90 days
- NPS: >50 (corporate wellness benchmark)
- Completion rate: >60% (employees who book complete the consultation)
- Resolution: >70% of consultations result in a clear next step (lab order, prescription, follow-up, or referral)
---

## Track C: Doctor Association Partnerships

These are the highest-leverage relationships in Kyros's network. Doctor associations represent specialist communities Kyros can plug into for credibility, doctor recruitment, and in-bound referral flow.

### FOGSI (Federation of Obstetric and Gynaecological Societies of India)

- **Scale:** 293 member societies, 47,000+ individual members
- **Annual conference:** AICOG
- **Relevance:** PCOS vertical primary; weight management for women secondary
- **Partnership model:** MOU-based (precedent: USAID/SHOPS Plus 2020). Rate cards not public.
- **Entry path:** Yuva FOGSI regional conferences; state branch sponsorships; CME webinar partnerships
- **Outcome target:** named partnership with one state FOGSI chapter by Month 6; one published joint study by Month 12
### IADVL (Indian Association of Dermatologists Venereologists and Leprologists)

- **Scale:** 17,000+ members, world's 2nd largest dermatology society after AAD
- **Annual conference:** CUTICON (regional + national)
- **Relevance:** Skin & hair vertical primary
- **Entry path:** CUTICON regional conferences; state branch sponsorships
- **Outcome target:** sponsorship of one CUTICON regional event by Month 9
### Indian Endocrine Society (IES)

- **Scale:** 2,000+ members
- **Annual conference:** ESICON (54th annual conference was 4–7 September 2025, Kolkata)
- **Relevance:** Thyroid + TRT + hormones verticals
- **Entry path:** ESICON sponsorship, CME partnerships, fellowship sponsorships
- **Outcome target:** ESICON 2026 sponsorship presence; CME webinar series partnership
### Indian Thyroid Society

- **Scale:** smaller, specialized
- **Relevance:** Thyroid vertical specifically (launch flagship)
- **Entry path:** Direct outreach to current president and secretary
- **Outcome target:** named partnership for the thyroid vertical launch
### Outbound sequence: Doctor association

Relationship-led, not campaign-led. **3 in-person touches per year:**

1. **Conference attendance** (sponsor a session, table presence, or speaking slot)
2. **CME webinar partnership** (Kyros-funded, association-branded, doctor-led)
3. **Published research collaboration** (joint clinical outcomes study)
   Budget: ₹3–8 lakhs per association annually for credible presence.

---

## Track D: Marketplace Placements

ekincare, Pazcare, Truworth, Onsurity, Loop Health, Nova Benefits all run corporate wellness marketplaces where employees pick services. Kyros as a vertical specialist provider fits naturally.

**Pitch frame:** "We're not competing with you. We're the specialty depth your platform doesn't have today. Plug us in as the chronic-condition specialist tier."

**Commercial structure:** revenue share (typically 70/30 in Kyros's favor on direct consults, since Kyros owns the doctor relationship; 50/50 on care plans where the marketplace owns the patient relationship).

**Timeline:** 3–6 months to placement.
 
---

## Per-Vertical B2B2C Angles

| Vertical | B2B angle | Best-fit employer cohort |
|---|---|---|
| **Thyroid** | "1-in-6 female workforce likely subclinically hypothyroid, presenting as fatigue/productivity loss. Annual TSH + anti-TPO + vitamin D add-on at ₹150/employee." | All employers; especially female-skewed (IT, BPO, consulting, BFSI) |
| **Weight management** | "Executive metabolic health program — quarterly bloods + monthly doctor follow-up + GLP-1 supervision where indicated." | BFSI leadership, consulting partners, IT executives |
| **PCOS** | "1-in-5 women employees has PCOS or pre-PCOS — annual screening + 6-session group program. Productivity loss documented: per Allara's published research, over 50% of PCOS patients have missed work; 72% report adverse effects on work quality." | Female-skewed workforces (IT services, BPO, consulting, BFSI) |
| **Skin & hair** | "Executive aesthetic health module" | Senior leadership cohort, 30–45 |
| **Men's intimate** | Fold into longevity / executive health bundle; do not pitch standalone B2B (corporate HR sensitivity) | N/A standalone |
| **Hormones / TRT** | "Executive male health program — quarterly hormonal panel, doctor follow-up, supervised TRT if indicated" | Senior male executive cohort |
| **Longevity** | "C-suite longevity program" — highest-fit B2B vertical; ₹15,000–30,000/executive/year realistic | C-suite of mid-large enterprises |
 
---

## ROI Calculator Structure

For corporate HR decision-makers, the pitch is productivity-loss avoidance + healthcare-cost reduction.

### Productivity loss avoidance model (PCOS example)

- Workforce: 1,000 employees, 45% women = 450 women
- Prevalence: 20% PCOS (Ganie Rotterdam criteria) = 90 women
- Productivity loss per affected employee: 5 days/year (conservative estimate based on Allara published research)
- Average cost per lost day: ₹3,500 (loaded compensation for knowledge worker)
- Total annual productivity loss: 90 × 5 × ₹3,500 = ₹15.75 lakhs
- Kyros annual contract: 1,000 employees × ₹2,500 = ₹25 lakhs
- Target utilization rate among affected women: 50% = 45 women
- Target productivity recovery: 60% of lost days = 3 days/year per treated employee
- Productivity recovery: 45 × 3 × ₹3,500 = ₹4.7 lakhs
- **Net ROI math for HR:** ₹25 lakhs cost vs ₹4.7 lakhs productivity recovery is unfavorable at PCOS alone — but the contract covers all 7 verticals. Adding thyroid (10.95% prevalence × full workforce × similar productivity model) shifts ROI to positive.
### Healthcare cost reduction model (for self-insured employers + insurer pitches)

- Average claims cost per chronic condition patient: ₹25,000–60,000/year (varies by condition)
- Kyros longitudinal management target: 15–25% reduction in claims via prevention, adherence, and early intervention
- Self-insured employer with 5,000 employees and ~500 chronic patients: savings of ₹15–30 lakhs/year against ₹125 lakhs Kyros annual contract — still net unfavorable at the platform level, but favorable per-patient
  **The honest ROI story for HR:** Kyros doesn't pay for itself in Year 1 on productivity math alone. It pays for itself in talent retention, ESG narrative, employee NPS, and Year-2 chronic-claims reduction once the longitudinal data builds.

---

## 90-Day B2B2C Operational Plan

### Days 1–30: Pipeline Foundation

**Track A (TPA):**
- Week 1: LinkedIn intros to Head of Provider Network at MediBuddy + Medi Assist
- Week 2: Send empanelment one-pagers
- Week 4: First discovery calls
  **Track B (Corporate):**
- Week 1–2: Build target list of 25 employers (10 unicorns + 10 large IT services + 5 BFSI)
- Week 2–3: First 10 LinkedIn intros
- Week 3–4: Pilot one-pager finalized
  **Track C (Doctor associations):**
- Week 2: Outreach to FOGSI state branch (start with Karnataka or Maharashtra given founder geography)
- Week 4: ESICON 2026 sponsorship inquiry
### Days 31–60: First Conversations

**Track A:** TPA empanelment applications submitted

**Track B:**
- 3 corporate pilot conversations active
- First pilot proposal sent
  **Track C:**
- First FOGSI chapter conversation scheduled
- IADVL CUTICON sponsorship terms received
### Days 61–90: First Pilot Live + Marketplace Outreach

**Track A:** TPA review in progress (typically 4–6 months from this point)

**Track B:**
- First corporate pilot signed
- Onboarding webinar delivered
- 100+ employees enrolled
- Second + third corporate pilots in negotiation
  **Track C:**
- FOGSI partnership terms signed
- ESICON 2026 sponsorship confirmed
  **Track D (Marketplace):**
- Outreach to ekincare and Pazcare for vertical-specialist provider placement
- First marketplace listing live by Day 90 (lower-friction than corporate direct)
### Benchmarks that would change the B2B2C plan

- **If by Day 60 corporate pilot conversion rate < 1 in 25 outbounds** → pause B2B2C, reframe pitch, possibly hire healthcare B2B sales specialist before continuing
- **If TPA cycle stalls past 12 months** → raise B2B2C pricing rather than discount (signals premium, filters serious buyers)
- **If doctor association partnership cost > ₹10 lakhs/year per association** → reduce to 1 anchor partnership instead of 3
- **If marketplace placement converts > 50 patients/month** → marketplace becomes Track A priority over direct TPA
---

## What to Never Do

1. **Never offer per-referral payments to doctors.** NMC code violation. Use CME credits, conference sponsorship, advisory honorarium — never per-patient cash.
2. **Never agree to capitated risk-bearing arrangements in Year 1.** Iora's model worked in US Medicare Advantage; Indian working-age chronic care has no equivalent risk-bearing payer. Take fee-for-service or PMPM (per-member-per-month) — never full-risk capitation in Year 1.
3. **Never pitch corporate wellness for men's intimate health vertical as standalone.** HR discomfort kills the broader contract. Fold into longevity/executive bundle.
4. **Never discount below ₹1,500/employee/year.** Below this, Kyros looks like a perk-aggregator (Onsurity range), not a clinical-depth partner.
5. **Never publish corporate pilot patient data without explicit DPDP consent flow.** Even aggregate data requires the corporate to have consent on file from their employees.
6. **Never name corporate partners publicly without written approval from their PR/communications team.** Pilot stage is private until both parties agree to announce.
7. **Never run group consultations for Schedule J–enumerated conditions.** Group webinars are general education; consultations must be 1:1 with doctor and patient.
---

## Cross-References

- **kyros-business-strategy** — CAC ceiling math that makes B2B2C strategic; reference brand analysis (Allara payer integration model)
- **kyros-clinical-compliance** — every B2B2C content piece still passes the doctor approval gate; same vocabulary rules apply
- **kyros-design-system** — visual register for B2B pitch decks and corporate-facing materials (same system, slightly more institutional treatment than D2C)
- **kyros-customer-acquisition** — D2C side of doctor referral network; SEO/GBP infrastructure that B2B partners review during due diligence
- **kyros-build-spec** — HRIS integration for corporate pilot onboarding, TPA claims API integration, marketplace API integration
 