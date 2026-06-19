# Kyros Patient App — Mobile UI Redesign · Execution Plan

> **Status:** Planning complete, approved for Phase 1. No code changed yet.
> **Created:** 2026-06-19 · **Branch:** dev
> **Goal:** Redesign the patient mobile app to a premium, warm-glassmorphism "luxury
> healthcare" visual language. More materiality and depth — floating cards, layered
> shadows, tactile surfaces, brighter ivory lighting. Less flat/presentation-like,
> stronger warmth/care/trust through light and materials (not more content).

---

## 0. How to resume in a fresh session

1. Read this whole file.
2. **Re-fetch the source design** (it is NOT in the repo — it lives in Claude Design):
   - Tool: `DesignSync` (load via `ToolSearch(query: "select:DesignSync")` first).
   - Project ID: `7fc3a3f8-daf8-4381-b600-0dc2d992b64d` (name: contains "Kyros Patient App").
   - Key files in that project:
     - `Kyros Patient App.dc.html` — **the main hi-fi design** (210KB, 11 sections)
     - `Kyros Home & Lifestyle Wireframes.dc.html` — low-fi exploration (101KB)
     - `uploads/mobile-app-flow.md` — route/screen flow spec
     - `screenshots/care.png`, `screenshots/home-p2.png`, `uploads/*.png` — visual refs
   - `get_file` returns a JSON blob; extract `.content` with python and save to a temp
     `.html`, then grep section markers (`<!-- ... -->`). The file is too big to read
     whole — read by section or use a sub-agent.
   - NOTE: `DesignSync` is normally for the `/design-sync` skill (pushing component
     libraries TO Claude Design). We are only using its **read** methods
     (`list_projects`, `list_files`, `get_file`) to pull the design. Do not run the
     full sync workflow.
3. The full design analysis and codebase audit are captured below — you should not need
   to redo them, but re-fetch the design HTML if you need exact pixel values for a
   specific component.
4. **Get user approval before editing code.** The user wants to approve each phase.

---

## 1. Source design — visual system reference

Three fonts: **Cormorant Garamond** (display/headings), **Newsreader** (data/metrics,
with `font-feature-settings: 'tnum'`), **DM Sans** (UI/body).

### Core palette (8 named + many derived)

| Name | Hex | Usage |
|------|-----|-------|
| Forest | `#21402F` | Primary actions, active nav, dark hero cards, primary buttons |
| Pine | `#3A5A45` | Secondary green, logo, icon strokes, "From Dr." tags |
| Sage | `#7D9079` | Tertiary green, P3 enrichment tier, illustrations |
| Canvas | `#ECE6DA` | Page/screen background tint |
| Card | `#F9F6EE` | Card surface background, tab bar background |
| Amber | `#C79740` | Data viz, softgel meds, payment action, notification dot |
| Terracotta | `#C2604A` | Heart-rate, alerts, errors, doctor avatar fallback |
| Success | `#4E7A53` | Checkmarks, "in range", taken/done states |

**Key derived colors:** text `#2A2E27`, text-2 `#6B6A5C`, text-3 `#8A8675`, text-4
`#A89F8A`, strikethrough `#9A9482`, inactive-tab `#98917C`, card borders `#E7E0D0`/
`#E2DBCB`, divider `#E0D9CA`, pill border `#D8D2C2`, page artboard `#CDC6B7`, light text
on dark `#F1EDE2`/`#E9EFE3`, input bg `#FFFDF8`, "in range" chip bg `#DCE3D5`, error text
`#9A4234`, amber-dark text `#8A6516`.

### Screen background (all phone screens)
`radial-gradient(130% 80% at 82% -5%, #f2ece0, #e7e1d2 60%, #e3ddcd)` — warm top-right
light source.

### Glassmorphism
- Standard: bg `rgba(255,253,248,.62–.66)` + `backdrop-filter: blur(10px)` + border
  `1px solid rgba(255,255,255,.7)` + radius 16–22 + shadow `0 10–12px 26–28px rgba(60,52,30,.10)`
- Tab bar: bg `#f9f6eecc` + `blur(12px)` + border-top `1px solid #e2dbcb`
- Payment (amber): bg `rgba(255,250,238,.7–.85)` + `blur(10px)` + border `1px solid #ecdcb4`
  + shadow `0 12px 28px rgba(150,110,30,.12)`

