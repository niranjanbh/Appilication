# Phase 1 AWS Setup — First-Time Provisioning

> One-time setup to get the backend live on AWS in `ap-south-1`. After this, ongoing
> deploys happen automatically via `.github/workflows/deploy-backend.yml` (see
> `docs/runbook-prod.md` for day-2 operations).

This guide assumes a **brand-new AWS account** on the current AWS Free Tier ($200 in
credits usable over 6 months, plus "Always Free" services — there is no special
12-months-free EC2/RDS allowance for new accounts anymore).

## Cost reality check

The topology below (single EC2 instance for app containers + Redis, **RDS Postgres**
for the database, no ElastiCache, no ALB) costs roughly:

| Item | Approx monthly cost (ap-south-1) |
|---|---|
| EC2 t3.small (2 vCPU, 2 GB) | ~$15 |
| EBS 20 GB gp3 | ~$1.6 |
| RDS db.t4g.small single-AZ (2 vCPU, 2 GB) | ~$25 |
| RDS storage 20 GB gp3 + backups within retention | ~$2.5 |
| Elastic IP (attached to running instance) | $0 |
| ECR storage (a few images) | ~$0.10/GB-month, negligible |
| SSM Parameter Store (standard tier) | $0 |
| Data transfer out (low volume) | ~$1–3 |
| **Total** | **~$42–47/month** |

The $200 credit covers roughly the first 4 months at this rate. The deliberate
trade-offs at this stage:

- **Postgres on RDS** — this is the PHI store. RDS gives automated daily backups,
  point-in-time recovery (any moment in the last 7 days), KMS storage encryption,
  pre-migration snapshots, and push-button resizing. Worth paying for from day one.
- **Redis stays in Docker on the EC2** — it holds only ephemeral state (OTPs, rate
  limits, Celery queue; security rule #13 says Redis is never the source of truth),
  so a managed ElastiCache node (~$11/month) buys little today. Move to ElastiCache
  in Phase 2.
- **Single-AZ RDS** — Multi-AZ doubles the RDS cost and only reduces downtime during
  an AZ failure; backups already protect against data loss. Enable Multi-AZ
  (`aws rds modify-db-instance --multi-az`) once there are paying users.

---

## Prerequisites

1. AWS account created, you're logged into the **AWS Console** as the root user (or an
   admin IAM user).
2. Use **AWS CloudShell** for every command below (Console → search "CloudShell" → open).
   It's free, pre-authenticated, runs bash, and avoids all the Windows/PowerShell
   quoting headaches with JSON. All commands in this guide are bash.
3. Your domain (`kyrosclinic.com`) is already on Cloudflare.
4. Region is **ap-south-1 (Mumbai)** everywhere — this is a hard data-residency
   requirement (`.claude/rules/security.md` #14).

In CloudShell, set the region as default for this session:

```bash
export AWS_REGION=ap-south-1
aws configure set region $AWS_REGION
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID  Region: $AWS_REGION"
```

---

## Phase 0 — Cost guardrails (do this first)

Create an AWS Budget that emails you before you're surprised by a bill. Replace
`you@example.com`.

```bash
EMAIL="you@example.com"

cat > /tmp/budget.json <<EOF
{
  "BudgetName": "kyros-monthly",
  "BudgetLimit": {"Amount": "25", "Unit": "USD"},
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
EOF

cat > /tmp/notifications.json <<EOF
[
  {
    "Notification": {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 80, "ThresholdType": "PERCENTAGE"},
    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "$EMAIL"}]
  },
  {
    "Notification": {"NotificationType": "FORECASTED", "ComparisonOperator": "GREATER_THAN", "Threshold": 100, "ThresholdType": "PERCENTAGE"},
    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "$EMAIL"}]
  }
]
EOF

aws budgets create-budget \
  --account-id $ACCOUNT_ID \
  --budget file:///tmp/budget.json \
  --notifications-with-subscribers file:///tmp/notifications.json
```

This alerts at 80% of $25/month actual spend and if forecasted spend exceeds $25 — well
below the $200 credit, so you'll know early if something runs away (e.g., an
oversized instance or a runaway Celery task generating S3/data-transfer costs).

---

## Phase 1 — IAM: EC2 instance role + CI deploy user

### 1a. EC2 instance role

