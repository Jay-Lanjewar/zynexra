"""Tests for semantic contradiction fix:
- survival clause absent -> suppression remains
- survival clause present but duration unspecified -> no suppression
- survival clause present with explicit duration -> no suppression
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.contradiction_engine import (
    _check_semantic_contradiction,
    _references_duration_insufficiency,
    validate_contradictions,
)
from backend.engines.normalization_engine import AuditIssue


def _make_issue(
    title: str = "Confidentiality Survival",
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


SURVIVAL_QUOTE = (
    '"The obligations relating to confidentiality shall survive termination '
    'or expiration of this Agreement."'
)


# --- (a) survival clause absent -> suppression remains ---


def test_suppress_no_survival_clause():
    assert _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "no survival clause",
    )


def test_suppress_survival_provision_missing():
    assert _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "survival provision missing",
    )


def test_suppress_survival_language_absent():
    assert _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "survival language absent",
    )


def test_suppress_does_not_specify_survival():
    assert _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause does not specify any survival provision.",
    )


def test_suppress_missing_clause():
    assert _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The survival clause is missing from this section.",
    )


# --- (b) survival clause present but duration unspecified -> no suppression ---


def test_keep_does_not_specify_duration():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause does not specify any duration for the survival of confidentiality obligations.",
    )


def test_keep_does_not_specify_a_duration():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause does not specify a duration for confidentiality survival.",
    )


def test_keep_does_not_specify_survival_period():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause does not specify a survival period for confidentiality obligations.",
    )


def test_keep_does_not_specify_length():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause does not specify the length of the survival period.",
    )


def test_keep_does_not_specify_expiration_date():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause does not specify an expiration date for the survival obligation.",
    )


def test_keep_does_not_specify_end_date():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause does not specify any end date for the survival of confidentiality.",
    )


def test_keep_does_not_specify_timeframe():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause does not specify any time frame for the survival of confidentiality.",
    )


def test_keep_duration_unspecified():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The survival duration is unspecified, creating a perpetual obligation concern.",
    )


def test_keep_no_specified_duration():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "No specified duration for the survival of confidentiality obligations.",
    )


def test_keep_survival_period_missing():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The survival period is missing from the confidentiality clause.",
    )


def test_keep_lacks_survival_period():
    assert not _check_semantic_contradiction(
        SURVIVAL_QUOTE,
        "The clause lacks a survival period for confidentiality obligations.",
    )


# --- (c) survival clause present with explicit duration -> no suppression ---


def test_keep_finite_duration_five_years():
    assert not _check_semantic_contradiction(
        '"Confidential obligations shall survive for a period of five (5) years."',
        "The survival period of five years is within standard range.",
    )


def test_keep_finite_duration_three_years():
    assert not _check_semantic_contradiction(
        '"Confidentiality shall survive for three (3) years after termination."',
        "A three-year survival period is reasonable and enforceable.",
    )


# --- duration-insufficiency unit tests ---


def test_duration_insufficiency_any_duration():
    assert _references_duration_insufficiency(
        "does not specify any duration"
    )


def test_duration_insufficiency_the_duration():
    assert _references_duration_insufficiency(
        "does not specify the duration"
    )


def test_duration_insufficiency_a_duration():
    assert _references_duration_insufficiency(
        "does not specify a duration"
    )


def test_duration_insufficiency_survival_period():
    assert _references_duration_insufficiency(
        "does not specify a survival period"
    )


def test_duration_insufficiency_length():
    assert _references_duration_insufficiency(
        "does not specify the length"
    )


def test_duration_insufficiency_expiration_date():
    assert _references_duration_insufficiency(
        "does not specify an expiration date"
    )


def test_duration_insufficiency_end_date():
    assert _references_duration_insufficiency(
        "does not specify an end date"
    )


def test_duration_insufficiency_time_period():
    assert _references_duration_insufficiency(
        "fails to specify a time period"
    )


def test_duration_insufficiency_time_limit():
    assert _references_duration_insufficiency(
        "lacks a time limit"
    )


def test_duration_insufficiency_does_not_match_clause_absent():
    assert not _references_duration_insufficiency(
        "does not specify any survival provision"
    )


def test_duration_insufficiency_does_not_match_no_survival():
    assert not _references_duration_insufficiency(
        "no survival clause"
    )


# --- integration with validate_contradictions ---


def test_validate_contradictions_keeps_unspecified_duration():
    """Semantic contradiction must NOT suppress duration-unspecified findings."""
    issue = _make_issue(
        quoted_text=SURVIVAL_QUOTE,
        risk_explanation="The clause does not specify any duration for the survival of confidentiality obligations.",
    )
    results = validate_contradictions([issue])
    semantic_results = [r for r in results if r.contradiction_type == "semantic_mismatch"]
    assert len(semantic_results) == 0, (
        f"Expected 0 semantic_mismatch results for duration-unspecified finding, "
        f"got {len(semantic_results)}: {[r.reason for r in semantic_results]}"
    )


def test_validate_contradictions_still_suppresses_clause_absent():
    """Semantic contradiction must STILL suppress clause-absent findings."""
    issue = _make_issue(
        quoted_text=SURVIVAL_QUOTE,
        risk_explanation="no survival clause in this agreement section.",
    )
    results = validate_contradictions([issue])
    semantic_results = [r for r in results if r.contradiction_type == "semantic_mismatch"]
    assert len(semantic_results) == 1
    assert semantic_results[0].contradiction_type == "semantic_mismatch"
