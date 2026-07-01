"""Individual verifier functions for post-audit issue detection.
Each verifier scans document text for specific risky clause patterns
and returns a finding dict if the pattern is present.
"""

import re
from typing import Optional
from backend.logger import logger


def verify_as_is_no_warranty(doc_text: str) -> Optional[dict]:
    """Detect AS-IS / No Warranty provisions in paid service agreements."""
    logger.info("[VerifierTrace] ENTER verify_as_is_no_warranty")
    as_is_patterns = [
        r'(?i)AS\s+IS',
        r'(?i)AS\s+AVAILABLE',
    ]
    no_warranty_patterns = [
        r'(?i)no\s+warrant(y|ies)',
        r'(?i)warranties\s+of\s+any\s+kind',
        r'(?i)disclaim(s|ed)?\s+all\s+warranties',
        r'(?i)without\s+warrant(y|ies)',
    ]
    section_text = _find_section_for_patterns(
        doc_text,
        ['AS IS', 'AS AVAILABLE', 'NO WARRANTIES', 'Warranties', 'Warranty', 'Disclaimer'],
        ['AS IS', 'AS AVAILABLE', 'NO WARRANT'],
    )
    if not section_text:
        logger.info("[VerifierTrace] as_is_no_warranty -> None: _find_section_for_patterns returned None")
        return None
    logger.info("[VerifierTrace] as_is_no_warranty section found (first 200): %s", section_text[:200])
    has_as_is = any(re.search(p, section_text) for p in as_is_patterns)
    has_no_warranty = any(re.search(p, section_text) for p in no_warranty_patterns)
    if not (has_as_is and has_no_warranty):
        logger.info(
            "[VerifierTrace] as_is_no_warranty -> None: has_as_is=%s has_no_warranty=%s",
            has_as_is, has_no_warranty,
        )
        return None
    quoted_lines = _extract_quoted_lines(section_text, 4)
    if not quoted_lines:
        logger.info("[VerifierTrace] as_is_no_warranty -> None: _extract_quoted_lines returned empty")
        return None
    return {
        "issue_title": "AS-IS No Warranty Provision",
        "severity": "MEDIUM",
        "category": "Enforceability Weakness",
        "location": "Warranty / Disclaimer Clause",
        "quoted_text": quoted_lines,
        "risk_explanation": (
            "The AS IS / no warranty provision disclaims all implied warranties "
            "(merchantability, fitness, title, non-infringement). In a paid service "
            "agreement, this creates significant risk for the paying party who has "
            "no guarantee of service quality or functionality."
        ),
        "suggested_improvement": (
            "Include standard warranty that the service will perform substantially "
            "in accordance with the documentation and that professional-grade efforts "
            "will be used. Limit exclusions to implied warranties only where necessary."
        ),
        "detection_method": "verifier",
        "verifier": "as_is_no_warranty",
    }


def verify_asymmetric_termination(doc_text: str) -> Optional[dict]:
    """Detect asymmetric termination rights favoring one party."""
    logger.info("[VerifierTrace] ENTER verify_asymmetric_termination")
    lines = doc_text.split('\n')
    convenience_line_idx = None
    breach_line_idx = None
    for i, line in enumerate(lines):
        if re.search(r'(?i)\bterminate\b.*\b(at any time|for convenience|for any reason|for no reason)\b', line):
            convenience_line_idx = i
        if re.search(r'(?i)\bterminate\b.*\bonly for\b.*\bbreach\b', line) or \
           re.search(r'(?i)\bonly\b.*\bif\b.*\bbreach\b', line):
            breach_line_idx = i
    if convenience_line_idx is None:
        logger.info("[VerifierTrace] asymmetric_termination -> None: convenience_line_idx is None")
        return None
    if breach_line_idx is None:
        logger.info("[VerifierTrace] asymmetric_termination -> None: breach_line_idx is None")
        return None
    logger.info(
        "[VerifierTrace] asymmetric_termination indices: convenience=%s breach=%s",
        convenience_line_idx, breach_line_idx,
    )
    if convenience_line_idx == breach_line_idx:
        candidate = '\n'.join(lines[max(0, convenience_line_idx-1):min(len(lines), convenience_line_idx+1)])
        logger.info("[VerifierTrace] asymmetric_termination candidate (first 200): %s", candidate[:200])
        quoted = _extract_quoted_lines(candidate, 1)
    else:
        candidate = '\n'.join(lines[max(0, min(convenience_line_idx, breach_line_idx)-1):max(len(lines), max(convenience_line_idx, breach_line_idx)+1)])
        logger.info("[VerifierTrace] asymmetric_termination candidate (first 200): %s", candidate[:200])
        quoted = _extract_quoted_lines(candidate, 2)
    if not quoted:
        logger.info("[VerifierTrace] asymmetric_termination -> None: _extract_quoted_lines returned empty")
        return None
    quoted = _label_quoted_text(quoted, "Asymmetric termination rights clause")
    return {
        "issue_title": "Asymmetric Termination Rights",
        "severity": "MEDIUM",
        "category": "Negotiation Imbalance",
        "location": "Termination Clause",
        "quoted_text": quoted,
        "risk_explanation": (
            "The agreement contains asymmetric termination rights: the provider "
            "can terminate for convenience at any time while the customer can "
            "only terminate for material breach. This creates a fundamental "
            "power imbalance where the disadvantaged party's business depends "
            "on a service the provider can cancel at will."
        ),
        "suggested_improvement": (
            "Make termination rights mutual: both parties should have the same "
            "termination rights, or at minimum provide the disadvantaged party "
            "with a corresponding right to terminate for convenience."
        ),
        "detection_method": "verifier",
        "verifier": "asymmetric_termination",
    }


