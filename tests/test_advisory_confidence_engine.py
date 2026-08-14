"""
Regression tests for AdvisoryConfidenceScorer refusal detection.

Covers the content-based refusal rule:
  - short and long genuine refusals are flagged (LOW confidence)
  - substantive caveated answers avoid the refusal penalty
  - legal disclaimers and ordinary hedging are not penalized
  - redirect tails ("...but please consult an attorney") stay refusals
  - genuine refusals are capped to LOW confidence

Usage:
    python -m pytest tests/test_advisory_confidence_engine.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.confidence_engine import advisory_scorer


def test_short_refusal_flagged():
    r = advisory_scorer._compute_refusal_score("I cannot answer that question.")
    assert r == 0.0


def test_long_refusal_flagged():
    text = ("I cannot provide a definitive legal opinion on this matter. The question "
            "involves complex issues of contract interpretation that depend on the specific "
            "facts, the governing law of the jurisdiction, and the exact wording of the "
            "agreement. I am unable to advise you on the enforceability of this provision and "
            "would strongly recommend that you retain an attorney to review the full contract.")
    assert advisory_scorer._compute_refusal_score(text) == 0.0


def test_caveat_substantive_answer_not_refusal():
    text = ("I cannot give a definitive answer, but this non-compete clause is likely "
            "enforceable under the governing law given its reasonable scope and duration.")
    assert advisory_scorer._compute_refusal_score(text) == 1.0


def test_disclaimer_with_substantive_answer_not_refusal():
    text = ("I am not a lawyer and this is not legal advice. In general, this clause appears "
            "enforceable because the consideration is adequate and the scope is reasonable.")
    assert advisory_scorer._compute_refusal_score(text) == 1.0


def test_ordinary_hedging_not_refusal_or_penalized():
    text = ("The clause probably may or might be enforceable, but it could potentially be "
            "challenged. I believe a court would likely uphold it under the governing law.")
    assert advisory_scorer._compute_refusal_score(text) == 1.0
    assert advisory_scorer._compute_hallucination_score(text) == 1.0


def test_answer_first_caveat_last_not_refusal():
    text = ("This non-compete clause is likely enforceable under the governing law. However, "
            "I cannot give a definitive answer without the full agreement.")
    assert advisory_scorer._compute_refusal_score(text) == 1.0


def test_redirect_tail_still_refusal():
    text = "I cannot answer, but please consult a lawyer about your non-compete agreement."
    assert advisory_scorer._compute_refusal_score(text) == 0.0


def test_genuine_refusal_score_capped_low():
    result = advisory_scorer.compute("I cannot answer that question.")
    assert result.factors["refusal_absent"] == 0.0
    assert result.score <= advisory_scorer.REFUSAL_MAX_SCORE
    assert result.label == "LOW"


def test_caveat_answer_scores_higher_than_refusal():
    refusal = advisory_scorer.compute("I cannot answer that question.")
    answer = advisory_scorer.compute(
        "I cannot give a definitive answer, but this non-compete clause is likely enforceable "
        "under the governing law given its reasonable scope and duration."
    )
    assert answer.score > refusal.score
    assert answer.label == "HIGH"
