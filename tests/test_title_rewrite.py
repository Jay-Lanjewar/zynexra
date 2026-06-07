"""Unit tests for title rewrite layer (rewrite_mislabeled_titles)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.normalization_engine import AuditIssue, rewrite_mislabeled_titles


def make_issue(title, category, quoted_text, severity="MEDIUM"):
    return AuditIssue(
        issue_title=title,
        category=category,
        severity=severity,
        quoted_text=quoted_text,
        risk_explanation="test",
    )


def test_non_solicitation_mislabeled_as_coc():
    """Rule 1: Non-solicitation clause mislabeled as Single-Trigger CoC."""
    issue = make_issue(
        title="Single-Trigger Change of Control Acceleration",
        category="Negotiation Imbalance",
        quoted_text="During the term of this Agreement and for a period of twelve (12) months "
                    "thereafter, neither Party shall directly or indirectly solicit, induce, or "
                    "encourage any employee of the other Party to terminate employment.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert len(result) == 1
    assert result[0].issue_title == "Non-Solicitation Clause in NDA"
    print("PASS: test_non_solicitation_mislabeled_as_coc")


def test_non_solicitation_with_coc_not_rewritten():
    """Rule 1 negative: Non-solicitation with actual CoC language should NOT be rewritten."""
    issue = make_issue(
        title="Single-Trigger Change of Control Acceleration",
        category="Negotiation Imbalance",
        quoted_text="Upon a change of control, the non-solicitation obligation shall accelerate.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert result[0].issue_title == "Single-Trigger Change of Control Acceleration"
    print("PASS: test_non_solicitation_with_coc_not_rewritten")


def test_non_compete_mislabeled_as_coc():
    """Rule 2: Non-compete clause mislabeled as Single-Trigger CoC."""
    issue = make_issue(
        title="Single-Trigger Change of Control Acceleration",
        category="Negotiation Imbalance",
        quoted_text="For a period of eighteen (18) months following the termination of "
                    "Employee's employment for any reason, Employee shall not compete directly "
                    "or indirectly with the Company anywhere in the world.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert len(result) == 1
    assert result[0].issue_title == "Excessive Non-Compete Duration"
    print("PASS: test_non_compete_mislabeled_as_coc")


def test_non_compete_short_duration_not_rewritten():
    """Rule 2 negative: Non-compete with <=6 months should NOT be rewritten."""
    issue = make_issue(
        title="Single-Trigger Change of Control Acceleration",
        category="Negotiation Imbalance",
        quoted_text="For a period of six (6) months following termination, Employee shall not compete with Company.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert result[0].issue_title == "Single-Trigger Change of Control Acceleration"
    print("PASS: test_non_compete_short_duration_not_rewritten")


def test_generic_non_competition_excessive():
    """Rule 3: Generic 'Non-Competition' with excessive duration."""
    issue = make_issue(
        title="Non-Competition",
        category="Enforceability Weakness",
        quoted_text="For a period of eighteen (18) months following termination, Employee "
                    "shall not compete with Company.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert len(result) == 1
    assert result[0].issue_title == "Excessive Non-Compete Duration"
    print("PASS: test_generic_non_competition_excessive")


def test_generic_non_competition_standard_not_rewritten():
    """Rule 3 negative: Generic 'Non-Competition' with <=6 months should NOT be rewritten."""
    issue = make_issue(
        title="Non-Competition",
        category="Enforceability Weakness",
        quoted_text="For a period of three (3) months following termination, Employee shall not compete.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert result[0].issue_title == "Non-Competition"
    print("PASS: test_generic_non_competition_standard_not_rewritten")


def test_consultant_ip_retention():
    """Rule 4: Consultant IP retention mislabeled as generic IP Ownership."""
    issue = make_issue(
        title="Intellectual Property Ownership",
        category="Intellectual Property",
        quoted_text="Consultant retains all right, title, and interest in and to any and all "
                    "intellectual property, including without limitation software, code, algorithms.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert len(result) == 1
    assert result[0].issue_title == "Consultant Retains All Deliverable IP"
    print("PASS: test_consultant_ip_retention")


def test_ip_ownership_not_consultant_not_rewritten():
    """Rule 4 negative: 'IP Ownership' without consultant/retain language should NOT be rewritten."""
    issue = make_issue(
        title="Intellectual Property Ownership",
        category="Intellectual Property",
        quoted_text="Employee assigns all inventions to Company during employment.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert result[0].issue_title == "Intellectual Property Ownership"
    print("PASS: test_ip_ownership_not_consultant_not_rewritten")


def test_empty_list():
    """Empty issue list should not crash."""
    result = rewrite_mislabeled_titles([])
    assert result == []
    print("PASS: test_empty_list")


def test_no_rewrite_needed():
    """Issues that don't match any rule should pass through unchanged."""
    issue = make_issue(
        title="Perpetual Confidentiality Survival",
        category="Enforceability Weakness",
        quoted_text="Confidentiality obligations shall survive perpetually.",
    )
    result = rewrite_mislabeled_titles([issue])
    assert result[0].issue_title == "Perpetual Confidentiality Survival"
    print("PASS: test_no_rewrite_needed")


def test_multiple_issues_mixed():
    """Multiple issues, some rewritten, some not."""
    issues = [
        make_issue(
            title="Single-Trigger Change of Control Acceleration",
            category="Negotiation Imbalance",
            quoted_text="During the term, neither Party shall solicit any employee.",
        ),
        make_issue(
            title="Perpetual Confidentiality Survival",
            category="Enforceability Weakness",
            quoted_text="Confidentiality obligations shall survive perpetually.",
        ),
        make_issue(
            title="Intellectual Property Ownership",
            category="Intellectual Property",
            quoted_text="Consultant retains all right, title, and interest in IP.",
        ),
    ]
    result = rewrite_mislabeled_titles(issues)
    assert result[0].issue_title == "Non-Solicitation Clause in NDA"
    assert result[1].issue_title == "Perpetual Confidentiality Survival"
    assert result[2].issue_title == "Consultant Retains All Deliverable IP"
    print("PASS: test_multiple_issues_mixed")


if __name__ == "__main__":
    test_non_solicitation_mislabeled_as_coc()
    test_non_solicitation_with_coc_not_rewritten()
    test_non_compete_mislabeled_as_coc()
    test_non_compete_short_duration_not_rewritten()
    test_generic_non_competition_excessive()
    test_generic_non_competition_standard_not_rewritten()
    test_consultant_ip_retention()
    test_ip_ownership_not_consultant_not_rewritten()
    test_empty_list()
    test_no_rewrite_needed()
    test_multiple_issues_mixed()
    print("\nAll tests passed!")
