# Kyros Production Runbook

**Last reviewed:** 2026-06-11  
**DPO contact:** dpo@kyrosclinic.com  
**On-call:** See on-call schedule in PagerDuty / Slack #on-call  
**Incident channel:** Slack #incidents  

---

## Table of Contents

1. [Phase 1 Topology](#1-phase-1-topology)
2. [Deployment Procedure](#2-deployment-procedure)
3. [Rollback Procedure](#3-rollback-procedure)
4. [Database Failure](#4-database-failure)
5. [Restore from S3 Backup](#5-restore-from-s3-backup)
6. [Celery Queue Stuck](#6-celery-queue-stuck)
7. [Payment Reconciliation Mismatch](#7-payment-reconciliation-mismatch)
8. [Audit Integrity Failure](#8-audit-integrity-failure)
9. [On-Call Escalation Matrix](#9-on-call-escalation-matrix)
10. [Post-Mortem Template](#10-post-mortem-template)

---

## 1. Phase 1 Topology

```
Internet → Cloudflare (DNS + proxy, Full-strict TLS)
              │  ports 80/443 open to Cloudflare IPs only — no port 22
          EC2 t3.small (ap-south-1a, Elastic IP, encrypted EBS)
          └── Docker Compose (project: kyros)
              ├── caddy          (TLS termination, Cloudflare Origin CA cert)
              ├── backend-api    (localhost:8000)
              ├── celery-worker
              ├── celery-beat
              ├── postgres       (kyros_postgres_data volume — the PHI store)
              └── redis          (ephemeral only — security rule #13)
                      │
          S3 kyros-phi-production (SSE-KMS, public access blocked)
          └── db-backups/  (nightly + pre-deploy pg_dumps, 14-day lifecycle expiry)
```

**Postgres runs in-container on the EC2 — there is no RDS in Phase 1.** Durability
comes from the encrypted EBS volume plus `pg_dump`s to S3: nightly via
`kyros-db-backup.timer` (22:00 UTC = 03:30 IST) and before every migration via the
deploy pipeline. Move to RDS when the first real patient data lands
(`docs/deploy-phase1-aws-setup.md`, Phase 3b note).

**Key resources**

| Resource | Identifier |
|---|---|
| EC2 instance | `i-XXXXXXXXXX` (ap-south-1) |
| Postgres | container `kyros-postgres-1`, volume `kyros_postgres_data` |
| ECR | `ACCOUNT.dkr.ecr.ap-south-1.amazonaws.com/kyros-backend` |
| S3 (PHI files + DB backups) | `kyros-phi-production` |
| Secrets | SSM Parameter Store `/kyros/production/backend` (SecureString JSON) |

**Shell access** (SSM Session Manager — no bastion, no open port 22):
```bash
aws ssm start-session --target i-XXXXXXXXXX --region ap-south-1
```

**Docker Compose on EC2:**
```bash
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros ps
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros logs -f backend-api
```

---

## 2. Deployment Procedure

**Normal deploy (CI-triggered):**

CI pipeline runs automatically on merge to `main`
(`.github/workflows/deploy-backend.yml`). Steps (all EC2 access tunnels over SSM):
1. Run tests, then build and push Docker image to ECR with `GIT_SHA` tag.
2. `pg_dump` the database to S3 (`infra/scripts/snapshot-before-deploy.sh` →
   `db-backups/kyros-pre-deploy-<timestamp>-<sha>.sql.gz`).
3. Run `alembic upgrade head` in a one-off container on the `kyros_default` network.
4. `docker compose up -d` with the new image tag, then health-check `/healthz`.
5. If health checks fail: see §3 for rollback.

**Manual deploy** (emergency or re-deploy without code change), from any machine
with the `kyros-ci` AWS credentials and the deploy SSH key:
```bash
export ECR_REGISTRY=<account>.dkr.ecr.ap-south-1.amazonaws.com
export EC2_HOST=<instance_id>            # i-… — tunnels over SSM, not an IP
# deploy key at /tmp/deploy_key (mode 0600)
./infra/scripts/deploy-phase1.sh <git_sha>
```

**Migration-only deploy** (schema change without code change, rare) — run the
backup first, then in an SSM session on the EC2:
```bash
sudo docker run --rm --network kyros_default \
  --env-file /etc/kyros/backend.env \
  REGISTRY/kyros-backend:TAG alembic upgrade head
```

---

## 3. Rollback Procedure

**Code rollback** (no schema changes involved):
```bash
# On EC2 directly
cd /etc/kyros
sudo IMAGE_TAG=<previous_sha> docker compose -f docker-compose.yml up -d
```

**Schema rollback** — generally not used. Prefer forward-only migrations.  
If absolutely necessary:
1. Verify the migration has a `downgrade()` function.
2. Restore from the pre-deploy `pg_dump` in S3 (§5) — safer than running `downgrade`.
3. Deploy the previous code image after restore completes.

**Checking available images in ECR:**
```bash
aws ecr describe-images --repository-name kyros-backend \
  --region ap-south-1 \
  --query 'sort_by(imageDetails, &imagePushedAt)[-10:].[imageTags[0],imagePushedAt]' \
  --output table
```

---

## 4. Database Failure

**There is no automatic failover in Phase 1.** Postgres is a single container on a
single EC2 instance.

**Postgres container crashes:** `restart: unless-stopped` brings it back
automatically, and the data volume (`kyros_postgres_data`) survives container
restarts. If it's crash-looping:
```bash
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros logs postgres --tail=100
sudo docker stats --no-stream    # check for memory pressure first — most likely cause on 2 GB
```

**EC2 instance or EBS volume lost:** provision a replacement instance per
`docs/deploy-phase1-aws-setup.md` Phases 5–7 and restore the latest dump from S3
(§5). **RPO: up to 24 hours** (nightly dump, or the pre-deploy dump if a deploy ran
more recently). Communicate the data-loss window — this may trigger a DPDP breach
assessment (`docs/dpdp-breach-runbook.md`).

**Phase 2 (RDS Multi-AZ)** removes this category: automatic failover in 60–120 s,
PITR with 5-minute granularity. The application already reconnects via
`pool_pre_ping=True` (SQLAlchemy). Move when the first real patient data lands.

---

## 5. Restore from S3 Backup

Use when data corruption is detected, a bad migration is deployed, or the host is
being rebuilt.

**RPO:** up to 24 h (nightly dump) or the pre-deploy dump of the offending deploy.  
**RTO:** ~15 minutes on a healthy host.

```bash
# 1. Pick a backup (nightly/ for scheduled, root of db-backups/ for pre-deploy)
aws s3 ls s3://kyros-phi-production/db-backups/ --recursive --region ap-south-1

# 2. In an SSM session on the EC2: stop all writers, keep postgres up
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros \
  stop backend-api celery-worker celery-beat

# 3. Move the corrupt database aside and create a fresh one
source <(sudo grep -E '^(POSTGRES_USER|POSTGRES_DB)=' /etc/kyros/backend.env)
sudo docker exec kyros-postgres-1 psql -U "$POSTGRES_USER" -d postgres -c \
  "ALTER DATABASE \"$POSTGRES_DB\" RENAME TO \"${POSTGRES_DB}_corrupt\";"
sudo docker exec kyros-postgres-1 psql -U "$POSTGRES_USER" -d postgres -c \
  "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\";"

# 4. Re-apply init.sql (extensions + readonly-role grants — the dumps are taken
#    with --no-acl, so grants don't round-trip)
sudo docker exec -i kyros-postgres-1 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  < /etc/kyros/postgres-init.sql

# 5. Restore the dump
aws s3 cp "s3://kyros-phi-production/db-backups/<BACKUP>.sql.gz" - --region ap-south-1 \
  | gunzip \
  | sudo docker exec -i kyros-postgres-1 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
      --set ON_ERROR_STOP=1

# 6. Restart the app
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros up -d
```

**After any restore:**
- Run `alembic current` (one-off container, as in §2 migration-only deploy) to
  confirm schema version; re-apply any migrations newer than the restore point.
- Verify `/readyz` returns `{"db": true, "redis": true}`.
- Once verified, drop the saved copy:
  `DROP DATABASE "<db>_corrupt";` — until then it's your undo button.
- Notify affected users if data was lost (triggers DPDP breach assessment — see
  `docs/dpdp-breach-runbook.md`).

---

## 6. Celery Queue Stuck

**Symptom:** CloudWatch alarm `kyros-production-celery-ocr-queue-critical` fires. Queue depth > 200 for 10+ minutes.

**Step 1 — Identify the backlog:**
```bash
# On EC2
sudo docker exec $(docker ps -qf name=celery-worker) \
  celery -A app.worker.celery_app inspect active
```

**Step 2 — Check worker health:**
```bash
sudo docker compose -f /etc/kyros/docker-compose.yml logs celery-worker | tail -50
sudo docker stats --no-stream $(docker ps -qf name=celery-worker)
```

**Step 3 — Identify stuck tasks:**
```bash
# Connect to Redis and inspect queue
sudo docker exec $(docker ps -qf name=backend-api) \
  python -c "
import redis, json
r = redis.Redis.from_url('REDIS_URL')
msgs = [json.loads(r.lindex('ocr', i)) for i in range(min(5, r.llen('ocr')))]
for m in msgs: print(m.get('id'), m.get('task'))
"
```

**Step 4 — Restart worker** (if worker is OOM or hung):
```bash
sudo docker compose -f /etc/kyros/docker-compose.yml restart celery-worker
```

**Step 5 — If task is fatally broken** (e.g., bad payload crashing workers):
```bash
# Purge the specific queue (last resort — tasks are lost)
sudo docker exec $(docker ps -qf name=celery-worker) \
  celery -A app.worker.celery_app purge -Q ocr --force
```
Document any purged tasks in the incident post-mortem.

**Step 6 — Scale up workers** (Phase 1 — increase concurrency):
```bash
sudo docker compose -f /etc/kyros/docker-compose.yml \
  exec celery-worker \
  celery -A app.worker.celery_app control pool_grow 4
```

---

## 7. Payment Reconciliation Mismatch

**Symptom:** Razorpay dashboard shows a payment as captured, but `kc_payments` row shows `status=created` or `failed`.

**Investigation:**
```bash
# Query payment by Razorpay order ID
make shell-db
SELECT id, status, razorpay_order_id, razorpay_payment_id, amount_paise, updated_at
FROM kc_payments
WHERE razorpay_order_id = 'order_XXXXXXXXXX';
```

**Common causes:**
1. Webhook delivery failure (Razorpay webhook missed or HMAC validation failed).
2. Application error during webhook processing (check `ad_audit_log` for failed webhook entries).
3. Race condition between webhook and manual verification.

**Resolution — manual status update** (only after confirming payment in Razorpay dashboard):
```bash
# Confirm the payment in Razorpay dashboard first
# Then update via admin API or direct SQL (with audit trail)
make shell-db
BEGIN;
UPDATE kc_payments
SET status = 'paid',
    razorpay_payment_id = 'pay_XXXXXXXXXX',
    updated_at = NOW()
WHERE razorpay_order_id = 'order_XXXXXXXXXX'
  AND status != 'paid';
-- Insert audit record
INSERT INTO ad_audit_log (actor_user_id, actor_role, action, resource_type, resource_id, allowed, reason, created_at)
VALUES (NULL, 'system', 'manual_payment_reconciliation', 'payment', '<payment_uuid>', true, 'reconciliation:INCIDENT_ID', NOW());
COMMIT;
```

**After resolution:**
- Trigger consultation booking confirmation if payment was for a consultation.
- Notify patient via WhatsApp/email.
- File incident post-mortem within 24 hours.

---

## 8. Audit Integrity Failure

**Symptom:** Sentry warning `AUDIT INTEGRITY DRIFT` or CloudWatch/Slack alert from `verify_audit_integrity` beat task.

This means the SHA-256 hash of a past day's `ad_audit_log` records no longer matches the hash computed when those records were first sealed. It indicates possible tampering, accidental deletion, or a migration that touched audit rows.

**Immediate actions:**
1. Do NOT make any changes to the `ad_audit_log` table until investigation is complete.
2. Page the security on-call if outside business hours.
3. Notify DPO at dpo@kyrosclinic.com within 1 hour.

**Investigation:**
```bash
# Get the drift details from Sentry or CloudWatch logs
# Check if any DDL ran against ad_audit_log recently
make shell-db
SELECT schemaname, tablename, attname, n_distinct
FROM pg_stats WHERE tablename = 'ad_audit_log'
ORDER BY attname;

-- Check if any rows were modified (should be impossible due to trigger)
SELECT COUNT(*) FROM ad_audit_log
WHERE DATE(created_at) = '2026-06-03';  -- the drifted date

-- Check Postgres logs for any UPDATE/DELETE on ad_audit_log
-- (these should have been blocked by the trigger)
```

**If tampering is confirmed:**  
Follow `docs/dpdp-breach-runbook.md`. Data integrity violation affecting PHI is a reportable incident under DPDP.

**If accidental (migration or admin fix):**  
1. Re-compute and store the correct hash in Redis: `audit:integrity:<YYYY-MM-DD>`.
2. Document the incident and the corrective action.
3. Post-mortem within 48 hours.

---

## 9. On-Call Escalation Matrix

| Alarm | Severity | First responder | Escalation (30 min no ack) |
|---|---|---|---|
| API 5xx > 1% | P1 | Backend on-call | Engineering lead |
| ALB unhealthy host | P1 | Backend on-call | Engineering lead |
| Postgres container down / connection failure | P1 | Backend on-call + DBA | CTO |
| EC2 memory/CPU pressure sustained > 80% | P2 | Backend on-call | Engineering lead |
| Redis memory > 80% | P2 | Backend on-call | Engineering lead |
| Celery OCR queue > 200 | P2 | Backend on-call | Engineering lead |
| Payment webhook failure > 5% | P1 | Backend on-call | Finance lead |
| Audit integrity drift | P1 | Security on-call | DPO + CTO |
| DPDP data request overdue | P2 | DPO | CTO |

**PagerDuty service:** `kyros-backend-prod`  
**Slack:** #incidents (auto-created by PagerDuty integration)

---

## 10. Post-Mortem Template

```markdown
# Incident Post-Mortem — YYYY-MM-DD — <title>

**Severity:** P1 / P2  
**Duration:** HH:MM (start) → HH:MM (end), TZ=IST  
**Incident commander:**  
**Scribe:**  

## Impact
- Users affected: ~N
- Services affected:
- Data at risk: yes/no (if yes, see DPDP breach runbook)

## Timeline (IST)
| Time | Event |
|---|---|
| HH:MM | Alarm fired |
| HH:MM | On-call acknowledged |
| HH:MM | Root cause identified |
| HH:MM | Fix deployed |
| HH:MM | All-clear |

## Root Cause
[Describe the technical cause. What failed, why it failed.]

## Contributing Factors
- 

## Resolution
[What was done to resolve the incident.]

## Action Items
| Action | Owner | Due |
|---|---|---|
| | | |

## What Went Well
- 

## What Could Be Improved
- 
```

---

*For DPDP breach incidents, see `docs/dpdp-breach-runbook.md`.*  
*For data protection impact assessment, see `docs/dpia-v1.md`.*