The EC2 instance needs permission to: pull from ECR, read the SSM secrets parameter,
decrypt it, and register with SSM Session Manager (so you can shell in **without
opening port 22**).

```bash
cat > /tmp/ec2-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name kyros-ec2-role \
  --assume-role-policy-document file:///tmp/ec2-trust-policy.json

aws iam attach-role-policy --role-name kyros-ec2-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

aws iam attach-role-policy --role-name kyros-ec2-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# SSM Parameter Store read + KMS decrypt for the SecureString
KMS_KEY_ARN=$(aws kms describe-key --key-id alias/aws/ssm --query KeyMetadata.Arn --output text)

cat > /tmp/ec2-ssm-params-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:${AWS_REGION}:${ACCOUNT_ID}:parameter/kyros/*"
    },
    {
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "${KMS_KEY_ARN}"
    },
    {
      "Effect": "Allow",
      "Action": "ecr:DescribeRegistry",
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy --role-name kyros-ec2-role \
  --policy-name kyros-ssm-params \
  --policy-document file:///tmp/ec2-ssm-params-policy.json

aws iam create-instance-profile --instance-profile-name kyros-ec2-profile
aws iam add-role-to-instance-profile \
  --instance-profile-name kyros-ec2-profile --role-name kyros-ec2-role

# IAM eventual consistency — wait a moment before launching the instance later
sleep 10
```

### 1b. CI deploy user (for GitHub Actions)

```bash
aws iam create-user --user-name kyros-ci

cat > /tmp/ci-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRPushPull",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRegistry"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SSMTunnelToInstance",
      "Effect": "Allow",
      "Action": "ssm:StartSession",
      "Resource": [
        "arn:aws:ec2:${AWS_REGION}:${ACCOUNT_ID}:instance/*",
        "arn:aws:ssm:${AWS_REGION}::document/AWS-StartSSHSession"
      ]
    },
    {
      "Sid": "SSMTunnelTerminate",
      "Effect": "Allow",
      "Action": ["ssm:TerminateSession", "ssm:ResumeSession"],
      "Resource": "arn:aws:ssm:${AWS_REGION}:*:session/$${aws:username}-*"
    },
    {
      "Sid": "RDSPreDeploySnapshot",
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBSnapshot",
        "rds:DeleteDBSnapshot",
        "rds:DescribeDBSnapshots",
        "rds:DescribeDBInstances",
        "rds:AddTagsToResource"
      ],
      "Resource": [
        "arn:aws:rds:${AWS_REGION}:${ACCOUNT_ID}:db:kyros-prod",
        "arn:aws:rds:${AWS_REGION}:${ACCOUNT_ID}:snapshot:kyros-pre-deploy-*"
      ]
    }
  ]
}
EOF

aws iam put-user-policy --user-name kyros-ci \
  --policy-name kyros-ci-deploy --policy-document file:///tmp/ci-policy.json

aws iam create-access-key --user-name kyros-ci
```

**Save the `AccessKeyId` and `SecretAccessKey` from the last command's output** —
you'll add these as GitHub secrets in Phase 7. They won't be shown again (you can
always `aws iam create-access-key` again later if lost, and delete the old one).

---

## Phase 2 — ECR repository

```bash
aws ecr create-repository \
  --repository-name kyros-backend \
  --image-scanning-configuration scanOnPush=true \
  --region $AWS_REGION
```

---

## Phase 3 — Networking & security group

Use the account's default VPC — no need for a custom VPC at this scale.

```bash
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)

SUBNET_ID=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC_ID \
  Name=availability-zone,Values=${AWS_REGION}a \
  --query 'Subnets[0].SubnetId' --output text)

echo "VPC: $VPC_ID  Subnet: $SUBNET_ID"

SG_ID=$(aws ec2 create-security-group \
  --group-name kyros-backend-sg \
  --description "Kyros Phase 1 backend - HTTPS via Cloudflare only" \
  --vpc-id $VPC_ID --query GroupId --output text)

echo "Security group: $SG_ID"
```

**No port 22 rule** — you'll shell in via SSM Session Manager (Phase 1a already grants
this). Open 80/443 **only to Cloudflare's IP ranges**, since Cloudflare proxies all
traffic and this prevents anyone from bypassing Cloudflare by hitting the EC2's IP
directly:

