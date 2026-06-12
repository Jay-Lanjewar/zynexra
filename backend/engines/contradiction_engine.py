from dataclasses import dataclass, field
from typing import List, Set
import re

from backend.logger import logger


SELF_NEGATING_PATTERNS = [
    re.compile(r"(?i)does\s+not\s+create\s+(significant\s+)?risk"),
    re.compile(r"(?i)does\s+not\s+appear\s+(to\s+)?(create\s+)?(significant\s+)?(risk|problematic)"),
    re.compile(r"(?i)(is|appears?\s+to\s+be)\s+standard\s+and\s+(does\s+not|is\s+not)"),
    re.compile(r"(?i)commercially\s+reasonable"),
    re.compile(r"(?i)balanced\s+and\s+commercially\s+reasonable"),
    re.compile(r"(?i)no\s+suggested\s+improvement\s+needed"),
    re.compile(r"(?i)does\s+not\s+warrant\s+a\s+finding"),
    re.compile(r"(?i)not\s+a\s+risk"),
    re.compile(r"(?i)no\s+significant\s+risk"),
]

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

TERMINATION_PHRASES = [
    re.compile(r"(?i)\b(?:cease|shall\s+not\s+survive|shall\s+not\s+continue|shall\s+not\s+remain|no\s+longer\s+bound)\b"),
    re.compile(r"(?i)\bimmediately\s+(?:cease|terminate|end)\b"),
    re.compile(r"(?i)\b(?:terminates?\s+immediately|termination\s+of\s+.*\s+obligations)\b"),
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

FINITE_DURATION_PATTERNS = [
    re.compile(r"(?i)for\s+a\s+period\s+of\s+\w+\s*\(\d+\)\s*years?"),
    re.compile(r"(?i)for\s+a\s+period\s+of\s+\d+\s*years?"),
    re.compile(r"(?i)\w+\s*\(\d+\)\s*years?"),
    re.compile(r"(?i)\d+\s*\(\w+\)\s*years?"),
    re.compile(r"(?i)\d+\s+years?"),
    re.compile(r"(?i)for\s+\d+\s+years?"),
    re.compile(r"(?i)lasts?\s+for\s+\d+\s*years?"),
    re.compile(r"(?i)lasts?\s+for\s+\w+\s*\(\d+\)\s*years?"),
]

PERPETUAL_OR_INDEFINITE_PATTERNS = [
    re.compile(r"(?i)\bperpetual\b"),
    re.compile(r"(?i)\bindefinite\b"),
    re.compile(r"(?i)\bwithout\s+limit\b"),
    re.compile(r"(?i)\bpermanently\b"),
    re.compile(r"(?i)\bin\s+perpetuity\b"),
    re.compile(r"(?i)\bindefinitely\b"),
]


def _has_finite_duration(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in FINITE_DURATION_PATTERNS)


def _has_perpetual_or_indefinite(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in PERPETUAL_OR_INDEFINITE_PATTERNS)


def _check_finite_duration_contradiction(
    issue_title: str, quoted_text: str, risk_explanation: str
) -> bool:
    if not quoted_text:
        return False
    if not _has_finite_duration(quoted_text):
        return False
    if _has_perpetual_or_indefinite(issue_title):
        return True
    if _has_perpetual_or_indefinite(risk_explanation):
        return True
    return False


OBLIGATION_DOMAIN_PATTERNS = [
    re.compile(r"(?i)\bconfidential"),
    re.compile(r"(?i)\bproprietary"),
    re.compile(r"(?i)\bnon-?disclos"),
    re.compile(r"(?i)\bnda\b"),
    re.compile(r"(?i)\bnon-?compete"),
    re.compile(r"(?i)\bcompetition"),
    re.compile(r"(?i)\brestrictive\s+covenant"),
    re.compile(r"(?i)\bgoverning\s+law"),
    re.compile(r"(?i)\bchoice\s+of\s+law"),
    re.compile(r"(?i)\bjurisdiction"),
    re.compile(r"(?i)\bvenue\b"),
    re.compile(r"(?i)\bindemnif"),
    re.compile(r"(?i)\bhold\s+harmless"),
    re.compile(r"(?i)\bentire\s+agreement"),
    re.compile(r"(?i)\bmerger\b"),
    re.compile(r"(?i)\bintegration\s+clause"),
    re.compile(r"(?i)\bsupersed"),
    re.compile(r"(?i)\bsurviv"),
    re.compile(r"(?i)\bpost-?termination"),
    re.compile(r"(?i)\bterminat(?:e|ion|ing)"),
    re.compile(r"(?i)\bexpir"),
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
    document_level_conflict: bool = False

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
            "document_level_conflict": self.document_level_conflict,
        }


def _has_survival_language(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in SURVIVAL_PHRASES)


def _has_termination_language(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in TERMINATION_PHRASES)


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
        r"(?i)\b(?:terminate|termination|expire|expiration|cease|dissolve)\b"
    )

    has_missing = bool(missing_indicators.search(risk_explanation))
    has_termination = bool(termination_indicators.search(risk_explanation))

    if has_missing:
        return True

    if has_termination and not _references_duration_insufficiency(risk_explanation):
        return True

    return False


