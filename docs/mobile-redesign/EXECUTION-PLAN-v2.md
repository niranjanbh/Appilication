# Kyros Patient App — Mobile UI Redesign · Execution Plan (v2)

> **Supersedes** `EXECUTION-PLAN.md` (v1). This version is grounded in the **actual** repository
> state (audited 2026-06-20), corrects path/scope errors in v1, and resolves governance conflicts
> between the hi-fi design HTML and the canonical `kyros-design-system` skill.
>
> **Status:** All phases (0–5) complete. Cool palette fully retired. Ready for device testing.
> **Created:** 2026-06-19 (v1) · **Revised:** 2026-06-20 (v2)
> **Branch:** dev
> **Goal:** Redesign the patient mobile app to a premium, warm-glassmorphism "luxury healthcare"
> visual language. More materiality and depth — floating cards, layered shadows, tactile surfaces,
> brighter ivory lighting. Less flat/presentation-like, stronger warmth/care/trust through light
> and materials.

---

## 0. Critical corrections to the v1 plan (read first)

The v1 plan was written against an assumed file layout that does not match the repo:

| v1 claim | Reality in repo | Impact |
|---|---|---|
| Token source is `packages/design-tokens/src/tokens.ts` | Source is **`design-tokens/tokens.json`** (root) + `design-tokens/tailwind-preset.js`. Consumed via `mobile/lib/design-tokens.ts` which imports the `@kyros/design-tokens` workspace package. | Every "edit tokens.ts" instruction in v1 targets a nonexistent file. |
| "Current palette is COOL, redesign flips to WARM" | tokens.json **already contains the full warm palette** (`forest #0F3D2E`, `ivory #FAF1E4`, `saffron #E08E3C`, `peachMist`, `jade`, `sage`, `terracotta`) alongside a legacy cool navy palette. The warm flip is **not a token rewrite — it is a `theme.ts` remap** plus purging legacy navy usage. | Far less risky than v1 implies. |
| "Add `@expo-google-fonts/newsreader`; load Newsreader for data (tnum)" | Only `cormorant-garamond`, `dm-sans`, `tiro-devanagari-hindi` are installed. **The canonical `kyros-design-system` skill locks typography to Cormorant + DM Sans + Tiro and does not include Newsreader.** | **Conflict.** See Decision D1. Default: do NOT add Newsreader; use DM Sans with `fontVariant: ['tabular-nums']`. |
| "Skeuomorphic medication icons (capsule/tablet/softgel/syringe)" | The canonical skill explicitly **bans** "pill bottles, pill organizers, syringes" and "skeuomorphic depth," mandating restrained elevation and 2D line illustration. | **Conflict.** See Decision D2. Default: 2D line icons on warm tint chips. |
| "Amber" accent (`#C79740`) | Canonical accent is **Saffron `#E08E3C`**; the appendix records `amber #C8A35E → saffron` migration. | Use `saffron` token everywhere v1 said "amber." |
| Component dir is flat `mobile/components/` | App primitives live in **`mobile/components/ui/`**; shared design-system primitives (`Button, Card, PullQuote, Stat, Tag`) live at `mobile/components/` root. New components follow `mobile/components/<Name>/` per rules. | Place new files correctly. |
| Bounce/spring presses everywhere | Canonical motion bans "bounce (any spring overshoot)" and mandates ease-out durations (120/220/450ms). | Decision D3: keep subtle spring (no overshoot) OR migrate to timing ease-out. |

**Governance rule:** where v1 (from the Claude Design hi-fi HTML) conflicts with the `kyros-design-system` skill, **the skill wins** unless the user explicitly overrides. All conflicts are surfaced in Section 7 (Open Decisions) for sign-off.

---

## 1. Source design — visual system reference (from v1, reconciled)

Three fonts: **Cormorant Garamond** (display/headings), **DM Sans** (UI/body + data with tabular-nums), **Tiro Devanagari Hindi** (Hindi). Newsreader omitted per D1 default.

### Core palette (reconciled with locked tokens)

