#!/usr/bin/env bash
# Phase 1 EC2 deployment script — run from CI after image push.
#
# Prerequisites:
#   - CI runner has AWS credentials (kyros-ci) + session-manager-plugin installed
#   - SSH_PRIVATE_KEY written to /tmp/deploy_key, EC2_HOST set to the instance ID
#     (e.g. i-0123456789abcdef0) — no public IP/bastion needed, SSH tunnels over SSM
#   - ECR image already pushed: ECR_REGISTRY/kyros-backend:IMAGE_TAG
#   - Postgres runs in-container on this host (no RDS); a pg_dump backup is
#     pushed to S3 before the Alembic migration (snapshot-before-deploy.sh)
#
# Usage: ./deploy-phase1.sh <image_tag>

set -euo pipefail

IMAGE_TAG="${1:-}"
if [ -z "${IMAGE_TAG}" ]; then
  echo "Usage: $0 <image_tag>" >&2
  exit 1
fi

ECR_REGISTRY="${ECR_REGISTRY:?ECR_REGISTRY not set}"
INSTANCE_ID="${EC2_HOST:?EC2_HOST (instance ID) not set}"
AWS_REGION="ap-south-1"
DEPLOY_USER="ec2-user"
SSH_KEY="/tmp/deploy_key"

log() { echo "[deploy-phase1] $(date -u +%H:%M:%S) $*"; }

# SSH tunnels over SSM Session Manager — no port 22 open to the internet.
SSH_CONFIG="$(mktemp)"
cat > "${SSH_CONFIG}" <<EOF
Host ${INSTANCE_ID}
  User ${DEPLOY_USER}
  IdentityFile ${SSH_KEY}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  ProxyCommand aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p --region ${AWS_REGION}
EOF

SSH_CMD="ssh -F ${SSH_CONFIG}"

# ── Step 1: Refresh /etc/kyros/backend.env from SSM ─────────────────────────
# Nothing else on the deploy path writes backend.env (the systemd unit only runs
# prepare-env on service start), so refresh it here — this also picks up SSM
# parameter changes on every deploy.
log "Refreshing backend.env from SSM Parameter Store..."

$SSH_CMD "${INSTANCE_ID}" "sudo /usr/local/bin/kyros-prepare-env.sh"

# ── Step 2: Back up Postgres before touching the schema ─────────────────────
# A restorable backup must exist before every migration (PHI database).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "${SCRIPT_DIR}/snapshot-before-deploy.sh" "${IMAGE_TAG}"

# ── Step 3: Bring up Postgres + Redis (creates the kyros_default network on a
#            first deploy, no-ops on subsequent ones) ───────────────────────
# --env-file feeds compose's ${VAR} substitution (env_file: inside the yml only
# reaches container environments, not substitution).
log "Ensuring postgres + redis are up..."

$SSH_CMD "${INSTANCE_ID}" bash <<REMOTE
  set -euo pipefail
  sudo docker compose --env-file /etc/kyros/backend.env \
    -f /etc/kyros/docker-compose.yml --project-name kyros up -d --wait postgres redis
REMOTE

# ── Step 4: Run Alembic migration on EC2 ────────────────────────────────────
log "Running migration: alembic upgrade head (image=${IMAGE_TAG})"

$SSH_CMD "${INSTANCE_ID}" bash <<REMOTE
  set -euo pipefail
  aws ecr get-login-password --region ${AWS_REGION} | sudo docker login --username AWS --password-stdin ${ECR_REGISTRY}
  sudo docker pull ${ECR_REGISTRY}/kyros-backend:${IMAGE_TAG}
  # Postgres runs in-container on the kyros compose network — join it so
  # KYROS_DATABASE_URL's "postgres" hostname resolves.
  sudo docker run --rm \
    --network kyros_default \
    --env-file /etc/kyros/backend.env \
    ${ECR_REGISTRY}/kyros-backend:${IMAGE_TAG} \
    alembic upgrade head
REMOTE

log "Migration completed successfully."

# ── Step 5: Deploy new containers ───────────────────────────────────────────
# Vars are passed inline after sudo (sudo resets exported environment), and they
# take precedence over the --env-file values.
log "Deploying new containers..."

$SSH_CMD "${INSTANCE_ID}" bash <<REMOTE
  set -euo pipefail
  echo "${IMAGE_TAG}" | sudo tee /etc/kyros/image-tag > /dev/null
  sudo ECR_REGISTRY="${ECR_REGISTRY}" IMAGE_TAG="${IMAGE_TAG}" \
    docker compose --env-file /etc/kyros/backend.env \
    -f /etc/kyros/docker-compose.yml --project-name kyros pull
  sudo ECR_REGISTRY="${ECR_REGISTRY}" IMAGE_TAG="${IMAGE_TAG}" \
    docker compose --env-file /etc/kyros/backend.env \
    -f /etc/kyros/docker-compose.yml --project-name kyros up -d --remove-orphans
REMOTE

# ── Step 6: Health check ─────────────────────────────────────────────────────
log "Waiting for health check..."
for i in {1..12}; do
  if $SSH_CMD "${INSTANCE_ID}" curl -sf http://localhost:8000/healthz > /dev/null 2>&1; then
    log "Health check passed (attempt ${i}/12)."
    break
  fi
  if [ "${i}" -eq 12 ]; then
    log "ERROR: health check failed after 60 s — rolling back"
    $SSH_CMD "${INSTANCE_ID}" \
      "sudo docker compose --env-file /etc/kyros/backend.env -f /etc/kyros/docker-compose.yml --project-name kyros logs --tail=50"
    exit 1
  fi
  log "Not healthy yet (${i}/12), retrying in 5s..."
  sleep 5
done

log "Deploy of ${IMAGE_TAG} complete."