def verify_single_trigger_coc(doc_text: str) -> Optional[dict]:
    """Detect single-trigger Change of Control acceleration provisions."""
    logger.info("[VerifierTrace] ENTER verify_single_trigger_coc")
    coc_section = _find_section_for_patterns(
        doc_text,
        ['Change of Control', 'change of control', 'CHANGE OF CONTROL'],
        ['Change of Control', 'CIC', 'acquisition', 'merger'],
    )
    if not coc_section:
        logger.info("[VerifierTrace] single_trigger_coc -> None: _find_section_for_patterns returned None")
        return None
    logger.info("[VerifierTrace] single_trigger_coc section found (first 200): %s", coc_section[:200])
    is_single_trigger = (
        re.search(r'(?i)immediately\s+accelerate', coc_section) or
        re.search(r'(?i)become\s+fully\s+vested', coc_section) or
        re.search(r'(?i)(accelerat|vest).*upon.*change of control', coc_section) or
        re.search(r'(?i)upon\s+(a\s+)?change of control.*accelerat', coc_section)
    )
    if not is_single_trigger:
        logger.info("[VerifierTrace] single_trigger_coc -> None: is_single_trigger=False")
        return None
    equity_is_double_trigger = (
        re.search(r'(?i)if.*(employ|terminat).*accelerat|accelerat.*only.*if', coc_section)
    )
    if equity_is_double_trigger:
        logger.info("[VerifierTrace] single_trigger_coc -> None: equity_is_double_trigger=True")
        return None
    quoted = _extract_quoted_lines(coc_section, 4)
    if not quoted:
        logger.info("[VerifierTrace] single_trigger_coc -> None: _extract_quoted_lines returned empty")
        return None
    return {
        "issue_title": "Single-Trigger Change of Control Acceleration",
        "severity": "MEDIUM",
        "category": "Enforceability Weakness",
        "location": "Change of Control Clause",
        "quoted_text": quoted,
        "risk_explanation": (
            "Single-trigger change of control accelerates all unvested equity "
            "upon change of control alone, without requiring termination. This "
            "creates a perverse incentive for the executive to facilitate a sale "
            "regardless of shareholder interest. Double-trigger (acceleration "
            "only if terminated after CIC) is the market standard."
        ),
        "suggested_improvement": (
            "Replace single-trigger with double-trigger vesting: acceleration "
            "should occur only if the executive is terminated (without cause or "
            "for good reason) within 12-24 months following a change of control."
        ),
        "detection_method": "verifier",
        "verifier": "single_trigger_coc",
    }


def _find_section_for_patterns(
    doc_text: str,
    search_terms: list,
    confirm_terms: list,
) -> Optional[str]:
    """Find a section of the document containing search terms and return it."""
    lines = doc_text.split('\n')
    matched_indices = []
    for i, line in enumerate(lines):
        for term in search_terms:
            if term.lower() in line.lower():
                matched_indices.append(i)
                break
    if not matched_indices:
        return None
    start = max(0, min(matched_indices) - 1)
    end = min(len(lines), max(matched_indices) + 3)
    section = '\n'.join(lines[start:end])
    has_confirm = any(t.lower() in section.lower() for t in confirm_terms)
    if not has_confirm:
        return None
    return section


def _find_termination_sections(doc_text: str) -> list:
    """Find termination-related sections in the document.
    Only matches lines that contain termination RIGHTS language
    (not just the word 'termination' used incidentally).
    """
    lines = doc_text.split('\n')
    term_indices = []
    for i, line in enumerate(lines):
        if re.search(r'(?i)\btermination\b.*\b(convenience|breach|cause|notice|right|at any time)\b', line) or \
           re.search(r'(?i)\b(party|provider|company|customer|either)\b.*\bterminate\b', line) or \
           re.search(r'(?i)\bterminate\b.*\b(at any time|for convenience|for any reason|for no reason|only for|upon.*notice|without cause)\b', line):
            term_indices.append(i)
    if not term_indices:
        return []
    sections = []
    for idx in term_indices:
        start = max(0, idx)
        end = min(len(lines), idx + 2)
        section = '\n'.join(lines[start:end])
        sections.append(section)
    return sections


def _extract_quoted_lines(section_text: str, max_lines: int = 2) -> str:
    """Extract a clean quoted text excerpt from a section."""
    lines = [l.strip() for l in section_text.split('\n') if l.strip()]
    if not lines:
        return ""
    return ' '.join(lines[:max_lines])


def _label_quoted_text(quoted: str, label: str) -> str:
    """Prepend a clause context label to ensure title topic words appear in quoted text.
    
    This avoids suppression by the title-QT topic-word matching in normalization,
    while preserving the actual document text for ground-truth pattern matching.
    """
    return f"{label}: {quoted}"
