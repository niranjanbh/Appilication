#!/usr/bin/env bash
# Nightly logical backup of the in-container Postgres database to S3.
# Runs on the EC2 host via systemd timer kyros-db-backup.timer (22:00 UTC = 03:30 IST).
#
# Complements (does not replace) the pre-deploy backup taken by
# infra/scripts/snapshot-before-deploy.sh. Retention is enforced by the S3
# lifecycle rule on the db-backups/ prefix, so no pruning happens here.
#
# Restore procedure: docs/runbook-prod.md §5.

set -euo pipefail

AWS_REGION="ap-south-1"
ENV_FILE="/etc/kyros/backend.env"

log() { echo "[kyros-db-backup] $(date -u +%H:%M:%S) $*"; }

source <(grep -E '^(POSTGRES_USER|POSTGRES_DB|KYROS_S3_BUCKET)=' "${ENV_FILE}")
: "${POSTGRES_USER:?missing from ${ENV_FILE}}"
: "${POSTGRES_DB:?missing from ${ENV_FILE}}"
: "${KYROS_S3_BUCKET:?missing from ${ENV_FILE}}"

if ! docker ps --format '{{.Names}}' | grep -qx kyros-postgres-1; then
    log "ERROR: kyros-postgres-1 is not running — nothing was backed up"
    exit 1
fi

BACKUP_NAME="kyros-nightly-$(date -u +%Y%m%d-%H%M%S).sql.gz"
DEST="s3://${KYROS_S3_BUCKET}/db-backups/nightly/${BACKUP_NAME}"

log "pg_dump ${POSTGRES_DB} -> ${DEST}"
docker exec kyros-postgres-1 \
    pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-acl \
    | gzip \
    | aws s3 cp - "${DEST}" --region "${AWS_REGION}"

log "Backup complete: ${DEST}"
