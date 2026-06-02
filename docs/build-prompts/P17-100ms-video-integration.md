# P17 — 100ms Video Integration

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §7 (Celery video provisioning), §6 (Redis locks)
- `docs/strategy/build-spec.md` — section 5 (video consultation)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `backend/`:
- Implement `app/integrations/hms.py` for room provisioning, JWT generation
- Celery task `provision_video_room(consultation_id)` runs at T-15min
- Update `kc_consultations.video_room_id` post-provision
- `/v1/clinic/patient/consultations/{id}/join` and `/v1/doctor/consultations/{id}/join` return role-scoped JWTs

In `mobile/`:
- Integrate `@100mslive/react-native-room-kit`
- Pre-call waiting room
- In-call layout
- Post-call return to consultation detail

**Acceptance:**
- Two devices on Indian 4G hold a 30-min consultation
- One-way latency < 300ms p95
- Recording opt-in dialog presented before call starts

---

*To execute: tell Claude Code `Execute P17. Read docs/build-prompts/P17-100ms-video-integration.md, then plan before editing.`*
