---
paths:
  - "backend/app/adminui/**"
---

# Admin UI Rules (Super Admin + Coordinator portals)

The admin UI is server-rendered Jinja2 + HTMX + Alpine.js, mounted on the same FastAPI app
that serves the API. Same code, same DB session machinery, same RBAC primitives — but a
different authentication mechanism, a different response shape, and a stricter audit posture.

## Authentication: session cookies, not JWT

- The admin UI uses HttpOnly, Secure, SameSite=Lax session cookies.
- Cookie value is an opaque session ID. The session record lives in Redis (
  `session:admin:<uuid>` or `session:coord:<uuid>`) with a hard TTL.
- Login is `POST /admin/login` or `POST /coord/login` — separate from `/v1/auth/login`. Same
  argon2id verification, separate cookie issuance.
- CSRF protection via double-submit token. Every non-GET form includes a hidden CSRF token;
  the dependency `verify_csrf` checks it against the session.

## URL namespaces

- `/admin/*` — super admin only. The first `enforce_role(Role.SUPER_ADMIN)` dependency is on
  the router.
- `/coord/*` — coordinator only. The first `enforce_role(Role.COORDINATOR)` dependency is on
  the router.
- Never combine them in one tree. A super admin who needs to view what a coordinator sees uses
  the audit log, not a shared UI.

## HTMX patterns

- Endpoints return HTML fragments for `hx-target` updates, full HTML pages for navigation.
- The same view function detects HTMX by checking `request.headers.get("HX-Request") == "true"`
  and returns a fragment template vs a full page template.
- Use `hx-post` for form submission, `hx-get` for filtering and pagination, `hx-swap` for
  targeted updates.
- Avoid `hx-trigger="every Ns"` polling in the admin UI; queue-depth and refresh patterns use
  manual refresh buttons.

## Template structure

```
backend/app/adminui/templates/
├── base.html                 # shared layout, navigation, design tokens
├── admin/
│   ├── _layout.html          # admin-specific layout extending base
│   ├── dashboard.html
│   ├── doctors_list.html
│   ├── doctors_list_rows.html   # partial for HTMX swap
│   └── ...
└── coordinator/
    ├── _layout.html
    └── ...
```

- Partial templates have a leading underscore.
- Never share a template file across admin and coordinator namespaces. The visual register is
  similar, the data shown is different (clinical-content discipline).

## Coordinator UI: clinical content stripped

The coordinator portal must not render lab values, prescription contents, or doctor note
content — at any level. The route layer uses `CoordinatorXxxView` Pydantic schemas (clinical
fields omitted at the schema layer); the template layer must not display fields it doesn't
have, but a future bug where a doctor schema sneaks in is the failure mode. Templates use
explicit field names, never `{{ patient }}` or `{{ consultation }}` directly.

## Audit log on staff actions

Every state-changing admin action (deactivate doctor, refund payment, edit configuration)
writes to `ad_audit_log` with rich metadata including reason text from the form.

Read-only navigation (listing doctors, opening a doctor detail page) is also audit-logged but
at a lower verbosity (`action='admin_view_xxx'`).

## Money-mover actions require fresh authentication

Razorpay refund, doctor payout adjustments, and similar money-moving actions check that the
admin's session is "fresh" — re-authenticated within the last 10 minutes. Otherwise the action
form redirects to a confirmation step that requires password re-entry.

## Tailwind via design tokens

The admin UI uses the same design tokens as the rest of the platform. A Tailwind preset
consumed from `design-tokens/tailwind-preset.js` is compiled to a single
`backend/app/adminui/static/css/admin.css` at build time.

Do not introduce inline styles or hex colors in templates. The visual register matches the
patient-facing surface per `.claude/skills/kyros-design-system/SKILL.md`.

## Static assets

`backend/app/adminui/static/` is mounted under `/admin/static` and `/coord/static` via
StaticFiles. HTMX and Alpine.js are bundled (not loaded from CDN) for offline-development
parity and to avoid third-party CDN dependencies in production.

## What to read

- `docs/strategy/backend-strategy.md` §3 (FastAPI architecture — admin UI mounting)
- `docs/strategy/backend-strategy.md` §11 (RBAC — coordinator scoping rules)
- `.claude/skills/kyros-design-system/SKILL.md` (visual register, design tokens)
