from dataclasses import dataclass, field
from typing import List
import re

from backend.logger import logger


SURVIVAL_PHRASES = [
    re.compile(r"(?i)\bsurvive\s+(?:the\s+)?termination\b"),
    re.compile(r"(?i)\bcontinues?\s+(?:to\s+)?(?:be\s+)?(?:in\s+)?effect\s+(?:after\s+)?(?:the\s+)?termination\b"),
    re.compile(r"(?i)\bcontinue\s+(?:to\s+)?(?:be\s+)?(?:in\s+)?effect\s+(?:after\s+)?(?:the\s+)?termination\b"),
    re.compile(r"(?i)\bremain\s+(?:in\s+)?effect\s+(?:after\s+)?(?:termination|expiration)\b"),
    re.compile(r"(?i)\bshall\s+survive\b"),
    re.compile(r"(?i)\bwill\s+survive\b"),
    re.compile(r"(?i)\bobligations?\s+.*\bsurvive\b"),
    re.compile(r"(?i)\bprovisions?\s+.*\bsurvive\b"),
    re.compile(r"(?i)\bterms?\s+.*\bsurvive\b"),
    re.compile(r"(?i)\bcontinues?\s+after\s+termination\b"),
]

PROHIBITED_CATEGORIES = {
    "confidentiality termination",
    "missing survival clause",
    "termination survival",
    "survival clause missing",
    "no survival provision",
    "absence of survival",
    "survival omission",
    "confidentiality ends on termination",
    "termination of confidentiality",
}

DURATION_INSUFFICIENCY_CUES = [
    re.compile(r"(?i)\b(?:duration|period|time\s*frame|timeframe|length)\s+(?:is\s+)?(?:insufficient|inadequate|too\s+short|too\s+brev)"),
    re.compile(r"(?i)\b(?:does\s+not\s+specify|fails?\s+to\s+specify|lacks?)\s+(?:a\s+)?(?:duration|period|time\s*limit|time\s*frame)"),
    re.compile(r"(?i)\b(?:no\s+)?(?:specified|defined|stated)\s+(?:duration|period|end\s*date|termination\s*date)"),
    re.compile(r"(?i)\b(?:survival\s+)?(?:period|duration)\s+(?:is\s+)?(?:unspecified|undefined|not\s+stated|missing)"),
    re.compile(r"(?i)\b(?:indefinite|perpetual|permanent)\s+(?:obligation|duty|commitment|survival)"),
    re.compile(r"(?i)\b(?:no\s+)?(?:end\s*date|expiration\s*date|termination\s*date)\s+(?:is\s+)?(?:provided|specified|stated|defined)"),
    re.compile(r"(?i)\b(?:continues\s+(?:indefinitely|forever|perpetually)|no\s+end\s+to\s+obligations)"),
]


@dataclass
class ContradictionResult:
    has_contradiction: bool
    issue_index: int
    contradiction_type: str
    quoted_text: str
    category: str
    risk_explanation: str
    reason: str
    suppressed: bool = False

    def to_dict(self):
        return {
            "has_contradiction": self.has_contradiction,
            "issue_index": self.issue_index,
            "contradiction_type": self.contradiction_type,
            "quoted_text": self.quoted_text,
            "category": self.category,
            "risk_explanation": self.risk_explanation,
            "reason": self.reason,
            "suppressed": self.suppressed,
        }


def _has_survival_language(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in SURVIVAL_PHRASES)


def _is_prohibited_category(category: str) -> bool:
    return category.strip().lower() in PROHIBITED_CATEGORIES


def _references_duration_insufficiency(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in DURATION_INSUFFICIENCY_CUES)


def _check_semantic_contradiction(quoted_text: str, risk_explanation: str) -> bool:
    if not quoted_text or not risk_explanation:
        return False

    survival_in_quote = _has_survival_language(quoted_text)
    if not survival_in_quote:
        return False

    risk_lower = risk_explanation.lower()

    missing_indicators = re.compile(
        r"(?i)\b(?:missing|absent|lacks?|no\s+(?:survival|provision|clause)|omitted|not\s+found|not\s+present|does\s+not\s+(?:exist|appear|state|specify))\b"
    )
    termination_indicators = re.compile(
        r"(?i)\b(?:terminate|termination|end|expire|expiration|cease|dissolve)\b"
    )

    has_missing = bool(missing_indicators.search(risk_explanation))
    has_termination = bool(termination_indicators.search(risk_explanation))

    if has_missing:
        return True

    if has_termination and not _references_duration_insufficiency(risk_explanation):
        return True

    return False


def validate_contradictions(issues: list) -> List[ContradictionResult]:
    results: List[ContradictionResult] = []

    for idx, issue in enumerate(issues):
        quoted = issue.quoted_text or ""
        category = issue.category or ""
        risk = issue.risk_explanation or ""

        if _has_survival_language(quoted) and _is_prohibited_category(category):
            if not _references_duration_insufficiency(risk):
                result = ContradictionResult(
                    has_contradiction=True,
                    issue_index=idx,
                    contradiction_type="survival_category_mismatch",
                    quoted_text=quoted,
                    category=category,
                    risk_explanation=risk,
                    reason=f"Quoted text contains survival language ('survive termination' or equivalent), but category '{category}' contradicts this. Category prohibited unless reasoning references duration insufficiency.",
                )
                results.append(result)
                logger.warning(
                    "[Contradiction] Issue %d: survival-category contradiction detected. Category='%s' vs survival language in quoted text. Reason: %s",
                    idx, category, result.reason,
                )
                continue

        if _check_semantic_contradiction(quoted, risk):
            result = ContradictionResult(
                has_contradiction=True,
                issue_index=idx,
                contradiction_type="semantic_mismatch",
                quoted_text=quoted,
                category=category,
                risk_explanation=risk,
                reason=f"Semantic contradiction between quoted text (contains survival language) and risk explanation (implies termination/absence).",
            )
            results.append(result)
            logger.warning(
                "[Contradiction] Issue %d: semantic contradiction detected. Quoted text has survival language but risk explanation implies termination or absence.",
                idx,
            )

    return results


def apply_contradiction_suppression(issues: list, contradictions: List[ContradictionResult]) -> list:
    if not contradictions:
        return issues

    suppressed_indices = {c.issue_index for c in contradictions if c.has_contradiction}

    kept_issues = []
    for idx, issue in enumerate(issues):
        if idx in suppressed_indices:
            for c in contradictions:
                if c.issue_index == idx:
                    c.suppressed = True
            logger.info(
                "[Contradiction] Suppressing issue %d due to contradiction: %s",
                idx, c.contradiction_type,
            )
        else:
            kept_issues.append(issue)

    if suppressed_indices:
        logger.info("[Contradiction] Total issues suppressed -> %d", len(suppressed_indices))

    return kept_issues
