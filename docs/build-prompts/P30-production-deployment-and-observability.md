# P30 — Production Deployment + Observability

> Build prompt extracted from `docs/strategy/build-spec.md` section 19 (Claude Code Prompt Queue P1–P30).
> Treat this file as the working brief. Do NOT modify the build-spec; re-run
> `scripts/extract-build-prompts.py` to refresh.

## Required reading

Open and skim these BEFORE planning. Read only the sections referenced; the strategy docs are long.

- `docs/strategy/backend-strategy.md` — §14 (observability), §16 (phased deployment)
- `docs/strategy/build-spec.md` — section 14 (infrastructure plan)

## Acceptance gates (in addition to the prompt's own acceptance criteria)

- Migrations (if any) are reviewed before applying. Auto-generate, then open the file.
- Tests added or updated, including RBAC matrix entries for new endpoints.
- `make ruff && make mypy && make test` all pass.
- Every authorization decision audit-logged.
- No PHI in logs, fixtures, or error responses returned to the client.
- Cross-user 404 verified for any resource-scoped endpoint.

## Original prompt

- Configure ECS Fargate task definitions (Phase 2 ready)
- Configure RDS Multi-AZ
- Configure ElastiCache Redis Multi-AZ
- Configure CloudWatch dashboards + Sentry
- Configure AWS WAF managed rule sets
- Configure CloudFront for public website
- Configure backup retention (RDS daily snapshots 30-day, S3 versioning)
- Document runbook: `docs/runbook-prod.md`
- Document DPDP breach runbook: `docs/dpdp-breach-runbook.md`
- Document DPIA: `docs/dpia-v1.md`

**Acceptance:**
- Phase 1 EC2 t3.small deployment live in ap-south-1
- All four frontends (website, doctor-portal, mobile via TestFlight + Play Internal, RNW patient portal) deployed
- Sentry catches errors from all services
- CloudWatch alarms configured for: API 5xx > 1%, RDS CPU > 80%, Redis memory > 80%
- DPDP DPIA documented + DPO designated + breach runbook ready

---

---

*To execute: tell Claude Code `Execute P30. Read docs/build-prompts/P30-production-deployment-and-observability.md, then plan before editing.`*
