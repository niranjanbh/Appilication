---
name: kyros-customer-acquisition
description: Customer acquisition strategy, SEO architecture, and growth context for the Kyros platform.
---
---
name: kyros-customer-acquisition
description: This is the canonical system for Kyros’s D2C acquisition, covering all moves to bring in paying patients at sub-₹300 CAC, including channel mix, tiering, CAC math, and content cadence. It owns all non-SEO growth channels—Google Business Profile, email/WhatsApp, referrals, Reddit/community, YouTube, founder-led content, and syndication—while integrating with SEO/AI search via kyros-public-site-strategy as the Tier-1 channel. It also drives per-vertical acquisition strategy and keyword inventories across all seven clinical verticals, defines the 30/60/90-day execution plan, and replaces fragmented social and acquisition efforts with a unified growth equation.
sequence: 4 of 5 skills — read AFTER business-strategy, clinical-compliance, design-system; pair with kyros-public-site-strategy (4a)
---

# Kyros Customer acquisition (D2C)

This skill owns **how Kyros acquires paying patients at sub-₹300 CAC** — the *equation* of channels, CAC math, and per-vertical plays that bring patients in across owned, organic, and community surfaces. The public website + organic/AI-search engine (the #1 channel) has its own home in kyros-public-site-strategy; this skill frames that channel's role and owns every other channel. B2B2C (corporate wellness, TPA, insurers) lives in kyros-b2b2c-partnerships, as a parallel pursuit from Day 1.

## Skill Read Order

1. kyros-business-strategy — positioning, model, unit economics
2. kyros-clinical-compliance — regulatory rules, vocabulary, doctor approval gate
3. kyros-design-system — visual register, production stack, hook architecture
4. kyros-public-site-strategy — the public website + organic/AI-search engine (SEO is Tier 1, channel #1 below; this skill's per-vertical keyword inventories feed it)
5. **kyros-customer-equation** (this file)
6. kyros-b2b2c-partnerships — B2B partnership playbook
7. kyros-build-spec (product spec) — technical architecture + Claude Code prompts P1–P30
---

## Core Constraint: The ₹300 CAC Ceiling

At ₹400–600 pricing (full derivation in kyros-business-strategy), the CAC ceiling for healthy unit economics is ₹300. This eliminates Meta and Google paid prospecting as primary channels — Indian metro healthcare CAC on Meta runs ₹400–800, and Google Search Ads on high-intent terms imply ₹800–2,000 CAC.

**Only organic SEO, GBP, referral, email/WhatsApp owned audience, partnerships, and B2B2C deliver sub-₹300 CAC sustainably.** This skill is the operational map of those channels.
 
---

## Channel Mix Tiers

### Tier 1 — Foundational (60% of acquisition effort)

The channels that fund the business. These must work or Kyros cannot exist.

1. **SEO with topical authority on chronic conditions** — programmatic at scale per vertical
2. **Google Business Profile + local SEO** per Tier-1 city
3. **Email + WhatsApp owned audience** — list-building pre-launch + nurture
4. **Referral program** — patient and doctor referrals
### Tier 2 — Amplification (25% of effort)

Channels that compound the foundation. Only work if Tier 1 is real.

5. **YouTube long-form clinical content** — 12–20 min doctor-led explainers
6. **Founder voice on Instagram + LinkedIn** — institutional positioning, not personality influence
7. **Content syndication** — Indian Express health, The Hindu, Mint, Femina
### Tier 3 — Catalytic (15% of effort)

Low-frequency, high-impact channels.

8. **Reddit + condition-specific community presence**
9. **Doctor association partnerships** (covered in kyros-b2b2c-partnerships)
10. **Doctor referral network** — specialists referring chronic patients to Kyros
    **Paid social retargeting is permitted at 5% of spend as a Tier-3 booster** for organic-acquired audiences — never as Tier-1 prospecting.

---

## Tier 1 Detail

### 1. SEO + AI Search (channel #1 — full playbook in kyros-public-site-strategy)

SEO/AISO is the deepest Tier-1 lever and the foundational sub-₹300 CAC engine. Its full strategy *and* execution — site architecture, the Learn/Decide/Act intent model, topic clusters, the scaled-content-abuse safeguard, E-E-A-T and entity SEO, technical SEO and schema, the AI Search Optimization layer, link building and digital PR, the English-first/vernacular decision, KPIs, the validation/testing toolchains, and the launch checklist — now lives in **kyros-public-site-strategy** alongside the rest of the public website, because by mid-2026 AI search became a distinct discipline (the organic↔AI-citation overlap collapsed from ~76% to ~38%) and because a site's search strategy and its execution are one continuous job.

What this skill needs to hold about this channel:

- **Architecture in brief:** condition-hub site (`/conditions/{vertical}/`, `/learn/{vertical}/{query-slug}/`, plus `/{city}/{vertical}-specialist-online/` city pages), all authority into kyros.clinic, three intent layers (Learn → Decide → Act), mandatory internal-linking rule (every article links to its pillar + 2 related + 1 conversion page).
- **Velocity:** 20 articles by M3, 50 by M6, ~200 by M12, then 8–12/month — *only* with genuine doctor-added value per page (thin/scaled content now drags whole-domain authority).
- **E-E-A-T:** doctor byline + visible NMC reg #, specialty match, "medically reviewed [date]", Indian primary-source references, schema (`MedicalCondition`, `MedicalWebPage`, `Physician`), no AI body copy without doctor attestation.
- **AISO reality:** AI Overviews appear on ~48.75% of healthcare queries (Conductor 2026); ~90% of brands have zero AI mentions; AI-referred visitors convert ~14.2% vs ~2.8% organic. Citation is earned via cross-platform presence (4+ platforms ≈ 2.8× citation odds) — and **YouTube is the single strongest correlate with health AI-Overview visibility**, which is why the YouTube channel below (Tier 2.5) is also a primary SEO asset, not just amplification.
- **Local separation:** Google shows **no AI Overviews on local-provider queries** ("dermatologist near me") — those route through Google Business Profile (§ 2 below), not articles. Keep the channels distinct.
  For everything operational on this channel, read kyros-public-site-strategy. The per-vertical keyword inventories that feed it stay here (§ "Per-Vertical Acquisition Playbooks").

### 2. Google Business Profile

**Tier-1 cities for Phase 0:** Bengaluru, Mumbai, Delhi-NCR, Hyderabad.

Each city gets a dedicated GBP listing once doctor coverage is real (do not list cities before a panel doctor serves that geography).

**GBP operational pattern:**
- Weekly posts: condition-specific clinical content, Indian context photography
- Q&A monitoring: respond within 24 hours
- Photo refresh: monthly, premium-warm clinical register (no athleisure, no stock smiling doctors)
- Review solicitation: only post-consultation, only via the patient app's review flow (never via email blast)
- Doctor profile cards: NMC reg #, specialty, conditions treated
### 3. Email + WhatsApp Owned Audience

**Email list build pre-launch:**
- Lead magnets: PCOS phenotype quiz, thyroid panel decoder, TRT readiness checklist, weight-management baseline assessment
- Cadence: bi-weekly Kyros Clinical Editor letter (doctor-reviewed)
- Tooling: Mailchimp or Sendy on Indian server; double opt-in; DPDP consent capture at signup
- Target: 5,000 emails by launch; 25,000 by Month 12
  **WhatsApp Business API:**
- Provider via Indian BSP (AiSensy, Wati, or Interakt)
- Use cases: appointment reminders (utility, ₹0.115/msg), medication adherence (utility), pre-consultation forms (utility), lab result notifications (utility), post-consultation follow-up (service — free in 24h window)
- DPDP consent flow: explicit opt-in at signup, easy opt-out
- **Higher engagement than email in India** (~80% open vs ~25%) — WhatsApp is the primary nurture channel
  **What NOT to send via WhatsApp/email:**
- Cold outbound to non-consented audiences
- Clinical advice without doctor review
- Specific dosage information
- Brand-name drug promotion
### 4. Referral Program

**Patient referral:**
- Referrer: ₹500 credit toward next follow-up (no cash payout)
- Referred: ₹200 off first consultation
- Tracking: unique code per patient, surfaced in app and post-consultation email
  **Doctor referral (specialist → Kyros):**
- Specialists who don't do chronic management refer chronic patients (e.g., surgical gynecologist refers PCOS lifestyle patients)
- NMC-compliant honorarium structure (CME credits, conference sponsorship, advisory honorarium — not per-referral payments which violate NMC code)
- Doctor association partnerships (FOGSI, IADVL, IES) covered in kyros-b2b2c-partnerships
---

## Tier 2 Detail

### 5. YouTube Long-Form Strategy

**Format:** 12–20 minute doctor-led clinical explainers. Premium-warm clinical visual grammar (forest/ivory/saffron, no music in clinical content, conversational voiceover).

**Why long-form:** per SE Ranking December 2025 study of 50,807 German-language health queries, YouTube was the single most cited domain in health AI Overviews (4.43% of all citations). Long-form doctor-led content is one of the highest-leverage AI Overview placement strategies. **This makes YouTube a primary SEO/AISO asset, not just Tier-2 amplification** — Ahrefs' 75,000-brand study found brand mentions in YouTube titles, transcripts, and descriptions the strongest single correlate with AI-Overview visibility. Title/describe/transcribe deliberately with condition and brand terms. See kyros-public-site-strategy § 9.

**Cadence:**
- Phase 0: 1 video / 2 weeks per priority vertical
- Phase 1: 1 video / week per active vertical
- Phase 2: 2 videos / week sustained
  **Anchor topics per vertical:**
- Thyroid: "TSH explained for Indian patients" / "Hashimoto's vs hypothyroidism" / "When to test anti-TPO"
- Weight management: "GLP-1 medications for Indian patients — what your doctor evaluates" / "Reading your metabolic panel" / "Weight management for Indian metabolisms"
- PCOS: "PCOS phenotype A/B/C/D for Indian women" / "Insulin resistance in PCOS" / "When metformin makes sense"
- Skin & hair: "AGA in Indian men — what dermatologists actually do" / "Adult acne after 25" / "Melasma in Indian skin"
- Men's intimate: "ED evaluation — what a urologist checks" / "The metabolic story behind ED"
- Hormones/TRT: "Low testosterone in Indian men — beyond the WhatsApp groups" / "Free testosterone vs total"
- Longevity: "ApoB > LDL for Indian patients" / "Reading your cardiometabolic panel"
  **Production:** see kyros-design-system for production stack, weekly workflow, and voice settings.

### 6. Founder Voice on Instagram + LinkedIn

**Instagram:**
- Founder (Niranjan) real face on About-page content and founder-perspective Reels
- Founder cloned voice on non-clinical brand storytelling (per kyros-clinical-compliance)
- Clinical Reels use Kyros Clinical Editor voice + doctor reviewer credit on-screen
- Hook architecture per kyros-design-system
- Cadence: 4–6 posts/week (Reels + carousels + stat cards)
  **LinkedIn:**
- Founder long-form essays (600–1,500 words)
- Topics: building a doctor-first telehealth practice in India, what Schedule J means for healthtech, why supplement-D2C captures volume but caps LTV, the clinical-management gap in Indian chronic care
- Cadence: 2 essays/week
- This is the institutional-positioning channel — investors, advisors, senior clinicians follow LinkedIn
### 7. Content Syndication

**Target publications:** Indian Express health vertical, The Hindu Wellness, Mint Lounge, Femina Health, YourStory's HealthBytes, The Ken (HealthCheck newsletter).

**Pitch frame:** doctor-bylined explainers with kyros.clinic backlink. Topics that travel: PCOS productivity loss research, thyroid prevalence in Indian women, the GLP-1 landscape post-generic launch, men's hormonal health beyond the gym-bro stereotype.

**Cadence:** 1 syndicated essay/month sustained.
 
---

## Tier 3 Detail

### 8. Reddit + Telegram Community Presence

**Active Indian Reddit communities (verified May 2026):**
- r/PCOS (large global, active India cohort)
- r/IndianWomen (PCOS, thyroid threads)
- r/Mounjaro (booming 2025–26, India sub-cohort)
- r/IndianFitness (TRT, weight management threads)
- r/IndianSkincare, r/IndianHaircare
- r/Testosterone (global with India cohort)
- r/india (health threads)
  **Engagement pattern (Allara's playbook, India translation):**
- Founder/doctor participation: earnest, no solicitation
- Never DM patients
- Never link without value (don't drop kyros.clinic in every comment)
- Doctor AMAs with NMC reg # disclosed
- Patience: 6-month curve before community recognizes Kyros as credible
  **Telegram:** smaller, more closed. Monitor but don't initiate. PCOS, thyroid, and Mounjaro Telegram groups exist; engagement requires invitation.

### 9. Doctor Association Partnerships

Covered in kyros-b2b2c-partnerships. Operational summary here: FOGSI (PCOS), IADVL (skin & hair), Indian Endocrine Society (thyroid + TRT + hormones), Indian Thyroid Society — each represents a path to in-bound doctor-to-doctor referrals at zero paid CAC.

### 10. Doctor Referral Network

Same channel as above from the supply-side: senior surgical specialists (gynecologists, urologists, bariatric surgeons) who don't do longitudinal chronic management refer their chronic patients to Kyros. Operational mechanics in kyros-b2b2c-partnerships.
 
---

## Per-Vertical Acquisition Playbooks

Seven verticals, each with its own community gravity, search behavior, hook architecture, and acquisition cadence. The clinical facts per vertical live in kyros-clinical-compliance; the acquisition playbook lives here.

### 2.1 Thyroid (Launch Flagship)

**Why this vertical first:** Schedule J enumerates only "Goitre" — highest legal headroom. Adult prevalence 10.95% per Unnikrishnan 2013 (Indian J Endocrinol Metab). 7M+ top-decile urban TAM.

**Patient journey:** Symptom recognition (fatigue, weight, hair, mood) → GP visit → TSH on routine panel → endocrinologist or GP-initiated levothyroxine → 6-week recheck → indefinite. Pain points: dose-titration confusion, panel-vs-symptom mismatch, anti-TPO not explained, supplement noise online.

**Top creators in vertical (clinical):** Dr V Mohan, Dr Shashank Joshi, Dr Tanmay Singh. **Wellness (do not emulate):** Rujuta Diwekar, Luke Coutinho thyroid content.

**Top SEO keywords:**
- Informational: "TSH normal range India", "thyroid symptoms in women", "Hashimoto vs hypothyroidism", "free T3 free T4 meaning"
- Treatment: "thyroid diet plan India", "levothyroxine timing"
- Provider: "thyroid doctor online consultation", "best endocrinologist near me"
  **Hook architecture (per kyros-design-system):**
- "Your TSH is 4.8 and your doctor said wait and watch — here's what I tell my patients who can't keep waiting."
- "Hair fall after pregnancy isn't always postpartum — TPO antibodies have a story to tell."
- **Avoid:** "reverse your thyroid," "cure hypothyroidism naturally" (though only "goitre" is Schedule J-enumerated, DMR Act misleading-claim provisions still apply).
  **Reddit/community:** r/IndianWomen thyroid threads, r/india health, Facebook "Hypothyroidism India" / "Hashimoto's Thyroiditis India."

**Cadence:**
- Phase 0: 15 anchor SEO articles; GBP in 3 cities; Reddit AMA on r/india; bi-weekly founder LinkedIn essay
- Phase 1: YouTube long-form "TSH explained for Indian patients" anchor + 4 follow-up videos; email nurture sequence
- Phase 2: WhatsApp medication-adherence loop, diagnostic-lab partner (Redcliffe most likely)
  **Reference comparable:** Paloma Health (US, thyroid-first telehealth, $9M Series A 2022). Doctor-first integrates labs + medication + nutrition.

---

### 2.2 Weight Management (Including Doctor-Supervised GLP-1)

**Promoted to flagship Q3 2026** when Sun Pharma (₹3,400/month) and Natco (₹1,250/month) generic semaglutide are widely available post-March 2026 Novo Nordisk patent expiry.

**Patient journey:** Self-recognition + comorbidity nudge → diet apps (Healthify, Fitterfly) → frustration → endocrinologist or bariatric surgeon → Mounjaro/Wegovy prescription → titration → adherence/side-effect management. **2025–2026 new entry point:** WhatsApp groups for Mounjaro dose-sharing (unsupervised, dangerous).

**Top creators (clinical):** Dr Pradeep Chowbey (bariatric), Dr Shashank Shah, Dr Ambrish Mithal (endo). **Emerging cohort:** Mounjaro user-creators on Instagram (avoid endorsing or replicating; many violate ASCI Addendum 2 qualification requirement).

**Top SEO keywords:**
- Informational: "Mounjaro India price", "tirzepatide side effects", "semaglutide generic India"
- Treatment: "GLP-1 prescription India", "weight loss doctor online"
- High-intent transactional + symptom-management. **Highest search volume of any Kyros vertical.**
  **Hook architecture:**
- "Mounjaro isn't a shortcut — it's a tool. Here's how to use it without the GI side effects."
- "Before you order Mounjaro from a WhatsApp group, here's what dose escalation should actually look like."
- **Avoid:** "guaranteed weight loss," "X kg in Y weeks" (Schedule J #39 Obesity cure-claim prohibition).
  **Reddit/community:** r/Mounjaro (booming), r/IndianFitness weight loss threads, r/loseit India cohort.

**Cadence:**
- Phase 0: keyword saturation around GLP-1 long-tails; preparatory content; community presence on r/Mounjaro India
- Phase 1: YouTube "Mounjaro 101 for Indian patients" anchor; WhatsApp adherence loop for GLP-1 patients
- Phase 2: corporate executive metabolic health program
  **Reference comparable:** Calibrate Health (US, $173M Series B 2021, doctor-supervised GLP-1, premium-priced). Ro Body program. Found Health.

**B2B angle:** corporate executives (BFSI, IT leadership, consulting partners). "Executive metabolic health program" — quarterly bloods + monthly doctor follow-up + GLP-1 supervision where indicated.
 
---

### 2.3 PCOS

**Why this vertical matters:** 7.2–19.6% prevalence in Indian women (Ganie 2024 JAMA Network Open, n=9,824). 12M women TAM. Strong B2B angle for female-skewed workforces.

**Patient journey:** Adolescent irregular periods → gynaecologist → ultrasound + LH/FSH/AMH → OCP prescription → frustration → diet/inositol experimentation → re-presentation in late 20s for fertility or weight → second-opinion → influencer-driven supplement use.

**Top creators (clinical):** Dr Duru Shah, Dr Nandita Palshetkar. **Influencer cohort (educational):** Dr Tanaya ("Dr Cuterus" — large following), Dr Riddhima Shetty. **Wellness (do not emulate):** Rujuta Diwekar PCOS content.

**Top SEO keywords:**
- Informational: "PCOS vs PCOD", "PCOS diet plan", "irregular periods causes"
- Treatment: "PCOS treatment India", "inositol India", "metformin for PCOS"
- Provider: "PCOS doctor online", "PCOS hair loss"
  **Hook architecture:**
- "PCOS isn't a diet problem. It's an insulin problem that looks like a diet problem."
- "Your gynaecologist said 'lose 5 kg and come back.' That advice is true and also insufficient."
- **Avoid:** "reverse PCOS," "cure PCOS" (Schedule J #15 "Diseases and disorders of uterus").
  **Reddit/community:** r/PCOS (huge global, active India cohort), r/IndianWomen PCOS threads.

**Cadence:**
- Phase 0: SEO + GBP; founder LinkedIn essays; partner with FOGSI state chapter for CME webinar
- Phase 1: YouTube "PCOS phenotype A/B/C/D for Indian women" 5-part series; Instagram founder-voice carousels
- Phase 2: corporate group program (covered in kyros-b2b2c-partnerships)
  **Reference comparable:** Allara Health (explicit reference brand — $26M Series B Jan 2025, multi-disciplinary structure, 4× growth via insurance integration).

**B2B angle:** IT services, BPO, consulting workforces with female skew. "1-in-5 women employees has PCOS or pre-PCOS — annual screening + 6-session group program."
 
---

### 2.4 Skin & Hair

**Why this vertical matters:** AGA 58% in Indian males 30–50 (Sehgal consensus, PMC). Adult acne 25–35% in 25–35 age cohort. High-margin self-pay market currently captured by Mosaic Wellness (Rs 736 Cr FY25), Traya, The Derma Co.

**Patient journey:** Self-treatment via Mamaearth/The Derma Co/Minimalist → derma visit when severe → minoxidil/finasteride/topical retinoid → expensive private clinic procedures (PRP/transplant) → maintenance gap.

**Top creators (clinical):** Dr Aanchal MD, Dr Geetika Mittal Gupta, Dr Manasi Shirolikar, Dr Jaishree Sharad. **Wellness/D2C (competitive):** Man Matters/Be Bodywise creators.

**Top SEO keywords:**
- Informational: "Hair fall treatment India", "DHT blocker", "tretinoin India price"
- Treatment: "minoxidil side effects", "finasteride for women", "melasma treatment"
- Provider: "best dermatologist online"
  **Hook architecture:**
- "Hair fall isn't always a hair problem. Here are the four tests every Indian patient should have before starting minoxidil."
- **Avoid:** "guaranteed hair regrowth," "cure baldness" (Schedule J #5 Baldness, #10 Hair growth — both apply).
  **Reddit/community:** r/IndianSkincare, r/IndianHaircare, r/IndianMakeupAddicts, Facebook "Acne Warriors India."

**Cadence:**
- Phase 0: SEO + GBP; IADVL partnership initiation
- Phase 1: YouTube + Instagram founder-voice (compliance-gated)
- Phase 2: corporate executive aesthetics
  **Reference comparable:** Hims & Hers (US, doctor-supervised topical finasteride/minoxidil). Curology.

**B2B angle:** corporate executive cohort, 30–45, premature baldness anxiety. "Executive aesthetic health module."
 
---

### 2.5 Men's Intimate Health

**Why this vertical is hardest:** highest density of Schedule J entries (#30, #36, #47). Every claim category restricted. ED prevalence 30–40% in urban men 40+ per Apollo Hospitals andrology data.

**Patient journey:** Late presentation due to stigma. Online searches → ayurvedic ads → frustration → quiet urology/andrology visit → fragmented care.

**Top creators (clinical):** Dr Anup Dhir, Dr Vijayant Govinda Gupta. **Sparse legitimate creator base — whitespace.** Wellness/D2C dominates voice (Man Matters/Mosaic, Misters, Bold Care).

**Top SEO keywords:**
- Informational: "ED causes", "low libido causes", "premature ejaculation explained"
- Treatment: "sildenafil India price" (compliance-risk territory)
- Provider: "andrologist near me", "ED treatment India" (frame as evaluation, not treatment)
  **Hook architecture:**
- "ED isn't always about libido — sometimes it's the first sign of a metabolic story."
- **Avoid:** any cure-claim language (Schedule J #30, #36, #47 all explicit). **Highest regulatory-risk vertical.**
  **Reddit/community:** r/IndianMen, r/AskMenIndia (closed). Private Telegram groups. WhatsApp word-of-mouth.

**Cadence:**
- Phase 0: SEO + GBP foundation; minimal social presence
- Phase 1: highly compliance-gated content; Kyros Clinical Editor voice safer than founder voice for this vertical
- Phase 2: integrate with hormones/TRT vertical
  **Reference comparable:** Hims (built the playbook), Ro (Roman). Doctor-supervised PDE5 inhibitors + behavioural therapy.

**B2B angle:** Fold into longevity / executive health bundle; do not pitch standalone B2B due to corporate-HR discomfort.
 
---

### 2.6 Hormones / TRT

**Why this vertical has whitespace:** 48.18% symptomatic TDS in Indian men ≥40 (Yadav 2019). Almost no legitimate Indian creator covers TRT clinically.

**Patient journey:** Symptom-driven → GP → often only total testosterone tested (not free + SHBG) → either dismissal or unsupervised TRT via gym/supplement channels.

**Top creators:** **Major whitespace.** No premium-warm clinical TRT brand in India. Some urology clinics offer it unbranded. Closest: Apollo's andrology practice.

**Top SEO keywords:**
- Informational: "Low testosterone symptoms India", "testosterone levels by age India", "free testosterone vs total"
- Treatment: "TRT cost India", "testosterone replacement therapy doctor"
  **Hook architecture:**
- "Your total testosterone is 'normal' but you feel exhausted — here's why free testosterone and SHBG matter more."
- **Avoid:** "boost testosterone naturally" (Schedule J #43 Power to rejuvinate, #44 Premature ageing).
  **Reddit/community:** r/Testosterone (global with India cohort), r/IndianFitness TRT threads, gym WhatsApp groups (unsupervised — do not engage).

**Cadence:**
- Phase 0: long-form clinical SEO; thought-leadership essays
- Phase 1: founder LinkedIn essay series on executive metabolic health
- Phase 2: corporate executive bundle
  **Reference comparable:** Maximus Tribe (US, doctor-supervised TRT, premium-priced).

**B2B angle:** Executive male health program — quarterly hormonal panel, doctor follow-up, supervised TRT if indicated. Position carefully (corporate HR sensitivity).
 
---

### 2.7 Longevity

**Why this vertical drives LTV ceiling:** highest disposable-income cohort, wearable-adoption-mature, biomarker-curious post-Huberman/Attia popularization. ₹15,000–30,000 annual programs achievable.

**Patient journey:** Wearable data → curiosity → comprehensive biomarker panel (often via Healthians/Redcliffe) → fragmented interpretation → seek a doctor who reads wearable + lab + lifestyle data together.

**Top creators (clinical, India):** emerging. **Major whitespace** for a clinical-voice creator in India. Currently dominated by international voices (Peter Attia, Andrew Huberman, Rhonda Patrick).

**Top SEO keywords:**
- Informational: "ApoB India", "Lp(a) India", "VO2 max test India", "biological age test"
- Treatment: "comprehensive health checkup India", "longevity doctor online"
  **Hook architecture:**
- "ApoB > LDL. Here's why your standard lipid panel is missing half the story."
- "Your body has been keeping score. You can read it."
- **Avoid:** "reverse aging," "anti-aging cure" (Schedule J #43, #44).
  **Reddit/community:** r/longevity, r/Biohackers, founder/VC WhatsApp groups, podcast listeners.

**Cadence:**
- Phase 0: founder thought-leadership essays on LinkedIn; SEO on advanced-biomarker long-tails
- Phase 1: YouTube long-form clinical explainers (5-part biomarker series)
- Phase 2: corporate executive longevity program — highest LTV vertical
  **Reference comparable:** Function Health ($351M total raised: $53M Series A June 2024 a16z-led + $298M Series B November 2025 Redpoint-led at $2.5B valuation per TechCrunch). Membership model: biomarkers + AI medical intelligence + clinician review.

**B2B angle:** Highest-fit vertical for corporate executive programs. ₹15,000–30,000/executive/year realistic.
 
---

## 30/60/90 Day Operational Plan

### Days 1–30: Foundation Lock + SEO Sprint

**Acquisition foundation:**
- Day 1–7: Lock Figma component library + token system (per kyros-design-system)
- Day 8–14: Publish 5 SEO anchor articles (thyroid vertical priority — launch flagship)
- Day 15–21: Set up Google Business Profile for Bengaluru + Mumbai (where founder + first doctor coverage)
- Day 22–28: Launch email lead magnet ("Thyroid Panel Decoder" — doctor-reviewed PCOS phenotype quiz)
- Day 28–30: First founder LinkedIn essay + Instagram launch posts
  **Doctor + clinical foundation (parallel):**
- Day 1–10: Sign first 2 thyroid panel doctors (endocrinologists)
- Day 10–20: Doctor approval workflow operational (per kyros-clinical-compliance)
- Day 20–30: First 5 articles reviewed and live with NMC reg # bylines
### Days 31–60: Soft Launch + Content Velocity

**Acquisition velocity:**
- Day 31–45: Publish next 15 SEO articles (3 per vertical priority, including weight management preparatory content)
- Day 35: Launch YouTube channel with first 2 doctor-led explainers
- Day 40: Soft launch to closed list (100–300 pre-launch email signups)
- Day 45–55: First Reddit AMA (r/india, thyroid vertical, doctor + founder)
- Day 50–60: Founder LinkedIn cadence locks at 2 essays/week
- Day 55–60: WhatsApp Business API onboarding (utility templates approved)
### Days 61–90: Public Launch + Scale Foundations

- Day 61–70: Public launch PR push (Mint, Inc42, YourStory, The Ken, Economic Times Tech, Storyboard18 angle)
- Day 65: Bengaluru GBP + Mumbai GBP fully optimized with weekly post cadence
- Day 70–80: First published clinical outcomes pilot (N=50–100, "Thyroid symptom resolution in Indian patients on supervised levothyroxine"); co-authored where possible
- Day 75–85: Patient referral program live in app
- Day 80–90: Email list crosses 5,000; WhatsApp opt-in list crosses 2,000; YouTube channel crosses 1,000 subscribers
### Benchmarks that would change the plan

- **If by Day 60 organic SEO traffic < 5,000 monthly visitors** → content velocity is insufficient; double content budget or reduce vertical scope from 7 to 4.
- **If by Day 90 patient acquisition < 50 paying patients across all channels** → reconsider channel mix; possibly delay weight/PCOS verticals until thyroid is proven.
- **If CAC trending above ₹400 across the channel mix** → pause amplification channels (Tier 2), double down on Tier 1 (SEO + GBP + referral).
- **If doctor reviewer SLA > 72 hours per article** → bottleneck is doctor capacity, not content; recruit additional reviewers before scaling article cadence.
---

## What to Never Do

These are non-negotiable. Full regulatory rationale lives in kyros-clinical-compliance.

1. **No paid prospecting on Meta/Google as primary channel.** CAC math forbids it at ₹400–600 pricing. Retargeting only, 5% of spend cap.
2. **No clinical content without RMP credit on screen.** Pinned-comment credits don't count.
3. **No drug brand names** in public content. Generic/INN molecule names allowed in educational mechanism framing only.
4. **No before/after imagery** in any vertical.
5. **No engagement-bait questions** ("Comment below if this is you 👇").
6. **No fabricated testimonials, names, ratings, outcomes.**
7. **No "cure," "reverse," "guarantee," "miracle"** vocabulary.
8. **No music in clinical content** (per kyros-design-system).
9. **No emojis in carousels** beyond 1 per caption, never in opening line.
10. **No drift into wellness-app or D2C-health aesthetic.** Bouncy fonts, transformation photos, "level up your health" copy, mandala/paisley patterns — banned even in the warm 50/50 register.
11. **No advisory board members or doctors named who haven't publicly committed in writing.**
12. **No Twitter/X account openings** at this phase. Revisit Phase 2 with documented public-reply policy.
---

## Cross-References

- **kyros-public-site-strategy** — the full public website: SEO + AI Search Optimization strategy *and* execution (architecture, AISO/GEO, technical, schema, link building, validation/testing toolchains, ranking levers, KPIs, launch checklist). This skill's Tier-1 channel #1; the per-vertical keyword inventories below feed its clusters.
- **kyros-business-strategy** — CAC ceiling derivation, TAM/SAM/SOM per vertical
- **kyros-clinical-compliance** — vocabulary lists, doctor approval gate, regulatory rationale per vertical
- **kyros-design-system** — hook architecture, format × mode matrix, weekly production workflow, voice settings
- **kyros-b2b2c-partnerships** — doctor association partnerships (FOGSI, IADVL, IES), B2B side of doctor referral network
- **kyros-build-spec** — public website URL structure, schema markup implementation, GBP + WhatsApp + email infrastructure
 