# Dev-to-Production Checklist

Values used during development/testing that need production replacements before go-live.

| Variable / Config | File | Dev Value | Production Action | Date |
|---|---|---|---|---|
| `KYROS_MFA_ENCRYPTION_KEY` | `backend/.env` | Placeholder `<generate-32+-random-chars>` | Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` | 2026-06-23 |
| `EAS projectId` | `mobile/app.json` | `b1a2763c-...` (dev account) | Confirm this is the production Expo project or create a new one | 2026-06-23 |
| `KYROS_RAZORPAY_KEY_ID` | `backend/.env` | Not set | Get live key from Razorpay dashboard | 2026-06-23 |
| `KYROS_RAZORPAY_KEY_SECRET` | `backend/.env` | Not set (blank → signature check is skipped in dev, logs a warning) | REQUIRED: app now refuses to boot in production if blank. Get live secret from Razorpay dashboard | 2026-06-25 |
| `KYROS_RAZORPAY_WEBHOOK_SECRET` | `backend/.env` | Not set (blank → webhooks rejected) | REQUIRED: app now refuses to boot in production if blank. Configure webhook in Razorpay and copy secret | 2026-06-25 |
| `KYROS_AUTHKEY_API_KEY` | `backend/.env` | Not set | Get from Authkey/MSG91 dashboard | 2026-06-23 |
| `KYROS_SENTRY_DSN` | `backend/.env` / SSM `/kyros/production/backend` | Not set — **confirmed still empty in live prod** as of 2026-06-12 go-live (no error reporting in production) | Create Sentry project, copy DSN, set in SSM param (file → `jq .` validate → `put-parameter`), restart backend | 2026-06-23 |
| `KYROS_GOOGLE_OAUTH_CLIENT_IDS` | `backend/.env` | Not set (setting up now) | Use production Google Cloud client IDs | 2026-06-23 |
| `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` | `mobile/.env` | Not set (setting up now) | Use production Google Cloud web client ID | 2026-06-23 |
| `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID` | `mobile/.env` | Not set (setting up now) | Use production Google Cloud iOS client ID | 2026-06-23 |
| `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID` | `mobile/.env` | Not set (setting up now) | Use production Google Cloud Android client ID | 2026-06-23 |
| Apple Team ID | `mobile/eas.json` | `REPLACE_WITH_APPLE_TEAM_ID` | Get from Apple Developer account | 2026-06-23 |
| App Store Connect App ID | `mobile/eas.json` | `REPLACE_WITH_APP_STORE_CONNECT_APP_ID` | Create app in App Store Connect | 2026-06-23 |
| Android SHA-1 fingerprint | Google Cloud Console | Dev keystore SHA-1 | Verify matches production signing key | 2026-06-23 |
| `KYROS_LIVEKIT_API_KEY` | `backend/.env` | `APIkyros877055598d` (dev key) | Generate production key on LiveKit server | 2026-06-25 |
| `KYROS_LIVEKIT_API_SECRET` | `backend/.env` | Dev secret (see `.env`) | Generate production secret on LiveKit server | 2026-06-25 |
| `KYROS_LIVEKIT_HOST` | `backend/.env`, `infra/ecs/task-def-{backend-api,celery-worker}.json` | dev `ws://livekit:7880`; ECS placeholder `wss://video.kyrosclinic.com` | Confirm the production WSS hostname and point it at the deployed `ap-south-1` LiveKit server (rule #14 data residency) | 2026-06-26 |
| `KYROS_LIVEKIT_RECORDINGS_BUCKET` | `backend/.env`, `infra/ecs/task-def-{backend-api,celery-worker}.json` | dev not set; ECS placeholder `kyros-prod-recordings` | Create the S3 bucket in `ap-south-1` with bucket-default SSE-KMS encryption (rule #6). Set `KYROS_S3_KMS_KEY_ID` and configure bucket default encryption to `aws:kms` with that key | 2026-06-26 |
| `KYROS_LIVEKIT_API_KEY` / `_SECRET` (ECS) | `infra/ecs/task-def-{backend-api,celery-worker}.json` | Secrets Manager refs `kyros/prod/backend:livekit_api_key` / `:livekit_api_secret` | Create those two keys in the `kyros/prod/backend` Secrets Manager secret with the production LiveKit key pair (replaces the removed HMS secret refs) | 2026-06-26 |
| LiveKit server config keys | `infra/docker/livekit/livekit.yaml` | Dev key pair | Must match `KYROS_LIVEKIT_API_KEY`/`SECRET` in production | 2026-06-25 |
| LiveKit web SDK (admin/coord join page) | `backend/app/adminui/static/vendor/livekit-client.umd.min.js` | ✅ Vendored (livekit-client 2.20.0 UMD min) | Done — bundled, not CDN. `/admin/static` and `/coord/static` mount the same dir, so one file serves both. On SDK upgrade, re-copy from `node_modules/livekit-client/dist/livekit-client.umd.js` | 2026-06-26 |
| `POSTGRES_PASSWORD` | postgres container env / SSM `/kyros/production/backend` | Real prod value, but **exposed in chat during 2026-06-12 deploy debugging** | ROTATE: generate new password, update SSM param (file → `jq .` validate → `put-parameter`), restart postgres + backend + worker + beat | 2026-06-27 |
| `KYROS_JWT_SECRET` | `backend/.env` / SSM `/kyros/production/backend` | Repo placeholder `CHANGEME_minimum_32_chars_…`; real prod value **exposed in chat 2026-06-12** | ROTATE: ≥32 chars (startup validator rejects placeholder/short), regenerate, update SSM. NOTE: rotating invalidates all live JWT sessions | 2026-06-27 |
| `KYROS_OTP_SECRET` | `backend/.env` / SSM `/kyros/production/backend` | Repo placeholder `CHANGEME_minimum_32_chars_…`; real prod value **exposed in chat 2026-06-12** | ROTATE: ≥32 chars (startup validator rejects placeholder/short), regenerate, update SSM | 2026-06-27 |
| `KYROS_SMTP_HOST` / `_USER` / `_PASSWORD` | `backend/.env` / SSM `/kyros/production/backend` | Dev = `mailhog:1025`, no auth; prod SMTP creds **exposed in chat 2026-06-12** | ROTATE SMTP credentials at provider, update SSM, restart backend + worker | 2026-06-27 |
| CloudWatch alarms (dead) | `infra/cloudformation/cloudwatch-alarms.yml` | References RDS + ElastiCache metrics | Phase-1 topology has **no RDS/ElastiCache** (in-container postgres + redis on one EC2) — these alarms reference non-existent metrics and never fire. Rewrite for EC2/container metrics, or remove until RDS migration | 2026-06-27 |

---

## Operational follow-ups (not config — won't fit the table above)

These are go-live pending items from 2026-06-12 that are runbook/process tasks, not env values:

- **Restore drill never performed** (runbook §5). With Phase-1 in-container Postgres on a single
  EC2 (no RDS), an untested backup is not a backup. Perform a full restore drill before any real
  patient PHI lands. Trigger to move Postgres to RDS is the **first real patient record**, not
  user growth.
- **Manual-copy deploy files**: `kyros-prepare-env.sh` and the systemd unit files are NOT synced
  by the deploy (only `docker-compose.prod.yml` is). Stale copies caused most June 12 failures —
  verify these are current on the EC2 after each deploy.
