# P19 — Doctor Consultation View + Notes

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/frontend-strategy.md` — doctor portal consultation room
- `docs/strategy/backend-strategy.md` — §10 (kc_doctor_notes), §11 (doctor scoping)
- `docs/strategy/build-spec.md` — section 9 (consultation view, notes)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

In `doctor-portal/`:
- Implement `ConsultationVideoLayout` component: video on left (100ms web SDK), patient context panel on right
- `PatientContextPanel`: tabs for previous notes, prescriptions, labs, wearable data
- `NotesPanel`: real-time notes during call
- Post-call summary: notes, prescription builder, lab order builder, follow-up scheduling

In `backend/`:
- Implement `/v1/doctor/consultations/{id}/notes` POST (append-only, version-tracked)
- Implement `/v1/doctor/consultations/{id}/lab-order` POST

**Acceptance:**
- Doctor completes a consultation end-to-end on a single screen
- Notes saved with version increment on every save
- Lab order persists to `kc_lab_orders`

---

*To execute: tell Claude Code `Execute P19. Read docs/build-prompts/P19-doctor-consultation-view-and-notes.md, then plan before editing.`*
