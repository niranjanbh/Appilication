# Dev-to-Production Tracker Rule

Whenever you use, set, or configure a **development/testing value** — env variable, API key,
placeholder credential, test URL, debug flag, or any config that differs between dev and
production — you MUST:

1. **Log it** in `docs/dev-to-prod-checklist.md` with:
   - The variable or config name
   - Where it's set (file path)
   - The dev/test value used (redact secrets — just note "dev key" or "test value")
   - What the production value should be or where to get it
   - Date added

2. **Tell the user** at the end of your response: "Added [item] to the dev-to-prod checklist —
   you'll need a production value before go-live."

## Format for docs/dev-to-prod-checklist.md

```markdown
| Variable / Config | File | Dev Value | Production Action | Date |
|---|---|---|---|---|
| EXAMPLE_KEY | backend/.env | test_xxx | Get live key from provider dashboard | 2026-06-23 |
```

## What counts as a dev/testing value

- Placeholder API keys or secrets (Razorpay test keys, sandbox URLs, etc.)
- `localhost` or `127.0.0.1` URLs in config
- Debug flags set to `true`
- Test email addresses or phone numbers in config
- Expo development build URLs
- Self-signed or debug certificates/keystores
- Any value with "test", "dev", "debug", "sandbox", "example", or "placeholder" in it
- SHA-1 from debug keystores (vs production signing keys)

## What does NOT count

- Values that are the same in dev and production (e.g., `KYROS_AWS_REGION=ap-south-1`)
- Code logic (only config/env values)
- Values already documented in `.env.example` with clear production instructions