### Shadow system (layered, warm-tinted)
| Level | Value | Usage |
|-------|-------|-------|
| XS | `0 4px 12px rgba(60,52,30,.05)` | list items, small cards |
| S  | `0 5px 14px rgba(60,52,30,.05)` | state-matrix cards |
| M  | `0 6px 16–18px rgba(60,52,30,.06–08)` | standard cards |
| L  | `0 8px 20–22px rgba(60,52,30,.07–10)` | tab bar, info boxes, med detail |
| XL | `0 10px 24–26px rgba(60,52,30,.06–10)` | adherence/glass/info panels |
| 2XL| `0 12px 28px rgba(60,52,30,.10)` | glass content cards |
| 3XL| `0 14px 30px rgba(33,64,47,.2–.28)` | dark/hero cards (green-tinted) |
| Device | `0 18–20px 44–50px rgba(40,40,30,.28–.3)` | phone frames |

Rule: dark (Forest) cards carry **green-tinted** shadows; payment/amber carry
**amber-tinted** shadows; everything else **warm-brown** `rgba(60,52,30,...)`.

### Skeuomorphic medication icons (SVG, with inset shadows)
- **Capsule** 34×18, radius 9, fill `linear-gradient(90deg,#f4f1e8 50%,#bf6b4a 50%)`,
  shadow `inset 0 1px 1px #fff, 0 2px 3px rgba(0,0,0,.14)`
- **Tablet** 26×26 circle, `radial-gradient(circle at 34% 28%,#fff,#e6dfd0)` + 1px score line `#cdc6b4`
- **Softgel** 26×26 circle, `radial-gradient(circle at 34% 28%,#f3c87c,#c2891f)`,
  shadow `inset 0 1px 2px #ffe6ab, 0 2px 3px rgba(0,0,0,.16)`
- **Injection** 30×30 SVG syringe rotated 45°, body gradient `#f6f3ea→#fffdf8→#e6dfd0`,
  needle/plunger `#bf6b4a`

### Scales
- **Spacing:** 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,20,22,24,26
- **Radius:** 4,5,6,7,8,9,10,11,12,13,14,16,18,20,22,34,36,44,46, 50%(circle)
- **Font size:** 8,8.5,9,9.5,10,10.5,11,11.5,12,12.5,13,13.5,14,15,16,17,18,20,21,22,23,24,25,26,30,40,52

### Animations
- `spin` 1.3–1.4s linear infinite (spinners)
- `pulse` 0/100%→1, 50%→.4, 1.3s infinite (live/processing dots)
- `shimmer` bg-position -200px→400px, 1.4s infinite, gradient
  `linear-gradient(90deg,#ece5d5,#f6f1e6,#ece5d5)` size 400px (skeletons)

### Component patterns
- **Primary button:** bg `#21402F`, text `#F4EFE3`, radius 13–14 (or 22 pill), pad `11px 0`
- **Ghost button:** border `1.5px solid #21402F`/`#C0BBAB`/`#C8D0C2`, matching text
- **Amber button:** bg `#C79740`, text `#fff`, radius 13
- **Filter chip selected:** bg `#21402F`, text `#F4EFE3`, radius 16–18, pad `5–6px 13px`
- **Filter chip unselected:** bg `#F4F0E6`, border `1px solid #E0D9CA`, text `#6B6A5C`
- **Search/input:** bg `#FFFDF8`, border `1px solid #E7E0D0`, radius 13, placeholder `#A89F8A`
- **Toggle:** track 38×22 radius 12 (active `#3A5A45`), knob 18×18 white
- **Status chips:** "in range" bg `#DCE3D5`/text `#3A5A45`; "processing" bg `#F1E3C4`/text `#8A6516`

---

## 2. Eleven design sections (from `Kyros Patient App.dc.html`)

1. **Visual System Tile** — palette, type, treatments, components (the token source)
2. **Home — 3 phases:** Phase 0 empty (just onboarded) → Phase 1 payment pending →
   Phase 2 rich active treatment. Home is a *living dashboard, never empty*; missing
   data sources become gentle completion cards that fill in over the journey.
3. **Navigation** — recommended **5-tab** glass dock: Home · Care · Records · Reminders · Lifestyle
4. **Completion-card family** — P1 critical / P2 care-prep / P3 enrichment tiers + locked/contextual
5. **Care pipeline** — 6 states: Request → Awaiting assignment → Payment → Confirmed → Join window → Rx pending
6. **Records** — Vault (filtered list) → Detail (biomarker reference ranges) → Trends (charts)
7. **Reminders** — adherence ring, doctor-set meds (read-only, "From Dr." + lock),
   personal reminders, medication detail/history with missed-dose correction
8. **Lifestyle** — Not connected (blurred ghost preview + manual fallback) → Connected
   (activity rings, sleep bars, HR line) → Manual entry
