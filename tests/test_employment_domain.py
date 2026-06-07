"""Regression tests for employment-agreement domain classification.

Verifies that EMPLOYMENT AGREEMENT documents are classified as LEGAL
(or at worst POSSIBLY_LEGAL) and that their issues are NOT suppressed
by the downstream pipeline suppression logic.
"""

from backend.engines.legal_domain_engine import (
    compute_document_domain_confidence,
    DocumentDomain,
)
from backend.engines.normalization_engine import (
    AuditIssue,
    build_audit_json_payload,
    _apply_standard_nda_suppression,
)

EMPLOYMENT_TEXT = """EMPLOYMENT AGREEMENT

This Employment Agreement is entered into as of June 1, 2026 between MegaCorp Inc. ("Employer") and John Employee ("Employee").

1. POSITION. Employee shall serve as Senior Software Engineer, reporting to the VP of Engineering.

2. COMPENSATION. Employer shall pay Employee an annual base salary of $150,000, payable in accordance with Employer's standard payroll practices. Employee is eligible for an annual discretionary bonus of up to 20% of base salary.

3. AT-WILL EMPLOYMENT. Employment is at-will. Either party may terminate the employment relationship at any time, with or without cause or prior notice.

4. CONFIDENTIALITY. Employee shall hold in confidence all Confidential Information of Employer during and after employment. "Confidential Information" includes all non-public information about Employer's business, products, customers, financials, strategies, and intellectual property.

5. INVENTION ASSIGNMENT. Employee hereby assigns to Employer all right, title, and interest in any and all inventions, discoveries, improvements, copyrightable works, and intellectual property that Employee conceives or creates during employment, whether during or outside of working hours, and whether or not related to Employee's job duties. Employee agrees to execute all documents necessary to perfect Employer's rights in such inventions.

6. NON-COMPETITION. For a period of twelve (12) months following termination of employment for any reason, Employee shall not, directly or indirectly, engage in any business that competes with Employer within a 50-mile radius of any Employer office location. This restriction applies regardless of the reason for termination.

7. NON-SOLICITATION. For twelve (12) months following termination, Employee shall not solicit or induce any employee or customer of Employer to terminate their relationship with Employer.

8. SEVERANCE. If Employer terminates Employee without cause, Employee shall receive three months of base salary as severance.

9. GOVERNING LAW. This Agreement shall be governed by the laws of the State of Texas.
"""


def test_employment_domain_is_not_non_legal():
    """Employment agreements must be classified as LEGAL or POSSIBLY_LEGAL,
    never NON_LEGAL, so that downstream suppression is not triggered."""
    result = compute_document_domain_confidence(EMPLOYMENT_TEXT)
    assert result.domain != DocumentDomain.NON_LEGAL, (
        f"Employment agreement classified as NON_LEGAL "
        f"(effective_score={result.confidence:.4f})"
    )
    # The boost should push the score to at least POSSIBLY_LEGAL threshold
    assert result.confidence >= 0.08, (
        f"Employment agreement score {result.confidence:.4f} "
        f"below NON_LEGAL threshold 0.08"
    )


def test_employment_domain_is_legal_after_boost():
    """The employment-title boost should raise effective_score to at least
    POSSIBLY_LEGAL threshold + 0.05 = 0.25, making the domain LEGAL."""
    result = compute_document_domain_confidence(EMPLOYMENT_TEXT)
    assert result.domain == DocumentDomain.LEGAL, (
        f"Expected LEGAL, got {result.domain} "
        f"(effective_score={result.confidence:.4f})"
    )
    assert result.confidence >= 0.25, (
        f"Employment agreement effective_score={result.confidence:.4f} "
        f"below expected boost target 0.25"
    )


def test_employment_issues_survive_full_pipeline():
    """When employment text is provided as user_input and parsed_issues are
    supplied, the full build_audit_json_payload must NOT suppress the issues."""
    sample_issues = [
        AuditIssue(
            issue_title="Overbroad Invention Assignment",
            severity="HIGH",
            category="Intellectual Property",
            location="Section 5",
            quoted_text="Employee hereby assigns to Employer all right, title, and interest in any and all inventions...",
            risk_explanation="Assigns inventions created outside working hours and unrelated to job duties.",
        ),
        AuditIssue(
            issue_title="Overbroad Non-Compete",
            severity="MEDIUM",
            category="Restrictive Covenants",
            location="Section 6",
            quoted_text="Employee shall not...engage in any business that competes with Employer...",
            risk_explanation="12-month non-compete with 50-mile radius applies regardless of termination reason.",
        ),
    ]

    # Build a minimal complete_response (simulates model JSON output)
    complete_response = '{"issues":[{"issue_title":"Overbroad Invention Assignment","severity":"HIGH","category":"Intellectual Property"}]}'

    result = build_audit_json_payload(
        complete_response=complete_response,
        model="test-model",
        user_input=EMPLOYMENT_TEXT,
        fallback_used=True,
        parsed_issues=sample_issues,
    )

    final_issues_raw = result.get("issues", [])
    # Must have at least one issue (the pipeline must not zero them out)
    assert len(final_issues_raw) > 0, (
        "All employment issues were suppressed by the pipeline! "
        f"structured_parse_failed={result.get('structured_parse_failed')}, "
        f"metadata.domain={result.get('metadata', {}).get('domain', 'N/A')}"
    )

    # Verify domain in metadata is LEGAL
    metadata = result.get("metadata", {})
    domain = metadata.get("domain", "")
    assert domain == DocumentDomain.LEGAL.value, (
        f"Expected LEGAL domain in pipeline metadata, got '{domain}'"
    )


def test_employment_suppression_is_not_triggered():
    """The _apply_standard_nda_suppression rule must NOT modify employment
    issues (it only applies to NDA-style confidentiality categories)."""
    issue = AuditIssue(
        issue_title="Overbroad Invention Assignment",
        severity="HIGH",
        category="Intellectual Property",
        location="Section 5",
        quoted_text="Employee hereby assigns to Employer all right, title, and interest...",
        risk_explanation="Overbroad invention assignment.",
    )
    before_sev = issue.severity
    modified = _apply_standard_nda_suppression([issue], EMPLOYMENT_TEXT)
    assert modified == 0, (
        f"Standard NDA suppression modified {modified} employment issue(s) "
        f"(severity changed from {before_sev} to {issue.severity}). "
        "Employment IP issues should NOT be suppressed by NDA rules."
    )
    assert issue.severity == before_sev, (
        f"Employment issue severity changed from {before_sev} to {issue.severity}"
    )