def _extract_obligation_domains(text: str) -> Set[str]:
    if not text:
        return set()
    domains: Set[str] = set()
    for pattern in OBLIGATION_DOMAIN_PATTERNS:
        if pattern.search(text):
            domains.add(pattern.pattern)
    return domains


def _find_document_level_conflicts(issues: list) -> Set[int]:
    survival_indices: List[int] = []
    termination_indices: List[int] = []

    for idx, issue in enumerate(issues):
        quoted = issue.quoted_text or ""
        if _has_survival_language(quoted):
            survival_indices.append(idx)
        if _has_termination_language(quoted):
            termination_indices.append(idx)

    if not survival_indices or not termination_indices:
        return set()

    conflict_indices: Set[int] = set()
    for s_idx in survival_indices:
        s_issue = issues[s_idx]
        s_text = ((s_issue.category or "") + " " + (s_issue.quoted_text or "") + " " + (s_issue.risk_explanation or ""))
        s_domains = _extract_obligation_domains(s_text)

        for t_idx in termination_indices:
            if s_idx == t_idx:
                continue
            t_issue = issues[t_idx]
            t_text = ((t_issue.category or "") + " " + (t_issue.quoted_text or "") + " " + (t_issue.risk_explanation or ""))
            t_domains = _extract_obligation_domains(t_text)

            if s_domains & t_domains:
                conflict_indices.add(s_idx)
                conflict_indices.add(t_idx)

    return conflict_indices


def _is_self_negating(issue) -> tuple:
    """Check if model reports an issue but its own risk_explanation says it's not risky.

    Returns (True, matched_phrase) if a self-negating pattern is found,
    (False, "") otherwise.
    """
    risk = (issue.risk_explanation or "").lower()
    sev = (issue.severity or "").upper()
    base_sev = sev.split("/")[0].strip()
    if base_sev not in ("LOW", "MEDIUM"):
        return False, ""
    for pattern in SELF_NEGATING_PATTERNS:
        match = pattern.search(risk)
        if match:
            return True, match.group(0)
    return False, ""


def validate_contradictions(issues: list, document_text: str = "") -> List[ContradictionResult]:
    results: List[ContradictionResult] = []

    document_conflict_indices = _find_document_level_conflicts(issues)

    conflict_found = len(document_conflict_indices) > 0
    logger.info(
        "[ContradictionDetection] contradiction_found=%s document_level_conflict_count=%d issue_indices=%s",
        conflict_found, len(document_conflict_indices),
        sorted(document_conflict_indices) if document_conflict_indices else "[]"
    )

    for idx, issue in enumerate(issues):
        quoted = issue.quoted_text or ""
        category = issue.category or ""
        risk = issue.risk_explanation or ""

        is_document_level = idx in document_conflict_indices

        if is_document_level:
            logger.info(
                "[ContradictionSuppression] document_level_conflict=True issue=%d category='%s' - keeping valid contradiction (contradictory clauses exist document-wide)",
                idx, category
            )

        if _has_survival_language(quoted) and _is_prohibited_category(category):
            if not _references_duration_insufficiency(risk):
                if is_document_level:
                    logger.info(
                        "[ContradictionDetection] survival_category_mismatch detected issue=%d category='%s' "
                        "but document_level_conflict=True - NOT suppressing",
                        idx, category
                    )
                    continue

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
                    "[ContradictionSuppression] suppressed_reason=survival_category_mismatch issue=%d category='%s'",
                    idx, category
                )
                continue

        if _check_semantic_contradiction(quoted, risk):
            if is_document_level:
                logger.info(
                    "[ContradictionDetection] semantic_contradiction detected issue=%d "
                    "but document_level_conflict=True - NOT suppressing",
                    idx
                )
                continue

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
                "[ContradictionSuppression] suppressed_reason=semantic_mismatch issue=%d",
                idx
            )
            continue

        if _check_finite_duration_contradiction(issue.issue_title, quoted, risk):
            if is_document_level:
                logger.info(
                    "[ContradictionDetection] finite_duration_contradiction detected issue=%d "
                    "but document_level_conflict=True - NOT suppressing",
                    idx
                )
                continue

            result = ContradictionResult(
                has_contradiction=True,
                issue_index=idx,
                contradiction_type="finite_duration_contradiction",
                quoted_text=quoted,
                category=category,
                risk_explanation=risk,
                reason=f"Quoted text contains explicit finite duration, but issue title or risk explanation claims perpetual/indefinite survival.",
            )
            results.append(result)
            logger.warning(
                "[ContradictionSuppression] suppressed_reason=finite_duration_contradiction issue=%d",
                idx
            )
            continue

        is_self_neg, matched_phrase = _is_self_negating(issue)
        if is_self_neg:
            if is_document_level:
                logger.info(
                    "[SelfNegatingSuppression] document_level_conflict=True issue=%d "
                    "issue_title='%s' category='%s' severity='%s' matched_phrase='%s' - NOT suppressing",
                    idx, issue.issue_title, category, issue.severity, matched_phrase
                )
                continue

            result = ContradictionResult(
                has_contradiction=True,
                issue_index=idx,
                contradiction_type="self_negating",
                quoted_text=quoted,
                category=category,
                risk_explanation=risk,
                reason=f"Model flags issue but its own risk_explanation states the clause is not risky (self-negating finding).",
            )
            results.append(result)
            logger.warning(
                "[SelfNegatingSuppression] issue_title='%s' category='%s' severity='%s' matched_phrase='%s'",
                issue.issue_title, category, issue.severity, matched_phrase
            )

    return results


