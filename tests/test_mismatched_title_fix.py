"""
Unit tests for the mismatched title suppression fix (P2).

Tests verify that:
1. Mismatched title/quoted_text findings are suppressed
2. Matched findings are preserved
3. Edge cases are handled (empty title, empty quoted_text, etc.)

Usage:
    python -m pytest tests/test_mismatched_title_fix.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.normalization_engine import (
    AuditIssue,
    suppress_mismatched_title_findings,
)


def _make_issue(title="", quoted_text="", category="", severity="MEDIUM"):
    return AuditIssue(
        issue_title=title,
        severity=severity,
        category=category,
        location="test",
        quoted_text=quoted_text,
        risk_explanation="test",
        suggested_improvement="test",
    )


# =========================================================================
# Positive cases — mismatched titles should be suppressed
# =========================================================================

class TestMismatchedTitleSuppression:
    def test_non_compete_title_with_liability_text(self):
        """Title says 'Non-Compete Duration' but text is about liability cap."""
        issue = _make_issue(
            title="Excessive Non-Compete Duration",
            quoted_text="VENDOR'S TOTAL LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED THE GREATER OF (A) THE FEES PAID BY CUSTOMER IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM, OR (B) $500,000.",
            category="Negotiation Imbalance",
        )
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 0

    def test_confidentiality_title_with_indemnity_text(self):
        """Title says 'Confidentiality Termination' but text is about indemnification."""
        issue = _make_issue(
            title="Confidentiality Termination",
            quoted_text="Vendor shall indemnify, defend, and hold harmless Customer from any claims, damages, or expenses arising from Vendor's negligence.",
            category="Confidentiality Risk",
        )
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 0

    def test_termination_title_with_liability_text(self):
        """Title says 'Termination' but text is about limitation of liability."""
        issue = _make_issue(
            title="Termination for Convenience",
            quoted_text="CONSULTANT'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED THE TOTAL FEES PAID.",
            category="Enforceability Weakness",
        )
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 0

    def test_governing_law_title_with_warranty_text(self):
        """Title says 'Governing Law' but text is about warranty disclaimer."""
        issue = _make_issue(
            title="Governing Law Risk",
            quoted_text="LICENSOR DISCLAIMS ALL OTHER WARRANTIES, INCLUDING WITHOUT LIMITATION THE IMPLIED WARRANTIES OF MERCHANTABILITY.",
            category="Enforceability Weakness",
        )
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 0


# =========================================================================
# Negative cases — matched titles should be preserved
# =========================================================================

class TestMatchedTitlePreservation:
    def test_non_compete_title_with_non_compete_text(self):
        """Title says 'Non-Compete Duration' and text is about non-compete."""
        issue = _make_issue(
            title="Excessive Non-Compete Duration",
            quoted_text="For a period of eighteen (18) months following termination, Employee shall not engage in any business that competes.",
            category="Enforceability Weakness",
        )
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 1

    def test_liability_title_with_liability_text(self):
        """Title says 'Limitation of Liability' and text is about liability."""
        issue = _make_issue(
            title="Limitation of Liability",
            quoted_text="CONSULTANT'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED THE TOTAL FEES PAID.",
            category="Liability Exposure",
        )
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 1

    def test_confidentiality_title_with_confidentiality_text(self):
        """Title says 'Confidentiality' and text is about confidentiality."""
        issue = _make_issue(
            title="Incomplete Confidentiality Exclusions",
            quoted_text="Employee agrees to hold in confidence all proprietary and confidential information of the Company.",
            category="Confidentiality Risk",
        )
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 1

    def test_indemnification_title_with_indemnity_text(self):
        """Title says 'Indemnification' and text is about indemnification."""
        issue = _make_issue(
            title="Excessive Indemnity",
            quoted_text="Vendor shall indemnify, defend, and hold harmless Customer from any claims.",
            category="Indemnification",
        )
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 1


# =========================================================================
# Edge cases
# =========================================================================

class TestEdgeCases:
    def test_empty_issues(self):
        result = suppress_mismatched_title_findings([])
        assert result == []

    def test_empty_quoted_text(self):
        issue = _make_issue(title="Non-Compete Duration", quoted_text="")
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 1

    def test_empty_title(self):
        issue = _make_issue(title="", quoted_text="some text here")
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 1

    def test_both_empty(self):
        issue = _make_issue(title="", quoted_text="")
        result = suppress_mismatched_title_findings([issue])
        assert len(result) == 1

    def test_mixed_mismatched_and_matched(self):
        """One mismatched (suppressed) and one matched (preserved)."""
        mismatched = _make_issue(
            title="Non-Compete Duration",
            quoted_text="VENDOR'S TOTAL LIABILITY SHALL NOT EXCEED $500,000.",
        )
        matched = _make_issue(
            title="Non-Compete Duration",
            quoted_text="For a period of eighteen (18) months, Employee shall not compete.",
        )
        result = suppress_mismatched_title_findings([mismatched, matched])
        assert len(result) == 1
        assert result[0].issue_title == "Non-Compete Duration"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