| Name | Hex | Usage |
|------|-----|-------|
| Forest | `#0F3D2E` | Primary actions, active nav, dark hero cards, primary buttons |
| Jade | `#2E7D5B` | Success, checkmarks, "in range", taken/done states |
| Sage | `#7D9079` | Tertiary green, P3 enrichment tier, chart reference bands |
| Ivory | `#FAF1E4` | Page/screen background (light theme) |
| Peach Mist | `#FCE4CC` | Warm welcome strips, 40% warmth surfaces |
| White | `#FFFFFF` | Card surfaces (clinical clarity) |
| Saffron | `#E08E3C` | Data viz, caution, payment action, notification dot |
| Terracotta | `#C2604A` | Decorative only (emotional empty states), never sole carrier of meaning |
| Alert | `#B53A2B` | Errors, critical states |
| Ink | `#1A1A1A` | Primary text |
| Stone | `#6B6B68` | Secondary text (captions only — fails AA on ivory for body) |

### Screen background (light theme)
`radial-gradient(130% 80% at 82% -5%, #FCE4CC, #FAF1E4 55%, #F3E7D2)` — warm peach-mist top-right light source, ivory body.

### Glassmorphism
- Standard: bg `rgba(255,253,248,.62–.66)` + `backdrop-filter: blur(10px)` + border `1px solid rgba(255,255,255,.6)` + radius 16–22 + shadow `md`
- Tab bar: bg `rgba(249,246,238,.8)` + `blur(12px)` + border-top `1px solid rgba(15,61,46,.08)`
- Android fallback: solid `surfaceStrong` (no blur — already implemented)

### Shadow system (warm-tinted, restrained per skill)

| Level | Value | Usage |
|-------|-------|-------|
| xs | `0 2px 8px rgba(60,52,30,.05)` | List items, small chips |
| sm | `0 4px 12px rgba(60,52,30,.06)` | State-matrix cards |
| md | `0 8px 20px rgba(60,52,30,.08)` | Standard cards |
| lg | `0 12px 24px rgba(60,52,30,.10)` | Tab bar, info boxes, modals |
| hero | `0 12px 28px rgba(15,61,46,.25)` | Dark/hero cards (forest/green-tinted) |
| caution | `0 8px 20px rgba(224,142,60,.18)` | Saffron/payment cards |
| dark-xs | `0 2px 8px rgba(0,0,0,.35)` | Dark theme list items |
| dark-md | `0 8px 20px rgba(0,0,0,.40)` | Dark theme cards |
| dark-lg | `0 12px 24px rgba(0,0,0,.45)` | Dark theme elevated |

### Contrast verification (WCAG AA)

| Pair | Ratio | Status |
|------|-------|--------|
| Forest on Ivory | 12.4:1 | Pass (all uses) |
| Ink on Ivory | 15.8:1 | Pass (body text) |
| Stone on Ivory | 5.2:1 | Pass (captions only) |
| Saffron on Forest | 4.6:1 | Pass (CTA text) |
| Ivory on Forest | 12.4:1 | Pass (button text) |
| Saffron on Ivory | **2.8:1** | **FAIL — banned for text** |
| Terracotta on Ivory | **3.1:1** | **FAIL — decorative only** |
| IvoryText on ForestSurface (dark) | ~11:1 | Pass |
| Saffron on ForestInk (dark) | ~6:1 | Pass |

### Component patterns
- **Primary button:** bg `forest`, text `ivory`, radius 13–14 (or 22 pill), pad `11px 0`
- **Ghost button:** border `1.5px solid forest`, matching text
- **Saffron button:** bg `saffron`, text `white`, radius 13
- **Filter chip selected:** bg `forest`, text `ivory`, radius 16–18, pad `5–6px 13px`
- **Filter chip unselected:** bg warm tint, border `1px solid rgba(15,61,46,.08)`, text `stone`
- **Search/input:** bg `white`, border `1px solid rgba(15,61,46,.08)`, radius 13, placeholder `stone`
- **Toggle:** track 38×22 radius 12 (active `jade`), knob 18×18 white

### Animations
- Motion durations from tokens: micro 120ms, entrance 220ms, transition 450ms
- Easing: ease-out (per skill — no bounce/overshoot)
- `shimmer` — warm: `linear-gradient(90deg, #ECE5D5, #F6F1E6, #ECE5D5)` size 400px, 1.4s infinite
- `pulse` — 0/100%→1, 50%→.4, 1.3s infinite (processing dots)

---

## 2. Current codebase state (audited 2026-06-20)

**Stack:** Expo SDK 56, RN 0.85.3, React 19, expo-router, TanStack Query, react-hook-form + zod, TypeScript strict. RN New Architecture: components use native `boxShadow` strings and CSS gradient strings directly.

