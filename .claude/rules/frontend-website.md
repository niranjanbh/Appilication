---
paths:
  - "website/**/*.{ts,tsx,mdx}"
---

# Public Website Rules (Next.js 14 App Router)

The `website/` subtree is the public marketing surface: home, condition pages, how-it-works,
pricing, about, advisory board, our doctors, for doctors, FAQ, contact, legal pages, and the
MDX content system. It is the highest-trust surface — patients form their first impression
here.

## TypeScript posture

- `strict: true`. No `any` without inline justification.
- Component prop types are explicit. Avoid inferring complex props from JSX.

## App Router conventions

- Server Components by default. Add `"use client"` only when component needs client-side
  interactivity (forms, animations, tabs).
- Route handlers (`app/api/...`) act as light proxies to the FastAPI backend for public
  endpoints only (lead capture, booking inquiry). Never proxy authenticated endpoints — the
  patient app handles those directly.
- Use `next/image` for all images. Bandwidth on Indian mobile networks matters.
- Use `next/font` with Cormorant Garamond + DM Sans + Tiro Devanagari Hindi loaded as
  recommended in `.claude/skills/kyros-design-system/SKILL.md`.

## Design tokens and styling

- Tailwind config consumes `design-tokens/tailwind-preset.js`. Identical preset across all
  three frontends.
- **No hex literals in component code.** Colors from `tokens.colors.*`.
- Apply the 10-step visual rhythm pattern (per kyros-design-system) on long pages: alternate
  density, color background, full-bleed image, pull quote, stat row, etc.

## MDX content system

```
website/content/
└── learn/
    ├── thyroid/
    │   ├── _meta.json
    │   ├── hypothyroidism-symptoms.mdx
    │   └── ...
    ├── pcos/
    └── ...
```

MDX frontmatter:
```yaml
---
title: "Hypothyroidism Symptoms in Indian Women"
slug: "hypothyroidism-symptoms"
vertical: "thyroid"
doctor_author_id: "<doctor_uuid>"
doctor_reviewed_at: "2026-04-15"
references:
  - { citation: "...", url: "..." }
---
```

- Every clinical claim cites a peer-reviewed source via `<Citation>` component.
- Every article displays the reviewing doctor's name + NMC number + review date.
- See `.claude/skills/kyros-clinical-compliance/SKILL.md` for the doctor approval gate.

## Schema markup

Every page emits structured data via `app/.../page.tsx` JSON-LD:

- Home: `Organization`, `MedicalBusiness`.
- Condition pages: `MedicalCondition`, `MedicalWebPage`.
- Doctor pages: `Person` + `Physician`.
- Articles: `Article` + `MedicalScholarlyArticle` when applicable.
- FAQ pages: `FAQPage`.
- Doctor directory: `ItemList` of `Physician`.

Validate via Google Rich Results Test on every PR that touches a templated page.

## SEO discipline

- One `<h1>` per page.
- Canonical URLs set explicitly via metadata.
- Open Graph + Twitter card metadata on every page.
- `robots.txt` allows everything; `sitemap.xml` is generated at build via `next-sitemap`.
- Page slugs are lowercase, hyphenated, English. No transliteration in URLs.

## Performance budgets

- Lighthouse Performance ≥ 80 (mobile), ≥ 95 (desktop).
- Lighthouse SEO ≥ 95.
- Lighthouse Accessibility ≥ 95.
- LCP < 2.5s on a Moto G4 emulation.
- CLS < 0.1.
- INP < 200ms.

These are CI gates, not aspirational.

## Forms and lead capture

- Booking inquiry form → `POST /v1/public/booking-inquiry` on the backend.
- Lead capture form → `POST /v1/public/leads`.
- Both use react-hook-form + zod for client-side validation. Server validates again.
- No PHI in lead forms beyond name, email, phone, and one free-text "what brought you here"
  field. Detailed intake happens post-account-creation.
- CAPTCHA on all public forms (hCaptcha or Turnstile). Indian mobile-first audience requires
  CAPTCHA UX that works on small screens.

## Legal pages

These exist and must be kept current:

- `/privacy` — DPDP-compliant privacy notice.
- `/terms` — terms of use.
- `/telemedicine-consent` — the consent text users acknowledge during signup, versioned.
- `/data-deletion` — DPDP rights process.
- `/refund-policy`.

Each has a `last_updated_at` date. Changes go through legal review before merge.

## Phase scope on public website

Honest startup state applies. About, Advisory Board, and Our Doctors pages reflect actual
team and credentials at all times. No invented advisors, no aspirational doctor headcount.

See build-spec section 18 (Phase Scope on Public Website) for what is in Phase A vs B vs C.

## What to read

- `docs/strategy/frontend-strategy.md` — website section
- `docs/strategy/build-spec.md` — section 7 (Public website), section 18 (Phase scope)
- `.claude/skills/kyros-design-system/SKILL.md`
- `.claude/skills/kyros-clinical-compliance/SKILL.md` (doctor approval, claim discipline)
- `.claude/skills/kyros-customer-acquisition/SKILL.md` (SEO architecture)
