"""Unit tests for the pure _artifact_hash helper (no DB required)."""

from __future__ import annotations

import types

from app.services.sign_off_service import _artifact_hash


def _content(
    title: str = "Test Article",
    body_md: str | None = "Some body.",
    content_url: str | None = None,
) -> object:
    return types.SimpleNamespace(title=title, body_md=body_md, content_url=content_url)


def test_artifact_hash_is_stable_for_identical_content() -> None:
    c = _content()
    assert _artifact_hash(c) == _artifact_hash(c)


def test_artifact_hash_changes_when_title_changes() -> None:
    c1 = _content(title="Title A")
    c2 = _content(title="Title B")
    assert _artifact_hash(c1) != _artifact_hash(c2)


def test_artifact_hash_changes_when_body_changes() -> None:
    c1 = _content(body_md="Body A")
    c2 = _content(body_md="Body B")
    assert _artifact_hash(c1) != _artifact_hash(c2)


def test_artifact_hash_handles_none_fields() -> None:
    c = _content(body_md=None, content_url=None)
    h = _artifact_hash(c)
    assert len(h) == 64  # SHA-256 hex digest is always 64 chars
