#!/usr/bin/env bash
# Phase 1 EC2 deployment script — run from CI after image push.
#
# Prerequisites:
#   - CI runner has SSH access to EC2 via bastion (SSH_PRIVATE_KEY, EC2_HOST, BASTION_HOST set)
#   - ECR image already pushed: ECR_REGISTRY/kyros-backend:IMAGE_TAG
#   - RDS is accessible from the EC2 host
#
# Usage: ./deploy-phase1.sh <image_tag>

set -euo pipefail

IMAGE_TAG="${1:-}"
if [ -z "${IMAGE_TAG}" ]; then
  echo "Usage: $0 <image_tag>" >&2
  exit 1
fi

ECR_REGISTRY="${ECR_REGISTRY:?ECR_REGISTRY not set}"
EC2_HOST="${EC2_HOST:?EC2_HOST not set}"
BASTION_HOST="${BASTION_HOST:-}"
AWS_REGION="ap-south-1"
DEPLOY_USER="ec2-user"

log() { echo "[deploy-phase1] $(date -u +%H:%M:%S) $*"; }

# ── Step 1: RDS snapshot before migration ───────────────────────────────────
log "Creating pre-deploy RDS snapshot..."
bash "$(dirname "$0")/snapshot-before-deploy.sh" "${IMAGE_TAG}"

# ── Step 2: Run Alembic migration on EC2 ────────────────────────────────────
log "Running migration: alembic upgrade head (image=${IMAGE_TAG})"

SSH_CMD="ssh"
if [ -n "${BASTION_HOST}" ]; then
  SSH_CMD="ssh -J ${DEPLOY_USER}@${BASTION_HOST}"
fi

$SSH_CMD "${DEPLOY_USER}@${EC2_HOST}" bash <<REMOTE
  set -euo pipefail
  aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
  docker pull ${ECR_REGISTRY}/kyros-backend:${IMAGE_TAG}
  # Run migration using same secrets as production
  source /etc/kyros/backend.env
  docker run --rm \
    --env-file /etc/kyros/backend.env \
    --network host \
    ${ECR_REGISTRY}/kyros-backend:${IMAGE_TAG} \
    alembic upgrade head
REMOTE

log "Migration completed successfully."

# ── Step 3: Deploy new containers ───────────────────────────────────────────
log "Deploying new containers..."

$SSH_CMD "${DEPLOY_USER}@${EC2_HOST}" bash <<REMOTE
  set -euo pipefail
  echo "${IMAGE_TAG}" > /etc/kyros/image-tag
  export IMAGE_TAG="${IMAGE_TAG}"
  export ECR_REGISTRY="${ECR_REGISTRY}"
  docker compose -f /etc/kyros/docker-compose.yml --project-name kyros pull
  docker compose -f /etc/kyros/docker-compose.yml --project-name kyros up -d --remove-orphans
REMOTE

# ── Step 4: Health check ─────────────────────────────────────────────────────
log "Waiting for health check..."
for i in {1..12}; do
  if $SSH_CMD "${DEPLOY_USER}@${EC2_HOST}" curl -sf http://localhost:8000/healthz > /dev/null 2>&1; then
    log "Health check passed (attempt ${i}/12)."
    break
  fi
  if [ "${i}" -eq 12 ]; then
    log "ERROR: health check failed after 60 s — rolling back"
    $SSH_CMD "${DEPLOY_USER}@${EC2_HOST}" \
      "docker compose -f /etc/kyros/docker-compose.yml --project-name kyros logs --tail=50"
    exit 1
  fi
  log "Not healthy yet (${i}/12), retrying in 5s..."
  sleep 5
done

log "Deploy of ${IMAGE_TAG} complete."
