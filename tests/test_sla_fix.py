"""
Unit tests for the "No SLA" hallucination fix (P1).

Tests verify that:
1. The prompt contains the SLA verification step
2. The prompt lists the correct SLA keywords
3. A helper function correctly detects SLA presence in contracts
4. The normalization function suppresses false SLA findings

Usage:
    python -m pytest tests/test_sla_fix.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.prompts.audit_prompt import build_audit_prompt
from backend.engines.normalization_engine import (
    AuditIssue,
    suppress_false_sla_findings,
)


# =========================================================================
# Helper: SLA keyword detection
# =========================================================================

SLA_KEYWORDS = [
    "service level", "uptime", "availability", "99.5%", "98%", "99%",
    "sla", "guarantee", "maintain",
]


def contract_has_sla_keywords(contract_text: str) -> bool:
    """Check if a contract contains SLA-related keywords.
    
    This mirrors the logic added to the prompt rule.
    """
    text_lower = contract_text.lower()
    return any(kw in text_lower for kw in SLA_KEYWORDS)


# =========================================================================
# Prompt structure tests
# =========================================================================

def test_prompt_contains_sla_verification_step():
    prompt = build_audit_prompt()
    assert "BEFORE generating this finding" in prompt
    assert "scan the ENTIRE contract" in prompt


def test_prompt_contains_sla_keywords_list():
    prompt = build_audit_prompt()
    assert "service level" in prompt
    assert "uptime" in prompt
    assert "availability" in prompt
    assert "performance" in prompt
    assert "99.5%" in prompt
    assert "98%" in prompt
    assert "99%" in prompt
    assert "SLA" in prompt
    assert "guarantee" in prompt
    assert "maintain" in prompt


def test_prompt_contains_do_not_instruction():
    prompt = build_audit_prompt()
    assert "No Service Level Agreement" in prompt
    assert "ONLY applies when NONE of these words appear" in prompt


def test_prompt_sla_rule_is_single_rule():
    prompt = build_audit_prompt()
    # Find the SLA rule section
    sla_idx = prompt.find("No Service Level Agreement")
    before_idx = prompt.find("BEFORE generating this finding")
    # The BEFORE instruction should appear after the SLA rule starts
    assert before_idx > sla_idx - 500  # Within 500 chars before "No Service Level Agreement"


# =========================================================================
# SLA keyword detection tests
# =========================================================================

def test_valid_missing_sla():
    """Contract with no SLA keywords should be detected as missing SLA."""
    contract = """
    This Agreement is between Party A and Party B.
    The term of this Agreement is twelve months.
    Either party may terminate with thirty days notice.
    """
    assert contract_has_sla_keywords(contract) == False


def test_explicit_sla_uptime():
    """Contract with explicit uptime SLA should be detected."""
    contract = """
    SERVICE LEVELS
    Provider shall maintain 99.5% uptime measured monthly.
    """
    assert contract_has_sla_keywords(contract) == True


def test_explicit_sla_availability():
    """Contract with availability commitment should be detected."""
    contract = """
    The Services shall be available 24 hours a day, 7 days a week.
    Provider guarantees 99.9% availability.
    """
    assert contract_has_sla_keywords(contract) == True


def test_sla_performance_metrics():
    """Contract with performance metrics should be detected."""
    contract = """
    Vendor shall maintain:
    (a) order accuracy of at least 99.5%;
    (b) on-time shipment rate of at least 98%;
    (c) inventory accuracy of at least 99%.
    """
    assert contract_has_sla_keywords(contract) == True


def test_sla_commercially_reasonable_efforts():
    """Contract with 'commercially reasonable efforts' and percentage should be detected."""
    contract = """
    Provider shall use commercially reasonable efforts to make the Services
    available at least 99.5% of the time in any calendar month.
    """
    assert contract_has_sla_keywords(contract) == True


def test_sla_service_level_phrase():
    """Contract containing 'service level' phrase should be detected."""
    contract = """
    The Provider agrees to the following service level commitments:
    Response time within 4 hours for critical issues.
    """
    assert contract_has_sla_keywords(contract) == True


def test_sla_maintain_keyword():
    """Contract containing 'maintain' should be detected."""
    contract = """
    Vendor shall maintain the following standards:
    - 99% uptime
    - 4-hour response time
    """
    assert contract_has_sla_keywords(contract) == True


def test_sla_different_wording_guarantee():
    """Contract using 'guarantee' should be detected."""
    contract = """
    We guarantee that the platform will be operational at least 99% of the time.
    """
    assert contract_has_sla_keywords(contract) == True


def test_no_sla_no_keywords():
    """Contract with no SLA-related words should not be detected."""
    contract = """
    This Software License Agreement is between Licensor and Licensee.
    The license fee is $10,000.
    This Agreement is governed by California law.
    """
    assert contract_has_sla_keywords(contract) == False


def test_no_sla_similar_words():
    """Contract with similar but not matching words should not be detected."""
    contract = """
    This Agreement is about service delivery.
    The Provider will perform the work.
    No specific performance targets are defined.
    """
    assert contract_has_sla_keywords(contract) == False


def test_sla_partial_match_99():
    """Contract containing '99%' should be detected."""
    contract = """
    Provider shall maintain 99% or higher performance.
    """
    assert contract_has_sla_keywords(contract) == True


def test_sla_partial_match_98():
    """Contract containing '98%' should be detected."""
    contract = """
    On-time delivery rate must be 98% or higher.
    """
    assert contract_has_sla_keywords(contract) == True


# =========================================================================
# Edge cases
# =========================================================================

def test_empty_contract():
    """Empty contract should not trigger SLA detection."""
    assert contract_has_sla_keywords("") == False


def test_case_insensitive():
    """Detection should be case-insensitive."""
    assert contract_has_sla_keywords("SERVICE LEVEL") == True
    assert contract_has_sla_keywords("UPTIME") == True
    assert contract_has_sla_keywords("99.5%") == True


def test_sla_in_exhibit_reference():
    """Contract referencing SLA in exhibit should be detected."""
    contract = """
    The service levels are described in Exhibit B.
    Provider shall maintain the service levels as set forth therein.
    """
    assert contract_has_sla_keywords(contract) == True


def test_sla_in_definition():
    """Contract defining 'Service Level' should be detected."""
    contract = """
    'Service Level' means the performance targets set forth in Schedule 2.
    Provider shall maintain the Service Levels.
    """
    assert contract_has_sla_keywords(contract) == True


# =========================================================================
# Normalization suppression tests
# =========================================================================

def test_suppress_false_sla_with_sla_keywords():
    """False 'No SLA' finding should be suppressed when contract has SLA keywords."""
    issues = [
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="Provider shall maintain 99.5% uptime.",
        )
    ]
    doc_text = "Section 4: Service Levels. Provider shall maintain 99.5% uptime."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 0, f"Expected 0 issues after suppression, got {len(result)}"


def test_suppress_false_sla_case_insensitive():
    """Suppression should work case-insensitively."""
    issues = [
        AuditIssue(
            issue_title="NO SERVICE LEVEL AGREEMENT",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="Some text.",
        )
    ]
    doc_text = "SLA commitment: 99% uptime guaranteed."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 0


def test_no_suppress_when_no_sla_keywords():
    """SaaS finding should NOT be suppressed when SaaS contract has no SLA keywords."""
    issues = [
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="No performance targets defined.",
        )
    ]
    # SaaS/cloud document without SLA keywords — finding is valid, must not be suppressed
    doc_text = "This SaaS subscription agreement covers cloud platform access. No performance targets are defined."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 1, f"Expected 1 issue (no suppression), got {len(result)}"


def test_no_suppress_non_sla_issues():
    """Non-SLA issues should not be affected by SLA suppression."""
    issues = [
        AuditIssue(
            issue_title="Incomplete Confidentiality Exclusions",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="Some confidentiality text.",
        )
    ]
    doc_text = "Service level commitment: 99.5% uptime."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 1, f"Expected 1 issue (no suppression), got {len(result)}"


def test_suppress_multiple_false_sla():
    """Multiple false SLA findings should all be suppressed."""
    issues = [
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="Text 1.",
        ),
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="LOW",
            category="Structural Omission",
            quoted_text="Text 2.",
        ),
    ]
    doc_text = "Uptime guarantee: 99.9%."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 0


def test_suppress_empty_doc_text():
    """Empty doc_text should not suppress anything."""
    issues = [
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="Some text.",
        )
    ]
    result = suppress_false_sla_findings(issues, "")
    assert len(result) == 1


def test_suppress_partial_sla_keywords():
    """Finding should be suppressed if contract has ANY SLA keyword."""
    issues = [
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="Some text.",
        )
    ]
    # Contract only has "maintain" — but that's enough
    doc_text = "Vendor shall maintain quality standards."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 0


def test_suppress_mixed_sla_and_non_sla_issues():
    """Only SLA issues should be suppressed; other issues should remain."""
    issues = [
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="Text 1.",
        ),
        AuditIssue(
            issue_title="Asymmetric Termination Rights",
            severity="MEDIUM",
            category="Negotiation Imbalance",
            quoted_text="Text 2.",
        ),
    ]
    doc_text = "Service level: 99.5% uptime."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 1
    assert result[0].issue_title == "Asymmetric Termination Rights"


def test_no_suppress_when_contract_disclaims_sla():
    """Finding should NOT be suppressed when contract explicitly says 'no SLA'."""
    issues = [
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="No service level agreement.",
        )
    ]
    doc_text = "NO SERVICE LEVEL AGREEMENT. Provider does not guarantee any level of uptime."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 1, f"Expected 1 issue (no suppression for disclaimers), got {len(result)}"


def test_no_suppress_when_contract_says_as_is():
    """Finding should NOT be suppressed when contract says 'AS IS'."""
    issues = [
        AuditIssue(
            issue_title="No Service Level Agreement",
            severity="MEDIUM",
            category="Enforceability Weakness",
            quoted_text="No SLA.",
        )
    ]
    doc_text = "The service is provided AS IS. No guarantees of uptime."
    result = suppress_false_sla_findings(issues, doc_text)
    assert len(result) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
