"""Regression tests: Redaction P1 - PERSON lead-in over-matching.

A capitalized conversational/contact lead-in word ("Contact", "Regarding",
"Dear", ...) preceding a person's name was absorbed into the PERSON match and
redacted along with the name (e.g. "Contact John Smith" -> "[REDACTED_PERSON]").
The engine must strip the lead-in so only the actual name is redacted while
multi-word names and legal boilerplate remain handled correctly.
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


def test_contact_leadin_only_name_redacted(redaction_engine):
    text = "Contact John Smith"
    entities = _entities(redaction_engine, text)

    assert len(entities) == 1
    entity = entities[0]
    assert entity.entity_type == "PERSON"
    assert entity.original_text == "John Smith"
    assert entity.start == 8
    assert entity.end == 18

    redacted = _redacted(redaction_engine, text)
    assert redacted == "Contact [REDACTED_PERSON]"
    assert "John Smith" not in redacted


def test_multi_word_names_still_detected(redaction_engine):
    text = "Mary Jane Watson signed."
    entities = _entities(redaction_engine, text)

    assert len(entities) == 1
    entity = entities[0]
    assert entity.entity_type == "PERSON"
    assert entity.original_text == "Mary Jane Watson"
    assert (entity.start, entity.end) == (0, 16)

    redacted = _redacted(redaction_engine, text)
    assert redacted == "[REDACTED_PERSON] signed."
    assert "Mary Jane Watson" not in redacted


def test_legal_boilerplate_remains_unredacted(redaction_engine):
    text = "This Agreement between Jane Smith and Acme Corp."
    entities = _entities(redaction_engine, text)

    assert "This Agreement" not in [e.original_text for e in entities]
    assert any(e.original_text == "Acme Corp" and e.entity_type == "COMPANY" for e in entities)

    redacted = _redacted(redaction_engine, text)
    assert redacted.startswith("This Agreement")


def test_repeated_entity_consistency_with_leadin_prefix(redaction_engine):
    text = "Contact John Smith. John Smith is a consultant."
    entities = _entities(redaction_engine, text)

    jane = [e for e in entities if e.original_text == "John Smith"]
    assert len(jane) == 2
    assert {e.entity_type for e in jane} == {"PERSON"}
    assert all(e.replacement == "[REDACTED_PERSON]" for e in jane)

    redacted = _redacted(redaction_engine, text)
    assert "John Smith" not in redacted
    assert redacted.startswith("Contact [REDACTED_PERSON]. [REDACTED_PERSON] is a consultant.")


@pytest.mark.parametrize(
    ("text", "expected_name", "expected_redacted"),
    [
        ("Contact John Smith", "John Smith", "Contact [REDACTED_PERSON]"),
        ("Regarding Jane Smith", "Jane Smith", "Regarding [REDACTED_PERSON]"),
        ("Dear John Smith,", "John Smith", "Dear [REDACTED_PERSON],"),
        ("Hello John Smith", "John Smith", "Hello [REDACTED_PERSON]"),
        ("Please contact John Smith", "John Smith", "Please contact [REDACTED_PERSON]"),
        ("Re: John Smith", "John Smith", "Re: [REDACTED_PERSON]"),
        ("From Jane Smith", "Jane Smith", "From [REDACTED_PERSON]"),
        ("Call John Smith", "John Smith", "Call [REDACTED_PERSON]"),
    ],
)
def test_person_leadin_variants_redact_only_name(
    redaction_engine, text, expected_name, expected_redacted
):
    entities = _entities(redaction_engine, text)
    names = [e.original_text for e in entities if e.entity_type == "PERSON"]
    assert names == [expected_name]

    redacted = _redacted(redaction_engine, text)
    assert redacted == expected_redacted
    assert expected_name not in redacted
