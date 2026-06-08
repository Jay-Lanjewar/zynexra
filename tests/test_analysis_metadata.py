"""
Unit tests for the C2 (analysis_metadata) contract.

Verifies that:
1. build_audit_json_payload exposes analysis_metadata under metadata.analysis_metadata
   when it is provided.
2. The field is omitted when analysis_metadata is None (backward compat).
3. The shape contract matches what the frontend consumes:
   was_truncated (bool), kept_chars (int >= 0), dropped_chars (int >= 0),
   context_utilization_pct (float), pages_seen (int | None).

These tests are pure unit tests with no Ollama dependency.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.normalization_engine import build_audit_json_payload


def _make_issues_json():
    return [
        {
            "issue_title": "Sample issue",
            "severity": "MEDIUM",
            "category": "Liability Exposure",
            "location": "Section 1",
            "quoted_text": "Some quoted text.",
            "risk_explanation": "Some risk.",
            "suggested_improvement": "Some improvement.",
        }
    ]


def test_analysis_metadata_appears_when_provided():
    analysis = {
        "was_truncated": False,
        "kept_chars": 12000,
        "dropped_chars": 0,
        "context_utilization_pct": 73.4,
        "pages_seen": 7,
    }
    payload = build_audit_json_payload(
        complete_response="{}",
        model="qwen2.5:3b-instruct",
        user_input="some contract text",
        fallback_used=False,
        inference_duration_ms=200,
        parsed_issues=None,
        analysis_metadata=analysis,
    )
    assert "metadata" in payload
    assert "analysis_metadata" in payload["metadata"]
    md = payload["metadata"]["analysis_metadata"]
    assert md == analysis
    assert isinstance(md["was_truncated"], bool)
    assert isinstance(md["kept_chars"], int) and md["kept_chars"] >= 0
    assert isinstance(md["dropped_chars"], int) and md["dropped_chars"] >= 0
    assert isinstance(md["context_utilization_pct"], (int, float))
    assert md["pages_seen"] is None or isinstance(md["pages_seen"], int)


def test_analysis_metadata_omitted_when_none():
    payload = build_audit_json_payload(
        complete_response="{}",
        model="qwen2.5:3b-instruct",
        user_input="some contract text",
        fallback_used=False,
        inference_duration_ms=200,
        parsed_issues=None,
        analysis_metadata=None,
    )
    # metadata dict exists; analysis_metadata is simply absent
    assert "metadata" in payload
    assert "analysis_metadata" not in payload["metadata"]


def test_analysis_metadata_truncation_shape():
    analysis = {
        "was_truncated": True,
        "kept_chars": 8000,
        "dropped_chars": 4000,
        "context_utilization_pct": 100.0,
        "pages_seen": 32,
    }
    payload = build_audit_json_payload(
        complete_response="{}",
        model="qwen2.5:3b-instruct",
        user_input="a very long contract",
        fallback_used=False,
        inference_duration_ms=500,
        parsed_issues=None,
        analysis_metadata=analysis,
    )
    md = payload["metadata"]["analysis_metadata"]
    assert md["was_truncated"] is True
    assert md["kept_chars"] + md["dropped_chars"] == 12000
    assert md["pages_seen"] == 32


def test_analysis_metadata_pages_seen_can_be_none():
    analysis = {
        "was_truncated": False,
        "kept_chars": 5000,
        "dropped_chars": 0,
        "context_utilization_pct": 30.5,
        "pages_seen": None,
    }
    payload = build_audit_json_payload(
        complete_response="{}",
        model="qwen2.5:3b-instruct",
        user_input="contract text",
        fallback_used=False,
        inference_duration_ms=200,
        parsed_issues=None,
        analysis_metadata=analysis,
    )
    assert payload["metadata"]["analysis_metadata"]["pages_seen"] is None
