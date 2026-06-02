---
name: kyros-design-system
description: Design system tokens, visual register, and UI guidelines for the Kyros platform.
---
---
name: kyros-design-system
description: The single canonical home for how Kyros looks, sounds, and gets produced. Use this skill for any design, visual, brand, content production, or voice decision — color palette, typography, 50/50 media ratio, 60/40 dashboard ratio, photography direction, ElevenLabs voice settings, Figma component library, Jitter animation patterns, weekly content production workflow, format × mode matrix, warm-conversational hook architecture. This skill owns the visual and production register. Other skills reference operational facts here ("see production workflow") but do not duplicate color tokens, ratios, or hook examples.
sequence: 3 of 5 skills — read AFTER business-strategy and clinical-compliance
---

# Kyros Design System

This skill owns **how Kyros looks, sounds, and gets produced.** The visual register is premium-warm clinical — the lane Allara Health and Tia occupy internationally, not the lane Bodywise/Veera/&Me/Gynoveda occupy.

## Skill Read Order

1. kyros-business-strategy — positioning, model, unit economics
2. kyros-clinical-compliance — regulatory rules, vocabulary, doctor approval gate
3. **kyros-design-system** (this file)
4. kyros-customer-acquisition — D2C channel mix
5. kyros-b2b2c-partnerships — B2B partnership playbook
6. kyros-build-spec (product spec) — technical architecture + Claude Code prompts P1–P30
---

## Operating Principle (Visual Application)

Premium-warm clinical is not a half-step between austere-clinical and wellness-aesthetic. It is its own lane.

- **Austere-clinical** (Mayo Clinic website circa 2020): cold blue, dense type, no warmth. Wrong for Indian top-decile patient cohort — reads as institutional, not personal.
- **Wellness-aesthetic** (Bodywise, Veera, &Me, Gynoveda): pastel mandalas, lifestyle athleisure photography, "ancient wisdom" copy, hand-drawn icons. Wrong for Kyros — visually category-collapses into the supplement-D2C lane.
- **Premium-warm clinical** (Allara Health, Tia, Mayo Clinic 2024 refresh, Apple Health spots): warm color blocks (saffron, terracotta, peach mist), forest as anchor, real Indian context photography (chai, marigold, copper, window plant), italic Cormorant pull-quotes, typographic discipline, generous whitespace. **This is the Kyros lane.**
  If a piece visually drifts toward austere-clinical → add warmth (peach mist or sage field, italic Cormorant moment, warm photograph). If it drifts toward wellness-aesthetic → remove decoration, restore forest-ivory anchor, single-focal composition.

---

## Color Palette (Locked)

Eleven tokens. No others. Pastels, neons, gradient washes as full-page field, mandala color systems, ayurveda-cosmic palettes are all banned regardless of how warmly the rest of the piece reads.

### Anchor and companions

| Token | Hex | Usage |
|---|---|---|
| **Forest** | `#0F3D2E` | Primary brand. Headlines on warm backgrounds, primary CTAs, footer block, logo. Always somewhere on every page. |
| **Jade** | `#2D7A5F` | Saturated companion. Hover states, secondary headlines, color blocks, illustration fills. Not for body text. |
| **Sage** | `#8FA88E` | Soft supporting tint. Illustration fills at low opacity, secondary callouts, calm dashboard accents, field-eligible at 15–25% opacity. |

### Warm accents