**Installed UI deps (no installs needed):**
`react-native-reanimated ~3.16`, `expo-linear-gradient`, `expo-blur ~56`, `@expo/vector-icons` (Ionicons), `@shopify/react-native-skia ~1.5`, `victory-native ~41`, `expo-haptics`.

**Token system:**
- `design-tokens/tokens.json` — source of truth. Already has: warm palette (11 locked tokens), legacy cool navy palette, `glass.{light,dark,blur}`, `neumorph`, `skeu`, `slider`, `tintSoft`, `typography`, `spacing`, `borderRadius`, `motion`.
- `design-tokens/tailwind-preset.js` — web/portal preset (keep in sync).
- `mobile/lib/design-tokens.ts` — typed RN re-export (`px()` strips "px"), `withAlpha()` helper, `colors/glass/neumorph/skeu/slider/tintSoft/fontFamily/fontSize/spacing/borderRadius/motionDuration`.

**Theme layer:**
- `mobile/lib/theme.ts` — `lightPalette` (currently **cool**: `background: skyMist`, `primary: navyDeep`, `text: navyDeep`) and `darkPalette` (forest-ink), `useTheme()`.
- `mobile/lib/theme-context.tsx` — `ThemeProvider`, persisted preference, `light|dark|system`. Default `'light'`.

**Fonts loaded** in `mobile/app/_layout.tsx`: Cormorant (400/500/italic), DM Sans (400/500/600), Tiro Devanagari. Loading screen + root Stack header still use **cool** colors (`skyMist`, `navyDeep`).

**Tab nav** `mobile/app/(tabs)/_layout.tsx`: 6 tabs (Home, Plan/consultations, Reports, Reminders, Inbox/notifications, Profile). Floating frosted dock (64px), expo-blur on iOS/web, haptic on change, spring scale 0.97.

**Components:**
- `mobile/components/ui/` — AmbientBackground, AnimatedPressable, AuthBackdrop, CaptureGuard, EmptyState, ErrorBoundary, GlassCard, GlassTabBar, GoogleSignInButton, HapticPressable, IconChip, KyrosSlider, NeumorphCard, NeumorphInput, OfflineBanner, PrivacyShield, Skeleton, SkeuButton, SkeuToggle.
- `mobile/components/` (shared primitives) — Button (variants `forest|saffron|outline|ghost|navy`), Card (`clay|dark|glass|flat|white|ivory`), PullQuote, Stat, Tag.
- Feature components — `reminders/ReminderList`, `reports/ReportsFolderView`, `specialty/SpecialtyNavigation`.

**Cool-palette debt** (to be purged):
- `theme.ts` light palette → navy
- `Button.tsx` → `navy` variant, `outline`/`ghost` use `navyDeep`
- `home.tsx` → hero gradient `[navyMid, navyDeep]`; quick-action tints include `blue`/`violet`
- `AmbientBackground.tsx` → light glows use `electricBlue`/`accentViolet`/`successLight`
- `design.tsx` → header `navyDeep`, light bg `skyMist`, `navy` button demo
- `_layout.tsx` → loading bg `skyMist`, header bg `navyDeep`
- `GlassCard.tsx` → light glass borderEdge navy-tinted `rgba(0,31,63,...)`

**Missing for redesign:** `lifestyle` tab + screen; coordinator chat route; `AdherenceRing`, `ActivityRings`, `RangeBar`, `CompletionCard`, `PipelineStepper`, `ChatBubble`, `AvatarMenu`, `EmergencyBanner`, `DaySelector`, `MedIcon` (pending D2).

---

## 3. Current vs new — the deltas

| Area | Current | New design |
|------|---------|-----------|
| Tabs | 6 (Home, Plan, Reports, Reminders, Inbox, Profile) | **5** (Home, Care, Records, Reminders, Lifestyle) |
| Palette | Cool navy / sky-mist | **Warm ivory / forest** (tokens already exist, theme remap) |
| Background | Flat color | **Radial warm gradient**, top-right peach-mist light |
| Shadows | Mixed / neutral | **Warm-tinted, 4 levels** + hero + caution variants |
| Glass | Basic blur, navy-tinted border | **Warm glassmorphism** ivory bg + forest-tinted border |
| Cards | 7 variants (Neumorph/Glass/Card) | **Unified warm surface** (Card/GlassCard, retire Neumorph) |
| Fonts | 2 Latin (Cormorant, DM Sans) + Tiro | Same, + `tabular-nums` for data |
| Notifications | Full tab | **Header bell icon** |
| Profile | Full tab | **Avatar menu overlay** |
| Lifestyle | — | **New tab** (wearables, rings, manual) |
| Med icons | Ionicons | **2D line icons on warm tint chips** (D2 default) |
| States | Basic | **8-state matrix** everywhere |
| Motion | Mixed springs | **Ease-out timing** (120/220/450ms), no overshoot |

