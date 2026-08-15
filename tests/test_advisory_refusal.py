"""
Regression tests for Advisory refusal detection.

Verifies that the content-based refusal detection correctly identifies
mandated scope-refusals while preserving substantive answers and
refusing genuine refusals. Tests that the REFUSAL_MAX_SCORE cap
ensures genuine refusals are always shown as LOW confidence.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.confidence_engine import advisory_scorer


def test_mandated_refusal_1_low():
    """Mandated scope refusal #1: 'Zynexra does not generate full legal agreements...'"""
    refusal = "Zynexra does not generate full legal agreements. I can explain contract structures or provide example clauses for study purposes."
    r = advisory_scorer._compute_refusal_score(refusal)
    assert r == 0.0, f"Expected refusal_absent=0.0, got {r}"


def test_mandated_refusal_2_low():
    """Mandated scope refusal #2: 'This request is outside Zynexra's advisory scope...'"""
    refusal = "This request is outside Zynexra's advisory scope. I assist only with legal practice and contract-related questions."
    r = advisory_scorer._compute_refusal_score(refusal)
    assert r == 0.0, f"Expected refusal_absent=0.0, got {r}"


def test_substantive_answer_not_refusal():
    """A substantive answer containing a scope disclaimer should NOT be treated as a refusal."""
    refusal = "I cannot give a definitive answer, but this non-compete clause is likely enforceable under the governing law given its reasonable scope and duration."
    r = advisory_scorer._compute_refusal_score(refusal)
    assert r == 1.0, f"Expected refusal_absent=1.0, got {r}"


def test_genuine_refusal_score_capped_low():
    """A genuine refusal should always be capped to LOW confidence."""
    result = advisory_scorer.compute("I cannot answer that question.")
    assert result.factors["refusal_absent"] == 0.0
    assert result.score <= advisory_scorer.REFUSAL_MAX_SCORE
    assert result.label == "LOW"


def test_substantive_answer_scores_higher_than_refusal():
    """A substantive answer should score higher than a genuine refusal."""
    refusal = advisory_scorer.compute("I cannot answer that question.")
    answer = advisory_scorer.compute(
        "I cannot give a definitive answer, but this non-compete clause is likely enforceable "
        "under the governing law given its reasonable scope and duration."
    )
    assert answer.score > refusal.score
    assert answer.label == "HIGH"