def apply_contradiction_suppression(issues: list, contradictions: List[ContradictionResult]) -> list:
    if not contradictions:
        return issues

    suppressed_indices = {c.issue_index for c in contradictions if c.has_contradiction and not c.suppressed}

    kept_issues = []
    for idx, issue in enumerate(issues):
        if idx in suppressed_indices:
            for c in contradictions:
                if c.issue_index == idx:
                    c.suppressed = True
            logger.info(
                "[ContradictionSuppression] Suppressing issue %d - kept_after=%d",
                idx, len(kept_issues)
            )
        else:
            kept_issues.append(issue)

    if suppressed_indices:
        logger.info("[ContradictionSuppression] Total issues suppressed -> %d", len(suppressed_indices))
    else:
        logger.info("[ContradictionSuppression] No issues suppressed")

    return kept_issues


CONTRADICTION_INCOMPATIBLE_CATEGORIES = {
    "indemnification",
    "liability exposure",
}


def _scan_document_contradictions(document_text: str) -> Set[str]:
    """
    Scan full document text for contradictory clauses where one clause
    says an obligation survives termination and another says it terminates
    in the same obligation domain.

    Returns set of domain regex patterns that are in conflict.
    """
    if not document_text or not document_text.strip():
        return set()

    clauses = [c.strip() for c in re.split(r'\n\s*\n+', document_text) if c.strip()]
    if len(clauses) < 2:
        return set()

    survival_domains: Set[str] = set()
    termination_domains: Set[str] = set()

    for clause in clauses:
        if _has_survival_language(clause):
            survival_domains.update(_extract_obligation_domains(clause))
        if _has_termination_language(clause):
            termination_domains.update(_extract_obligation_domains(clause))

    return survival_domains & termination_domains


def classify_document_contradictions(issues: list, document_text: str = "") -> int:
    """
    Elevate issues involved in document-level contradictions to Structural Inconsistency.

    Detects contradictions both between existing issues and by scanning the full document.
    For each contradictory issue:
      - Sets category -> 'Structural Inconsistency'
      - Sets contradiction_detected -> True
      - Preserves original category in original_category

    Returns the number of elevated issues.
    """
    # 1. Find contradictions between existing issues
    conflict_indices = _find_document_level_conflicts(issues)

    # 2. Scan full document for clause-level contradictions not yet captured
    has_document_conflict = False
    if document_text:
        conflicting_domains = _scan_document_contradictions(document_text)
        if conflicting_domains:
            has_document_conflict = True
            for idx, issue in enumerate(issues):
                combined = " ".join(filter(None, [
                    issue.category, issue.quoted_text, issue.risk_explanation
                ]))
                issue_domains = _extract_obligation_domains(combined)
                if issue_domains & conflicting_domains:
                    conflict_indices.add(idx)

    # 3. Early exit if no conflict detected at all
    if not conflict_indices:
        logger.info(
            "[ContradictionClassification] skipped_reason=no_conflict_detected "
            "issue_level=%s document_level=%s issues=%d",
            bool(_find_document_level_conflicts(issues)),
            has_document_conflict,
            len(issues)
        )
        return 0

    # 4. Elevate all conflicting issues (with category allowlist)
    elevated_count = 0
    for idx in conflict_indices:
        if idx < len(issues):
            issue = issues[idx]
            if issue.category != "Structural Inconsistency":
                if issue.category.lower() in CONTRADICTION_INCOMPATIBLE_CATEGORIES:
                    logger.info(
                        "[ContradictionClassification] skipped_reason=non_compatible_category "
                        "issue=%d category='%s'",
                        idx, issue.category
                    )
                    continue
                issue.original_category = issue.category
                issue.category = "Structural Inconsistency"
                issue.contradiction_detected = True
                elevated_count += 1
                logger.info(
                    "[ContradictionClassification] Elevated issue %d: '%s' -> Structural Inconsistency "
                    "(contradiction_detected=True)",
                    idx, issue.original_category
                )

    if elevated_count:
        logger.info(
            "[ContradictionClassification] Total issues elevated: %d",
            elevated_count
        )

    return elevated_count