```bash
# IPv4
for cidr in $(curl -s https://www.cloudflare.com/ips-v4); do
  aws ec2 authorize-security-group-ingress --group-id $SG_ID \
    --protocol tcp --port 443 --cidr "$cidr" >/dev/null
  aws ec2 authorize-security-group-ingress --group-id $SG_ID \
    --protocol tcp --port 80 --cidr "$cidr" >/dev/null
done

# IPv6
for cidr in $(curl -s https://www.cloudflare.com/ips-v6); do
  aws ec2 authorize-security-group-ingress --group-id $SG_ID \
    --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,Ipv6Ranges="[{CidrIpv6=$cidr}]" >/dev/null
  aws ec2 authorize-security-group-ingress --group-id $SG_ID \
    --ip-permissions IpProtocol=tcp,FromPort=80,ToPort=80,Ipv6Ranges="[{CidrIpv6=$cidr}]" >/dev/null
done

echo "Security group rules added."
```

> Cloudflare's IP ranges change rarely (roughly yearly). If Cloudflare ever rotates
> them and your origin starts returning connection timeouts, re-run this block — it's
> idempotent enough (re-authorizing an existing rule errors harmlessly; new ranges get
> added).

---

## Phase 3b — RDS Postgres (the PHI database)

The database does **not** run in Docker. Provision a managed RDS Postgres 16 instance:
encrypted at rest (KMS), automated backups with point-in-time recovery, not publicly
accessible, reachable only from the EC2 security group.

```bash
# Security group for RDS: port 5432 only from the EC2 instances' SG
RDS_SG_ID=$(aws ec2 create-security-group \
  --group-name kyros-rds-sg \
  --description "Kyros RDS - Postgres from backend EC2 only" \
  --vpc-id $VPC_ID --query GroupId --output text)

aws ec2 authorize-security-group-ingress --group-id $RDS_SG_ID \
  --protocol tcp --port 5432 --source-group $SG_ID

# DB subnet group across the default VPC's subnets (RDS requires >= 2 AZs)
SUBNET_IDS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC_ID \
  --query 'Subnets[].SubnetId' --output text)

aws rds create-db-subnet-group \
  --db-subnet-group-name kyros-db-subnets \
  --db-subnet-group-description "Kyros default-VPC subnets" \
  --subnet-ids $SUBNET_IDS

# Master password — you'll embed this in KYROS_DATABASE_URL in Phase 4
RDS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')
echo "RDS_PASSWORD=$RDS_PASSWORD"   # note it down securely; also goes into SSM in Phase 4

# Latest Postgres 16.x available on RDS
PG_VERSION=$(aws rds describe-db-engine-versions --engine postgres \
  --query "DBEngineVersions[?starts_with(EngineVersion,'16.')].EngineVersion | [-1]" \
  --output text)
echo "Postgres version: $PG_VERSION"

aws rds create-db-instance \
  --db-instance-identifier kyros-prod \
  --db-instance-class db.t4g.small \
  --engine postgres \
  --engine-version $PG_VERSION \
  --db-name kyros \
  --master-username kyros \
  --master-user-password "$RDS_PASSWORD" \
  --allocated-storage 20 \
  --max-allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --backup-retention-period 7 \
  --deletion-protection \
  --no-publicly-accessible \
  --no-multi-az \
  --vpc-security-group-ids $RDS_SG_ID \
  --db-subnet-group-name kyros-db-subnets \
  --auto-minor-version-upgrade \
  --tags Key=Name,Value=kyros-prod

# Takes 5–10 minutes
aws rds wait db-instance-available --db-instance-identifier kyros-prod

RDS_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier kyros-prod \
  --query 'DBInstances[0].Endpoint.Address' --output text)
echo "RDS endpoint: $RDS_ENDPOINT"
```

> **As built (June 2026):** the live `kyros-prod` instance was created via the console
> with master username **`postgres`** (console default), not `kyros`. The database name
> is `kyros`. All connection strings below use `postgres` as the user.

**Write down `$RDS_ENDPOINT` and `$RDS_PASSWORD`** — both go into the SSM parameter in
Phase 4. The instance identifier `kyros-prod` becomes the `RDS_INSTANCE_ID` GitHub
secret in Phase 8 (the deploy pipeline snapshots it before every migration).

Storage autoscaling is capped at 100 GB (`--max-allocated-storage`) so a runaway
writer can't generate an unbounded storage bill.

