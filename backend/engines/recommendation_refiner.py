import re
from typing import Any, Dict, List, Tuple

from backend.logger import logger


GENERIC_ADVICE_VERBS = re.compile(
    r"\b(clarify|review|consider|revise|revisit|renegotiate|reconsider)\b",
    re.IGNORECASE,
)
SPECIFIC_MITIGATION_NOUNS = re.compile(
    r"\b(liability|indemnity|cap|limit|damages|obligation|termination|survival|"
    r"confidential|jurisdiction|arbitration|governing|scope|exposure|capped|"
    r"aggregate|monetary|exclusion|dispute|venue|prevail|reconcile|harmonize|"
    r"notice|cause|convenience|indemnification|liable|cap|survive|capped)\b",
    re.IGNORECASE,
)

def _resolve_refinement_group(category: str) -> str:
    lower = category.lower()
    if "indemnification" in lower or "indemnity" in lower:
        return "indemnification"
    if "confidentiality" in lower:
        return "confidentiality"
    if "liability exposure" in lower or "limitation of liability" in lower:
        return "limitation of liability"
    if "termination" in lower:
        return "termination"
    if "structural" in lower or "malformed" in lower or "conflicting" in lower:
        return "structural inconsistency"
    if "governing law" in lower:
        return "governing law"
    if "jurisdiction" in lower:
        return "jurisdiction"
    if "residuals" in lower:
        return "residuals"
    if "enforceability" in lower:
        return "enforceability weakness"
    if "negotiation" in lower or "imbalance" in lower:
        return "negotiation imbalance"
    if "privacy" in lower:
        return "confidentiality"
    return lower


CATEGORY_GOOD_KEYWORDS: Dict[str, List[str]] = {
    "indemnification": [
        "cap liability", "liability cap", "aggregate cap", "monetary cap",
        "narrow indemnification", "limit indemnification", "indemnity scope",
        "exclude indirect", "exclude consequential", "indemnification cap",
        "capped at", "defined monetary",
    ],
    "confidentiality": [
        "survival period", "survive termination", "post-termination",
        "continuing obligations", "confidentiality obligations after",
        "survive", "after termination", "confidential information",
        "obligations continue",
    ],
    "limitation of liability": [
        "aggregate cap", "liability cap", "limit liability", "cap liability",
        "exclude indirect", "exclude consequential", "mutual limitation",
        "define exclusions", "liability cap", "capped at",
    ],
    "termination": [
        "mutual termination", "termination rights", "termination for convenience",
        "termination for cause", "notice period", "post-termination obligations",
        "survival of terms", "terminate",
    ],
    "structural inconsistency": [
        "reconcile", "harmonize", "resolve conflict", "clarify conflicting",
        "inconsistent obligations", "conflicting clauses", "prevails",
        "provision governs",
    ],
    "governing law": [
        "governing law", "dispute resolution", "venue", "jurisdiction",
        "arbitration", "choice of law",
    ],
    "jurisdiction": [
        "governing law", "dispute resolution", "venue", "jurisdiction",
        "arbitration", "choice of law",
    ],
    "residuals": [
        "residual knowledge", "confidential information", "after termination",
        "confidentiality obligations continue",
    ],
    "enforceability weakness": [
        "consideration", "severability", "waiver", "entire agreement",
        "enforceable", "validity",
    ],
    "negotiation imbalance": [
        "mutual", "balanced", "reciprocal", "both parties",
        "symmetric", "even",
    ],
}

CategoryComponents = List[Tuple[str, str]]

