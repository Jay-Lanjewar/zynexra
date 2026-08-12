"""Regression test: creator-attribution validation must not reject valid REDACTION output.

REDACTION output is deterministic (regex engine), not an LLM utterance. A document
that legitimately contains a person named "Jay Lanjewar" is redacted to
[REDACTED_*], so the response no longer contains "jay". The creator-attribution
rule in ValidationEngine.validate_response() (rule #1) must therefore be skipped
for session_mode == "REDACTION"; it remains active for AUDIT/ADVISORY/other modes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from backend.engines.redaction_engine import RedactionEngine, RedactionOptions
from backend.engines.validation_engine import ValidationContext, ValidationEngine


@pytest.fixture(scope="module")
def redaction_engine():
    return RedactionEngine()


def _redact(engine, text):
    return engine.redact(text, RedactionOptions()).redacted_text


def test_redaction_output_with_lanjewar_name_is_valid(redaction_engine):
    text = (
        "This Equity Incentive Plan is entered into by Acme Corp and Jay Lanjewar, "
        "employee #2211, at 555-014-2211 and jay.lanjewar@acme.com."
    )
    result = ValidationEngine().validate_response(
        _redact(redaction_engine, text),
        ValidationContext(user_input=text, session_mode="REDACTION", is_creator_question=False),
    )
    assert result.is_valid is True, f"REDACTION output refused: {result.violation_reason}"


def test_redaction_output_still_rejects_first_person_ai_disclosure(redaction_engine):
    text = "Please redact this: I am an AI language model and I wrote this paragraph."
    result = ValidationEngine().validate_response(
        _redact(redaction_engine, text),
        ValidationContext(user_input=text, session_mode="REDACTION", is_creator_question=False),
    )
    assert result.is_valid is False
    assert result.violation_type == "identity_disclosure"


@pytest.mark.parametrize("mode", ["AUDIT", "ADVISORY"])
def test_creator_attribution_guard_still_active_for_other_modes(mode):
    result = ValidationEngine().validate_response(
        "The document is governed by Delaware law.",
        ValidationContext(
            user_input="Explain the agreement made by Lanjewar.",
            session_mode=mode,
            is_creator_question=False,
        ),
    )
    assert result.is_valid is False
    assert result.violation_type == "identity_guard"
