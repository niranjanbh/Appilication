#!/bin/bash
# LocalStack ready-hook: provision the dev uploads bucket.
# Runs once LocalStack is ready (mounted into /etc/localstack/init/ready.d/).
set -euo pipefail

BUCKET="${KYROS_S3_BUCKET:-kyros-dev-uploads}"

awslocal s3 mb "s3://${BUCKET}" 2>/dev/null || true

# Permit browser/device uploads (presigned POST) and downloads from the host origin.
awslocal s3api put-bucket-cors --bucket "${BUCKET}" --cors-configuration '{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"]
    }
  ]
}'

echo "LocalStack: bucket ${BUCKET} ready"
