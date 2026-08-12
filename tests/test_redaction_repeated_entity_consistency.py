"""Regression tests: P0 #2 - repeated identical entities receive a consistent
redaction decision and type at the document level.

PERSON candidates are classified using local context windows (legal-clause
template, company-context), so identical strings at different positions could
receive different decisions (redacted vs unredacted) and different types
(PERSON vs COMPANY). The engine reconciles repeated entities after overlap
dedupe so every occurrence of the same name shares one decision and one type.
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


def test_repeated_identical_person_consistent_decision_and_type(redaction_engine):
    text = "This Agreement between Jane Smith and Acme Corp. Separately, Jane Smith is a consultant."
    entities = _entities(redaction_engine, text)

    jane = [e for e in entities if e.original_text == "Jane Smith"]
    assert len(jane) == 2
    assert {e.entity_type for e in jane} == {"PERSON"}
    assert all(e.replacement == "[REDACTED_PERSON]" for e in jane)

    acme = [e for e in entities if e.original_text == "Acme Corp"]
    assert len(acme) == 1
    assert acme[0].entity_type == "COMPANY"

    redacted = _redacted(redaction_engine, text)
    assert "Jane Smith" not in redacted
    assert redacted.startswith("This Agreement between [REDACTED_PERSON] and [REDACTED_COMPANY].")


@pytest.mark.parametrize(
    "text",
    [
        "This Agreement between Jane Smith and Acme Corp. Separately, Jane Smith is a consultant.",
        "Jane Smith signed. Jane Smith approved. Acme Corp reviewed.",
        "Jane Smith resigned. This Agreement was reviewed by Jane Smith. Jane Smith rejoined.",
    ],
)
def test_no_identical_occurrence_left_unredacted_when_any_redacted(redaction_engine, text):
    entities = _entities(redaction_engine, text)
    jane = [e for e in entities if e.original_text == "Jane Smith"]
    assert jane, "expected at least one redacted Jane Smith occurrence"
    assert len({e.entity_type for e in jane}) == 1
    assert "Jane Smith" not in _redacted(redaction_engine, text)


def test_unrelated_company_person_not_merged(redaction_engine):
    text = "Acme Corp filed yesterday. Jane Smith approved it. Bob Jones reviewed it."
    entities = _entities(redaction_engine, text)

    assert len(entities) == 3
    acme = next(e for e in entities if e.original_text == "Acme Corp")
    assert acme.entity_type == "COMPANY"
    jane = next(e for e in entities if e.original_text == "Jane Smith")
    bob = next(e for e in entities if e.original_text == "Bob Jones")
    assert jane.entity_type == "PERSON"
    assert bob.entity_type == "PERSON"
    assert len({e.start for e in entities}) == 3

    repeated = "Jane Smith signed today. Bob Jones approved yesterday. Jane Smith will review."
    entities = _entities(redaction_engine, repeated)
    jane_occurrences = [e for e in entities if e.original_text == "Jane Smith"]
    assert len(jane_occurrences) == 2
    assert len({e.start for e in jane_occurrences}) == 2
    assert {e.entity_type for e in jane_occurrences} == {"PERSON"}


def test_single_occurrence_heuristics_unchanged(redaction_engine):
    text = "Jane Smith joined Acme Corp as outside counsel."
    entities = _entities(redaction_engine, text)
    jane = [e for e in entities if e.original_text == "Jane Smith"]
    assert len(jane) == 1
    assert jane[0].entity_type == "COMPANY"
    assert "Jane Smith" not in _redacted(redaction_engine, text)