> **Multi-AZ later:** when you have paying users, enable failover with
> `aws rds modify-db-instance --db-instance-identifier kyros-prod --multi-az
> --apply-immediately`. No data migration needed.

---

## Phase 4 — SSM secrets parameter

Generate the secrets the backend needs and store them as one SecureString JSON
parameter, exactly as `infra/ec2/kyros-prepare-env.sh` expects.

```bash
JWT_SECRET=$(openssl rand -hex 32)
OTP_SECRET=$(openssl rand -hex 32)
# $RDS_ENDPOINT and $RDS_PASSWORD come from Phase 3b

# Key names below are verified against backend/app/core/config.py (pydantic-settings,
# env_prefix "KYROS_" + field name). config.py is the source of truth — re-verify after
# any Settings change.
cat > /tmp/backend-secrets.json <<EOF
{
  "KYROS_APP_ENV": "production",
  "KYROS_APP_VERSION": "1.0.0",
  "KYROS_DEBUG": "false",

  "KYROS_DATABASE_URL": "postgresql+asyncpg://postgres:${RDS_PASSWORD}@${RDS_ENDPOINT}:5432/kyros?ssl=require",

  "KYROS_REDIS_URL": "redis://redis:6379/0",
  "KYROS_CELERY_BROKER_URL": "redis://redis:6379/1",
  "KYROS_CELERY_RESULT_BACKEND": "redis://redis:6379/2",

  "KYROS_JWT_SECRET": "${JWT_SECRET}",
  "KYROS_JWT_ALGORITHM": "HS256",
  "KYROS_JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
  "KYROS_JWT_REFRESH_TOKEN_EXPIRE_DAYS": "30",

  "KYROS_OTP_SECRET": "${OTP_SECRET}",
  "KYROS_OTP_TTL_SECONDS": "300",
  "KYROS_OTP_MAX_ATTEMPTS": "5",
  "KYROS_OTP_RESEND_COOLDOWN_SECONDS": "60",
  "KYROS_OTP_EMAIL_FALLBACK_ENABLED": "true",

  "KYROS_RATE_LIMIT_ENABLED": "true",
  "KYROS_STARTUP_SCHEMA_CHECK": "true",

  "KYROS_CORS_ALLOWED_ORIGINS": "https://kyrosclinic.com,https://www.kyrosclinic.com,https://portal.kyrosclinic.com",

  "KYROS_AWS_REGION": "${AWS_REGION}",
  "KYROS_S3_BUCKET": "kyros-phi-production",
  "KYROS_AWS_ACCESS_KEY_ID": "",
  "KYROS_AWS_SECRET_ACCESS_KEY": "",

  "KYROS_AUTHKEY_API_KEY": "",
  "KYROS_AUTHKEY_OTP_TEMPLATE_NAME": "kyros_otp",
  "KYROS_AUTHKEY_SENDER_ID": "KYROS",
  "KYROS_AUTHKEY_SMS_TEMPLATE_ID": "",

  "KYROS_RAZORPAY_KEY_ID": "",
  "KYROS_RAZORPAY_KEY_SECRET": "",
  "KYROS_RAZORPAY_WEBHOOK_SECRET": "",
  "KYROS_GST_NUMBER": "",

  "KYROS_HMS_ACCESS_KEY": "",
  "KYROS_HMS_SECRET": "",
  "KYROS_HMS_TEMPLATE_ID": "",

  "KYROS_GOOGLE_DOCUMENT_AI_SECRET_NAME": "",
  "KYROS_GOOGLE_DOCUMENT_AI_PROCESSOR_ID": "",
  "KYROS_GOOGLE_DOCUMENT_AI_LOCATION": "asia-south1",

  "KYROS_SMTP_HOST": "",
  "KYROS_SMTP_PORT": "587",
  "KYROS_SMTP_USER": "",
  "KYROS_SMTP_PASSWORD": "",
  "KYROS_EMAIL_FROM": "contact@kyrosclinic.com",
  "KYROS_ADMIN_ALERT_EMAIL": "admin@kyrosclinic.com",

  "KYROS_ABHA_CLIENT_ID": "",
  "KYROS_ABHA_CLIENT_SECRET": "",

  "KYROS_SENTRY_DSN": "",
  "KYROS_CLOUDWATCH_NAMESPACE": "Kyros/Backend"
}
EOF

aws ssm put-parameter \
  --name /kyros/production/backend \
  --type SecureString \
  --value file:///tmp/backend-secrets.json \
  --tier Standard

# Don't leave secrets on disk
shred -u /tmp/backend-secrets.json
```