CATEGORY_RISK_COMPONENTS: Dict[str, CategoryComponents] = {
    "indemnification": [
        (r"\b(unlimited|uncapped|no cap|no limit)\b",
         "Cap liability at a defined monetary amount"),
        (r"\b(all losses|any loss|all claims|any claim|all damages|any damage|"
         r"all liabilities|any liability)\b",
         "Narrow indemnification scope to exclude indirect and consequential damages"),
        (r"\b(hold harmless|indemnify|indemnity)\b",
         "Limit indemnity obligations to third-party claims only"),
        (r".*",
         "Define a clear aggregate cap on total indemnification exposure"),
    ],
    "confidentiality": [
        (r"\b(termination|expir|survival)\b",
         "Define a survival period so confidentiality obligations continue after termination"),
        (r"\b(all|any|broad|wide)\s+(confidential)\b",
         "Scope confidential information to clearly defined categories"),
        (r"\b(no|without|except)\s+(limitation|restriction)\b",
         "Add defined exceptions to confidential information"),
        (r".*",
         "Specify post-termination obligations for return or destruction of confidential materials"),
    ],
    "limitation of liability": [
        (r"\b(unlimited|uncapped|no cap|no limit|not limited)\b",
         "Define an express aggregate liability cap"),
        (r"\b(all losses|any loss|all damages|any damage|all claims|any claim)\b",
         "Exclude indirect, consequential, and incidental damages"),
        (r"\b(indemnify|indemnity|hold harmless)\b",
         "Ensure liability exclusion covers indemnification obligations"),
        (r".*",
         "Make liability limitations mutual and clearly define carve-outs"),
    ],
    "termination": [
        (r"\b(termination|terminate)\b",
         "Define notice periods and effective date of termination"),
        (r"\b(for cause|breach|default)\b",
         "Add cure periods and cure rights before termination for cause"),
        (r"\b(convenience|without cause|any reason)\b",
         "Make termination for convenience mutual with equal notice"),
        (r".*",
         "Specify post-termination obligations including survival of key provisions"),
    ],
    "structural inconsistency": [
        (r"\b(conflict|contradict|inconsistent|incompatible)\b",
         "Reconcile conflicting clauses to ensure consistent obligations"),
        (r"\b(obligation|require|shall|covenant)\b",
         "Clarify which provision governs in the event of conflict"),
        (r".*",
         "Harmonize obligations across related clauses to avoid impossible compliance"),
    ],
    "governing law": [
        (r"\b(jurisdiction|venue|forum|arbitration)\b",
         "Specify exclusive jurisdiction and venue"),
        (r"\b(governing law|choice of law|applicable law)\b",
         "Define governing law and confirm it governs all disputes"),
        (r".*",
         "Clarify dispute resolution procedures including arbitration rules if applicable"),
    ],
    "jurisdiction": [
        (r"\b(jurisdiction|venue|forum|arbitration)\b",
         "Specify exclusive jurisdiction and venue"),
        (r"\b(governing law|choice of law|applicable law)\b",
         "Define governing law and confirm it governs all disputes"),
        (r".*",
         "Clarify dispute resolution procedures including arbitration rules if applicable"),
    ],
    "residuals": [
        (r"\b(residual|residual knowledge)\b",
         "Clarify residual knowledge does not permit use of confidential information"),
        (r"\b(termination|survival|expir)\b",
         "Ensure confidentiality obligations continue after termination"),
        (r".*",
         "Define scope of permitted residual use and disclosure exceptions"),
    ],
    "enforceability weakness": [
        (r"\b(severability|invalid|unenforceable|void)\b",
         "Add severability clause to preserve remainder if any provision is invalid"),
        (r"\b(waiver|amendment|modification)\b",
         "Require written amendments and waivers to prevent oral modifications"),
        (r".*",
         "Include an entire agreement clause to prevent extrinsic claims"),
    ],
    "negotiation imbalance": [
        (r"\b(only|sole|exclusive|unilateral)\b",
         "Convert unilateral rights to mutual obligations"),
        (r"\b(indemnify|defend|hold harmless)\b",
         "Make indemnification obligations reciprocal"),
        (r"\b(terminate|termination|renew|renewal)\b",
         "Balance termination and renewal rights between parties"),
        (r".*",
         "Ensure remedies, warranties, and limitations apply equally to both parties"),
    ],
}


def _is_generic_advice(text: str) -> bool:
    has_generic = bool(GENERIC_ADVICE_VERBS.search(text))
    has_specific = bool(SPECIFIC_MITIGATION_NOUNS.search(text))
    if has_generic and not has_specific:
        return True
    if not has_specific:
        return True
    return False