---

## 4. Cross-cutting strategy (applies to all phases)

### 4.1 Android blur performance
The codebase already handles this: `CAN_BLUR = Platform.OS !== 'android'` in GlassCard/GlassTabBar.

**Improvements to standardize in Phase 2:**
- Centralize the capability check in `mobile/lib/platform/blur.ts` exporting `canLiveBlur` (currently duplicated).
- Cap concurrent live `BlurView`s per screen to ~3 (each is a GPU pass).
- **Never** put `BlurView` inside `FlatList` rows — use solid `surfaceStrong` cards in scrollables; reserve glass for chrome (dock, headers, modals, hero).
- Intensity ceilings from tokens (card 28, dock 42, shield 70).

### 4.2 Accessibility (enforced by CI lint + Phase 5 manual pass)
- No hex literals in components (existing CI lint).
- Every touchable keeps `accessibilityLabel` (existing pattern). New interactive components must accept and forward it.
- **Banned text colors on ivory:** saffron, terracotta (fail AA). Lint cannot catch — Phase 5 manual checklist.
- Respect `AccessibilityInfo.isReduceMotionEnabled()` — gate entrance animations, ring draws. Add `useReducedMotion()` hook.
- Dynamic type: verify at iOS XXL font scale.

### 4.3 Animation performance
- All animations on UI thread via Reanimated worklets (existing pattern).
- Ring/arc animations: Skia `Path` + animated `end` for 60fps (Skia is already a dep). Fallback: `react-native-svg` with reanimated `strokeDashoffset`.
- Durations from `motionDuration` tokens. Ease-out, no overshoot springs (D3).

### 4.4 Testing / verification strategy
1. **`design.tsx` showcase is the visual regression harness.** Extend each phase with new tokens/components.
2. **Typecheck per phase:** runs standalone (no Docker).
3. **CI hex-literal lint** must stay green every phase.
4. **Manual device matrix:** iOS (live blur), Android (solid fallback), web (CSS blur + WebSidebar). Verify after Phase 1 (theme), Phase 3 (nav), and each Phase 4 screen.
5. **Accessibility pass** in Phase 5: reduce-motion on, screen reader on critical flows.
6. **No PHI** in any new fixtures/labels (Faker only).

### 4.5 Sequencing principle
Each phase must leave the app **compiling and runnable**. Token additions are additive (never delete a token another file still imports until that file is migrated in Phase 5).

---

## 5. Phased execution plan

### Phase 0 — Discovery (DONE)
Design fetched/analyzed, codebase audited, plan written and revised.

---

### Phase 1 — Theme & token foundation (warm flip)

**Goal:** Light theme becomes warm ivory/forest; dark stays warm forest-ink; no cool navy on shared surfaces (loading, headers). App fully functional after this phase.

**Files & exact changes:**

#### 1.1 `design-tokens/tokens.json` (additive only)
- Add `shadow` group:
  ```json
  "shadow": {
    "xs": "0 2px 8px rgba(60,52,30,.05)",
    "sm": "0 4px 12px rgba(60,52,30,.06)",
    "md": "0 8px 20px rgba(60,52,30,.08)",
    "lg": "0 12px 24px rgba(60,52,30,.10)",
    "hero": "0 12px 28px rgba(15,61,46,.25)",
    "caution": "0 8px 20px rgba(224,142,60,.18)",
    "darkXs": "0 2px 8px rgba(0,0,0,.35)",
    "darkMd": "0 8px 20px rgba(0,0,0,.40)",
    "darkLg": "0 12px 24px rgba(0,0,0,.45)"
  }
  ```
