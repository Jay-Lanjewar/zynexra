import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.normalization_engine import (
    AuditIssue,
    suppress_false_incomplete_confidentiality_exclusions,
)


def _make_issue(
    title: str = "Incomplete Confidentiality Exclusions",
    quoted_text: str = "",
    category: str = "Enforceability Weakness",
    severity: str = "MEDIUM",
) -> AuditIssue:
    return AuditIssue(
        issue_title=title,
        severity=severity,
        category=category,
        quoted_text=quoted_text,
        risk_explanation="test",
        suggested_improvement="test",
    )


# --- All four exclusions present (should be suppressed) ---

NDA01_FULL_EXCLUSIONS = (
    "Confidential Information does not include information that: "
    "(a) is or becomes publicly known through no breach of this Agreement; "
    "(b) was rightfully in Receiving Party's possession prior to disclosure; "
    "(c) is independently developed by Receiving Party without use of or reference "
    "to Confidential Information; or "
    "(d) is rightfully obtained by Receiving Party from a third party without "
    "restriction on disclosure."
)


def test_suppress_when_all_four_in_quoted_text():
    issue = _make_issue(quoted_text=NDA01_FULL_EXCLUSIONS)
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 0, "Should be suppressed"
    assert len(log) == 1
    assert len(log[0]["matched_categories"]) == 4


def test_suppress_when_all_four_in_doc_text():
    issue = _make_issue(quoted_text="Some short quote")
    result, log = suppress_false_incomplete_confidentiality_exclusions(
        [issue], doc_text=NDA01_FULL_EXCLUSIONS
    )
    assert len(result) == 0, "Should be suppressed using doc_text"
    assert len(log) == 1
    assert log[0]["search_source"] == "doc_text"


def test_suppress_preserves_other_issues():
    other = _make_issue(title="Unrelated Finding", quoted_text="Something else")
    target = _make_issue(quoted_text=NDA01_FULL_EXCLUSIONS)
    result, log = suppress_false_incomplete_confidentiality_exclusions([other, target])
    assert len(result) == 1
    assert result[0].issue_title == "Unrelated Finding"
    assert len(log) == 1


# --- Fewer than four (should NOT be suppressed) ---

NDA02_TWO_EXCLUSIONS = (
    "Notwithstanding the foregoing, the obligations set forth in this Agreement "
    "shall not apply to any information that Recipient can demonstrate by written "
    "documentation: (a) is or becomes publicly available through no fault of "
    "Recipient; (b) was in Recipient's lawful possession prior to disclosure."
)


def test_keep_when_only_two_exclusions():
    issue = _make_issue(quoted_text=NDA02_TWO_EXCLUSIONS)
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 1, "Should NOT be suppressed with only 2 exclusions"
    assert len(log) == 0


NDA04_ONE_EXCLUSION = (
    "The obligations in Section 2 shall not apply to information that is or becomes "
    "generally available to the public other than as a result of a disclosure by "
    "Counterparty in violation of this Agreement."
)


def test_keep_when_only_one_exclusion():
    issue = _make_issue(quoted_text=NDA04_ONE_EXCLUSION)
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 1, "Should NOT be suppressed with only 1 exclusion"
    assert len(log) == 0


def test_keep_when_no_exclusions():
    issue = _make_issue(
        quoted_text="Employee agrees to hold in confidence all proprietary information."
    )
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 1, "Should NOT be suppressed with no exclusions"
    assert len(log) == 0


# --- Title mismatch (should NOT be suppressed) ---

def test_keep_non_matching_title():
    issue = _make_issue(
        title="Confidentiality Survival",
        quoted_text=NDA01_FULL_EXCLUSIONS,
    )
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 1, "Should NOT be suppressed with non-matching title"
    assert len(log) == 0


def test_keep_different_category_title():
    issue = _make_issue(
        title="Incomplete Indemnification Scope",
        quoted_text=NDA01_FULL_EXCLUSIONS,
    )
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 1
    assert len(log) == 0


# --- Edge cases ---

def test_empty_issues_list():
    result, log = suppress_false_incomplete_confidentiality_exclusions([])
    assert result == []
    assert log == []


def test_empty_quoted_text():
    issue = _make_issue(quoted_text="")
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 1
    assert len(log) == 0


def test_fallback_to_quoted_text_when_doc_text_short():
    issue = _make_issue(quoted_text=NDA01_FULL_EXCLUSIONS)
    result, log = suppress_false_incomplete_confidentiality_exclusions(
        [issue], doc_text="short"
    )
    assert len(result) == 0, "Should fall back to quoted_text and suppress"
    assert log[0]["search_source"] == "quoted_text"


# --- Alternate phrasings ---

def test_suppress_alternate_phrasings():
    alt_text = (
        "Confidential Information does not include information that is or becomes "
        "generally available to the public. Information that was known prior to "
        "disclosure is also excluded. Information independently developed without "
        "use of Confidential Information is excluded. Information received from "
        "a third party without restriction is excluded."
    )
    issue = _make_issue(quoted_text=alt_text)
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 0, "Should be suppressed with alternate phrasings"
    assert len(log) == 1
    assert set(log[0]["matched_categories"]) == {
        "publicly_available", "prior_possession",
        "independent_development", "third_party_receipt",
    }


def test_suppress_lawfully_obtained_phrasing():
    text = (
        "Confidential Information excludes information that is publicly available, "
        "information that was lawfully obtained before disclosure, information "
        "independently developed, and information from a third-party source."
    )
    issue = _make_issue(quoted_text=text)
    result, log = suppress_false_incomplete_confidentiality_exclusions([issue])
    assert len(result) == 0
    assert len(log) == 1
