"""Google Document AI — Healthcare Document Parser integration.

Confidence thresholds (build-spec §5):
  confidence < 0.85  → field added to low_confidence_fields list (flagged for doctor review)
  confidence < 0.60  → biomarker also marked needs_patient_correction=True

When KYROS_GOOGLE_DOCUMENT_AI_SECRET_NAME is empty the client operates in stub mode and
returns a synthetic parsed response so the application can be exercised without GCP credentials.

Service account JSON is fetched from AWS Secrets Manager (not env vars) so credentials never
appear in logs, Sentry, or the environment.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Confidence thresholds per build-spec §5
_DOCTOR_REVIEW_THRESHOLD = 0.85
_PATIENT_CORRECTION_THRESHOLD = 0.60

# Stub response returned when no GCP credentials are configured
_STUB_PARSED: dict[str, Any] = {
    "lab_name": "Stub Lab",
    "report_date": "2026-01-01",
    "patient_info": {
        "name_on_report": "Test Patient",
        "age": 30,
        "gender": "M",
    },
    "biomarkers": [
        {
            "name": "TSH",
            "value": "4.82",
            "unit": "mIU/L",
            "ref_low": "0.4",
            "ref_high": "4.0",
            "flag": "high",
            "confidence": 0.94,
            "needs_patient_correction": False,
        },
        {
            "name": "T4",
            "value": "8.5",
            "unit": "µg/dL",
            "ref_low": "5.1",
            "ref_high": "14.1",
            "flag": "normal",
            "confidence": 0.91,
            "needs_patient_correction": False,
        },
    ],
    "overall_confidence": 0.92,
    "_stub": True,
}


def _get_service_account_json() -> dict[str, Any]:
    """Fetch GCP service account JSON from AWS Secrets Manager."""
    import boto3
    from botocore.config import Config

    kwargs: dict[str, Any] = {
        "region_name": settings.aws_region,
        "config": Config(retries={"max_attempts": 3}),
    }
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url

    client = boto3.client("secretsmanager", **kwargs)
    response = client.get_secret_value(SecretId=settings.google_document_ai_secret_name)
    secret_str: str = response["SecretString"]
    result: dict[str, Any] = json.loads(secret_str)
    return result


def _apply_confidence_thresholds(
    biomarkers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Apply thresholds and return (annotated_biomarkers, low_confidence_field_names)."""
    low_confidence_fields: list[str] = []
    annotated: list[dict[str, Any]] = []
    for bm in biomarkers:
        confidence: float = float(bm.get("confidence", 1.0))
        entry = dict(bm)
        entry["needs_patient_correction"] = confidence < _PATIENT_CORRECTION_THRESHOLD
        if confidence < _DOCTOR_REVIEW_THRESHOLD:
            low_confidence_fields.append(bm.get("name", "unknown"))
        annotated.append(entry)
    return annotated, low_confidence_fields


def _parse_document_ai_response(document: Any) -> dict[str, Any]:
    """Convert a Document AI Document proto to the canonical parsed JSON shape."""
    lab_name: str | None = None
    report_date: str | None = None
    patient_info: dict[str, Any] = {}
    biomarkers: list[dict[str, Any]] = []

    for entity in document.entities:
        etype = entity.type_
        text = entity.mention_text.strip()
        confidence = entity.confidence

        if etype == "lab_name":
            lab_name = text
        elif etype == "report_date":
            report_date = text
        elif etype in ("patient_name", "name_on_report"):
            patient_info["name_on_report"] = text
        elif etype == "patient_age":
            try:
                patient_info["age"] = int(text)
            except ValueError:
                patient_info["age"] = text
        elif etype == "patient_gender":
            patient_info["gender"] = text[:1].upper() if text else None
        elif etype == "biomarker":
            bm: dict[str, Any] = {"confidence": round(confidence, 4)}
            for prop in entity.properties:
                ptype = prop.type_
                ptext = prop.mention_text.strip()
                if ptype == "biomarker_name":
                    bm["name"] = ptext
                elif ptype == "biomarker_value":
                    bm["value"] = ptext
                elif ptype == "biomarker_unit":
                    bm["unit"] = ptext
                elif ptype == "biomarker_reference_range_low":
                    bm["ref_low"] = ptext
                elif ptype == "biomarker_reference_range_high":
                    bm["ref_high"] = ptext
                elif ptype == "biomarker_flag":
                    bm["flag"] = ptext.lower()
            biomarkers.append(bm)

    if not biomarkers:
        logger.warning("document_ai.no_biomarkers_found")

    overall_confidence = (
        round(sum(b.get("confidence", 0.0) for b in biomarkers) / len(biomarkers), 4)
        if biomarkers
        else 0.0
    )

    annotated_biomarkers, low_confidence_fields = _apply_confidence_thresholds(biomarkers)

    return {
        "lab_name": lab_name,
        "report_date": report_date,
        "patient_info": patient_info,
        "biomarkers": annotated_biomarkers,
        "overall_confidence": overall_confidence,
        "_low_confidence_fields": low_confidence_fields,
    }


def parse_healthcare_document(file_bytes: bytes, *, mime_type: str = "application/pdf") -> dict[str, Any]:
    """Send file bytes to the Healthcare Document Parser and return canonical JSON.

    Returns a dict with keys:
      lab_name, report_date, patient_info, biomarkers, overall_confidence,
      _low_confidence_fields (list of biomarker names below threshold)

    In stub mode (no processor_id or secret configured) returns _STUB_PARSED.
    """
    if not settings.google_document_ai_processor_id or not settings.google_document_ai_secret_name:
        logger.warning("document_ai.stub_mode", reason="no_processor_id_or_secret_configured")
        stub = dict(_STUB_PARSED)
        annotated, low = _apply_confidence_thresholds(stub["biomarkers"])
        stub["biomarkers"] = annotated
        stub["_low_confidence_fields"] = low
        return stub

    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai
    from google.oauth2 import service_account

    sa_json = _get_service_account_json()
    creds = service_account.Credentials.from_service_account_info(
        sa_json,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    client_options = ClientOptions(
        api_endpoint=f"{settings.google_document_ai_location}-documentai.googleapis.com"
    )
    client = documentai.DocumentProcessorServiceClient(
        credentials=creds,
        client_options=client_options,
    )

    raw_document = documentai.RawDocument(content=file_bytes, mime_type=mime_type)
    request = documentai.ProcessRequest(
        name=settings.google_document_ai_processor_id,
        raw_document=raw_document,
    )

    logger.info("document_ai.processing", mime_type=mime_type, bytes_len=len(file_bytes))
    response = client.process_document(request=request)
    result = _parse_document_ai_response(response.document)
    logger.info(
        "document_ai.complete",
        overall_confidence=result.get("overall_confidence"),
        low_confidence_count=len(result.get("_low_confidence_fields", [])),
    )
    return result
