"""
Regression tests for Advisory history detail endpoint.

Verifies that convert_history_record_to_response() correctly formats
Advisory messages into a human-readable string, and that
validate_advisory_response() properly rejects non-string advisory_text.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.response_schemas import (
    convert_history_record_to_response,
    validate_advisory_response,
)


def test_advisory_history_detail_returns_string():
    """advisory_text must be a string, never a list or other type."""
    rec = {"messages": [{"user": "Is my non-compete enforceable?", "assistant": "Generally yes..."}]}
    r = convert_history_record_to_response(rec, "advisory", "model")
    assert isinstance(r["advisory_text"], str), (
        f"advisory_text must be str, got {type(r['advisory_text'])}: {r['advisory_text']!r}"
    )


def test_advisory_history_detail_content():
    """Non-empty conversation history is represented correctly in the formatted string."""
    rec = {
        "messages": [
            {"user": "Is my non-compete enforceable?", "assistant": "Generally yes..."},
            {"user": "What about jurisdiction?", "assistant": "Depends on the state."},
        ],
        "confidence_score": 0.9,
    }
    r = convert_history_record_to_response(rec, "advisory", "model")
    assert "Is my non-compete enforceable?" in r["advisory_text"]
    assert "Generally yes..." in r["advisory_text"]
    assert "What about jurisdiction?" in r["advisory_text"]
    assert "Depends on the state." in r["advisory_text"]


def test_validate_advisory_rejects_non_string():
    """validate_advisory_response() rejects a non-string advisory_text."""
    # A list as advisory_text should be rejected
    invalid = {"success": True, "model": "m", "mode": "ADVISORY",
               "response_type": "advisory", "schema_version": 1,
               "advisory_text": ["not", "a", "string"],
               "confidence_score": 0.5, "confidence_label": "HIGH",
               "issue_count": 0, "issues": [],
               "structured_parse_failed": False}
    result = validate_advisory_response(invalid)
    assert result is False, (
        f"validate_advisory_response should reject non-string advisory_text, "
        f"got {result}"
    )

    # A valid string advisory_text should still pass
    valid = {"success": True, "model": "m", "mode": "ADVISORY",
             "response_type": "advisory", "schema_version": 1,
             "advisory_text": "This is a valid string response",
             "confidence_score": 0.5, "confidence_label": "HIGH",
             "issue_count": 0, "issues": [],
               "structured_parse_failed": False}
    result2 = validate_advisory_response(valid)
    assert result2 is True, f"validate_advisory_response should accept string advisory_text, got {result2}"