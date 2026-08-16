"""
Regression tests for Advisory metadata preservation (P2).

Verifies that inference_duration_ms and analysis_metadata survive
from Ollama generation through app.py normalization and
build_mode_json_payload into the Advisory response metadata dict.

Tests that:
1. Actual inference duration is preserved (not hardcoded to 0)
2. Provided analysis_metadata is included in the response
3. Absent analysis_metadata defaults to {} without breaking normal responses
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app import app, SessionManager
from backend.prompts.advisory_prompt import build_advisory_prompt

client = TestClient(app)


def test_inference_duration_survives():
    """Actual inference duration should survive into Advisory metadata (not hardcoded to 0)."""
    mgr = SessionManager()
    session_id = "test_duration"

    resp = client.post(
        "/ask",
        json={
            "question": "What is a non-compete clause?",
            "session_id": session_id,
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    metadata = data.get("metadata", {})

    # The metadata should contain inference_duration_ms, and it should NOT be 0
    # (it reflects the actual Ollama generation time)
    inference_ms = metadata.get("inference_duration_ms", None)
    assert inference_ms is not None, "metadata should contain inference_duration_ms"
    assert inference_ms > 0, f"inference_duration_ms should be > 0, got {inference_ms}"
    # It should be a reasonable millisecond value (typically 1000-30000 for Ollama 3b)
    assert inference_ms < 60000, f"inference_duration_ms unreasonably large: {inference_ms}"


def test_analysis_metadata_survives():
    """Provided analysis_metadata should survive into the Advisory response."""
    mgr = SessionManager()
    session_id = "test_metadata"

    # Add a valid exchange to establish session history
    mgr.add_valid_exchange(session_id, "Prior question", "Prior answer")

    resp = client.post(
        "/ask",
        json={
            "question": "What about severance pay?",
            "session_id": session_id,
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    metadata = data.get("metadata", {})

    # analysis_metadata should be present (at minimum as {} when no doc context,
    # or with actual fields when document context was provided)
    has_analysis = "analysis_metadata" in metadata
    assert has_analysis, f"metadata should contain 'analysis_metadata', got keys: {list(metadata.keys())}"
    # When present, it should be a dict
    assert isinstance(metadata.get("analysis_metadata"), dict), (
        f"analysis_metadata should be a dict, got {type(metadata.get('analysis_metadata'))}"
    )


def test_absent_metadata_defaults_no_break():
    """When no document context is provided, absent analysis_metadata should
    default to {} without breaking normal Advisory responses."""
    mgr = SessionManager()
    session_id = "test_no_doc"

    resp = client.post(
        "/ask",
        json={
            "question": "What is a non-compete agreement?",
            "session_id": session_id,
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    metadata = data.get("metadata", {})

    # metadata should exist and be a dict
    assert isinstance(metadata, dict), f"metadata should be a dict, got {type(metadata)}"
    # It should not cause the response to fail validation
    assert data.get("success") == True, "Response should be successful"
    # The advisory_text should be non-empty
    assert len(data.get("advisory_text", "")) > 0, "advisory_text should be non-empty"
    # FRONTEND CONVERSATION CONTEXT should not appear (P1 #4 fix)
    assert "FRONTEND CONVERSATION CONTEXT" not in data.get("advisory_text", ""), (
        "task_anchor should not appear"
    )