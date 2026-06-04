#!/usr/bin/env bash
# Fetch secrets from AWS Secrets Manager and write /etc/kyros/backend.env.
# Runs as a systemd ExecStartPre step before the Docker Compose stack starts.
#
# Required IAM permissions on the EC2 instance role:
#   secretsmanager:GetSecretValue on arn:aws:secretsmanager:ap-south-1:*:secret:kyros/prod/*
#
# Usage: /usr/local/bin/kyros-prepare-env.sh [--env staging|production]

set -euo pipefail

ENV="${KYROS_ENV:-production}"
REGION="ap-south-1"
ENV_FILE="/etc/kyros/backend.env"
SECRET_NAME="kyros/${ENV}/backend"

log() { echo "[kyros-prepare-env] $*" >&2; }

log "Fetching secret: ${SECRET_NAME} from region ${REGION}"

# Retrieve secret JSON from Secrets Manager
SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "${SECRET_NAME}" \
    --region "${REGION}" \
    --query SecretString \
    --output text)

if [ -z "${SECRET_JSON}" ]; then
    log "ERROR: empty secret returned — aborting"
    exit 1
fi

# Write to env file with restricted permissions
install -m 0600 -o root -g root /dev/null "${ENV_FILE}"
# Convert JSON object to KEY=VALUE lines (requires jq)
echo "${SECRET_JSON}" | jq -r 'to_entries[] | "\(.key)=\(.value)"' > "${ENV_FILE}"
chmod 0600 "${ENV_FILE}"

# Also write image metadata for compose substitution
ECR_REGISTRY=$(aws ecr describe-registry --region "${REGION}" --query registryId --output text).dkr.ecr.${REGION}.amazonaws.com
IMAGE_TAG=$(cat /etc/kyros/image-tag 2>/dev/null || echo "latest")

cat >> "${ENV_FILE}" <<EOF
ECR_REGISTRY=${ECR_REGISTRY}
IMAGE_TAG=${IMAGE_TAG}
EOF

# Authenticate Docker to ECR
aws ecr get-login-password --region "${REGION}" \
    | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

log "Environment file written: ${ENV_FILE} ($(wc -l < "${ENV_FILE}") vars)"