- Add `gradient.screenWarm`: `"radial-gradient(130% 80% at 82% -5%, #FCE4CC, #FAF1E4 55%, #F3E7D2)"`
- Re-tint `glass.light.borderEdge` from `rgba(0,31,63,0.08)` → `rgba(15,61,46,0.08)`
- Add warm `tintSoft` entries for quick actions: `sage`, `peach`, `forest`, `saffron` pairs
- Do **not** remove legacy navy tokens yet (still imported elsewhere)

#### 1.2 `design-tokens/tailwind-preset.js`
- Mirror new `shadow`/`gradient` tokens for web portal parity.

#### 1.3 `mobile/lib/design-tokens.ts`
- Add typed re-exports: `shadow` group, `gradient` group.
- Add `numericProps = { fontVariant: ['tabular-nums'] as const }` for data/metric text.
- No breaking changes.

#### 1.4 `mobile/lib/theme.ts` — the core lever
Remap `lightPalette`:
- `background` → `colors.ivory` (was `skyMist`)
- `surface` → `colors.white`
- `surfaceMuted` → `colors.peachMist`
- `primary` → `colors.forest` (was `navyDeep`)
- `text` → `colors.ink` (was `navyDeep`)
- `textSub` → `colors.stone`
- `border` → `withAlpha(colors.forest, 0.08)` (was navy-tinted)
- `shadow` → `colors.forest` (warm-tinted shadow derivation)
- `navBar` → `colors.white`
- `success` → `colors.jade`
- `warning` → `colors.saffron`
- `critical` → `colors.alert`
- `skeletonBase` → `withAlpha(colors.stone, 0.12)`

`darkPalette` — confirm warm (already mostly warm):
- `primary` stays `saffron`
- `shadow` → `'#000000'`

#### 1.5 `mobile/app/_layout.tsx` — loading + root Stack
- `loadingBg` = `isDark ? colors.forestInk : colors.ivory`
- `loadingSpinner` = `isDark ? colors.saffron : colors.forest`
- Root Stack `headerBg` = `isDark ? colors.forestSurface : colors.forest`
- `contentStyle bg` = `isDark ? colors.forestInk : colors.ivory`

#### 1.6 Font decision (D1 default: no Newsreader)
- No new font install.
- `numericProps` export in design-tokens.ts covers tabular-nums for data display.
- If user overrides D1: `pnpm --filter mobile add @expo-google-fonts/newsreader`, load 3 weights in `_layout.tsx`, add `fontFamily.data` token.

**Acceptance criteria:**
- [ ] App launches; light theme shows ivory background, forest text, no navy on Home/loading/headers
- [ ] Dark theme unchanged-but-warm; toggle in profile works
- [ ] `design.tsx` palette grid renders; light bg is ivory, header is forest
- [ ] Typecheck + hex-lint green
- [ ] No removed token breaks an import

**Risks & mitigations:**
- *Navy still in `home.tsx`/`Button.tsx`/`design.tsx`* → cosmetic mismatch acceptable; purge in Phase 2/4
- *Shadow tint changes* → verify no shadow becomes invisible on ivory

---

### Phase 2 — Core component primitives

**Goal:** Warm-correct, reusable primitives. No screen restructure yet; screens still render with updated primitives.

**Modify:**

#### 2.1 `mobile/components/Button.tsx`
- Remove/retire `navy` variant (alias `navy → forest` for back-compat)
- `outline`/`ghost` use `colors.forest` not `navyDeep`
- Primary = forest, accent = saffron
- Motion: keep spring if no overshoot (damping 20, stiffness 500); else switch to `withTiming(220, easeOut)` (D3)

#### 2.2 `mobile/components/ui/AmbientBackground.tsx`
- Replace cool glows (`electricBlue/accentViolet/successLight`) with warm:
  - Light → `withAlpha(saffron, .08)`, `withAlpha(peachMist, .5)`, `withAlpha(sage, .10)`
  - Dark → keep `jadeGlow/saffron/sageDim`
- Consider replacing 3 LinearGradient blobs with single `gradient.screenWarm` radial (fewer layers, cheaper)

#### 2.3 `mobile/components/ui/GlassCard.tsx`
- Switch hardcoded `boxShadow` to shadow token (`shadow.md`)
- Warm tint over ivory; keep Android `surfaceStrong` fallback
- Extract `canLiveBlur` to shared helper `mobile/lib/platform/blur.ts`

#### 2.4 `mobile/components/ui/GlassTabBar.tsx`
- Use shared `canLiveBlur`; no logic change yet (5-tab in Phase 3)