9. **Coordinator chat** — emergency banner, message bubbles, composer
10. **IA rationale** — Q&A + avatar menu mock (Profile replacement)
11. **State matrix** — 8 universal states per surface: full · partial · empty · loading ·
    error · offline · privacy/locked · archived/done

---

## 3. Current codebase audit (mobile/)

**Stack:** Expo SDK 56, RN 0.85.3, React 19, expo-router (file-based), TanStack Query,
react-hook-form + zod. StyleSheet.create() everywhere (no NativeWind/styled-components),
strictly token-driven (no hex literals in components).

**UI deps already present (no new installs needed for most work):**
`react-native-reanimated` ~3.16, `expo-linear-gradient`, `expo-blur`, `@expo/vector-icons`
(Ionicons), `@shopify/react-native-skia` ~1.5, `victory-native` ~41, `expo-haptics`.

### Theme/token files (Phase 1 targets)
- `packages/design-tokens/src/tokens.ts` (workspace pkg `@kyros/design-tokens`) — source of truth
- `mobile/lib/theme.ts` — light/dark mapping, ThemeProvider, persisted preference
- `mobile/lib/design-tokens.ts` — re-export layer

**Current palette is COOL (navy/sky-mist light, forest-ink/jade dark) — the redesign
flips to WARM ivory/forest.** Tokens already include `glass`, `neumorph`, `skeu`,
`slider`, `tintSoft`, `motion` groups. Fonts loaded: CormorantGaramond (400/500/italic),
DMSans (400/500/600), TiroDevanagariHindi. **Newsreader is NOT loaded yet** — must add
`@expo-google-fonts/newsreader`.

### Current tab nav (`mobile/app/(tabs)/_layout.tsx`)
**6 tabs:** Home, Plan(consultations), Reports, Reminders, Inbox(notifications), Profile.
Floating frosted dock (64px), expo-blur on iOS/web, haptic on change, spring scale 0.97.
Desktop hides dock, renders `<WebSidebar>`.

### Existing shared components (`mobile/components/`, ~3,245 lines)
Button (5 variants), Card (6 variants), NeumorphCard, GlassCard, GlassTabBar, IconChip,
HapticPressable, AnimatedPressable, SkeuButton, SkeuToggle, KyrosSlider, AmbientBackground,
Skeleton/SkeletonCards, EmptyState, NeumorphInput, CaptureGuard, ErrorBoundary,
OfflineBanner, PrivacyShield, GoogleSignInButton. Web: WebSidebar, OpenInAppBanner,
DragDropUpload, PrintButton. Specialized: reminders/ReminderList, reports/ReportsFolderView,
specialty/SpecialtyNavigation.

### Existing screens
- **home.tsx** (~377) — greeting, avatar, hero gradient CTA, quick-actions grid (4),
  notes preview, care-plan card. Well implemented.
- **consultations.tsx** (~295) — upcoming/past, status pills, book CTA, pull-to-refresh.
- **reports.tsx** (~272) — FlatList, OCR status, upload FAB.
- **reminders.tsx** (~536) — form modal, adherence dialog, sliders, notifications, CRUD.
- **notifications.tsx** (~284) — list, unread badge, template routing.
- **profile.tsx** (~396) — identity card, grouped menu sections, theme toggle, sign out.
- Detail routes exist (likely partial): `consultations/[id]`, `consultations/book`,
  `reports/[id]`, `reports/upload`, `prescriptions/[id]`, `biomarkers/[name]`,
  `care-plans/[id]`, `education/[id]`, `insights`, `notes/index`, + profile sub-screens.

### Route inventory (from flow spec)
`(auth)/`: login, signup, verify-otp, forgot-password, reset-password.
`(onboarding)/`: welcome, consent, conditions, intake-form, health-sync, abha-link.
`(tabs)/`: home, consultations, reports, reminders, notifications, profile.
Stack: consultations/{book,[id],pre-consult-report,join/[id]}, reports/{upload,[id]},
biomarkers/[name], prescriptions/{index,[id]}, education/{index,[id]}, notes/index,
insights, notification-preferences, abha-settings, privacy-security, download-data,
delete-account. `app/design.tsx` = internal showcase, NOT a user screen.

**Healthcare UX rules (keep):** no PHI in titles/tab labels, explicit loading states,
reassuring empty states, Privacy Shield blurs PHI on background, CaptureGuard on
clinical screens, confirmation modals on destructive actions. Two form factors: phone
(dock) + desktop web (WebSidebar).

---

## 4. Current vs new — the deltas