> **Startup gates** (config.py `_refuse_unsafe_production_config`): with
> `KYROS_APP_ENV=production` the app refuses to start if `KYROS_JWT_SECRET` or
> `KYROS_OTP_SECRET` is a `CHANGEME` placeholder or shorter than 32 chars, if
> `KYROS_DEBUG` is true, or if `KYROS_CORS_ALLOWED_ORIGINS` contains a
> localhost/127.0.0.1 origin. If the container restarts in a loop, check
> `docker compose logs backend-api` for these messages first.
>
> Empty-string values for integrations you haven't set up yet (Razorpay, authkey.io,
> SMTP, 100ms, Document AI, Sentry, ABHA) are fine for getting the API up —
> pydantic-settings treats empty env vars as unset and falls back to field defaults;
> those features just won't work until you fill them in (re-run `put-parameter` with
> `--overwrite` and restart the stack to pick up changes).
>
> `KYROS_S3_BUCKET` references a bucket that doesn't exist yet. Creating the
> SSE-KMS-encrypted, public-access-blocked S3 bucket for lab reports/prescriptions is
> a separate follow-up (security rule #6) — the API will still start without it;
> file-upload endpoints just won't work until it exists.

---

## Phase 5 — Launch the EC2 instance

```bash
# Latest Amazon Linux 2023 AMI
AMI_ID=$(aws ssm get-parameters \
  --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query 'Parameters[0].Value' --output text)

# SSH key pair (used over the SSM tunnel, not over open port 22)
aws ec2 create-key-pair --key-name kyros-prod \
  --query 'KeyMaterial' --output text > /tmp/kyros-prod.pem
chmod 400 /tmp/kyros-prod.pem

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.small \
  --key-name kyros-prod \
  --subnet-id $SUBNET_ID \
  --security-group-ids $SG_ID \
  --iam-instance-profile Name=kyros-ec2-profile \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=kyros-backend-prod}]' \
  --metadata-options 'HttpTokens=required' \
  --query 'Instances[0].InstanceId' --output text)

echo "Instance: $INSTANCE_ID"

aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Elastic IP so DNS doesn't break on instance restart
ALLOC_ID=$(aws ec2 allocate-address --domain vpc --query AllocationId --output text)
aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $ALLOC_ID
PUBLIC_IP=$(aws ec2 describe-addresses --allocation-ids $ALLOC_ID \
  --query 'Addresses[0].PublicIp' --output text)

echo "Instance: $INSTANCE_ID   Public IP: $PUBLIC_IP"
```

**Write down `$INSTANCE_ID` and `$PUBLIC_IP`** — you'll need:
- `$INSTANCE_ID` for the `EC2_HOST` GitHub secret (Phase 7) and for SSM sessions below.
- `$PUBLIC_IP` for the Cloudflare DNS A record (Phase 6).

Wait ~1–2 minutes for the SSM agent (pre-installed on AL2023) to register, then verify:

```bash
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
  --query 'InstanceInformationList[0].PingStatus' --output text
# Should print: Online
```

Shell in (no open SSH port needed):

```bash
aws ssm start-session --target $INSTANCE_ID
```

---

## Phase 6 — Bootstrap the EC2 host

Run this **inside the SSM session** (`sudo` is required; AL2023's default `ssm-user`
has sudo). This installs Docker, configures swap, and lays down the files from
`infra/ec2/`.

```bash
sudo dnf update -y
sudo dnf install -y docker git jq

sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user ssm-user

# 2 GB swap (referenced by docker-compose.prod.yml comments)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Docker Compose v2 plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version

sudo mkdir -p /etc/kyros /var/lib/kyros/beat
```

Now copy the repo's `infra/ec2/` files onto the host. Easiest path: from your **local
machine** (not CloudShell, since CloudShell doesn't have your repo checked out),
clone the repo and `scp`/SSM-copy the four files:

- `infra/ec2/docker-compose.prod.yml` → `/etc/kyros/docker-compose.yml`
- `infra/ec2/kyros-prepare-env.sh` → `/usr/local/bin/kyros-prepare-env.sh`
- `infra/ec2/kyros-backend.service` → `/etc/systemd/system/kyros-backend.service`
- `infra/ec2/Caddyfile` → `/etc/kyros/Caddyfile` (after editing the hostname — see Phase 7)
- `infra/docker/postgres/init.sql` → `/etc/kyros/rds-init.sql` (applied to RDS once, below — not mounted)

The simplest way without configuring SCP-over-SSM: from CloudShell, since it doesn't
have the repo, use `aws ssm send-command` with the file contents inlined, or
(simpler) just `git clone` your repo into CloudShell — CloudShell has internet access
and persistent `$HOME` storage:

```bash
git clone https://github.com/<your-org>/<your-repo>.git /tmp/repo
```

Then use SSM `send-command` to write each file (works for text files; example for one,
repeat for the others by changing `SOURCE`/`DEST`):

```bash
write_remote_file() {
  local SRC=$1 DEST=$2 MODE=$3
  aws ssm send-command \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters commands="$(python3 -c "
import sys, base64, shlex
content = open('$SRC','rb').read()
b64 = base64.b64encode(content).decode()
print(f'echo {b64} | base64 -d | sudo tee $DEST > /dev/null && sudo chmod $MODE $DEST')
")" \
    --query 'Command.CommandId' --output text
}

write_remote_file /tmp/repo/infra/ec2/docker-compose.prod.yml /etc/kyros/docker-compose.yml 644
write_remote_file /tmp/repo/infra/ec2/kyros-prepare-env.sh /usr/local/bin/kyros-prepare-env.sh 755
write_remote_file /tmp/repo/infra/ec2/kyros-backend.service /etc/systemd/system/kyros-backend.service 644
write_remote_file /tmp/repo/infra/docker/postgres/init.sql /etc/kyros/rds-init.sql 644
```

(Edit `infra/ec2/Caddyfile` to use your real API hostname — e.g. `api.kyrosclinic.com` —
and the cert paths from Phase 7 before copying it.)

### Initialize the RDS database (one-time)

From the EC2 (in the SSM session), apply the extensions + readonly-role script against
RDS. All three extensions (`pgcrypto`, `pg_trgm`, `btree_gin`) are RDS-supported, and
the RDS master user has sufficient rights:

```bash
RDS_ENDPOINT=<from Phase 3b>

sudo docker run --rm -i \
  -e PGPASSWORD='<RDS_PASSWORD from Phase 3b>' \
  postgres:16-alpine \
  psql "host=${RDS_ENDPOINT} port=5432 user=postgres dbname=kyros sslmode=require" \
  < /etc/kyros/rds-init.sql
```

You should see `CREATE EXTENSION` ×3 and the role grants. This runs once; re-running
is harmless (everything is `IF NOT EXISTS`-guarded).

Then on the EC2 (back in the SSM session), seed the image tag and start the stack:

```bash
echo "latest" | sudo tee /etc/kyros/image-tag

sudo systemctl daemon-reload
sudo systemctl enable --now kyros-backend.service
sudo systemctl status kyros-backend.service --no-pager
```

`kyros-prepare-env.sh` runs as `ExecStartPre` — it needs the SSM parameter from Phase 4
to exist (it does) and the instance role permissions from Phase 1a (already attached).
If it fails, check:

```bash
sudo /usr/local/bin/kyros-prepare-env.sh   # run manually to see the error
sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros logs
```

---

## Phase 7 — Cloudflare: DNS + Origin CA + TLS mode

1. **DNS**: In Cloudflare, add an `A` record: `api` → `$PUBLIC_IP`, **Proxy status:
   Proxied** (orange cloud).

2. **Origin CA certificate**: Cloudflare dashboard → your domain → **SSL/TLS → Origin
   Server → Create Certificate**. Accept defaults (RSA, 15-year validity, hostnames
   `*.kyrosclinic.com` + `kyrosclinic.com`). Cloudflare shows you a certificate and private
   key — copy both.

3. Write them to the EC2 (in the SSM session):

   ```bash
   sudo mkdir -p /etc/kyros/caddy-certs
   sudo tee /etc/kyros/caddy-certs/cert.pem > /dev/null   # paste cert, then Ctrl-D
   sudo tee /etc/kyros/caddy-certs/key.pem > /dev/null    # paste key, then Ctrl-D
   sudo chmod 600 /etc/kyros/caddy-certs/key.pem
   ```

4. Make sure `/etc/kyros/Caddyfile` (copied in Phase 6) has the right hostname
   (`api.kyrosclinic.com`), then restart:

   ```bash
   sudo docker compose -f /etc/kyros/docker-compose.yml --project-name kyros up -d
   ```

5. **SSL/TLS mode**: Cloudflare dashboard → **SSL/TLS → Overview → Full (strict)**.
   This encrypts the Cloudflare-to-origin hop too (not just client-to-Cloudflare),
   which matters since this is PHI traffic (security rule #7).

6. Verify:

   ```bash
   curl -sf https://api.kyrosclinic.com/healthz && echo OK
   curl -sf https://api.kyrosclinic.com/readyz
   ```

---

## Phase 8 — GitHub Actions secrets + first deploy

In the GitHub repo: **Settings → Environments → production → Secrets** (the workflow
uses `environment: production`), add:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | from Phase 1b (`kyros-ci` user) |
| `AWS_SECRET_ACCESS_KEY` | from Phase 1b |
| `EC2_HOST` | `$INSTANCE_ID` (e.g. `i-0123456789abcdef0`) — **not** an IP, since deploys tunnel over SSM |
| `SSH_PRIVATE_KEY` | contents of `/tmp/kyros-prod.pem` from Phase 5 |
| `RDS_INSTANCE_ID` | `kyros-prod` (Phase 3b) — used for the pre-migration snapshot |

Remove the now-unused `BASTION_HOST` secret if present — this topology has no bastion.

> The workflow and `infra/scripts/deploy-phase1.sh` were updated alongside this guide
> to tunnel SSH over SSM (`aws ssm start-session` + `AWS-StartSSHSession`) instead of
> connecting to a public IP/bastion — matching the security-group setup in Phase 3
> (no port 22 open to the internet).

Trigger the first deploy by pushing to `main` (or re-running the workflow). It will:
1. Run tests.
2. Build and push the image to ECR.
3. Snapshot RDS (`kyros-pre-deploy-<timestamp>-<sha>`, pruned after 14 days).
4. Run `alembic upgrade head` against RDS.
5. `docker compose up -d` with the new image tag.
6. Health-check `/healthz`.

---

## Verification checklist

- [ ] `aws budgets describe-budgets --account-id $ACCOUNT_ID` shows `kyros-monthly`.
- [ ] `curl https://api.kyrosclinic.com/healthz` → `200`.
- [ ] `curl https://api.kyrosclinic.com/readyz` → `{"db": true, "redis": true}`.
- [ ] `aws ssm start-session --target $INSTANCE_ID` works without any inbound SG rule
      for port 22.
- [ ] `sudo docker compose -f /etc/kyros/docker-compose.yml ps` shows redis,
      backend-api, celery-worker, celery-beat, caddy all healthy/running (Postgres is
      on RDS, not in compose).
- [ ] `aws rds describe-db-instances --db-instance-identifier kyros-prod` shows
      `StorageEncrypted: true`, `PubliclyAccessible: false`,
      `BackupRetentionPeriod: 7`, `DeletionProtection: true`.
- [ ] Cloudflare SSL/TLS mode is **Full (strict)**.
- [ ] GitHub Actions `Deploy Backend` workflow succeeds end-to-end on a push to
      `main`, including the `kyros-pre-deploy-*` RDS snapshot step.

## What's deliberately deferred

- **S3 bucket for PHI** (`kyros-phi-production`, SSE-KMS, public access blocked) —
  needed before lab-report/prescription upload endpoints work.
- **Razorpay / 100ms / MSG91 / AiSensy / SendGrid / Sentry** credentials — fill into
  the SSM parameter (Phase 4) as you onboard each integration; `aws ssm put-parameter
  ... --overwrite` then restart the stack.
- **RDS Multi-AZ** — enable once there are paying users
  (`aws rds modify-db-instance --db-instance-identifier kyros-prod --multi-az`).
- **ElastiCache / ALB / CloudFront / WAF** — Phase 2, triggered by MRR > ₹50K or
  >500 concurrent users (`docs/strategy/build-spec.md` §14). `docs/runbook-prod.md`
  currently documents the Phase 2 topology in places; it should be updated to reflect
  this Phase 1 reality once this is live.
