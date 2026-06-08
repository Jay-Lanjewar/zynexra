"""
Confidence Design Simulation v2
Uses ONLY signals available at confidence time (no ground truth).
"""
import json
import re
import math
from pathlib import Path

CORPUS_DIR = Path("tests/validation_corpus")

RUN_FILES = [
    "phase1_results_20260603_194028.json",
    "phase1_results_20260603_194859.json",
    "phase1_results_20260603_195714.json",
]

review_data = {}
for f in CORPUS_DIR.glob("*.review.json"):
    doc_id = f.stem.replace(".review", "")
    with open(f) as fh:
        review_data[doc_id] = json.load(fh)


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def spearmanr(x, y):
    n = len(x)
    if n < 2:
        return 0.0, 1.0
    def rank_data(data):
        sorted_indices = sorted(range(n), key=lambda i: data[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and data[sorted_indices[j]] == data[sorted_indices[j + 1]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[sorted_indices[k]] = avg_rank
            i = j + 1
        return ranks
    rx = rank_data(x)
    ry = rank_data(y)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    std_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))
    if std_x == 0 or std_y == 0:
        return 0.0, 1.0
    rho = cov / (std_x * std_y)
    if abs(rho) >= 1.0:
        pval = 0.0
    else:
        t = rho * math.sqrt((n - 2) / (1 - rho ** 2))
        pval = min(1.0, 2 * math.exp(-0.5 * abs(t)))
    return rho, pval


def kendalltau(x, y):
    n = len(x)
    if n < 2:
        return 0.0, 1.0
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx * dy > 0:
                concordant += 1
            elif dx * dy < 0:
                discordant += 1
    tau = (concordant - discordant) / (concordant + discordant) if (concordant + discordant) > 0 else 0
    pval = min(1.0, 2 * math.exp(-0.5 * abs(tau) * math.sqrt(n)))
    return tau, pval


# =========================================================================
# CURRENT SCORER
# =========================================================================
def current_confidence(doc_result):
    raw = doc_result.get("raw_response", {})
    issues = raw.get("issues", [])
    meta = raw.get("metadata", {})
    
    parse_ok = not raw.get("structured_parse_failed", True)
    parse_score = 1.0 if parse_ok else 0.0
    
    issue_count = len(issues)
    if issue_count == 0:
        completeness = 0.3
    else:
        has_titles = any(i.get("issue_title") for i in issues)
        has_sev = any(i.get("severity") for i in issues)
        has_qt = any(i.get("quoted_text") for i in issues)
        present = sum([has_titles, has_sev, has_qt])
        completeness = clamp(0.4 + (present / 3) * 0.6)
    
    domain_conf = meta.get("domain_confidence", 0.3)
    consistency = clamp(domain_conf * 2.5)
    
    duplicate_score = 1.0
    refusal_score = 1.0
    length_score = 1.0
    
    WEIGHTS = {
        "structured_parse_success": 0.25,
        "issue_completeness": 0.20,
        "internal_consistency": 0.20,
        "duplicate_suppression": 0.10,
        "refusal_absent": 0.15,
        "response_length": 0.10,
    }
    
    base = (
        parse_score * WEIGHTS["structured_parse_success"]
        + completeness * WEIGHTS["issue_completeness"]
        + consistency * WEIGHTS["internal_consistency"]
        + duplicate_score * WEIGHTS["duplicate_suppression"]
        + refusal_score * WEIGHTS["refusal_absent"]
        + length_score * WEIGHTS["response_length"]
    )
    
    penalty_mult = 1.0
    if meta.get("policy_detection") not in ("NOT_POLICY", "UNKNOWN"):
        penalty_mult *= 0.30
    if meta.get("domain") == "NON_LEGAL":
        penalty_mult *= 0.30
    
    return clamp(base) * penalty_mult


# =========================================================================
# PROPOSED SCORER v2 (production-available signals only)
# =========================================================================
def proposed_confidence_v2(doc_result):
    """
    Confidence scorer using ONLY signals available at confidence time.
    No ground truth required.
    """
    raw = doc_result.get("raw_response", {})
    issues = raw.get("issues", [])
    meta = raw.get("metadata", {})
    gt_count = doc_result.get("gt_count", 0)  # only for simulation, not used in scoring
    
    # === SIGNAL 1: Parse Success ===
    parse_ok = not raw.get("structured_parse_failed", True)
    parse_score = 1.0 if parse_ok else 0.0
    
    # === SIGNAL 2: Quoted Text Context Match ===
    # Does quoted_text actually appear in the document?
    # This is the STRONGEST proxy for accuracy available at confidence time.
    doc_text = raw.get("legacy_text", "").lower()
    if not doc_text:
        doc_text = ""
    
    qt_matches = 0
    qt_total = 0
    for issue in issues:
        qt = (issue.get("quoted_text", "") or "").lower().strip()
        qt_total += 1
        if len(qt) < 20:
            qt_matches += 1  # short quotes are assumed correct
        elif qt in doc_text:
            qt_matches += 1
        else:
            truncated = qt[:40]
            if truncated in doc_text:
                qt_matches += 0.5
    
    qt_match_rate = qt_matches / qt_total if qt_total > 0 else 0.5
    
    # === SIGNAL 3: Category Validity ===
    valid_categories = {
        "Enforceability Weakness", "Liability Exposure", "Indemnification",
        "Governing Law", "Negotiation Imbalance", "Confidentiality Risk",
        "Termination Risk", "Intellectual Property", "Residuals",
        "Structural Inconsistency", "Compliance Risk", "Privacy Risk",
        "Force Majeure", "Dispute Resolution", "Payment Terms",
        "Non-Compete",
    }
    categories = [i.get("category", "") for i in issues]
    valid_count = sum(1 for c in categories if c in valid_categories)
    category_validity = valid_count / len(categories) if categories else 0.5
    
    # === SIGNAL 4: Severity Distribution ===
    # Models tend to assign correct severity to correct findings.
    # LOW severity on all findings suggests low confidence.
    severity_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    sev_scores = [severity_map.get(i.get("severity", "MEDIUM"), 1) for i in issues]
    avg_sev = sum(sev_scores) / len(sev_scores) if sev_scores else 1
    # Scale: avg severity 1.5 (MEDIUM-HIGH) = full credit
    severity_signal = clamp(avg_sev / 2.0)
    
    # === SIGNAL 5: Issue Count vs Document Complexity ===
    # Longer documents with more clauses should have more findings.
    word_count = len(doc_text.split())
    # Simple heuristic: ~1 finding per 500 words for legal docs
    expected_findings = max(1, word_count / 500)
    issue_count = len(issues)
    count_ratio = issue_count / expected_findings if expected_findings > 0 else 1
    # Over-finding is worse than under-finding
    count_signal = clamp(1.0 - abs(count_ratio - 1.0) * 0.3)
    
    # === SIGNAL 6: Domain Score ===
    domain_conf = meta.get("domain_confidence", 0.3)
    domain = meta.get("domain", "LEGAL")
    # LEGAL docs with high confidence = more reliable findings
    if domain == "LEGAL":
        domain_signal = clamp(0.5 + domain_conf)
    elif domain == "POSSIBLY_LEGAL":
        domain_signal = clamp(0.3 + domain_conf)
    else:
        domain_signal = 0.2
    
    # === SIGNAL 7: Policy Penalty ===
    policy_detect = meta.get("policy_detection", "UNKNOWN")
    is_policy = policy_detect not in ("NOT_POLICY", "UNKNOWN")
    
    # === SIGNAL 8: Cross-Clause Coherence ===
    # Multiple issues from different parts of the document = more reliable
    locations = [i.get("location", "") for i in issues]
    unique_locations = len(set(loc for loc in locations if loc))
    coherence = clamp(unique_locations / max(len(issues), 1))
    
    # === SIGNAL 9: Explanation Quality ===
    # Longer, more detailed explanations suggest more thorough analysis
    exp_lengths = [len(i.get("risk_explanation", "")) for i in issues]
    avg_exp_len = sum(exp_lengths) / len(exp_lengths) if exp_lengths else 0
    explanation_quality = clamp(avg_exp_len / 500)
    
    # === SIGNAL 10: Suggested Improvement Specificity ===
    # Specific improvements (with action verbs) suggest better understanding
    improvement_lengths = [len(i.get("suggested_improvement", "")) for i in issues]
    avg_imp_len = sum(improvement_lengths) / len(improvement_lengths) if improvement_lengths else 0
    improvement_quality = clamp(avg_imp_len / 400)
    
    # === WEIGHTS ===
    WEIGHTS = {
        "parse_success": 0.08,          # process baseline
        "qt_match_rate": 0.30,          # STRONGEST accuracy proxy
        "category_validity": 0.12,      # accuracy proxy
        "severity_signal": 0.05,        # weak accuracy proxy
        "count_signal": 0.08,           # document complexity match
        "domain_signal": 0.07,          # context quality
        "coherence": 0.08,              # cross-clause quality
        "explanation_quality": 0.12,    # analysis depth
        "improvement_quality": 0.10,    # actionable specificity
    }
    
    base = (
        parse_score * WEIGHTS["parse_success"]
        + qt_match_rate * WEIGHTS["qt_match_rate"]
        + category_validity * WEIGHTS["category_validity"]
        + severity_signal * WEIGHTS["severity_signal"]
        + count_signal * WEIGHTS["count_signal"]
        + domain_signal * WEIGHTS["domain_signal"]
        + coherence * WEIGHTS["coherence"]
        + explanation_quality * WEIGHTS["explanation_quality"]
        + improvement_quality * WEIGHTS["improvement_quality"]
    )
    
    # Penalties
    penalty_mult = 1.0
    if is_policy:
        penalty_mult *= 0.50
    
    score = clamp(base) * penalty_mult
    
    # Floor/ceiling based on parse
    if not parse_ok:
        score = min(score, 0.25)
    
    factors = {
        "parse_score": parse_score,
        "qt_match_rate": qt_match_rate,
        "category_validity": category_validity,
        "severity_signal": severity_signal,
        "count_signal": count_signal,
        "domain_signal": domain_signal,
        "coherence": coherence,
        "explanation_quality": explanation_quality,
        "improvement_quality": improvement_quality,
        "penalty_mult": penalty_mult,
    }
    
    return score, factors


def main():
    all_results = []
    for run_file in RUN_FILES:
        with open(CORPUS_DIR / run_file) as f:
            data = json.load(f)
        for doc in data["per_document"]:
            all_results.append(doc)
    
    print(f"Loaded {len(all_results)} document results from {len(RUN_FILES)} runs")
    
    current_scores = []
    proposed_scores = []
    labels = []
    
    for doc in all_results:
        c_score = current_confidence(doc)
        p_score, _ = proposed_confidence_v2(doc)
        current_scores.append(c_score)
        proposed_scores.append(p_score)
        labels.append(1 if doc["pass"] else 0)
    
    # =========================================================================
    # CURRENT SCORER
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  CURRENT SCORER (baseline)")
    print(f"{'='*72}")
    
    pass_scores = [s for s, l in zip(current_scores, labels) if l == 1]
    fail_scores = [s for s, l in zip(current_scores, labels) if l == 0]
    
    print(f"  PASS avg: {sum(pass_scores)/len(pass_scores):.4f}" if pass_scores else "  PASS avg: N/A")
    print(f"  FAIL avg: {sum(fail_scores)/len(fail_scores):.4f}" if fail_scores else "  FAIL avg: N/A")
    print(f"  Dynamic range: {max(current_scores) - min(current_scores):.4f}")
    print(f"  Min: {min(current_scores):.4f}, Max: {max(current_scores):.4f}")
    
    rho, pval = spearmanr(current_scores, labels)
    print(f"  Spearman rho: {rho:.4f} (p={pval:.4f})")
    tau, pval_tau = kendalltau(current_scores, labels)
    print(f"  Kendall tau: {tau:.4f} (p={pval_tau:.4f})")
    
    # =========================================================================
    # PROPOSED SCORER v2
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  PROPOSED SCORER v2 (production-available signals)")
    print(f"{'='*72}")
    
    pass_scores_p = [s for s, l in zip(proposed_scores, labels) if l == 1]
    fail_scores_p = [s for s, l in zip(proposed_scores, labels) if l == 0]
    
    print(f"  PASS avg: {sum(pass_scores_p)/len(pass_scores_p):.4f}" if pass_scores_p else "  PASS avg: N/A")
    print(f"  FAIL avg: {sum(fail_scores_p)/len(fail_scores_p):.4f}" if fail_scores_p else "  FAIL avg: N/A")
    print(f"  Dynamic range: {max(proposed_scores) - min(proposed_scores):.4f}")
    print(f"  Min: {min(proposed_scores):.4f}, Max: {max(proposed_scores):.4f}")
    
    rho_p, pval_p = spearmanr(proposed_scores, labels)
    print(f"  Spearman rho: {rho_p:.4f} (p={pval_p:.4f})")
    tau_p, pval_tau_p = kendalltau(proposed_scores, labels)
    print(f"  Kendall tau: {tau_p:.4f} (p={pval_tau_p:.4f})")
    
    # =========================================================================
    # COMPARISON TABLE
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  SIDE-BY-SIDE COMPARISON")
    print(f"{'='*72}")
    
    print(f"\n  {'Doc':<10} {'Pass':>5} {'GT':>3} {'TP':>3} {'FP':>3} {'FN':>3} {'Current':>8} {'Proposed':>8} {'Delta':>8}")
    print(f"  {'-'*10} {'-'*5} {'-'*3} {'-'*3} {'-'*3} {'-'*3} {'-'*8} {'-'*8} {'-'*8}")
    
    for doc, c, p in zip(all_results, current_scores, proposed_scores):
        d = p - c
        print(f"  {doc['doc_id']:<10} {str(doc['pass']):>5} {doc['gt_count']:>3} {doc['tp']:>3} {doc['fp']:>3} {doc['fn']:>3} {c:>8.3f} {p:>8.3f} {d:>+8.3f}")
    
    # =========================================================================
    # PER-FACTOR BREAKDOWN (unique docs only)
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  PROPOSED SCORER: PER-FACTOR BREAKDOWN (Run 1)")
    print(f"{'='*72}")
    
    for doc, p_score in zip(all_results[:10], proposed_scores[:10]):
        _, factors = proposed_confidence_v2(doc)
        print(f"\n  {doc['doc_id']} (pass={doc['pass']}):")
        for k, v in factors.items():
            print(f"    {k:<25} = {v:.4f}")
        print(f"    {'FINAL':<25} = {p_score:.4f}")
    
    # =========================================================================
    # LABEL DISTRIBUTION
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  LABEL DISTRIBUTION (PROPOSED)")
    print(f"{'='*72}")
    
    high = sum(1 for s in proposed_scores if s >= 0.75)
    medium = sum(1 for s in proposed_scores if 0.45 <= s < 0.75)
    low = sum(1 for s in proposed_scores if s < 0.45)
    print(f"  HIGH (>=0.75): {high}")
    print(f"  MEDIUM (0.45-0.75): {medium}")
    print(f"  LOW (<0.45): {low}")
    
    # =========================================================================
    # DISCRIMINATION ANALYSIS
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  DISCRIMINATION ANALYSIS")
    print(f"{'='*72}")
    
    pass_total = sum(labels)
    fail_total = len(labels) - pass_total
    
    pass_high = sum(1 for s, l in zip(proposed_scores, labels) if l == 1 and s >= 0.75)
    pass_medium = sum(1 for s, l in zip(proposed_scores, labels) if l == 1 and 0.45 <= s < 0.75)
    pass_low = sum(1 for s, l in zip(proposed_scores, labels) if l == 1 and s < 0.45)
    
    fail_high = sum(1 for s, l in zip(proposed_scores, labels) if l == 0 and s >= 0.75)
    fail_medium = sum(1 for s, l in zip(proposed_scores, labels) if l == 0 and 0.45 <= s < 0.75)
    fail_low = sum(1 for s, l in zip(proposed_scores, labels) if l == 0 and s < 0.45)
    
    print(f"  PASS docs -> HIGH: {pass_high}/{pass_total} | MEDIUM: {pass_medium}/{pass_total} | LOW: {pass_low}/{pass_total}")
    print(f"  FAIL docs -> HIGH: {fail_high}/{fail_total} | MEDIUM: {fail_medium}/{fail_total} | LOW: {fail_low}/{fail_total}")
    
    # Inversions
    inversions = 0
    for i in range(len(proposed_scores)):
        for j in range(i+1, len(proposed_scores)):
            if labels[i] == 1 and labels[j] == 0:
                if proposed_scores[i] < proposed_scores[j]:
                    inversions += 1
            elif labels[i] == 0 and labels[j] == 1:
                if proposed_scores[i] > proposed_scores[j]:
                    inversions += 1
    print(f"  Score inversions (PASS < FAIL): {inversions}")
    
    # =========================================================================
    # KEY INSIGHT
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  KEY INSIGHT")
    print(f"{'='*72}")
    print(f"""
  The proposed scorer uses ONLY production-available signals:
  - quoted_text context match (STRONGEST proxy — does the quote exist in the doc?)
  - category validity (are categories from the allowed set?)
  - explanation/improvement quality (analysis depth)
  - domain score (document classification quality)
  - cross-clause coherence (multiple locations = more thorough)
  
  It does NOT use:
  - TP/FP/FN (requires ground truth)
  - precision/recall (requires ground truth)
  - title accuracy (requires ground truth)
  
  The quoted_text context match is the single strongest signal because:
  1. If the model quotes text that exists in the document, the finding is likely real
  2. If the model fabricates a quote, the finding is likely false
  3. This is verifiable at confidence time without ground truth
  
  Current scorer weakness: 6/6 factors measure PROCESS, not ACCURACY.
  Proposed scorer strength: 7/9 factors measure ACCURACY proxies.
""")


if __name__ == "__main__":
    main()