| Area | Current | New design |
|------|---------|-----------|
| Tabs | 6 (Home, Plan, Reports, Reminders, Inbox, Profile) | **5** (Home, Care, Records, Reminders, Lifestyle) |
| Palette | Cool navy / sky-mist | **Warm ivory / forest** |
| Background | Flat color | **Radial warm gradient**, top-right light |
| Shadows | Neutral neumorphic | **Warm-tinted, 5 levels**, green/amber variants |
| Glass | Basic blur | **Warm glassmorphism** rgba ivory + white border |
| Cards | 7 variants (Neumorph/Glass/Card) | **Unified warm surface** + glass overlay |
| Fonts | 2 (Cormorant, DM Sans) | **3** (+Newsreader for data, tnum) |
| Notifications | Full tab | **Header bell icon** |
| Profile | Full tab | **Avatar menu overlay** |
| Lifestyle | — | **New tab** (wearables, rings, manual) |
| Med icons | Ionicons | **Skeuomorphic** capsule/tablet/softgel/syringe |
| States | Basic | **8-state matrix** everywhere |

---

## 5. Phased execution plan

### ✅ Phase 0 — Discovery (DONE)
Design fetched + analyzed, codebase audited, plan approved. This document.

### ▶ Phase 1 — Theme & token foundation (START HERE, needs approval)
Flip the token layer to warm ivory/forest. Touches everything downstream.
- `packages/design-tokens/src/tokens.ts`: new palette, 5-level warm shadow system
  (+ green/amber tint variants), warm glass values, radial-gradient bg, skeu med colors,
  8-state color matrix, Newsreader family + tnum, expand size scales.
- `mobile/lib/theme.ts`: remap light/dark to warm scheme.
- `mobile/lib/design-tokens.ts`: re-export updates.
- Add `@expo-google-fonts/newsreader`; load in `mobile/app/_layout.tsx`.
- **Verify** with `app/design.tsx` showcase before moving on.

### Phase 2 — Core component primitives
Modify: GlassCard (warm glass), NeumorphCard→WarmCard (ivory + warm shadow), Button
(Forest/Amber/Ghost), AmbientBackground (radial gradient), Skeleton (warm shimmer),
GlassTabBar (5-tab + glass), IconChip (forest pastels).
Create: `MedIcon` (skeuo SVG set), `CompletionCard` (P1/P2/P3 + locked), `PipelineStepper`,
`AdherenceRing` (SVG arc), `ActivityRings` (concentric SVG), `RangeBar` (biomarker),
`ChatBubble`, `AvatarMenu` (popover), `EmergencyBanner`, `DaySelector` (7-day circles).

### Phase 3 — Navigation restructure (6→5 tabs)
- `(tabs)/_layout.tsx`: Home · Care · Records · Reminders · Lifestyle.
- App-bar header: bell icon (→ notifications) + avatar (→ AvatarMenu).
- Rename: consultations→care, reports→records; add lifestyle; remove notifications &
  profile as tabs (reachable via header). Preserve routes/deep links — keep the old
  route files reachable as stack screens; only the *tab* set shrinks.

### Phase 4 — Screens (in order)
1. Home — 3-phase state machine (empty → payment-pending → rich)
2. Care — 6-state pipeline
3. Records — Vault + Detail (range bars) + Trends (victory-native charts)
4. Reminders — adherence ring, doctor-set vs personal, history + missed-dose correction
5. Lifestyle — connect/ghost-preview/connected(rings,bars,HR)/manual
6. Coordinator chat (new)
7. Avatar menu overlay (Profile replacement)

### Phase 5 — Polish & state matrix
Apply 8 universal states across surfaces; entrance/micro-interactions; verify both
form factors (phone dock + web sidebar); accessibility pass.

---

## 6. Decisions still open (confirm with user when relevant)
- Keep cool theme as an option, or fully replace? (Plan assumes **replace** the default;
  dark mode still supported, remapped warm.)
- Notifications & Profile: confirmed moving off the tab bar into the header (bell +
  avatar menu) per design section 10. Routes stay; only tab presence changes.
- Coordinator chat: new route needed (e.g. `app/chat/index.tsx` or `coordinator-chat`) —
  not in current route inventory.
- `make test` / typecheck require Docker for backend; mobile typecheck runs standalone.

## 7. Constraints (from CLAUDE.md / security.md)
- Healthcare platform: no PHI in tab labels, titles, logs, or fixtures (Faker only).
- Plan-before-edit; migrations reviewed (this redesign is frontend-only — no migrations
  expected). Get user approval per phase.