| Token | Hex | Usage |
|---|---|---|
| **Saffron** | `#E08E3C` | Primary accent. Pull-quote borders, step numbers, stat-block accents, leader lines on illustrations, hover details. Used freely under 50/50, more sparingly under 60/40. Never as page-wide field. |
| **Terracotta** | `#C25A4A` | Emotional warmth accent. Sensitive-category pull-quote borders (PCOS, men's intimate, TRT), condition-page accent moments, reflective-close visual underlines. 1–2 times per page maximum. Never combined with Alert. |

### Backgrounds

| Token | Hex | Usage |
|---|---|---|
| **Ivory** | `#FAF1E4` | Default page background. Warmer cream with peachier undertone than typical clinical neutrals. |
| **Peach mist** | `#FCE4CC` | Warm section backgrounds, pillar card fills, sensitive-category section tints, home page warmth moments. Field-eligible. |
| **White** | `#FFFFFF` | Clinical card backgrounds, dashboard primarily, lab result tables, prescription views. |

### Text

| Token | Hex | Usage |
|---|---|---|
| **Ink** | `#1A1A1A` | Body text. Never compromised for warmth. |
| **Stone** | `#6B6B68` | Secondary text, captions, metadata. |

### System

| Token | Hex | Usage |
|---|---|---|
| **Alert** | `#B53A2B` | Emergency banner, in-person referral, danger states only. Visually distinguishable from Terracotta because Alert is darker and redder. Terracotta carries no warning meaning. |

### WCAG AA contrast pairs

Verified accessible pairings (4.5:1+ for body, 3:1+ for large text):
- Forest on Ivory (12.4:1) — primary
- Forest on Peach mist (10.2:1) — secondary
- Forest on White (13.1:1) — clinical cards
- Ink on Ivory (15.8:1) — body text
- Ink on White (18.5:1) — clinical body
- Stone on Ivory (5.2:1) — captions only
- Saffron on Forest (4.6:1) — accent text on dark
- Ivory on Forest (12.4:1) — CTA button text
### Color use principles

1. Forest is the spine. Every page anchors to forest somewhere — headlines, primary CTA, or footer.
2. Saffron is the primary accent. Punctuates the page in 3–5 moments, never as field.
3. Terracotta is the warmth accent. 1–2 times per page maximum, reserved for emotional moments.
4. Sage and Peach mist are field-eligible — full-section backgrounds at low opacity. Saffron and Terracotta cannot.
5. Jade is for color blocks (callouts, three-pillar backgrounds at low opacity) and hovers. Never body text.
6. Never use mandala patterns, paisley borders, gradient washes as field, or ayurveda-tropic illustration styles. These read as wellness-aesthetic regardless of palette discipline.
---

## Typography (Locked)

### Cormorant Garamond

- **Use for:** headlines, pull-quotes, large display numerals, the brand motto.
- **Italic ONLY for:** pull-quotes and the brand motto. Upright for everything else.
- **Color may be:** Forest, Saffron (display numerals only), Terracotta (pull-quote moments only), Ink.
- **Sizes:** headlines 22–48px, display numerals up to 96px.
- **Devanagari fallback:** Cormorant Garamond does not ship a Devanagari weight. Hindi/Marathi headlines use **Tiro Devanagari Hindi** as the fallback display face. Pair Cormorant Garamond English with Tiro Devanagari Hindi when bilingual.
### DM Sans

- **Use for:** body, navigation, UI elements, captions, all metadata.
- **Color always:** Ink or Stone. Never colored.
- **Sizes:** body 13–15px.
- **Devanagari support:** DM Sans includes Devanagari weights — no fallback needed.
### Hierarchy

- H1 (page hero): Cormorant Garamond 42–48px, Forest, upright, weight 500
- H2 (section heads): Cormorant Garamond 28–32px, Forest, upright, weight 500
- H3 (sub-sections): Cormorant Garamond 22–24px, Forest, upright, weight 600
- Pull-quote: Cormorant Garamond italic 24–32px, Forest or Terracotta border-left 4px
- Body: DM Sans 14–15px, Ink, line-height 1.6
- Caption: DM Sans 12–13px, Stone, line-height 1.5
- Display numeral: Cormorant Garamond up to 96px, Forest or Saffron, upright
---

## The 50/50 Media Ratio + 60/40 Dashboard Ratio

These ratios are the discipline mechanism that prevents drift between austere-clinical and wellness-aesthetic.

### 50/50 ratio (applies to all marketing surfaces)

Social posts, condition pages, home page, about page, video scripts, email templates — anything a non-patient sees before becoming a patient.

- **50% clinical character:** typography discipline, evidence-led copy, line illustration anchor, plain composition, single-focal moments
- **50% editorial warmth:** italic Cormorant pull-quotes, saffron and terracotta accents, color block sections (peach mist, sage tint), warm architectural photography, conversational hero copy, ivory/peach-mist backgrounds
### 60/40 ratio (applies to dashboard and patient-facing prescription/lab views)

Patient app, patient web portal, dashboard, prescription view, lab result trends — the clinical-utility surfaces.

- **60% clinical clarity:** dense information clarity, table-led data display, restrained color (white card on ivory field), system-typography spacing
- **40% warmth:** peach-mist welcome strip on dashboard home, sage tint on trend chart reference bands, saffron only for caution/highlight, terracotta absent unless emotional empty-state moment
### What the 50/50 unlocks (vs. the older 60/40 media ratio)

- Color block sections behind pillar moments and credibility blocks
- More frequent italic Cormorant pull-quote moments per piece, with terracotta accent borders
- Warm architectural photography in more places (social posts, condition section breaks)
- Sage and peach-mist fills inside line illustration strokes (previously strict 2D forest line only)
- Wider use of saffron and terracotta accents (still never as full-page field)
- Warmer color grading on photography — golden-hour light, lifted shadows, real Indian context objects
### What it does not unlock

- Lifestyle photography of women in athleisure
- Mandala, paisley, or ayurveda-tropic visual styles
- Transformation imagery
- Faces in stock photos
- Pill bottles, pill organizers, syringes
- 3D CGI organs
- Bouncy fonts, neon accents, motion drama
- Pastel mandala infographics
- Gradient washes as page-wide fields
- Wellness-app or D2C-health aesthetic drift
---

## Visual Rhythm 10-Step Pattern

Every page longer than ~400 words MUST break up prose with visual moments. Stacked text without rhythm is the single most common failure mode.

Apply in this rough order on long pages:

1. **Hero** — warm-conversational opener, single emotional line in Cormorant, plain-clinical sub-line in DM Sans. Background ivory or soft peach-mist gradient.
2. **Pillar block** — three-column or stacked outcome statements. Each pillar card sits on peach mist or sage-tint background with forest headline.
3. **Italic Cormorant pull-quote** — single line, terracotta or saffron border-left 4px, breaks the prose. Background ivory or soft sage tint.
4. **Plain-clinical body** — paragraphs with sourced specifics. Background white or ivory.
5. **Anatomical line illustration** — 2D, forest green strokes, saffron leader lines. Internal fills sage or peach mist at low opacity allowed.
6. **Stat block** — display numerals in Cormorant up to 96px (Forest or Saffron), saffron underline, ivory or peach-mist field.
7. **Process steps** — numbered with saffron numerals on white circles, plain-clinical descriptions, optional sage or peach-mist section field behind the full sequence.
8. **Warm architectural photograph** — north-light or golden-hour interior, hands-and-objects, real Indian context. Never faces unless founder/doctor with credentials.
9. **Reflective close paragraph** — returning to warm-conversational register. Often paired with terracotta horizontal rule above.
10. **CTA card** — single button (Forest fill with ivory text, or Saffron fill with Forest text on softer warmth pages). "Talk to a doctor" or "Take the assessment."
### Sensitive-category visual handling

For PCOS, men's intimate health, sexual health, TRT pages: hero opens with single empathetic line. Visual register softens through warmer peach-mist field backgrounds, terracotta accents instead of saffron in pull-quote moments, and slightly more frequent italic Cormorant — but the page still maintains 50/50. It does not flip into wellness-app aesthetic. Empathy through warmth-with-restraint, not empathy through decoration. No pastel mandalas, no soft-focus stock photography, no athleisure imagery.
 
---

## Photography Direction

### Light

- **Clinical and dashboard surfaces:** north-light still life, disciplined.
- **Marketing surfaces:** golden-hour or warm window light encouraged. Lift shadows toward saffron undertones. Avoid cool-blue clinical grading.
### Subject

Hands and objects. The objects warm up:

- A cup of chai on a wooden surface
- Marigold or jasmine flowers in soft focus
- A leather-bound notebook with a pen
- A window plant casting morning light
- Hands holding a glass of water beside a lab report
- An open journal page with hand-written notes
- A copper or terracotta water vessel
- Soft cotton fabric folds in warm light
### Faces

- **No stock photography of patients or doctors.** Ever.
- Founder real face permitted on About page and founder-voice social content with full credentials displayed.
- Doctor real face permitted on Our Doctors page and doctor-on-camera social content with NMC credentials displayed.
### Context

Subtle real Indian context welcomed — never overt. A copper vessel, not a tagged "Indian household." A marigold, not a pooja setup. The warmth signals "this brand understands the Indian patient" without resorting to cultural stereotypes.

### Banned

- Lifestyle photography of women in athleisure
- Mandala or pooja-style composition
- Smiling-doctor stock with white coat and stethoscope
- Pill bottles, pill organizers, syringes
- Before/after pairings of any kind
- Hands holding a smartphone showing the app
- Group composition (always single focal subject)
---

## Voice Settings (ElevenLabs)

Two voice profiles. Cloned founder voice for non-clinical brand storytelling only; Kyros Clinical Editor for clinical content. The regulatory rationale lives in kyros-clinical-compliance — this section covers the operational voice settings.

### Cloned Founder Voice

- **Voice ID:** to be assigned at voice clone creation (Niranjan's voice)
- **Stability:** 0.50 — natural variation
- **Similarity boost:** 0.75 — recognizable as founder
- **Style:** 0.30 — measured, warm-conversational
- **Speaker boost:** on
- **Use cases:** brand storytelling, founder narrative, why-Kyros-exists, how telehealth works, what to expect from a consultation flow
- **Never use for:** clinical claims, condition guidance, mechanism explanation, prognosis, contraindication
### Kyros Clinical Editor Voice

- **Voice ID:** pre-built ElevenLabs voice, gender-neutral, professional (recommended starting voice: "Rachel" or equivalent calm-clinical voice from ElevenLabs library)
- **Stability:** 0.65 — more consistent, less personal
- **Similarity boost:** 0.50
- **Style:** 0.20 — flat-professional
- **Speaker boost:** on
- **Use cases:** clinical content, mechanism education, condition guidance under doctor sign-off
- **Required overlays:** AI voice disclosure on-screen in first 3 seconds + reviewing doctor's NMC reg number visible at start
### AI disclosure (operational)

Both voices require on-screen disclosure: **"AI voice"** or **"AI-generated voice"** in the first 3 seconds, visible for the duration of the asset. Captions or description-only disclosure does not count.
 
---

## Figma Component Library Structure

Six-level hierarchy. Token-driven, not hex-coded.

```
01-foundations/
  ├── colors (locked palette as variables)
  ├── typography (Cormorant Garamond + DM Sans + Tiro Devanagari Hindi)
  ├── spacing scale (4/8/12/16/24/32/48/64/96)
  ├── elevation/shadows (clinical-restrained, no skeuomorphic depth)
  └── motion tokens (durations, easings — see Jitter section)
 
02-tokens/
  ├── semantic colors (brand-primary, brand-accent, surface, text, alert)
  ├── semantic spacing (gutter, section-padding, card-padding)
  └── semantic radii (card, button, input — restrained: 6/8/12px max)
 
03-primitives/
  ├── Button (Forest fill, Saffron fill, Outline, Ghost)
  ├── Input (text, dropdown, date, time)
  ├── Card (white-on-ivory, ivory-on-peach-mist)
  ├── Tag (NMC reg #, doctor specialty, vertical)
  ├── Stat (display numeral with caption)
  ├── Pull-quote (italic Cormorant, terracotta or saffron border)
  └── Icon (lucide-react base set, forest stroke)
 
04-components/
  ├── Navigation (4-item primary, 4-column footer)
  ├── Hero (warm-conversational + plain-clinical sub)
  ├── Pillar block (3-column outcome statements)
  ├── Process steps (numbered, saffron circles)
  ├── Doctor card (placeholder pattern for honest startup state)
  ├── Lab result row (biomarker + reference range + status)
  ├── Consultation card (status, doctor, date, type)
  └── CTA card (single button, warm field background)
 
05-patterns/
  ├── Condition page template
  ├── Dashboard home
  ├── Lab report detail
  ├── Pre-consultation report
  ├── Booking flow (3 screens)
  └── Honest placeholder (advisory board, doctors, testimonials)
 
06-templates/
  ├── Marketing page (50/50 ratio applied)
  ├── Dashboard page (60/40 ratio applied)
  ├── Email template
  ├── Carousel (Instagram, LinkedIn)
  ├── Reel cover (Instagram, YouTube short)
  └── Static post (1080×1080, 1080×1350)
```

**Discipline rule:** never type hex values into a Figma component. Always pull from `01-foundations/colors` variables. When palette migrates, components migrate automatically.
 
---

## Jitter Animation Patterns

Restrained motion. Fades, slow draws, subtle drifts. No bounce, no spring, no rapid cuts.

### Motion tokens

- **Micro-interactions** (button press, focus state): 120ms ease-out
- **Entrance** (element appearing on scroll): 220ms ease-out
- **Section transitions** (slide change, carousel advance): 450ms ease-in-out
- **Line draw** (anatomical illustration): 1200–1800ms ease-in-out
- **Pull-quote reveal:** 600ms ease-out fade-in
- **Stat numeral count-up:** 800ms ease-out
- **Photograph cross-fade:** 1000ms ease-in-out
### Banned animations

- Bounce (any spring overshoot)
- Rapid cuts (anything under 100ms between visual changes)
- Text bouncing in or sliding in from edges with velocity
- Rotating decorative elements (mandala-adjacent)
- Particle effects, sparkles, gradient sweeps
- Camera shake or zoom-pulse on hooks
- Synced-to-music motion (no music in clinical content anyway)
### Line illustration animation

Anatomical visuals are 2D line drawings in Forest green with Saffron leader lines. Internal fills (Sage, Peach mist) at low opacity allowed inside line strokes.

Animation: line strokes draw themselves over 1200–1800ms. Fills appear at low opacity after stroke completes (200ms fade). Leader lines appear last (300ms fade). Total reveal 1700–2300ms.
 
---

## "No Music in Clinical Content" Rule

Locked. Applies to all consultation-related video assets, condition explainer videos, mechanism-of-action videos, founder clinical commentary, doctor on-camera assets.

**Why:** music is the marker that separates "infomercial-aesthetic" from "premium-warm clinical." Even subtle background scores read as wellness-aesthetic or dramatic-cinematic on contact. Silence is the alternative — three seconds of silence at the close lands harder than music.

**Pacing without music:**
- 30-second Reels: hook (3s) → body (20s) → close (5s) → silence (2s)
- Long-form (60–90s): hook → 2 plain-clinical beats → close → silence
- YouTube long-form (12–20 min): voiceover at conversational pace, ambient silence at section breaks
  **Where music is allowed:**
- Brand storytelling video (cloned founder voice, non-clinical) — quiet ambient, never percussive or melodic-foregrounded
- Product walkthrough (app feature tour, dashboard explainer) — only if no condition is named in the asset
---

## Weekly Content Production Workflow

A target weekly rhythm. Six working days, ~5–7 hours of production time at 8–10 pieces/week once templates exist.

### Monday morning — Plan

- Pick 7–10 topics across categories. Reference customer-acquisition skill for vertical priorities and per-vertical hook architecture.
- Decide format and mode for each (see Format × Mode Matrix below).
- Draft scripts for all clinical content. Route to doctor reviewer.
### Tuesday–Thursday — Produce

- Open Figma template for the chosen format. Templates pull tokens from `01-foundations/colors` — never type hex values.
- Drop in copy. Adjust line illustrations as needed.
- Animate in Jitter. Export MP4.
- Generate cloned founder voice (where used, non-clinical only) once script is final.
- Generate Kyros Clinical Editor voice (where used, clinical only) once doctor approval is on file. Never before.
- Generate captions in Veed.io.
- Save to scheduled-posts folder.
### Friday morning — Schedule

- Drop into Buffer or Later.
- Confirm posting times.
- Confirm doctor sign-offs are on file for every clinical piece.
- Confirm AI voice/face disclosures are visible on every piece using cloned voice or AI imagery.
### Per-piece time budget (after templates exist)

| Format | Time |
|---|---|
| LinkedIn long-form (600–1500 words) | 45–60 min |
| Line-animation Reel (30–60s) | 30–45 min |
| Typographic motion (15–30s) | 15–25 min |
| Carousel (6 slides) | 25–40 min |
| Founder talking-head video (real face) | 30 min (10 record, 20 caption+trim) |
| Guideline-curated link post | 10 min |
| Stat-card still | 10–15 min |
| Cloned-voice clinical Reel (with doctor-approved script) | 25–35 min |

**If a piece is taking 2× the budget, the bottleneck is the template, not the content.** Spend a day fixing the template; the next ten pieces get fast.
 
---

## Format × Mode Matrix

Two axes, multiplied. Formats describe what the content looks like. Modes describe who appears or is accountable.

### 9 Formats

1. LinkedIn long-form post (written, 600–1500 words)
2. Anatomical line-animation Reel (30–60s motion video)
3. Typographic motion graphic (15–30s text-only motion)
4. Carousel (6 static slides, Instagram + LinkedIn)
5. Voice-only Reel (voiceover with single still card)
6. Founder talking-head video (real face, phone-shot, casual)
7. Guideline-curated link post (short, pointing to authoritative source)
8. Stat-card still (single image, no motion)
9. Patient-education PDF / shareable (long-form, off-algorithm)
### 5 Modes

- **A. Founder presence** — real face, cloned voice (non-clinical only), or real face + real voice
- **B. Faceless clinical** — line animation or typographic, doctor-reviewed, NMC credit on screen, Kyros Clinical Editor voice
- **C. Faceless educational** — anatomy/physiology, doctor-approved, no specific clinical claims requiring named reviewer prominence
- **D. Doctor presence** — doctor on camera or in voiceover with full credentials displayed
- **E. Curatorial** — pointing to and contextualizing external authority, no Kyros claims
### Matrix

| Format | Modes available | Notes |
|---|---|---|
| 1. LinkedIn long-form | A, E | Founder voice register |
| 2. Line-animation Reel | A (cloned non-clinical), B, C | Mode B requires Kyros Clinical Editor voice + AI disclosure |
| 3. Typographic motion | A (cloned non-clinical), B, C | Same |
| 4. Carousel | A, B, C, E | Mode-dependent |
| 5. Voice-only Reel | A (cloned non-clinical), B, C | Same |
| 6. Founder talking-head | A only | Real face, never clinical (cloned face ban remains) |
| 7. Guideline-curated link | E only | Always pointing outward |
| 8. Stat-card still | B, C, E | Mode-dependent |
| 9. PDF / shareable | B, C, E | Mode-dependent |

Approved format×mode combinations only. New combinations require explicit reopen.
 
---

## Warm-Conversational Hook Architecture

Every post and every condition-page hero opens with a **single emotional or evocative line.** Body is plain-clinical. Close is reflective.

### Structure

1. **Hook** — one emotional line. No fear. No second-person accusation. No engagement-bait question.
2. **Plain-clinical body** — sourced, doctor-approved, mechanism-and-evaluation framing for any treatment-adjacent content. 10–18 word sentences.
3. **Reflective close** — single line, reflective register. Not action prompt, not engagement question.
4. **Optional CTA card** — "Talk to a doctor" / "Take the assessment" / "Begin with a doctor." Separate visual moment from the close. Forest fill with ivory text, or Saffron fill with Forest text on softer warmth pages.
### Hook examples by vertical

- **Thyroid:** "She thought she was just tired. For three years."
- **Weight management:** "You've tried five things. None of them worked. That isn't a character flaw."
- **PCOS:** "Your cycle has been a question mark for years. It doesn't have to stay one."
- **Skin & hair:** "The mirror has been telling you something for a while."
- **Men's intimate (men's):** "Most Indian men carry this in silence for years. The silence is the worst part."
- **Hormones / TRT:** "You don't recognise the man in the photographs anymore."
- **Longevity:** "Your body has been keeping score. You can read it."
### Reflective close examples

- "Three years is a long time to feel like a stranger to yourself."
- "The first honest conversation about your weight should be with someone who measures, not someone who sells."
- "Some answers are quiet. They're still answers."
- "Skin keeps a record. A doctor reads it."
- "There's no version of waiting that helps."
- "Slowing down is universal. Disappearing isn't."
- "The best time to read the chart is before it tells a story."
### What hooks must NOT do

- Trigger fear ("the silent killer in your bedroom")
- Accuse the audience ("you're killing yourself by ignoring this")
- Demand engagement ("comment below if this is you 👇")
- Promise outcomes ("feel like yourself again in 14 days")
- Promote a treatment class ("GLP-1s are changing weight loss")
- Use wellness-aesthetic vocabulary ("balance your hormones", "ancient wisdom", "root-cause cleanse")
---

## Cinematic Visual Grammar

The 50/50 ratio unlocks a warm cinematic register. The grammar:

### Visual

- Slow, single-axis camera moves (push-in or pull-back, never both in one shot)
- Warm architectural light — north-facing window with soft warmth, or golden-hour single source, long shadows
- Color: forest and ivory anchor, saffron and terracotta as accents (never as field), sage and peach mist as field-eligible warm tints
- Hands, objects, anatomy — never faces unless founder real-face or doctor on camera
- Line animation drawing itself for any organ visual (forest strokes, saffron leader lines, sage or peach-mist fills appearing at low opacity after the draw completes)
- Italic Cormorant pull-quotes used freely, with terracotta or saffron accent borders
- Warm architectural still photography in social posts
- Color block sections (peach-mist or sage field) under hero typography or behind pillar cards
### Audio

- **No music in clinical content** (see rule above)
- Voiceover at conversational pace, not "narration" pace
- Silence allowed and welcome
- Cloned founder voice (non-clinical) or Kyros Clinical Editor voice (clinical) — both with on-screen AI disclosure
### Pacing

- 30-second Reels: hook (3s) → body (20s) → close (5s) → silence (2s)
- Long-form (60–90s): hook → 2 plain-clinical beats → close → silence
- No rapid cuts. No text bouncing in. Text fades or draws.
---

## Production Stack

### Design and animation

- **Figma** — templates, carousels, stat cards, layout. Shared library of color tokens.
- **Jitter** — animation, motion graphics, line-draw effects.
- **Canva** — quick variants, templated outputs (secondary).
- **ElevenLabs** — cloned founder voice + Kyros Clinical Editor voice.
### Captions and post-production

- **Veed.io** — captions, language variants, subtitle export.
- **Descript** — interview editing, founder talking-head trimming.
### Scheduling

- **Buffer** or **Later** — sufficient for 30–80 pieces/month across phases.
### Avoid

- Make.com / Zapier pipelines feeding programmatic video generators (Creatomate, Shotstack). Amplify compliance errors. Revisit if volume passes 100/month.
- HeyGen / Synthesia AI avatar platforms. Visually drift from premium-warm clinical; virtual influencer disclosure overhead adds friction.
- 3D CGI organ generators (Runway, Pika, Luma for organs). Aesthetic mismatch with Kyros's 2D line illustration spec.
---

## Migration from Prior Visual Register (Appendix — For Reference Only)

Earlier Kyros design work used a cream-and-forest palette with amber accent at 60/40 (media) and 70/30 (dashboard) ratios. The premium-warm clinical register supersedes this:

- Amber `#C8A35E` → Saffron `#E08E3C` (warmer, more saturated)
- Cream `#F4EFE6` → Ivory `#FAF1E4` (peachier undertone)
- Added: Jade, Terracotta, Sage, Peach mist
- 60/40 media → 50/50 media
- 70/30 dashboard → 60/40 dashboard
- Line illustration: strict 2D forest line → forest stroke + sage/peach-mist fills at low opacity allowed
  The new architecture (covered in kyros-build-spec) is being built from scratch under the new register. Prior Figma frames are not migrated; they are rebuilt under the new token system.

---

## Cross-References

- **kyros-business-strategy** — the three pillars copy that the visual treatment applies to
- **kyros-clinical-compliance** — voice policy rationale (this skill owns voice settings; compliance owns policy)
- **kyros-customer-acquisition** — which channels each format/mode targets
- **kyros-b2b2c-partnerships** — visual register for B2B materials (same system, more institutional treatment)
- **kyros-build-spec** — how design tokens are implemented in code (Tailwind config, design-tokens.ts, shared component library)
 