#### 2.5 `mobile/components/ui/Skeleton.tsx`
- Warm shimmer gradient: `linear-gradient(90deg, #ECE5D5, #F6F1E6, #ECE5D5)` (light) / forest-tint (dark)
- Gate animation by reduce-motion

#### 2.6 `mobile/components/ui/IconChip.tsx`
- Warm tint pairs (sage/peach/forest/saffron) instead of cool

#### 2.7 `mobile/components/Card.tsx`
- `dark` variant already forest; ensure `clay/white` shadows use warm token
- `glass` border forest-tinted

#### 2.8 Deprecation: `NeumorphCard`, `SkeuButton`, `SkeuToggle`
- Add JSDoc `@deprecated` — do not use on new screens
- Migrate during Phase 4 screen rewrites
- Do not delete (still used by existing screens)

**Create** (co-located `mobile/components/<Name>/` with `.types.ts` + `index.ts`):

#### 2.9 New: `mobile/lib/platform/blur.ts`
- `canLiveBlur` boolean, `BlurConfig` type
- Single source for blur capability checks

#### 2.10 New: `mobile/lib/hooks/useReducedMotion.ts`
- Wraps `AccessibilityInfo.isReduceMotionEnabled()`
- Returns boolean, updates on change

#### 2.11 New: `mobile/components/AdherenceRing/`
- Skia animated arc, props `{ percent, size, label }`
- Reduce-motion aware (no draw animation, show final state)
- Colors: forest fill, stone track

#### 2.12 New: `mobile/components/ActivityRings/`
- Concentric Skia arcs (move/exercise/stand-style)
- Warm palette: forest/saffron/jade for the three rings
- Reduce-motion aware

#### 2.13 New: `mobile/components/RangeBar/`
- Biomarker reference range bar (low/in-range/high)
- Sage tint on in-range band, saffron/terracotta markers
- Pure layout (no Skia needed)

#### 2.14 New: `mobile/components/CompletionCard/`
- P1 (critical) / P2 (care-prep) / P3 (enrichment) + locked state
- Warmth: peach-mist (P1), white (P2), sage-tint (P3)
- Locked: muted + lock icon overlay

#### 2.15 New: `mobile/components/PipelineStepper/`
- 6-state care pipeline (horizontal stepper)
- Forest active, stone inactive, saffron pending-payment

#### 2.16 New: `mobile/components/ChatBubble/`
- Inbound/outbound variants
- "From Dr." tag, timestamp
- No PHI in fixtures (Faker)

#### 2.17 New: `mobile/components/EmergencyBanner/`
- Uses `colors.alert` (not terracotta)
- `accessibilityRole="alert"`

#### 2.18 New: `mobile/components/DaySelector/`
- 7-day circle row for reminders
- Today highlighted with forest, others stone

#### 2.19 New: `mobile/components/AvatarMenu/`
- Popover/overlay via `Modal` + warm glass
- Theme toggle, sign-out, profile sub-links

#### 2.20 New: `mobile/components/MedIcon/` (D2 default: 2D line icons)
- Default: Ionicons outline (`medical-outline`, `ellipse-outline`, `water-outline`) on tint chips
- If user overrides D2: skeuomorphic SVG set (capsule/tablet/softgel/syringe per v1 spec)

**Acceptance criteria:**
- [ ] All listed components render in `design.tsx` (light + dark) with no navy/cool literals
- [ ] AdherenceRing/ActivityRings animate at 60fps on device; freeze with reduce-motion
- [ ] Existing screens still compile and render with updated primitives
- [ ] Typecheck + hex-lint green
- [ ] Each new component accepts `accessibilityLabel`

**Risks & mitigations:**
- *Skia arc complexity:* prototype AdherenceRing first; fallback to `react-native-svg` strokeDashoffset
- *Component sprawl:* new components are additive; screens adopt them only in Phase 4

---

### Phase 3 — Navigation restructure (6 → 5 tabs)

**Goal:** Home · Care · Records · Reminders · Lifestyle. Notifications + Profile move to header.

**Files & changes:**

