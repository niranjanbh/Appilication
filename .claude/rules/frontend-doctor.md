---
paths:
  - "doctor-portal/**/*.{ts,tsx}"
---

# Doctor Portal Rules (Vite + React 18)

The `doctor-portal/` subtree is a single-page application built with Vite 5, React 18,
TypeScript strict, Tailwind CSS, and TanStack Query. It is the doctor's primary clinical
workspace: patient panel, schedule, consultation room launcher, prescription writer, lab
review.

## TypeScript posture

- `strict: true`. No `any` without inline justification.
- API types from generated client at `doctor-portal/src/api/generated/`. Regenerate via
  `make generate-clients` after backend OpenAPI changes.
- Domain types in `doctor-portal/src/types/`.

## Design tokens and styling

- Tailwind config consumes `design-tokens/tailwind-preset.js`. No bespoke Tailwind config.
- Components use Tailwind utility classes that map to tokens. Custom CSS only for animations
  and layout primitives the design system doesn't cover.
- **No hex literals.** Colors come from `tokens.colors.*` via the Tailwind preset. CI lints.
- Typography classes come from the preset (`text-display`, `text-body`, etc.), not raw
  sizes.

## Component organization

```
doctor-portal/src/
├── api/
│   ├── client.ts             # axios/fetch wrapper with JWT injection
│   └── generated/            # OpenAPI-generated types and client
├── components/
│   ├── primitives/           # Button, Card, Input, etc. — match kyros-design-system
│   ├── clinical/             # Prescription, LabReportViewer, ConsultationRoom
│   ├── layout/               # AppShell, Sidebar, TopBar
│   └── ...
├── features/
│   ├── auth/                 # Login, password reset, MFA
│   ├── panel/                # Patient panel views
│   ├── schedule/             # Availability management
│   ├── consultation/         # Consultation room launcher + room
│   ├── prescription/         # Writer, signer, history
│   ├── lab-review/           # Pending review queue, OCR correction
│   └── ...
├── hooks/                    # Cross-feature hooks
├── lib/                      # design-tokens.ts, time/date helpers, formatters
├── routes/                   # React Router routes
└── types/
```

## State management

- Server state: TanStack Query. One hook per resource type. Aggressive cache invalidation on
  mutations.
- Form state: react-hook-form + zod.
- Cross-component UI state: Zustand store at `doctor-portal/src/store/`. Keep it small.
  Drafts (in-progress prescription, in-progress notes) live here with localStorage persistence
  via Zustand's `persist` middleware.

## Auth

- Session via JWT access + refresh, same as mobile.
- Tokens in localStorage. Cleared on logout, on refresh failure, and on tab close (optional
  setting per doctor preference).
- Doctor JWTs may include MFA status; routes requiring fresh MFA gate on that.

## Clinical UX rules

- **Drafts auto-save every 30 seconds to localStorage AND every 5 minutes to backend.** Power
  outage in a consultation is a real failure mode.
- **Prescription signing is a deliberate, confirmed action.** Two-step UI: review → sign.
  Signing locks the prescription and triggers PDF generation.
- **Lab values are presented with reference ranges, time series, and OCR confidence indicators.**
  Low-confidence OCR fields are visually distinct and prompt correction.
- **Patient names in route titles are minimal.** Use first name + last initial to reduce
  shoulder-surfing risk in clinical settings.
- **Consultation timer is visible during a call.** Slot-based pricing means doctors want to
  see elapsed time.

## Patient panel scoping

The patient panel shows only patients with whom the doctor has at least one consultation. The
backend enforces this via `list_patients_for_doctor_panel(doctor_id, ...)`. The client never
fetches "all patients" or tries to construct cross-doctor views.

## Performance budgets

- Initial bundle: ≤300KB gzipped (excluding video SDK).
- Route bundle: ≤100KB gzipped.
- Time to interactive on mid-range laptop: ≤2s for dashboard, ≤3s for patient panel.
- Code-split by route via React.lazy + Suspense.

## Video consultation

- 100ms SDK loaded lazily on consultation room route.
- The doctor JWT contains a 100ms-scoped token issued by the backend per consultation, not a
  persistent 100ms credential. See backend-strategy §7 (video provisioning beat task).
- Room join requires the doctor's recording-consent acknowledgement (per consultation, before
  joining).

## Accessibility

- WCAG AA contrast on all text and interactive elements.
- Keyboard navigation works for the entire flow (login → panel → consultation → prescription).
  Doctors using assistive tech are real and underserved by most telemedicine UIs.
- Form errors associated with inputs via `aria-describedby`.

## What to read

- `docs/strategy/frontend-strategy.md` — doctor portal section
- `docs/strategy/build-spec.md` — section 9 (Doctor portal)
- `.claude/skills/kyros-design-system/SKILL.md`
- `.claude/skills/kyros-clinical-compliance/SKILL.md` (RMP requirements for telemedicine UI)
