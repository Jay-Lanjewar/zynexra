"""
Unit tests for AuditConfidenceScorer accuracy-proximate signals:
  - qt_match_rate: verify quotes against document
  - category_validity: check category in VALID_SET
  - explanation_quality: analysis depth proxy
  - improvement_quality: understanding proxy
  - severity_consistency: calibration proxy
  - location_diversity: thoroughness proxy
  - count_signal: issue count calibration
  - domain_signal: context quality
  - parse_success: baseline

Usage:
    python -m pytest tests/test_confidence_engine.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.confidence_engine import AuditConfidenceScorer, _label_from_score
from backend.engines.normalization_engine import AuditIssue


@pytest.fixture
def scorer():
    return AuditConfidenceScorer()


@pytest.fixture
def sample_doc_text():
    return (
        "CONFIDENTIALITY AGREEMENT\n\n"
        "This Confidentiality Agreement is made as of January 1, 2024 "
        "by and between Company and Recipient.\n\n"
        "1. CONFIDENTIAL INFORMATION. Confidential Information means "
        "all information disclosed by Company to Recipient.\n\n"
        "2. OBLIGATIONS. Recipient shall hold Confidential Information "
        "in confidence using a reasonable degree of care.\n\n"
        "3. EXCLUSIONS. The obligations in Section 2 shall not apply "
        "to information that is or becomes generally available to the public."
    )


# =========================================================================
# qt_match_rate Tests
# =========================================================================

def test_qt_match_rate_all_match(scorer, sample_doc_text):
    issues = [
        AuditIssue(
            issue_title="Confidentiality Obligations",
            severity="LOW",
            category="Confidentiality",
            location="2.",
            quoted_text="Recipient shall hold Confidential Information in confidence using a reasonable degree of care",
            risk_explanation="Standard confidentiality obligation.",
        )
    ]
    score = scorer._compute_qt_match_rate(issues, sample_doc_text)
    assert score == 1.0, f"Expected 1.0 for matching quoted_text, got {score}"


def test_qt_match_rate_no_match(scorer, sample_doc_text):
    issues = [
        AuditIssue(
            issue_title="Hallucinated Clause",
            severity="HIGH",
            category="Liability",
            location="99.",
            quoted_text="This clause does not appear anywhere in the document at all",
            risk_explanation="Made up clause.",
        )
    ]
    score = scorer._compute_qt_match_rate(issues, sample_doc_text)
    assert score == 0.0, f"Expected 0.0 for absent quoted_text, got {score}"


def test_qt_match_rate_short_quote_passes(scorer, sample_doc_text):
    issues = [
        AuditIssue(
            issue_title="Short Quote",
            severity="MEDIUM",
            category="Confidentiality",
            location="1.",
            quoted_text="Confidential Information",
            risk_explanation="Short quote.",
        )
    ]
    score = scorer._compute_qt_match_rate(issues, sample_doc_text)
    assert score == 1.0, f"Expected 1.0 for short quote (<20 chars), got {score}"


def test_qt_match_rate_empty_issues(scorer):
    score = scorer._compute_qt_match_rate([], "")
    assert score == 0.5, f"Expected 0.5 for empty issues, got {score}"


def test_qt_match_rate_no_doc_text(scorer):
    issues = [AuditIssue(quoted_text="Some quoted text")]
    score = scorer._compute_qt_match_rate(issues, "")
    assert score == 0.5, f"Expected 0.5 for empty doc_text, got {score}"


def test_qt_match_rate_mixed(scorer, sample_doc_text):
    issues = [
        AuditIssue(
            quoted_text="Recipient shall hold Confidential Information in confidence",
        ),
        AuditIssue(
            quoted_text="This clause is completely made up and does not exist",
        ),
    ]
    score = scorer._compute_qt_match_rate(issues, sample_doc_text)
    assert score == 0.5, f"Expected 0.5 (1 match + 1 miss = 0.5 avg), got {score}"


def test_qt_match_rate_truncated_match(scorer, sample_doc_text):
    issues = [
        AuditIssue(
            quoted_text="This Confidentiality Agreement is made as of January 1, 2024 by and between Company and Recipient. Additional text that extends beyond the first 40 chars",
        ),
    ]
    score = scorer._compute_qt_match_rate(issues, sample_doc_text)
    assert score == 0.5, f"Expected 0.5 (truncated match), got {score}"


# =========================================================================
# category_validity Tests
# =========================================================================

def test_category_validity_all_valid(scorer):
    issues = [
        AuditIssue(category="Confidentiality"),
        AuditIssue(category="Indemnification"),
        AuditIssue(category="Termination"),
    ]
    score = scorer._compute_category_validity(issues)
    assert score == 1.0, f"Expected 1.0 for all valid categories, got {score}"


def test_category_validity_all_invalid(scorer):
    issues = [
        AuditIssue(category="RandomCategory"),
        AuditIssue(category="MadeUpCategory"),
    ]
    score = scorer._compute_category_validity(issues)
    assert score == 0.0, f"Expected 0.0 for all invalid categories, got {score}"


def test_category_validity_mixed(scorer):
    issues = [
        AuditIssue(category="Confidentiality"),
        AuditIssue(category="InvalidCategory"),
    ]
    score = scorer._compute_category_validity(issues)
    assert score == 0.5, f"Expected 0.5 for mixed valid/invalid, got {score}"


def test_category_validity_empty(scorer):
    score = scorer._compute_category_validity([])
    assert score == 0.5, f"Expected 0.5 for empty issues, got {score}"


# =========================================================================
# explanation_quality Tests
# =========================================================================

def test_explanation_quality_detailed(scorer):
    issues = [
        AuditIssue(risk_explanation="This is a very detailed explanation that covers multiple aspects of the risk and provides comprehensive analysis of the issue. It examines the implications and consequences thoroughly and systematically across all dimensions.")
    ]
    score = scorer._compute_explanation_quality(issues)
    assert score == 1.0, f"Expected 1.0 for detailed explanation, got {score}"


def test_explanation_quality_brief(scorer):
    issues = [
        AuditIssue(risk_explanation="This is a brief note about the issue.")
    ]
    score = scorer._compute_explanation_quality(issues)
    assert score == 0.4, f"Expected 0.4 for brief explanation, got {score}"


def test_explanation_quality_empty(scorer):
    issues = [
        AuditIssue(risk_explanation="")
    ]
    score = scorer._compute_explanation_quality(issues)
    assert score == 0.2, f"Expected 0.2 for empty explanation, got {score}"


def test_explanation_quality_no_issues(scorer):
    score = scorer._compute_explanation_quality([])
    assert score == 0.3, f"Expected 0.3 for no issues, got {score}"


# =========================================================================
# improvement_quality Tests
# =========================================================================

def test_improvement_quality_specific(scorer):
    issues = [
        AuditIssue(suggested_improvement="Add a mutual non-disclosure clause with specific carve-outs for publicly available information and independently developed materials to protect both parties effectively and comprehensively in all circumstances.")
    ]
    score = scorer._compute_improvement_quality(issues)
    assert score == 1.0, f"Expected 1.0 for specific improvement, got {score}"


def test_improvement_quality_generic(scorer):
    issues = [
        AuditIssue(suggested_improvement="Review this clause.")
    ]
    score = scorer._compute_improvement_quality(issues)
    assert score == 0.4, f"Expected 0.4 for generic improvement, got {score}"


def test_improvement_quality_empty(scorer):
    issues = [
        AuditIssue(suggested_improvement="")
    ]
    score = scorer._compute_improvement_quality(issues)
    assert score == 0.2, f"Expected 0.2 for empty improvement, got {score}"


# =========================================================================
# severity_consistency Tests
# =========================================================================

def test_severity_consistency_mixed(scorer):
    issues = [
        AuditIssue(severity="LOW"),
        AuditIssue(severity="MEDIUM"),
        AuditIssue(severity="HIGH"),
    ]
    score = scorer._compute_severity_consistency(issues)
    assert score == 1.0, f"Expected 1.0 for mixed severities, got {score}"


def test_severity_consistency_all_medium(scorer):
    issues = [
        AuditIssue(severity="MEDIUM"),
        AuditIssue(severity="MEDIUM"),
    ]
    score = scorer._compute_severity_consistency(issues)
    assert score == 0.8, f"Expected 0.8 for all MEDIUM, got {score}"


def test_severity_consistency_all_low(scorer):
    issues = [
        AuditIssue(severity="LOW"),
        AuditIssue(severity="LOW"),
    ]
    score = scorer._compute_severity_consistency(issues)
    assert score == 0.5, f"Expected 0.5 for all LOW, got {score}"


def test_severity_consistency_empty(scorer):
    score = scorer._compute_severity_consistency([])
    assert score == 0.5, f"Expected 0.5 for empty issues, got {score}"


# =========================================================================
# location_diversity Tests
# =========================================================================

def test_location_diversity_high(scorer):
    issues = [
        AuditIssue(location="Section 1"),
        AuditIssue(location="Section 2"),
        AuditIssue(location="Section 3"),
    ]
    score = scorer._compute_location_diversity(issues)
    assert score == 1.0, f"Expected 1.0 for 3+ unique locations, got {score}"


def test_location_diversity_medium(scorer):
    issues = [
        AuditIssue(location="Section 1"),
        AuditIssue(location="Section 2"),
    ]
    score = scorer._compute_location_diversity(issues)
    assert score == 0.7, f"Expected 0.7 for 2 unique locations, got {score}"


def test_location_diversity_low(scorer):
    issues = [
        AuditIssue(location="Section 1"),
        AuditIssue(location="Section 1"),
    ]
    score = scorer._compute_location_diversity(issues)
    assert score == 0.4, f"Expected 0.4 for 1 unique location, got {score}"


# =========================================================================
# count_signal Tests
# =========================================================================

def test_count_signal_short_doc(scorer):
    doc = "word " * 100
    score = scorer._compute_count_signal(1, doc)
    assert score == 1.0, f"Expected 1.0 for 1 issue in short doc, got {score}"


def test_count_signal_medium_doc(scorer):
    doc = "word " * 300
    score = scorer._compute_count_signal(2, doc)
    assert score == 1.0, f"Expected 1.0 for 2 issues in medium doc, got {score}"


def test_count_signal_overfinding(scorer):
    doc = "word " * 300
    score = scorer._compute_count_signal(10, doc)
    assert score == 0.4, f"Expected 0.4 for over-finding, got {score}"


# =========================================================================
# Post-Hoc Penalty Tests
# =========================================================================

def test_penalty_policy_detected(scorer):
    result = scorer.compute(
        response_text="Some audit response with issues",
        issue_count=3,
        structured_parse_failed=False,
        policy_detected=True,
    )
    assert result.score < 0.50, f"Expected score < 0.50 for policy-detected, got {result.score}"
    assert "policy_detected" in result.penalties


def test_penalty_non_legal_detected(scorer):
    result = scorer.compute(
        response_text="Some audit response with issues",
        issue_count=3,
        structured_parse_failed=False,
        non_legal_detected=True,
    )
    assert result.score < 0.30, f"Expected score < 0.30 for non-legal, got {result.score}"
    assert "non_legal_detected" in result.penalties


def test_penalty_duplicate_suppression(scorer):
    result = scorer.compute(
        response_text="Some audit response with issues",
        issue_count=3,
        structured_parse_failed=False,
        duplicate_suppressed=2,
    )
    assert result.score <= 0.80, f"Expected score <= 0.80 for duplicates > 0, got {result.score}"
    assert "duplicate_suppression_penalty" in result.penalties


def test_penalty_no_penalty_when_not_applicable(scorer):
    result = scorer.compute(
        response_text="Some audit response with issues",
        issue_count=3,
        structured_parse_failed=False,
        policy_detected=False,
        non_legal_detected=False,
        duplicate_suppressed=0,
    )
    assert len(result.penalties) == 0, f"Expected no penalties, got {result.penalties}"


def test_penalty_combined_multiple(scorer):
    result = scorer.compute(
        response_text="Some audit response with issues",
        issue_count=3,
        structured_parse_failed=False,
        policy_detected=True,
        non_legal_detected=True,
        duplicate_suppressed=1,
    )
    assert result.score < 0.10, f"Expected score < 0.10 for all penalties, got {result.score}"
    assert len(result.penalties) == 3


# =========================================================================
# Integration: Full compute() with issues
# =========================================================================

def test_full_compute_with_good_issues(scorer, sample_doc_text):
    issues = [
        AuditIssue(
            issue_title="Confidentiality Obligations",
            severity="MEDIUM",
            category="Confidentiality",
            location="Section 2",
            quoted_text="Recipient shall hold Confidential Information in confidence using a reasonable degree of care",
            risk_explanation="This is a detailed explanation of the confidentiality risk.",
            suggested_improvement="Add specific carve-outs for publicly available information.",
        )
    ]
    result = scorer.compute(
        response_text="Some audit response with issues",
        issue_count=1,
        structured_parse_failed=False,
        issues=issues,
        doc_text=sample_doc_text,
        domain_confidence=0.8,
    )
    assert "qt_match_rate" in result.factors
    assert result.factors["qt_match_rate"] == 1.0
    assert "category_validity" in result.factors
    assert result.factors["category_validity"] == 1.0
    assert result.score > 0.7, f"Expected score > 0.7 for good issues, got {result.score}"


def test_full_compute_with_hallucination(scorer, sample_doc_text):
    issues = [
        AuditIssue(
            issue_title="Hallucinated Issue",
            severity="HIGH",
            category="InvalidCategory",
            location="Section 99",
            quoted_text="This clause does not exist anywhere in the provided agreement",
            risk_explanation="Bad.",
            suggested_improvement="Fix it.",
        )
    ]
    result = scorer.compute(
        response_text="Some audit response with issues",
        issue_count=1,
        structured_parse_failed=False,
        issues=issues,
        doc_text=sample_doc_text,
        domain_confidence=0.8,
    )
    assert result.factors["qt_match_rate"] == 0.0
    assert result.factors["category_validity"] == 0.0
    assert result.score < 0.5, f"Expected score < 0.5 for hallucinated issue, got {result.score}"


def test_full_compute_no_issues(scorer):
    result = scorer.compute(
        response_text="Some audit response",
        issue_count=0,
        structured_parse_failed=False,
        issues=[],
        doc_text="",
    )
    assert result.score < 0.5, f"Expected score < 0.5 for no issues, got {result.score}"


def test_full_compute_parse_failed(scorer):
    result = scorer.compute(
        response_text="Some audit response",
        issue_count=3,
        structured_parse_failed=True,
        issues=[],
        doc_text="",
    )
    assert result.score <= 0.25, f"Expected score <= 0.25 for parse failed, got {result.score}"


# =========================================================================
# Label from score
# =========================================================================

def test_label_high():
    assert _label_from_score(0.75) == "HIGH"

def test_label_medium():
    assert _label_from_score(0.60) == "MEDIUM"
    assert _label_from_score(0.45) == "MEDIUM"

def test_label_low():
    assert _label_from_score(0.44) == "LOW"
    assert _label_from_score(0.0) == "LOW"
