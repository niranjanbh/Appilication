"""S3 helpers for lab report upload, download, and presigned URL generation.

All object keys follow the convention:
  patients/{patient_uuid}/lab-reports/{lab_report_uuid}/{filename}

Presigned PUT URLs are valid for 15 minutes (security rule: 9-minute max for download,
15 minutes for upload — see backend-strategy §13).
"""

from __future__ import annotations

import uuid
from typing import Any

import boto3
import structlog
from botocore.config import Config

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Content-type allowlist for lab report uploads
ALLOWED_CONTENT_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png"})
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _s3_client() -> Any:
    kwargs: dict[str, Any] = {
        "region_name": settings.aws_region,
        "config": Config(signature_version="s3v4"),
    }
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("s3", **kwargs)


def lab_report_s3_key(
    patient_uuid: uuid.UUID,
    lab_report_uuid: uuid.UUID,
    filename: str,
) -> str:
    return f"patients/{patient_uuid}/lab-reports/{lab_report_uuid}/{filename}"


def generate_upload_url(
    *,
    patient_uuid: uuid.UUID,
    lab_report_uuid: uuid.UUID,
    filename: str,
    content_type: str,
    file_size_bytes: int,
) -> dict[str, Any]:
    """Return a presigned POST (fields + url) valid for 15 minutes.

    The presigned POST pins content-type and enforces the 10 MB size limit
    at the S3 layer as a defence-in-depth measure.
    """
    client = _s3_client()
    key = lab_report_s3_key(patient_uuid, lab_report_uuid, filename)
    result: dict[str, Any] = client.generate_presigned_post(
        Bucket=settings.s3_bucket,
        Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, MAX_FILE_SIZE_BYTES],
        ],
        ExpiresIn=900,  # 15 minutes
    )
    return {"upload_url": result["url"], "fields": result["fields"], "s3_key": key}


def generate_download_url(*, s3_key: str) -> str:
    """Return a presigned GET URL valid for 10 minutes."""
    client = _s3_client()
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=600,  # 10 minutes
    )
    return url


def data_export_s3_key(user_id: uuid.UUID, request_id: uuid.UUID) -> str:
    """Deterministic key for a DPDP data-export ZIP — derivable from the DSR row."""
    return f"exports/{user_id}/{request_id}.zip"


def put_bytes(
    *,
    s3_key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """Server-side upload of in-memory bytes with SSE-KMS (security rule 6).

    Used for generated PHI artifacts (DPDP export ZIPs). All PHI in S3 must be
    encrypted with SSE-KMS; an explicit key is used when configured, otherwise
    the account default aws/s3 KMS key.
    """
    client = _s3_client()
    extra: dict[str, Any] = {"ServerSideEncryption": "aws:kms"}
    if settings.s3_kms_key_id:
        extra["SSEKMSKeyId"] = settings.s3_kms_key_id
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=s3_key,
        Body=data,
        ContentType=content_type,
        **extra,
    )


def head_object(*, s3_key: str) -> dict[str, Any] | None:
    """Return S3 HEAD metadata or None if the object does not exist."""
    import botocore.exceptions

    client = _s3_client()
    try:
        response: dict[str, Any] = client.head_object(
            Bucket=settings.s3_bucket, Key=s3_key
        )
        return response
    except botocore.exceptions.ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise


def download_bytes(*, s3_key: str) -> bytes:
    """Download an S3 object into memory and return its bytes."""
    import io

    client = _s3_client()
    buf = io.BytesIO()
    client.download_fileobj(settings.s3_bucket, s3_key, buf)
    return buf.getvalue()
