"""
Regression tests for Advisory disclaimer/grounding guardrail (P1 #1).

Verifies that every Advisory response clearly communicates it is informational
and not legal advice, that the prompt prohibits fabrication, and that the
disclaimer is consistently present across all response types.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.response_schemas import build_advisory_response, AdvisoryResponse
from backend.prompts.advisory_prompt import build_advisory_prompt, LEGAL_DISCLAIMER


def test_disclaimer_always_present_in_response():
    """build_advisory_response() always contains the standardized disclaimer field."""
    # Substantive answer
    r1 = build_advisory_response(
        "This non-compete clause is likely enforceable under the governing law.",
        "model-1",
    )
    assert "disclaimer" in r1, "disclaimer missing from substantive response"
    assert r1["disclaimer"] != "", "disclaimer should be non-empty"

    # Refusal/scope response
    r2 = build_advisory_response(
        "I cannot answer that question.",
        "model-1",
    )
    assert "disclaimer" in r2, "disclaimer missing from refusal response"
    assert r1["disclaimer"] == r2["disclaimer"], (
        "disclaimer should be identical across response types"
    )


def test_advisory_response_exposes_disclaimer():
    """AdvisoryResponse exposes the disclaimer field correctly."""
    r = AdvisoryResponse(disclaimer="test disclaimer value")
    assert r.disclaimer == "test disclaimer value", "disclaimer not stored correctly"

    r2 = AdvisoryResponse()
    assert r2.disclaimer == "", "default disclaimer should be empty string"

    # to_dict() includes disclaimer when set
    d = r.to_dict()
    assert "disclaimer" in d, "disclaimer omitted from to_dict()"
    assert d["disclaimer"] == "test disclaimer value"


def test_prompt_contains_safety_instructions():
    """build_advisory_prompt() contains the mandatory safety instructions."""
    prompt = build_advisory_prompt()

    # Informational-only disclaimer
    assert "This is informational only and does not constitute legal advice" in prompt

    # Jurisdiction caveat
    assert "Laws vary by jurisdiction" in prompt

    # Fabrication prohibition (check for the key phrase)
    assert "FABRICATION PROHIBITION" in prompt

    # Jurisdiction limitation
    assert "JURISDICTIONAL LIMITATION" in prompt


def test_prompt_contains_all_required_segments():
    """Verify all three required segments are present in the prompt."""
    prompt = build_advisory_prompt()

    # 1. Informational-only disclaimer
    assert "This is informational only and does not constitute legal advice" in prompt

    # 2. "I am not a lawyer" / not legal advice
    assert "I am not a lawyer" in prompt, "missing 'I am not a lawyer'"

    # 3. Jurisdiction varies
    assert "Laws vary by jurisdiction" in prompt, "missing 'Laws vary by jurisdiction'"

    # 4. Fabrication prohibition
    assert "Do not invent, cite, or reference statutes" in prompt, (
        "missing fabrication prohibition text"
    )

    # 5. Cannot verify/guarantee accuracy
    assert "cannot verify or guarantee its accuracy" in prompt, (
        "missing accuracy disclaimer"
    )

    # 6. Jurisdiction limitation
    assert (
        "explicitly state that the analysis is based on general legal principles"
        in prompt
    ), "missing jurisdiction limitation"