#### 3.1 `mobile/app/(tabs)/_layout.tsx`
- Rebuild `TABS` to 5: `home`, `care` (was consultations), `records` (was reports), `reminders`, `lifestyle`
- **Strategy (D4 default): relabel only, keep filenames.** Tab labeled "Care" still routes to `consultations.tsx`; "Records" still routes to `reports.tsx`. Avoids cascading `router.push` breakage.
- Notifications + Profile: set `href: null` on their tab entries (keeps file location, removes from bar, deep links survive)
- Update Ionicons for new labels
- Add `headerRight` with `HeaderBell` (→ notifications) and `HeaderAvatar` (→ AvatarMenu)
- Warm header colors

#### 3.2 New: `mobile/app/(tabs)/lifestyle.tsx`
- Minimal scaffold (empty/not-connected state) so the tab is functional
- Full build in Phase 4.5

#### 3.3 New: `mobile/components/ui/HeaderBell.tsx`
- Unread badge from notifications query
- Taps → notifications screen

#### 3.4 New: `mobile/components/ui/HeaderAvatar.tsx`
- Opens `AvatarMenu` overlay

#### 3.5 `mobile/components/web/WebSidebar.tsx`
- Mirror the 5-item nav + notifications/profile entries
- Warm palette

#### 3.6 `mobile/app/_layout.tsx`
- Register coordinator chat route as stack screen: `app/chat/index.tsx` (scaffold only, D5)

#### 3.7 New: `mobile/app/chat/index.tsx`
- Scaffold with placeholder content

**Acceptance criteria:**
- [ ] 5 tabs render with warm glass dock (iOS/web blur, Android solid)
- [ ] Bell + avatar in header; tapping bell → notifications; avatar → AvatarMenu overlay
- [ ] All deep links work: `/consultations/[id]`, `/reports/[id]`, `/notifications`, `/profile` sub-routes
- [ ] WebSidebar shows matching nav
- [ ] App runs on all 3 targets (iOS, Android, web)

**Risks & mitigations:**
- *Lost deep links* → use `href: null` instead of deletion; smoke-test each route
- *Renames cascade* → D4 defers renames; only labels change

---

### Phase 4 — Screens (in order; each independently shippable)

Apply primitives + warm register screen-by-screen. Each sub-step leaves app runnable.

#### 4.1 Home (`mobile/app/(tabs)/home.tsx`)
- Replace cool hero gradient `[navyMid, navyDeep]` → `[jade, forest]`
- Avatar gradient same warm
- Quick-action tints → warm (`sage/peach/saffron/forest`)
- Replace `NeumorphCard` → `Card`/`GlassCard`
- Add peach-mist welcome strip (60/40 warmth)
- **3-phase state machine:** empty (just onboarded) → payment-pending → rich active, using `CompletionCard` tiers
- Acceptance: no navy literals; 3 states render; reduce-motion respected

#### 4.2 Care (`mobile/app/(tabs)/consultations.tsx` + `consultations/[id].tsx`, `book.tsx`)
- 6-state pipeline via `PipelineStepper`
- Status pills warm
- Book CTA forest
- Preserve pull-to-refresh

#### 4.3 Records (`mobile/app/(tabs)/reports.tsx` + `reports/[id].tsx`, `biomarkers/[name].tsx`)
- Vault list: solid `surfaceStrong` cards (no blur in FlatList per §4.1)
- Detail: `RangeBar` for biomarker reference ranges
- Trends: victory-native charts (sage reference bands, forest line, tabular-nums labels)

#### 4.4 Reminders (`mobile/app/(tabs)/reminders.tsx` + `ReminderList`)
- `AdherenceRing` header
- Doctor-set (read-only, "From Dr." tag + lock) vs personal
- `DaySelector`
- History + missed-dose correction
- Med icons per D2

#### 4.5 Lifestyle (`mobile/app/(tabs)/lifestyle.tsx`)
- Not-connected: ghost preview (blurred) + manual fallback
- Connected: `ActivityRings`, sleep bars, HR line (victory-native)
- Manual entry form
- Wearable APIs in `mobile/lib/native/` with web no-ops

#### 4.6 Coordinator chat (`mobile/app/chat/index.tsx`)
- `EmergencyBanner` (alert color)
- `ChatBubble` list + composer
- Faker fixtures, no PHI

#### 4.7 Avatar menu (wired in header via `HeaderAvatar`)
- Profile replacement overlay
- Theme toggle, sign out
- Profile sub-links (payments, sessions, privacy-security, etc. — routes preserved)