def _needs_refinement(suggestion: str, category: str) -> bool:
    suggestion = suggestion.strip()
    if not suggestion or len(suggestion) < 25:
        return True
    group = _resolve_refinement_group(category)
    good_keywords = CATEGORY_GOOD_KEYWORDS.get(group, [])
    sug_lower = suggestion.lower()
    for keyword in good_keywords:
        if keyword.lower() in sug_lower:
            return False
    if _is_generic_advice(suggestion):
        return True
    return len(suggestion) < 40


def _get_relevant_components(issue: Any, category: str) -> List[str]:
    group = _resolve_refinement_group(category)
    components = CATEGORY_RISK_COMPONENTS.get(group, [])
    if not components:
        return []

    search_text = " ".join([
        issue.quoted_text or "",
        issue.risk_explanation or "",
        issue.issue_title or "",
    ])

    seen: set = set()
    selected: List[str] = []
    for pattern, component_text in components:
        if component_text in seen:
            continue
        if pattern == ".*" or re.search(pattern, search_text, re.IGNORECASE):
            selected.append(component_text)
            seen.add(component_text)

    return selected


def _build_suggestion(components: List[str]) -> str:
    if not components:
        return ""
    if len(components) == 1:
        return components[0]
    if len(components) == 2:
        return f"{components[0]} and {components[1]}"
    return ", ".join(components[:-1]) + f", and {components[-1]}"


_DEFAULT_COMPONENTS: Dict[str, List[str]] = {
    "indemnification": [
        "Cap liability at a defined monetary amount",
        "Narrow indemnification scope to exclude indirect and consequential damages",
        "Define a clear aggregate cap on total indemnification exposure",
    ],
    "confidentiality": [
        "Define a survival period so confidentiality obligations continue after termination",
        "Specify exceptions to confidential information and post-termination obligations",
    ],
    "limitation of liability": [
        "Define an express aggregate liability cap",
        "Exclude indirect, consequential, and incidental damages",
    ],
    "termination": [
        "Add mutual termination rights with defined notice periods",
        "Specify post-termination obligations and survival of key provisions",
    ],
    "structural inconsistency": [
        "Reconcile conflicting clauses to ensure consistent obligations",
        "Clarify which provision governs in the event of conflict",
    ],
    "governing law": [
        "Define governing law and specify exclusive jurisdiction",
        "Clarify dispute resolution procedures",
    ],
    "jurisdiction": [
        "Define governing law and specify exclusive jurisdiction",
        "Clarify dispute resolution procedures",
    ],
    "residuals": [
        "Clarify residual knowledge does not permit use of confidential information",
        "Ensure confidentiality obligations continue after termination",
    ],
    "enforceability weakness": [
        "Add severability, waiver, and entire agreement clauses",
    ],
    "negotiation imbalance": [
        "Convert unilateral rights to mutual obligations",
        "Ensure remedies apply equally to both parties",
    ],
}


def _build_default_suggestion(category: str) -> str:
    group = _resolve_refinement_group(category)
    components = _DEFAULT_COMPONENTS.get(group, [])
    return _build_suggestion(components) if components else ""


def refine_suggested_improvement(issue: Any) -> str:
    category = issue.category.strip() if issue.category else ""
    current = issue.suggested_improvement.strip() if issue.suggested_improvement else ""

    group = _resolve_refinement_group(category)

    if group not in CATEGORY_RISK_COMPONENTS and group not in CATEGORY_GOOD_KEYWORDS:
        return current

    if not _needs_refinement(current, category):
        return current

    components = _get_relevant_components(issue, category)
    if components:
        refined = _build_suggestion(components)
        logger.info(
            "[Refiner] Category=%s length=%d components=%d -> refined",
            category, len(current), len(components),
        )
        return refined

    default = _build_default_suggestion(category)
    if default:
        logger.info(
            "[Refiner] Category=%s length=%d -> default fallback",
            category, len(current),
        )
        return default

    return current


def refine_suggested_improvements(issues: List[Any]) -> List[Any]:
    for issue in issues:
        if not issue.category:
            continue
        original = issue.suggested_improvement
        refined = refine_suggested_improvement(issue)
        if refined != original:
            issue.suggested_improvement = refined
    return issues
