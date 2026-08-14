"""Regression tests: Redaction P1 - ID_NUMBER false-positive precision.

The catch-all ID_NUMBER alternative [A-Z]{1,4}[- ]?\d{5,12} accepted arbitrary
letter+digit tokens (order/invoice/ref/po/sku codes). Two PHONE-style post-match
guards reject:
  * multi-letter prefixes without an ID label within +/-24 chars
  * catch-all digit runs longer than 9 digits

Strict shapes (PAN, 15-char international ID, SSN), labeled forms, and
unlabeled one-letter passport/license forms are preserved.
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


def _id_entities(engine, text):
    return [e for e in _entities(engine, text) if e.entity_type == "ID_NUMBER"]


@pytest.mark.parametrize(
    "text",
    [
        "AB123456",
        "AB1234567",
        "ABC1234567",
        "XYZ12345678",
        "ORD12345678",
        "PO123456",
        "PO-123456",
        "REF-123456",
        "INV1234567890",
        "TRK123456789",
        "SKU123456",
        "A123456789012",
    ],
)
def test_multi_letter_generic_codes_false_positive(redaction_engine, text):
    assert _id_entities(redaction_engine, text) == []
    assert _redacted(redaction_engine, text) == text


def test_order_context_code_false_positive(redaction_engine):
    text = "Order ABC123456"
    assert _id_entities(redaction_engine, text) == []
    assert _redacted(redaction_engine, text) == text


def test_invoice_context_code_false_positive(redaction_engine):
    text = "The invoice INV1234567890 was paid."
    assert _id_entities(redaction_engine, text) == []
    assert "INV1234567890" in _redacted(redaction_engine, text)


@pytest.mark.parametrize(
    "text",
    [
        "ABCDE1234F",
        "ABCDE1234X",
    ],
)
def test_pan_format_detected(redaction_engine, text):
    entities = _id_entities(redaction_engine, text)
    assert len(entities) == 1
    assert entities[0].original_text == text


def test_15_char_international_id_detected(redaction_engine):
    text = "AB12CDEFGHIJKLM"
    entities = _id_entities(redaction_engine, text)
    assert len(entities) == 1
    assert entities[0].original_text == text


@pytest.mark.parametrize("text", ["P1234567", "G123456789", "D1234567", "A123456"])
def test_one_letter_passport_license_detected(redaction_engine, text):
    entities = _id_entities(redaction_engine, text)
    assert len(entities) == 1
    entity = entities[0]
    assert entity.entity_type == "ID_NUMBER"
    assert entity.original_text == text


@pytest.mark.parametrize(
    "text",
    [
        "SSN 123-45-6789",
        "TIN 123-45-6789",
        "ID No. 123456",
        "License No. D1234567",
        "Passport Number G123456789",
        "Employee ID E12345",
        "GSTIN 27AAPFU0939F1Z5",
    ],
)
def test_labeled_id_forms_detected(redaction_engine, text):
    assert _id_entities(redaction_engine, text)


@pytest.mark.parametrize("text", ["123-45-6789", "987-65-4321"])
def test_ssn_shaped_value_is_id_number(redaction_engine, text):
    entities = _id_entities(redaction_engine, text)
    assert len(entities) == 1
    assert entities[0].original_text == text
    assert "PHONE" not in [e.entity_type for e in _entities(redaction_engine, text)]


@pytest.mark.parametrize("text", ["P 1234567", "G-123456789"])
def test_one_letter_id_with_separator_preserved_by_guard(redaction_engine, text):
    end = len(text)
    assert redaction_engine._reject_id_number_match(text, text, 0, end) is False
    redacted = _redacted(redaction_engine, text)
    assert "".join(ch for ch in text if ch.isdigit()) not in redacted


def test_multi_letter_id_with_label_nearby_detected(redaction_engine):
    text = "Employee ID EM123456"
    assert _id_entities(redaction_engine, text)


def test_overlap_ab_id_rejected_phone_remains(redaction_engine):
    text = "AB 12345678"
    assert _id_entities(redaction_engine, text) == []
    phones = [e for e in _entities(redaction_engine, text) if e.entity_type == "PHONE"]
    assert len(phones) == 1
    assert phones[0].original_text == "12345678"


def test_overlap_call_phone_not_id(redaction_engine):
    text = "Call 555-123-4567"
    assert _id_entities(redaction_engine, text) == []
    phones = [e for e in _entities(redaction_engine, text) if e.entity_type == "PHONE"]
    assert len(phones) == 1
    assert phones[0].original_text == "555-123-4567"