**Per-screen acceptance:**
- [ ] Warm palette, primitives adopted
- [ ] Loading/empty/error states explicit and reassuring (healthcare UX)
- [ ] CaptureGuard on clinical screens retained
- [ ] PrivacyShield still covers backgrounded PHI
- [ ] Typecheck + hex-lint green
- [ ] Device matrix smoke test

---

### Phase 5 — Polish, state matrix & accessibility

- Apply **8 universal states** (full · partial · empty · loading · error · offline · privacy-locked · archived/done) consistently via `EmptyState`/`Skeleton`/`OfflineBanner`/`PrivacyShield`
- Entrance micro-interactions (ease-out, reduce-motion gated)
- **Full accessibility pass:**
  - Contrast audit (saffron/terracotta text ban enforced)
  - Screen reader on login/booking/prescription
  - Dynamic type at iOS XXL
  - Reduce-motion verification
- Verify both form factors (phone dock + WebSidebar)
- **Token cleanup:** grep for legacy cool references; once zero files import navy tokens, remove:
  - `navyDeep`, `navyMid`, `skyMist`, `iceBlue`, `coolGray`, `electricBlue`, `accentViolet` from tokens.json + design-tokens.ts + tailwind-preset.js
- Update `design.tsx` to reflect final system; retire `navy` button demo

**Acceptance:**
- [ ] Zero cool-palette references (grep clean)
- [ ] All 8 states present on every surface
- [ ] Accessibility checklist signed off
- [ ] Both form factors verified (phone + web)

---

## 6. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| v1's wrong paths cause edits to nonexistent files | High | §0 corrections; all paths in this doc verified against repo |
| Skill-vs-hifi conflicts (Newsreader, skeuo, amber, bounce) | High | Decisions D1–D3 default to locked skill; user override required |
| Android blur jank | Medium | Centralized `canLiveBlur`, no blur in lists, intensity caps (§4.1) |
| Tab rename cascades break router.push calls | Medium | D4: relabel only, keep filenames; `href: null` for removed tabs |
| Removing navy tokens breaks an importer | Medium | Additive-only until Phase 5 grep-clean removal |
| Skia ring perf/integration | Medium | Prototype first; svg fallback |
| Contrast failures (saffron/terracotta on ivory) | Medium | Lint can't catch; Phase 5 manual checklist |
| Reduce-motion not honored on new animations | Low | `useReducedMotion()` hook gating all entrances/arcs |

---

## 7. Decisions (LOCKED — 2026-06-20)

- **D1 — Newsreader font: YES (override)** — Add `@expo-google-fonts/newsreader` for data/metrics display. Luxury typography: display serif (Cormorant) + data serif (Newsreader) + UI sans (DM Sans).
- **D2 — Skeuomorphic med icons: YES (override)** — Keep skeuomorphic SVG set (capsule/tablet/softgel/syringe with gradients and inset shadows). Keep NeumorphCard/SkeuButton/SkeuToggle. Premium materiality > flat compliance.
- **D3 — Spring motion: YES** — Keep subtle springs (high damping, no overshoot) on presses. Use ease-out `withTiming` for new entrances. Natural iOS-like feel.
- **D4 — Tab route renames: RELABEL ONLY** — Keep `consultations.tsx`/`reports.tsx` filenames; tabs read "Care"/"Records". Avoids cascade breakage.
- **D5 — Coordinator chat route: `app/chat/index.tsx`** — Confirmed.
- **D6 — Cool theme retirement: FULLY REPLACE** — Warm ivory/forest is the Kyros identity. No cool theme option.
- **D7 — Warm radial screen gradient: YES** — `gradient.screenWarm` token applied on screen roots. Luxury light-source effect.

---

## 8. Verification commands

```bash
# Typecheck (runs standalone, no Docker)
pnpm --filter mobile tsc --noEmit

# Hex-literal lint (existing CI)
pnpm --filter mobile lint

# Grep for cool-palette debt (Phase 5 cleanup)
grep -rE "navyDeep|navyMid|skyMist|electricBlue|accentViolet|iceBlue|coolGray" mobile/

# Shadow consistency check
grep -rn "boxShadow" mobile/components/ mobile/app/
```

---

## 9. How to resume in a fresh session

1. Read this whole file (`docs/mobile-redesign/EXECUTION-PLAN-v2.md`).
2. Check which phase is current (status markers above).
3. For the design source, use `DesignSync` read methods (see v1 §0 for project ID / file names).
4. **Get user approval before editing code.** The user wants to approve each phase.
