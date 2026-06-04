#!/usr/bin/env bash
# Create a manual RDS snapshot before a production deploy.
# Called by deploy-phase1.sh but can also run standalone.
#
# Usage: ./snapshot-before-deploy.sh <image_tag>

set -euo pipefail

IMAGE_TAG="${1:-manual}"
RDS_INSTANCE="${RDS_INSTANCE_ID:?RDS_INSTANCE_ID not set}"
AWS_REGION="ap-south-1"
SNAPSHOT_ID="kyros-pre-deploy-$(date -u +%Y%m%d-%H%M%S)-${IMAGE_TAG:0:12}"

log() { echo "[snapshot] $(date -u +%H:%M:%S) $*"; }

log "Creating RDS snapshot: ${SNAPSHOT_ID}"
aws rds create-db-snapshot \
  --db-instance-identifier "${RDS_INSTANCE}" \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --region "${AWS_REGION}"

log "Waiting for snapshot to complete (this can take 1–5 min)..."
aws rds wait db-snapshot-completed \
  --db-instance-identifier "${RDS_INSTANCE}" \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --region "${AWS_REGION}"

log "Snapshot ready: ${SNAPSHOT_ID}"

# Prune pre-deploy snapshots older than 14 days to manage cost
CUTOFF=$(date -u -d "14 days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
  || date -u -v -14d +%Y-%m-%dT%H:%M:%SZ)

OLD_SNAPSHOTS=$(aws rds describe-db-snapshots \
  --db-instance-identifier "${RDS_INSTANCE}" \
  --snapshot-type manual \
  --query "DBSnapshots[?SnapshotCreateTime<='${CUTOFF}' && starts_with(DBSnapshotIdentifier,'kyros-pre-deploy-')].DBSnapshotIdentifier" \
  --output text \
  --region "${AWS_REGION}")

for snap in ${OLD_SNAPSHOTS}; do
  log "Pruning old snapshot: ${snap}"
  aws rds delete-db-snapshot \
    --db-snapshot-identifier "${snap}" \
    --region "${AWS_REGION}" || true
done
