"""Unit tests for PHIAuditMiddleware's pure helpers (no DB, no app)."""

from __future__ import annotations

import uuid

from app.observability.middleware import _is_phi_audit_exempt, _resource_from_path_params


def test_resource_from_path_params_empty() -> None:
    assert _resource_from_path_params({}) == (None, None)


def test_resource_from_path_params_no_id_key() -> None:
    assert _resource_from_path_params({"slug": "thyroid-basics"}) == (None, None)


def test_resource_from_path_params_single_id() -> None:
    rid = uuid.uuid4()
    assert _resource_from_path_params({"content_id": str(rid)}) == ("content", rid)


def test_resource_from_path_params_takes_last_id_key() -> None:
    """Multiple {x_id} segments: the last one wins (the route's "leaf" resource)."""
    patient_id = uuid.uuid4()
    report_id = uuid.uuid4()
    path_params = {"patient_id": str(patient_id), "report_id": str(report_id)}
    assert _resource_from_path_params(path_params) == ("report", report_id)


def test_resource_from_path_params_unparseable_uuid() -> None:
    assert _resource_from_path_params({"content_id": "not-a-uuid"}) == (None, None)


def test_is_phi_audit_exempt_skip_paths() -> None:
    assert _is_phi_audit_exempt("/healthz")
    assert _is_phi_audit_exempt("/readyz")


def test_is_phi_audit_exempt_docs_and_openapi() -> None:
    from app.core.config import settings

    # dev/test config: docs and openapi are enabled (only disabled in production).
    assert settings.docs_url is not None
    assert settings.openapi_url is not None
    assert _is_phi_audit_exempt(settings.docs_url)
    assert _is_phi_audit_exempt(settings.openapi_url)


def test_is_phi_audit_exempt_prefixes() -> None:
    assert _is_phi_audit_exempt("/v1/auth/login")
    assert _is_phi_audit_exempt("/v1/public/articles")
    assert _is_phi_audit_exempt("/v1/webhooks/razorpay")


def test_is_phi_audit_exempt_false_for_phi_routes() -> None:
    assert not _is_phi_audit_exempt("/v1/doctor/patients")
    assert not _is_phi_audit_exempt("/admin/content/123/publish")
    assert not _is_phi_audit_exempt("/coord/patients")
