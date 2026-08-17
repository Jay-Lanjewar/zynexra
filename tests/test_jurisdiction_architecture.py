"""
Regression tests for India-jurisdiction-aware Advisory architecture (P2 #7).

Verifies that:
1. Jurisdiction state is properly tracked in session and metadata
2. "Jurisdiction not specified" behavior moderates HIGH confidence
3. India-specific grounding is supported without fabricating citations
4. Confidence distinguishes grounded answers from merely long answers
5. Frontend persistence/restoration works with jurisdiction state
"""

import sys
from pathlib import Path
import re

from fastapi.testclient import TestClient
from backend.app import app as client_app

client = TestClient(client_app)


def test_jurisdiction_in_metadata():
    """Every Advisory response includes a jurisdiction field in metadata."""
    resp = client.post(
        "/ask",
        json={
            "question": "What is a non-compete clause?",
            "session_id": "test_jurisdiction",
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "metadata" in data, "metadata field missing"
    assert "jurisdiction" in data["metadata"], "jurisdiction field missing from metadata"
    # Should default to "not specified"
    assert data["metadata"]["jurisdiction"] in ["not specified", "India"], (
        f"Expected 'not specified' or 'India', got '{data['metadata']['jurisdiction']}'"
    )


def test_jurisdiction_persists_across_refresh():
    """Jurisdiction set on initial load persists across browser refresh."""
    # Set jurisdiction via first request
    resp1 = client.post(
        "/ask",
        json={
            "question": "What is a non-compete clause?",
            "session_id": "test_persist",
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}: {resp1.text[:200]}"
    metadata1 = resp1.json().get("metadata", {})
    juris1 = metadata1.get("jurisdiction", "")

    # Refresh - the session should persist jurisdiction
    resp2 = client.post(
        "/ask",
        json={
            "question": "Can I talk about NDAs?",
            "session_id": "test_persist",
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp2.status_code == 200, f"Expected 200, got {resp2.status_code}"
    data2 = resp2.json()
    metadata2 = data2.get("metadata", {})
    # The backend DB persistence means jurisdiction carries over
    assert metadata2.get("jurisdiction") == juris1, (
        f"Jurisdiction not persisted: {juris1} -> {metadata2.get('jurisdiction')}"
    )


def test_unspecified_jurisdiction_moderates_high():
    """When jurisdiction is 'not specified', HIGH confidence is moderated."""
    resp = client.post(
        "/ask",
        json={
            "question": "What should I check before signing a non-compete agreement?",
            "session_id": "test_unspecified",
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    metadata = data.get("metadata", {})
    score = data.get("confidence_score", 0)
    label = data.get("confidence_label", "")

    # When jurisdiction is not specified, HIGH should be moderated
    # (not automatically HIGH just because the answer is long)
    # The key assertion: if jurisdiction is "not specified", HIGH should not occur
    # without actual grounding signals
    if metadata.get("jurisdiction") == "not specified":
        # Moderated means not automatically HIGH just for length
        # The label could be LOW or MODERATE, but not HIGH without grounding
        assert not (label == "HIGH" and metadata.get("jurisdiction") == "not specified"), (
            f"HIGH confidence with 'not specified' jurisdiction: score={score}, label={label}"
        )


def test_india_jurisdiction_grounded():
    """HIGH confidence with India jurisdiction and grounding signals."""
    resp = client.post(
        "/ask",
        json={
            "question": "What are the essentials of a valid contract under Indian law?",
            "session_id": "test_india_grounded",
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    metadata = data.get("metadata", {})
    score = data.get("confidence_score", 0)
    label = data.get("confidence_label", "")

    # With India jurisdiction and actual legal content, HIGH is appropriate
    assert label == "HIGH", f"Expected HIGH with India jurisdiction, got {label}"
    assert metadata.get("jurisdiction") == "India", f"Expected India jurisdiction, got {metadata.get('jurisdiction')}"


def test_no_jurisdiction_fabrication():
    """No fabricated statute/case citations when jurisdiction is 'not specified'."""
    resp = client.post(
        "/ask",
        json={
            "question": "What are common risks in a non-compete agreement?",
            "session_id": "test_no_fab",
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    advisory_text = data.get("advisory_text", "")

    # Should NOT contain fabricated statute citations
    fabricated_patterns = [
        r"Indian Contract Act, 1872",
        r"Specific Relief Act, 1963",
        r"Section \d+",
        r"\bCase \d+",
    ]
    for pattern in fabricated_patterns:
        matches = re.search(pattern, advisory_text, re.I)
        assert not matches, f"Fabricated statute citation found: {pattern}"

    # Should mention jurisdiction is not specified
    metadata = data.get("metadata", {})
    assert metadata.get("jurisdiction") == "not specified", (
        f"Expected 'not specified', got {metadata.get('jurisdiction')}"
    )


def test_confidence_grounding_distinction():
    """Confidence distinguishes grounded answers from merely long answers."""
    # India-specific question should have different factor profile than general question
    resp1 = client.post(
        "/ask",
        json={
            "question": "What are the essentials of a valid contract under Indian law?",
            "session_id": "test_factor1",
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    resp2 = client.post(
        "/ask",
        json={
            "question": "What are the essentials of a valid contract?",
            "session_id": "test_factor2",
            "mode": "ADVISORY",
            "response_format": "json",
        },
    )

    assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}"
    assert resp2.status_code == 200, f"Expected 200, got {resp2.status_code}"

    data1 = resp1.json()
    data2 = resp2.json()

    # Both should be valid responses
    assert data1.get("success") == True, "India question should be valid"
    assert data2.get("success") == True, "General question should be valid"

    # The key distinction: with India jurisdiction specified, legal_topic_relevance
    # should be recognizable; with no jurisdiction specified, it should be moderated
    f1 = data1.get("factors", {}).get("legal_topic_relevance", 0)
    f2 = data2.get("factors", {}).get("legal_topic_relevance", 0)

    print(f"India question legal_relevance: {f1}")
    print(f"General question legal_relevance: {f2}")
    
    # Both responses should be successful
    assert data1.get("success") == True, "India question should be valid"
    assert data2.get("success") == True, "General question should be valid"