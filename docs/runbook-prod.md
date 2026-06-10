# Kyros Production Runbook

**Last reviewed:** 2026-06-04  
**DPO contact:** dpo@kyrosclinic.com  
**On-call:** See on-call schedule in PagerDuty / Slack #on-call  
**Incident channel:** Slack #incidents  

---

## Table of Contents

1. [Phase 1 Topology](#1-phase-1-topology)
2. [Deployment Procedure](#2-deployment-procedure)
3. [Rollback Procedure](#3-rollback-procedure)
4. [Database Failover (Phase 2 Multi-AZ)](#4-database-failover)
5. [PITR Restore from Backup](#5-pitr-restore-from-backup)
6. [Celery Queue Stuck](#6-celery-queue-stuck)
7. [Payment Reconciliation Mismatch](#7-payment-reconciliation-mismatch)
8. [Audit Integrity Failure](#8-audit-integrity-failure)
9. [On-Call Escalation Matrix](#9-on-call-escalation-matrix)
10. [Post-Mortem Template](#10-post-mortem-template)

---

## 1. Phase 1 Topology

```
Internet → CloudFront (website static) → S3
         → AWS WAF → ALB (TLS 1.3)
                       │
                   EC2 t3.small (ap-south-1a)
                   ├── backend-api  (localhost:8000)
                   ├── celery-worker
                   └── celery-beat
                       │
              ┌────────┴────────┐
         RDS db.t3.micro    ElastiCache Redis t3.micro
         (private subnet)   (private subnet)
```

**Key resources**

| Resource | Identifier |
|---|---|
| EC2 instance | `i-XXXXXXXXXX` (ap-south-1) |
| RDS | `kyros-prod-postgres` |
| ElastiCache | `kyros-prod-redis` |
| ALB | `kyros-prod-alb` |
| ECR | `ACCOUNT.dkr.ecr.ap-south-1.amazonaws.com/kyros-backend` |
| S3 uploads | `kyros-prod-uploads` |
| Secrets Manager | `kyros/production/backend` |

**SSH access** (via bastion):
```bash
ssh -J ec2-user@BASTION_IP ec2-user@EC2_PRIVATE_IP
```

**Docker Compose on EC2:**
```bash
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros ps
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros logs -f backend-api
```

---

## 2. Deployment Procedure

**Normal deploy (CI-triggered):**

CI pipeline runs automatically on merge to `main`. Steps:
1. Build and push Docker image to ECR with `GIT_SHA` tag.
2. Create RDS snapshot (`infra/scripts/snapshot-before-deploy.sh`).
3. Run `alembic upgrade head` against RDS (separate container, same image).
4. Run `infra/scripts/deploy-phase1.sh GIT_SHA` — pulls image, compose up, health checks.
5. If health checks fail: automatic rollback triggered (see §3).

**Manual deploy** (emergency or re-deploy without code change):
```bash
export IMAGE_TAG=<git_sha>
export ECR_REGISTRY=<account>.dkr.ecr.ap-south-1.amazonaws.com
export EC2_HOST=<ec2_private_ip>
export BASTION_HOST=<bastion_ip>
export RDS_INSTANCE_ID=kyros-prod-postgres
./infra/scripts/deploy-phase1.sh $IMAGE_TAG
```

**Migration-only deploy** (schema change without code change, rare):
```bash
ssh -J ec2-user@BASTION ec2-user@EC2 \
  "docker run --rm --env-file /etc/kyros/backend.env --network host \
   REGISTRY/kyros-backend:TAG alembic upgrade head"
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
2. Restore from RDS pre-deploy snapshot (§5) — faster and safer than running `downgrade`.
3. Deploy the previous code image after restore completes.

**Checking available images in ECR:**
```bash
aws ecr describe-images --repository-name kyros-backend \
  --region ap-south-1 \
  --query 'sort_by(imageDetails, &imagePushedAt)[-10:].[imageTags[0],imagePushedAt]' \
  --output table
```

---

## 4. Database Failover

**Phase 1 (single instance):** No automatic failover. On RDS failure, restore from backup (§5).

**Phase 2 (Multi-AZ):** RDS automatically fails over to the standby replica. Typical failover time: 60–120 seconds. The application reconnects via `pool_pre_ping=True` (SQLAlchemy).

**Steps during a Phase 2 failover:**
1. CloudWatch alarm `kyros-production-rds-connection-failures` will fire — page acknowledged.
2. Check RDS console for failover event: `Events → DB Instance Events`.
3. Monitor `DatabaseConnections` CloudWatch metric — should recover within 2 min.
4. If app containers stuck: restart them.
   ```bash
   sudo docker compose -f /etc/kyros/docker-compose.yml restart backend-api
   ```
5. Verify `/readyz` returns `{"db": true, "redis": true}`.
6. Verify Celery worker reconnects:
   ```bash
   sudo docker compose -f /etc/kyros/docker-compose.yml logs celery-worker | tail -20
   ```

**Forcing a Phase 2 failover (maintenance window):**
```bash
aws rds reboot-db-instance \
  --db-instance-identifier kyros-prod-postgres \
  --force-failover \
  --region ap-south-1
```

---

## 5. PITR Restore from Backup

Use when data corruption is detected or a bad migration is deployed.

**RPO:** 5 minutes (RDS PITR granularity).  
**RTO:** ~30 minutes for a restore to a new instance + update connection string.

```bash
# 1. Pick restore point (UTC timestamp, must be within retention window)
RESTORE_TIME="2026-06-03T14:30:00Z"

# 2. Restore to a new instance
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier kyros-prod-postgres \
  --target-db-instance-identifier kyros-prod-postgres-restored \
  --restore-time "${RESTORE_TIME}" \
  --db-instance-class db.t3.micro \
  --region ap-south-1

# 3. Wait for restore (takes 15–30 min)
aws rds wait db-instance-available \
  --db-instance-identifier kyros-prod-postgres-restored \
  --region ap-south-1

# 4. Get new endpoint
aws rds describe-db-instances \
  --db-instance-identifier kyros-prod-postgres-restored \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text \
  --region ap-south-1

# 5. Update DATABASE_URL in Secrets Manager to point at new instance
aws secretsmanager put-secret-value \
  --secret-id kyros/production/backend \
  --secret-string '{"database_url": "postgresql+asyncpg://kyros:PASSWORD@NEW_ENDPOINT:5432/kyros", ...}'

# 6. Re-run kyros-prepare-env.sh and restart containers
sudo /usr/local/bin/kyros-prepare-env.sh
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros up -d
```

**Restore from pre-deploy snapshot** (preferred when migration caused corruption):
```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier kyros-prod-postgres-snapshot-restored \
  --db-snapshot-identifier kyros-pre-deploy-SNAPSHOT_ID \
  --db-instance-class db.t3.micro \
  --region ap-south-1
```
Then follow steps 3–6 above.

**After any restore:**
- Run `alembic current` to confirm schema version.
- Re-apply any migrations that occurred after the restore point.
- Notify affected users if data was lost (triggers DPDP breach assessment — see `docs/dpdp-breach-runbook.md`).

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
| RDS connection failure | P1 | Backend on-call + DBA | CTO |
| RDS CPU > 80% | P2 | Backend on-call | Engineering lead |
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
