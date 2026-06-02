---
paths:
  - "mobile/**/*.{ts,tsx}"
---

# Patient Mobile + Patient Web Portal Rules (Expo + RN + RN Web)

The `mobile/` subtree is Expo 51 with TypeScript strict, expo-router for navigation, and a
React Native Web build target for the patient web portal. One codebase, two artifacts (native
app + web portal).

## TypeScript posture

- `strict: true` in `tsconfig.json`. No `any` without an inline justification comment.
- All API response types come from generated types in `mobile/lib/api/generated/` (run
  `make openapi` then `make generate-clients` to regenerate). Never hand-write API types.
- Domain types (separate from API types) live in `mobile/types/`.

## Design tokens

- Import design tokens from `mobile/lib/design-tokens.ts` (typed export generated from
  `design-tokens/tokens.json`).
- **No hex literals in component code.** All colors come from `tokens.colors.*`. CI lints for
  this.
- Typography sizes, line heights, spacing, shadows, radii — all tokenized. No raw numbers
  except where a token doesn't exist (and that's a signal to add one).
- See `.claude/skills/kyros-design-system/SKILL.md` for the visual register.

## Component patterns

- Functional components only. No class components.
- Co-locate component, its types, and its tests in the same directory:
  ```
  mobile/components/Button/
  ├── Button.tsx
  ├── Button.types.ts
  ├── Button.test.tsx
  └── index.ts
  ```
- Primitives that exist in `kyros-design-system` (Button, Card, PullQuote, Stat, Tag) are
  shared with website and doctor portal via the design-tokens preset; their RN implementation
  lives in `mobile/components/primitives/`.

## RN Web compatibility

Patient web portal builds from the same RN code via `react-native-web`. Constraints:

- Use `react-native` imports, not direct DOM. `View`, `Text`, `Pressable`, `ScrollView`,
  `Image`, `TextInput`.
- Conditional platform code via `Platform.OS === 'web'` or `Platform.select({...})`. Keep
  these surgical — most components should be platform-agnostic.
- Native-only APIs (HealthKit, Health Connect, Expo notifications) are wrapped in
  `mobile/lib/native/` with web no-op fallbacks.

## Auth and storage

- Tokens stored in `expo-secure-store` on native, `localStorage` on web with a clear UX
  warning about device security.
- JWT access token has 60-min TTL. Refresh token rotates on use. On 401 with valid refresh,
  the client retries once with a refreshed token. On refresh failure, log out and route to
  login.
- Never log tokens. Never include them in error reports.

## State management

- Server state via TanStack Query (`@tanstack/react-query`). One query hook per resource:
  `useConsultations`, `useLabReports`, `useConsultation(id)`.
- Local UI state via `useState` and `useReducer`. Avoid Redux/Zustand unless the state spans
  >3 distant components.
- Form state via `react-hook-form` with `zod` schemas matching the API request shape.

## Navigation

- expo-router file-based routing. Routes under `mobile/app/`.
- Auth-gated routes live in `mobile/app/(authenticated)/`. Public routes (login, onboarding,
  password reset) live in `mobile/app/(auth)/`.
- Deep linking configured for all critical screens (open consultation, open lab report).

## Healthcare-specific UX rules

- **No PHI in screen titles or navigation breadcrumbs.** Tab labels are "Consultations" not
  "<patient name>'s Consultations."
- **Loading states for clinical content are explicit.** Lab values appearing then disappearing
  during reload looks like a data error to a worried patient.
- **Empty states reassure.** "No prescriptions yet" with helpful next-step copy, not just a
  blank screen.
- **Sensitive actions confirm.** Deletion, account closure, data export — modal confirmations
  with clear copy.

## Accessibility

- Every touchable has an `accessibilityLabel`.
- Color contrast meets WCAG AA against the chosen background tokens (verified via Storybook).
- Form inputs have visible labels (never placeholder-as-label).
- Critical flows (login, booking, prescription view) tested with screen reader on both iOS
  and Android.

## What to read

- `docs/strategy/frontend-strategy.md` — patient mobile + RN Web sections
- `docs/strategy/build-spec.md` — section 8 (Mobile app surface)
- `.claude/skills/kyros-design-system/SKILL.md` — visual register, format×mode matrix
