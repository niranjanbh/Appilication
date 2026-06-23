# Dev-to-Production Checklist

Values used during development/testing that need production replacements before go-live.

| Variable / Config | File | Dev Value | Production Action | Date |
|---|---|---|---|---|
| `KYROS_MFA_ENCRYPTION_KEY` | `backend/.env` | Placeholder `<generate-32+-random-chars>` | Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` | 2026-06-23 |
| `EAS projectId` | `mobile/app.json` | `b1a2763c-...` (dev account) | Confirm this is the production Expo project or create a new one | 2026-06-23 |
| `KYROS_RAZORPAY_KEY_ID` | `backend/.env` | Not set | Get live key from Razorpay dashboard | 2026-06-23 |
| `KYROS_RAZORPAY_KEY_SECRET` | `backend/.env` | Not set | Get live secret from Razorpay dashboard | 2026-06-23 |
| `KYROS_RAZORPAY_WEBHOOK_SECRET` | `backend/.env` | Not set | Configure webhook in Razorpay and copy secret | 2026-06-23 |
| `KYROS_HMS_ACCESS_KEY` | `backend/.env` | Not set | Get from 100ms dashboard | 2026-06-23 |
| `KYROS_HMS_SECRET` | `backend/.env` | Not set | Get from 100ms dashboard | 2026-06-23 |
| `KYROS_AUTHKEY_API_KEY` | `backend/.env` | Not set | Get from Authkey/MSG91 dashboard | 2026-06-23 |
| `KYROS_SENTRY_DSN` | `backend/.env` | Not set | Create Sentry project and copy DSN | 2026-06-23 |
| `KYROS_GOOGLE_OAUTH_CLIENT_IDS` | `backend/.env` | Not set (setting up now) | Use production Google Cloud client IDs | 2026-06-23 |
| `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` | `mobile/.env` | Not set (setting up now) | Use production Google Cloud web client ID | 2026-06-23 |
| `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID` | `mobile/.env` | Not set (setting up now) | Use production Google Cloud iOS client ID | 2026-06-23 |
| `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID` | `mobile/.env` | Not set (setting up now) | Use production Google Cloud Android client ID | 2026-06-23 |
| Apple Team ID | `mobile/eas.json` | `REPLACE_WITH_APPLE_TEAM_ID` | Get from Apple Developer account | 2026-06-23 |
| App Store Connect App ID | `mobile/eas.json` | `REPLACE_WITH_APP_STORE_CONNECT_APP_ID` | Create app in App Store Connect | 2026-06-23 |
| Android SHA-1 fingerprint | Google Cloud Console | Dev keystore SHA-1 | Verify matches production signing key | 2026-06-23 |
