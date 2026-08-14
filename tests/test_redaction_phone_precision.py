"""Regression tests: Redaction P1 - PHONE false-positive precision.

The PHONE regex is intentionally broad and accepted year ranges, generic
"NNNN-NNNN" reference numbers, and overlong bare digit runs. Two PHONE-only
post-match guards reject:
  * exact \d{4}-\d{4} matches (year ranges / 4-4 references)
  * pure-digit candidates longer than 11 digits after stripping +, (, )

Legitimate phone formats must still be detected and redacted.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from backend.engines.redaction_engine import RedactionEngine, RedactionOptions


@pytest.fixture(scope="module")
def redaction_engine():
    return RedactionEngine()


def _entities(engine, text):
    return engine.redact(text, RedactionOptions()).entities


def _redacted(engine, text):
    return engine.redact(text, RedactionOptions()).redacted_text


def test_year_range_false_positive(redaction_engine):
    text = "2024-2025"
    assert _entities(redaction_engine, text) == []
    assert _redacted(redaction_engine, text) == text


def test_four_digit_dash_four_digit_false_positive(redaction_engine):
    text = "1234-5678"
    assert _entities(redaction_engine, text) == []
    assert _redacted(redaction_engine, text) == text


@pytest.mark.parametrize("text", ["5550001234567", "123456789012", "555000123456"])
def test_overlong_bare_number_false_positive(redaction_engine, text):
    assert _entities(redaction_engine, text) == []
    assert _redacted(redaction_engine, text) == text


def test_ssn_shaped_value_remains_id_number(redaction_engine):
    text = "123-45-6789"
    entities = _entities(redaction_engine, text)

    assert len(entities) == 1
    entity = entities[0]
    assert entity.entity_type == "ID_NUMBER"
    assert entity.original_text == "123-45-6789"
    assert (entity.start, entity.end) == (0, 11)

    redacted = _redacted(redaction_engine, text)
    assert redacted == "[REDACTED_ID_NUMBER]"


@pytest.mark.parametrize(
    "text",
    [
        "+1 (555) 123-4567",
        "(555) 123-4567",
        "555-123-4567",
        "555 123 4567",
        "555.123.4567",
        "080-1234-5678",
        "44 20 7946 0958",
        "1-800-123-4567",
        "5551234567",
        "18005551234",
    ],
)
def test_legit_phone_formats_detected(redaction_engine, text):
    entities = _entities(redaction_engine, text)

    assert len(entities) == 1
    entity = entities[0]
    assert entity.entity_type == "PHONE"
    assert entity.original_text == text
    assert (entity.start, entity.end) == (0, len(text))

    redacted = _redacted(redaction_engine, text)
    assert redacted == "[REDACTED_PHONE]"