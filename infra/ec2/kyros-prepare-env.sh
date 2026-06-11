#!/usr/bin/env bash
# Fetch secrets from AWS SSM Parameter Store and write /etc/kyros/backend.env.
# Runs as a systemd ExecStartPre step before the Docker Compose stack starts.
#
# Uses SSM Parameter Store (free tier) instead of Secrets Manager ($0.40/secret/mo).
# Secrets are stored as a single JSON SecureString at /kyros/<env>/backend.
#
# Required IAM permissions on the EC2 instance role:
#   ssm:GetParameter on arn:aws:ssm:ap-south-1:*:parameter/kyros/*
#   kms:Decrypt on the KMS key used for SecureString (20 000 free calls/mo)
#
# Usage: /usr/local/bin/kyros-prepare-env.sh [--env staging|production]

set -euo pipefail

ENV="${KYROS_ENV:-production}"
REGION="ap-south-1"
ENV_FILE="/etc/kyros/backend.env"
PARAM_NAME="/kyros/${ENV}/backend"

log() { echo "[kyros-prepare-env] $*" >&2; }

log "Fetching parameter: ${PARAM_NAME} from SSM (region ${REGION})"

# Retrieve SecureString parameter from SSM Parameter Store (free standard tier)
SECRET_JSON=$(aws ssm get-parameter \
    --name "${PARAM_NAME}" \
    --with-decryption \
    --region "${REGION}" \
    --query Parameter.Value \
    --output text)

if [ -z "${SECRET_JSON}" ]; then
    log "ERROR: empty parameter returned — aborting"
    exit 1
fi

# Write backend.env with restricted permissions
install -m 0600 -o root -g root /dev/null "${ENV_FILE}"
# Convert JSON object { "KEY": "value", ... } → KEY=value lines
echo "${SECRET_JSON}" | jq -r 'to_entries[] | "\(.key)=\(.value)"' > "${ENV_FILE}"
chmod 0600 "${ENV_FILE}"

# Postgres runs on RDS — KYROS_DATABASE_URL in the SSM JSON already points at the
# RDS endpoint, so no local postgres.env is needed.

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
