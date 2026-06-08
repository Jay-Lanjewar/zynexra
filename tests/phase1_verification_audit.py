"""
Verification Audit — Three Highest-Confidence Pipeline Issues.

For each issue:
  1. Reproduce the failure
  2. Identify exact source code line and conditional
  3. Apply minimal patch
  4. Measure before/after delta

Usage:
    python tests/phase1_verification_audit.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.legal_domain_engine import (
    compute_document_domain_confidence,
    compute_non_legal_penalty,
    compute_legal_keyword_ratio,
    compute_contract_structure_score,
    compute_legal_phrase_density,
    NON_LEGAL_PATTERNS_STRONG,
    NON_LEGAL_PATTERNS_WEAK,
    NON_LEGAL_THRESHOLD,
    POSSIBLY_LEGAL_THRESHOLD,
)
from backend.engines.policy_detection_engine import (
    detect_policy_document,
    compute_policy_keyword_score,
    compute_contractual_signal_score,
    compute_policy_structure_score,
    detect_policy_type,
    POLICY_KEYWORD_THRESHOLD,
    CONTRACTUAL_SIGNAL_THRESHOLD,
    POLICY_DOMINANCE_RATIO,
)
from backend.engines.normalization_engine import (
    _apply_mutual_capped_indemnity_suppression,
    AuditIssue,
)

CORPUS_DIR = Path(__file__).resolve().parent / "validation_corpus"


# ---------------------------------------------------------------------------
# 1. NDA-04: Domain Detection Failure
# ---------------------------------------------------------------------------

def investigate_nda04():
    print("=" * 72)
    print("  INVESTIGATION 1: NDA-04 Domain Detection Failure")
    print("=" * 72)

    doc_path = CORPUS_DIR / "NDA-04.txt"
    with open(doc_path) as f:
        text = f.read()

    print(f"\n  Document length: {len(text)} chars")
    print(f"  First 100 chars: {text[:100]}")

    # Reproduce domain detection
    result = compute_document_domain_confidence(text)
    print(f"\n  Domain: {result.domain}")
    print(f"  Effective score: {result.confidence:.4f}")
    print(f"  Legal keyword ratio: {result.legal_keyword_ratio:.4f}")
    print(f"  Structure score: {result.structure_score:.4f}")
    print(f"  Legal phrase density: {result.legal_phrase_density:.4f}")
    print(f"  Non-legal penalty: {result.non_legal_penalty:.4f}")
    print(f"  Thresholds: NON_LEGAL <= {NON_LEGAL_THRESHOLD}, LEGAL >= {POSSIBLY_LEGAL_THRESHOLD}")

    # Step-by-step compute to verify
    legal_signal = (
        result.legal_keyword_ratio * 0.40 +
        result.structure_score * 0.35 +
        result.legal_phrase_density * 0.25
    )
    effective_score = max(0.0, legal_signal - result.non_legal_penalty)
    print(f"\n  Manual legal_signal = {legal_signal:.4f}")
    print(f"  Manual effective_score = {effective_score:.4f}")
    assert abs(effective_score - result.confidence) < 0.001, "Score mismatch"

    # Find which NON_LEGAL patterns match
    print(f"\n  Checking NON_LEGAL patterns...")
    for i, pat in enumerate(NON_LEGAL_PATTERNS_STRONG):
        matches = pat.findall(text)
        if matches:
            print(f"    STRONG pattern {i}: matched {len(matches)} time(s)")
            for m in matches[:5]:
                idx = text.lower().find(m.lower())
                context = text[max(0, idx-20):idx+len(m)+20]
                print(f"      Context: ...{context}...")

    for i, pat in enumerate(NON_LEGAL_PATTERNS_WEAK):
        matches = pat.findall(text)
        if matches:
            print(f"    WEAK pattern {i}: matched {len(matches)} time(s)")
            for m in matches[:5]:
                idx = text.lower().find(m.lower())
                context = text[max(0, idx-20):idx+len(m)+20]
                print(f"      Context: ...{context}...")

    # Check the non-legal penalty manually
    penalty = compute_non_legal_penalty(text)
    print(f"\n  Computed non_legal_penalty: {penalty:.4f}")

    # Check structure score patterns
    print(f"\n  Structure patterns matched:")
    from backend.engines.legal_domain_engine import CONTRACT_STRUCTURE_PATTERNS
    matched = 0
    for i, pat in enumerate(CONTRACT_STRUCTURE_PATTERNS):
        if pat.search(text):
            matched += 1
            idx = text.find(pat.pattern[:20] if len(pat.pattern) > 20 else pat.pattern)
            print(f"    Pattern {i}: {pat.pattern[:60]}...")

    return result


# ---------------------------------------------------------------------------
# 2. EMP-03: Policy Detection Failure
# ---------------------------------------------------------------------------

def investigate_emp03():
    print("\n" + "=" * 72)
    print("  INVESTIGATION 2: EMP-03 Policy Detection Failure")
    print("=" * 72)

    doc_path = CORPUS_DIR / "EMP-03.txt"
    with open(doc_path) as f:
        text = f.read()

    print(f"\n  Document length: {len(text)} chars")
    print(f"  First line: {text.split(chr(10))[0]}")

    # Reproduce policy detection
    result = detect_policy_document(text)
    print(f"\n  Detection: {result.detection}")
    print(f"  Confidence: {result.confidence:.4f}")
    print(f"  Policy type: {result.policy_type}")
    print(f"  Policy keyword score: {result.policy_keyword_score:.4f}")
    print(f"  Contractual signal score: {result.contractual_signal_score:.4f}")
    print(f"  Matched policy keywords: {result.matched_policy_keywords}")
    print(f"  Matched contractual signals: {result.matched_contractual_signals}")
    print(f"  Explanation: {result.explanation}")

    # Step-by-step
    policy_score, matched_pk = compute_policy_keyword_score(text)
    contractual_score, matched_cs = compute_contractual_signal_score(text)
    structure_score = compute_policy_structure_score(text)
    policy_type, type_score, type_keywords = detect_policy_type(text)

    policy_signal = policy_score * 0.40 + structure_score * 0.35 + type_score * 0.25
    effective_signal = max(0.0, policy_signal - contractual_score * 0.5)

    print(f"\n  Policy score: {policy_score:.4f}")
    print(f"  Contractual score: {contractual_score:.4f}")
    print(f"  Structure score: {structure_score:.4f}")
    print(f"  Type score: {type_score:.4f}")
    print(f"  Type: {policy_type}")
    print(f"  Type keywords: {type_keywords}")
    print(f"  Policy signal: {policy_signal:.4f}")
    print(f"  Effective signal: {effective_signal:.4f}")

    print(f"\n  Thresholds:")
    print(f"    POLICY_KEYWORD_THRESHOLD = {POLICY_KEYWORD_THRESHOLD}")
    print(f"    CONTRACTUAL_SIGNAL_THRESHOLD = {CONTRACTUAL_SIGNAL_THRESHOLD}")
    print(f"    POLICY_DOMINANCE_RATIO = {POLICY_DOMINANCE_RATIO}")

    print(f"\n  is_clearly_policy checks:")
    print(f"    policy_signal >= {POLICY_KEYWORD_THRESHOLD}: {policy_signal >= POLICY_KEYWORD_THRESHOLD} ({policy_signal:.4f} >= {POLICY_KEYWORD_THRESHOLD})")
    print(f"    contractual_score < {CONTRACTUAL_SIGNAL_THRESHOLD}: {contractual_score < CONTRACTUAL_SIGNAL_THRESHOLD} ({contractual_score:.4f} < {CONTRACTUAL_SIGNAL_THRESHOLD})")
    ratio = policy_signal / max(contractual_score, 0.001)
    print(f"    ratio >= {POLICY_DOMINANCE_RATIO}: {ratio >= POLICY_DOMINANCE_RATIO} ({ratio:.2f} >= {POLICY_DOMINANCE_RATIO})")

    print(f"\n  is_strongly_policy checks:")
    print(f"    policy_signal >= {POLICY_KEYWORD_THRESHOLD * 2}: {policy_signal >= POLICY_KEYWORD_THRESHOLD * 2} ({policy_signal:.4f} >= {POLICY_KEYWORD_THRESHOLD * 2})")
    print(f"    contractual_score < {CONTRACTUAL_SIGNAL_THRESHOLD * 1.5}: {contractual_score < CONTRACTUAL_SIGNAL_THRESHOLD * 1.5} ({contractual_score:.4f} < {CONTRACTUAL_SIGNAL_THRESHOLD * 1.5})")

    # Check the employment agreement short-circuit regex
    employment_re = re.compile(r"(?im)^\s*EMPLOYMENT\s+(?:AGREEMENT|CONTRACT)\b")
    print(f"\n  Employment short-circuit check:")
    print(f"    Regex: {employment_re.pattern}")
    print(f"    Matches: {bool(employment_re.search(text))}")
    # Check what the line actually looks like
    for line in text.split(chr(10)):
        if "EMPLOYMENT" in line.upper():
            print(f"    Line: {line}")

    return result


# ---------------------------------------------------------------------------
# 3. VEN-01: Mutual-Capped-Indemnity Suppression Failure
# ---------------------------------------------------------------------------

def investigate_ven01():
    print("\n" + "=" * 72)
    print("  INVESTIGATION 3: VEN-01 Mutual-Capped-Indemnity Suppression Failure")
    print("=" * 72)

    doc_path = CORPUS_DIR / "VEN-01.txt"
    with open(doc_path) as f:
        text = f.read()

    full_lower = text.lower()

    print(f"\n  Document length: {len(text)} chars")

    # Test each regex condition
    mutual_re = re.compile(
        r"\b(?:each party\b.*\bindemnif(?:y|ies)\b.*\bthe other|"
        r"mutual indemnit(?:y|ation)|"
        r"both parties\b.*\bindemnif(?:y|ies))",
        re.IGNORECASE
    )
    has_mutual = bool(mutual_re.search(text))
    print(f"\n  Mutual indemnity check (regex): {has_mutual}")

    cap_re = re.compile(
        r"\b(?:liability cap|aggregate cap|capped at|maximum liability|"
        r"shall not exceed|limited to|cap of)\b",
        re.IGNORECASE
    )
    has_cap = bool(cap_re.search(text))
    print(f"  Liability cap check (regex): {has_cap}")

    exclusion_re = re.compile(
        r"\b(?:consequential|indirect)\s+damages\b",
        re.IGNORECASE
    )
    has_exclusion = bool(exclusion_re.search(text))
    print(f"  Exclusion check (regex): {has_exclusion}")

    # Show what each regex actually finds
    print(f"\n  Mutual matches:")
    for m in mutual_re.finditer(text):
        print(f"    '{m.group()[:80]}' at pos {m.start()}")

    print(f"\n  Cap matches:")
    for m in cap_re.finditer(text):
        print(f"    '{m.group()[:80]}' at pos {m.start()}")

    print(f"\n  Exclusion matches:")
    for m in exclusion_re.finditer(text):
        print(f"    '{m.group()[:80]}' at pos {m.start()}")

    # Show the relevant sections
    print(f"\n  Section 6 (liability):")
    sec6_match = re.search(r"6\.\s*LIMITATION OF LIABILITY.*?(?=\n\s*\d+\.|\Z)", text, re.DOTALL | re.IGNORECASE)
    if sec6_match:
        print(f"    {sec6_match.group().strip()[:300]}")

    print(f"\n  Section 7 (indemnification):")
    sec7_match = re.search(r"7\.\s*INDEMNIFICATION.*?(?=\n\s*\d+\.|\Z)", text, re.DOTALL | re.IGNORECASE)
    if sec7_match:
        print(f"    {sec7_match.group().strip()[:300]}")

    # Simulate suppression on a MEDIUM Liability Exposure issue
    test_issues = [
        AuditIssue(
            issue_title="Liability Exposure",
            severity="MEDIUM",
            category="Liability Exposure",
            location="6.",
            quoted_text="Neither party's aggregate liability...shall exceed the total fees paid...",
            risk_explanation="The limitation of liability clause does not include a cap on specific types of damages...",
            suggested_improvement="Agree to a specific monetary cap...",
        )
    ]

    # Check individual suppression conditions
    print(f"\n  Manual suppression condition check:")
    print(f"    Mutual: {has_mutual}")
    print(f"    Cap: {has_cap}")
    print(f"    Exclusion: {has_exclusion}")
    print(f"    All 3 doc conditions: {has_mutual and has_cap and has_exclusion}")

    if not has_mutual:
        print(f"    -> FAILS at mutual check")
    elif not has_cap:
        print(f"    -> FAILS at cap check")
    elif not has_exclusion:
        print(f"    -> FAILS at exclusion check")

    # Run actual suppression
    before = len(test_issues)
    modified = _apply_mutual_capped_indemnity_suppression(test_issues, text)
    after = len(test_issues)
    sev_after = test_issues[0].severity if test_issues else "N/A"
    print(f"\n  Actual suppression result:")
    print(f"    Modified: {modified}")
    print(f"    Severity after: {sev_after}")

    return {
        "has_mutual": has_mutual,
        "has_cap": has_cap,
        "has_exclusion": has_exclusion,
        "modified": modified,
    }


if __name__ == "__main__":
    r1 = investigate_nda04()
    r2 = investigate_emp03()
    r3 = investigate_ven01()
