---
name: project-p5-status
description: P5 build status — public website foundation complete
metadata:
  type: project
---

P5 complete as of 2026-06-02.

**Why:** Build out the full public website (Next.js 14) including all pages, schema markup, booking flow, and the backend public endpoint.

**What was built:**
- 22 pages: home, conditions overview, 7 condition detail pages (SSG), how-it-works, pricing, about, advisory-board, our-doctors, for-doctors, faq, contact, book, 4 legal pages
- Visual rhythm 10-step pattern applied to all long pages
- Schema markup: MedicalCondition, MedicalWebPage, FAQPage, Organization, MedicalBusiness, HowTo, Person on all relevant pages
- Honest startup state on About, Advisory Board, Our Doctors (placeholder pattern)
- Booking flow: 3-step client component (condition → intake → contact) submitting to `/v1/public/booking-inquiry` via Next.js route handler proxy
- React-hook-form + zod added for form validation
- sitemap.ts and robots.ts auto-generated
- Backend: migration 0004 (ad_booking_inquiries table), public router (/conditions GET, /booking-inquiry POST)
- 42/42 tests pass; ruff + mypy clean; `pnpm build` produces all 22 pages cleanly

**How to apply:** Booking flow and forms require `pnpm install` in `website/` (added react-hook-form, zod, @hookform/resolvers). Makefile test target fixed to set JWT/OTP secrets for alembic step.
