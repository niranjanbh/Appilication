#!/usr/bin/env bash
# Logical backup of the in-container Postgres database before a production
# deploy/migration. Pushes a gzipped pg_dump to S3.
#
# Postgres runs on the EC2 host itself (no RDS) — this replaces the old RDS
# snapshot step. Restore with:
#   gunzip -c <backup>.sql.gz | docker exec -i kyros-postgres-1 \
#     psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
#
# Old backups expire via an S3 lifecycle rule on the db-backups/ prefix
# (set once on the bucket — see infra/ec2 bootstrap notes), so no pruning here.
#
# On a first-ever deploy the postgres container doesn't exist yet (empty DB,
# nothing to back up) — this script detects that and exits 0.
#
# Called by deploy-phase1.sh but can also run standalone.
#
# Usage: ./snapshot-before-deploy.sh <image_tag>

set -euo pipefail

IMAGE_TAG="${1:-manual}"
INSTANCE_ID="${EC2_HOST:?EC2_HOST (instance ID) not set}"
AWS_REGION="ap-south-1"
DEPLOY_USER="ec2-user"
SSH_KEY="/tmp/deploy_key"

log() { echo "[snapshot] $(date -u +%H:%M:%S) $*"; }

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

BACKUP_NAME="kyros-pre-deploy-$(date -u +%Y%m%d-%H%M%S)-${IMAGE_TAG:0:12}.sql.gz"

log "Backing up kyros-postgres-1 -> db-backups/${BACKUP_NAME}"

$SSH_CMD "${INSTANCE_ID}" bash <<REMOTE
  set -euo pipefail
  if ! sudo docker ps --format '{{.Names}}' | grep -qx kyros-postgres-1; then
    echo "[snapshot] kyros-postgres-1 not running yet (first deploy?) — skipping backup"
    exit 0
  fi
  source <(grep -E '^(POSTGRES_USER|POSTGRES_DB|KYROS_S3_BUCKET)=' /etc/kyros/backend.env)
  DEST="s3://\${KYROS_S3_BUCKET}/db-backups/${BACKUP_NAME}"
  sudo docker exec kyros-postgres-1 \
    pg_dump -U "\${POSTGRES_USER}" -d "\${POSTGRES_DB}" --no-owner --no-acl \
    | gzip \
    | aws s3 cp - "\${DEST}" --region ${AWS_REGION}
  echo "[snapshot] backup written to \${DEST}"
REMOTE

log "Backup step complete."
