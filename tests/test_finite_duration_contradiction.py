"""Tests for finite-duration contradiction rule."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.contradiction_engine import (
    _check_finite_duration_contradiction,
    _has_finite_duration,
    _has_perpetual_or_indefinite,
    validate_contradictions,
)
from backend.engines.normalization_engine import AuditIssue


def _make_survival_issue(
    title: str = "Perpetual Confidentiality Survival",
    quoted_text: str = "",
    risk_explanation: str = "",
    category: str = "Enforceability Weakness",
    severity: str = "MEDIUM",
) -> AuditIssue:
    return AuditIssue(
        issue_title=title,
        severity=severity,
        category=category,
        quoted_text=quoted_text,
        risk_explanation=risk_explanation,
        suggested_improvement="test",
    )


# --- Pattern-level tests ---


def test_has_finite_duration_five_years():
    assert _has_finite_duration("survive termination for a period of five (5) years")


def test_has_finite_duration_three_years():
    assert _has_finite_duration("Confidentiality obligations shall survive for three (3) years")


def test_has_finite_duration_numeric():
    assert _has_finite_duration("survival period of 2 years")


def test_has_no_finite_duration():
    assert not _has_finite_duration("Confidential Information shall survive perpetually")


def test_has_no_finite_duration_empty():
    assert not _has_finite_duration("")


def test_has_perpetual_in_title():
    assert _has_perpetual_or_indefinite("Perpetual Confidentiality Survival")


def test_has_indefinite_in_risk():
    assert _has_perpetual_or_indefinite("The survival duration is indefinite")


def test_has_no_perpetual():
    assert not _has_perpetual_or_indefinite("Confidentiality Survival")


def test_has_no_perpetual_empty():
    assert not _has_perpetual_or_indefinite("")


# --- Case 1: finite duration + perpetual risk -> suppress ---


def test_suppress_finite_duration_with_perpetual_risk():
    """NDA-02 pattern: quoted says 'five (5) years', risk claims 'indefinite'."""
    assert _check_finite_duration_contradiction(
        issue_title="Confidentiality Survival",
        quoted_text="The confidentiality obligations shall survive termination of this Agreement for a period of five (5) years.",
        risk_explanation="Confidentiality obligations that survive indefinitely may be unenforceable in many jurisdictions.",
    )


def test_suppress_finite_duration_with_perpetual_title():
    """NDA-03 pattern: quoted says 'three (3) years', title says 'Perpetual'."""
    assert _check_finite_duration_contradiction(
        issue_title="Perpetual Confidentiality Survival",
        quoted_text="Confidentiality obligations shall survive for three (3) years after termination.",
        risk_explanation="The clause creates an indefinite obligation.",
    )


# --- Case 2: finite duration + finite risk -> keep ---


def test_keep_finite_duration_with_finite_risk():
    """Both finite: no contradiction."""
    assert not _check_finite_duration_contradiction(
        issue_title="Confidentiality Survival",
        quoted_text="The confidentiality obligations shall survive termination of this Agreement for a period of five (5) years.",
        risk_explanation="The survival period of five years is within standard range.",
    )


# --- Case 3: perpetual quoted text -> keep ---


def test_keep_perpetual_quoted_text():
    """NDA-04 pattern: quoted says 'perpetually' — no finite duration to contradict."""
    assert not _check_finite_duration_contradiction(
        issue_title="Perpetual Confidentiality Survival",
        quoted_text="Confidential Information shall survive termination or expiration of this Agreement perpetually and shall continue in full force and effect indefinitely.",
        risk_explanation="The perpetual survival of confidentiality obligations creates an indefinite obligation.",
    )


# --- Case 4: NDA-04 regression test ---


def test_nda04_no_suppression():
    """NDA-04 true perpetual survival must NOT be suppressed."""
    issue = _make_survival_issue(
        title="Perpetual Confidentiality Survival",
        quoted_text=(
            '"Confidential Information shall survive termination or expiration of this '
            'Agreement perpetually and shall continue in full force and effect indefinitely."'
        ),
        risk_explanation=(
            "The perpetual survival of confidentiality obligations creates an indefinite "
            "obligation that may be unenforceable in many jurisdictions."
        ),
    )
    results = validate_contradictions([issue])
    assert len(results) == 0, "NDA-04 must not be suppressed"


# --- Integration with validate_contradictions ---


def test_validate_contradictions_suppresses_finite_duration():
    """validate_contradictions should return a ContradictionResult for finite-duration pattern."""
    issue = _make_survival_issue(
        title="Confidentiality Survival",
        quoted_text="The confidentiality obligations shall survive termination of this Agreement for a period of five (5) years.",
        risk_explanation="Confidentiality obligations that survive indefinitely may be unenforceable.",
    )
    results = validate_contradictions([issue])
    assert len(results) == 1
    assert results[0].contradiction_type == "finite_duration_contradiction"
    assert results[0].has_contradiction is True


def test_validate_contradictions_keeps_finite_finite():
    """validate_contradictions should not flag finite duration + finite risk."""
    issue = _make_survival_issue(
        title="Confidentiality Survival",
        quoted_text="The confidentiality obligations shall survive termination of this Agreement for a period of five (5) years.",
        risk_explanation="The survival period of five years is within standard range.",
    )
    results = validate_contradictions([issue])
    assert len(results) == 0


def test_validate_contradictions_keeps_perpetual_quoted():
    """validate_contradictions should not flag perpetual quoted text."""
    issue = _make_survival_issue(
        title="Perpetual Confidentiality Survival",
        quoted_text="Confidential Information shall survive perpetually and shall continue indefinitely.",
        risk_explanation="The perpetual survival creates an indefinite obligation.",
    )
    results = validate_contradictions([issue])
    assert len(results) == 0
