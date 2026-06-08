"""
Correctness-Score Design Audit
Evaluates 5+ candidate formulas for continuous correctness = f(TP, FP, FN).
Recomputes confidence correlation using both binary PASS/FAIL and continuous correctness.
"""
import json
import math
from pathlib import Path

CORPUS_DIR = Path("tests/validation_corpus")

RUN_FILES = [
    "phase1_results_20260603_194028.json",
    "phase1_results_20260603_194859.json",
    "phase1_results_20260603_195714.json",
]


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
# CANDIDATE CORRECTNESS FORMULAS
# =========================================================================

def f1_correctness(tp, fp, fn):
    """F1 score: harmonic mean of precision and recall."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def f2_correctness(tp, fp, fn):
    """F2 score: recall-weighted harmonic mean (recall 2x more important than precision)."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    if precision + recall == 0:
        return 0.0
    return (1 + 4) * precision * recall / (4 * precision + recall)


def weighted_correctness(tp, fp, fn, gt_count):
    """Weighted correctness: TP/TP_total minus FP/FN penalties.
    
    Rationale:
    - TP gets full credit (finding correct issues)
    - FP gets partial penalty (false findings are bad but not catastrophic)
    - FN gets heavy penalty (missing issues is worse than false positives)
    - gt_count normalizes for document complexity
    """
    if gt_count == 0:
        # No GT issues: any finding is FP
        return 0.0 if fp > 0 else 1.0
    
    tp_score = tp / gt_count
    fp_penalty = fp * 0.15  # moderate penalty per FP
    fn_penalty = fn * 0.35  # heavy penalty per FN (missing issues is worse)
    
    raw = tp_score - fp_penalty - fn_penalty
    return clamp(raw)


def precision_recall_composite(tp, fp, fn):
    """Precision-recall composite with asymmetric penalties.
    
    Rationale:
    - Precision and recall are equally weighted
    - FP penalty: 0.2 per false positive (moderate)
    - FN penalty: 0.3 per false negative (heavier)
    """
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    # Asymmetric penalties
    fp_penalty = fp * 0.05  # per-FP penalty scaled down
    fn_penalty = fn * 0.10  # per-FN penalty (2x FP)
    
    raw = precision * 0.5 + recall * 0.5 - fp_penalty - fn_penalty
    return clamp(raw)


def jaccard_correctness(tp, fp, fn):
    """Jaccard-inspired correctness: TP / (TP + FP + FN).
    
    Rationale:
    - Simple intersection-over-union
    - TP counts in both numerator and denominator
    - FP and FN are equally penalized
    """
    total = tp + fp + fn
    if total == 0:
        return 1.0  # no issues found, no issues expected
    return tp / total


def completeness_penalized(tp, fp, fn, gt_count):
    """Completeness with FP/FN penalties.
    
    Rationale:
    - Start with completeness (TP/gt_count)
    - Penalize for FP (false findings reduce quality)
    - Penalize for FN (missing findings reduce quality)
    - Bonus for matching count exactly
    """
    if gt_count == 0:
        return 0.0 if fp > 0 else 1.0
    
    completeness = tp / gt_count
    fp_rate = fp / (tp + fp) if (tp + fp) > 0 else 0
    fn_rate = fn / gt_count
    
    # Penalties
    fp_penalty = fp_rate * 0.25
    fn_penalty = fn_rate * 0.35
    
    # Bonus for exact count match
    count_bonus = 0.1 if (tp + fp) == gt_count else 0
    
    raw = completeness - fp_penalty - fn_penalty + count_bonus
    return clamp(raw)


def severity_weighted(tp, fp, fn, gt_count, issues, gt_issues):
    """Severity-weighted correctness: weight TP by severity match.
    
    Rationale:
    - Finding the right issue with the right severity is worth more
    - Finding the right issue with wrong severity is worth less
    - FP and FN penalized as usual
    """
    if gt_count == 0:
        return 0.0 if fp > 0 else 1.0
    
    # Simplified: assume severity accuracy from doc result
    # (we don't have per-issue matching here, so use doc-level severity_accuracy)
    severity_accuracy = 1.0  # placeholder
    
    tp_score = (tp / gt_count) * severity_accuracy
    fp_penalty = fp * 0.15
    fn_penalty = fn * 0.35
    
    raw = tp_score - fp_penalty - fn_penalty
    return clamp(raw)


# =========================================================================
# MAIN ANALYSIS
# =========================================================================
def main():
    # Load all results
    all_results = []
    for run_file in RUN_FILES:
        with open(CORPUS_DIR / run_file) as f:
            data = json.load(f)
        for doc in data["per_document"]:
            all_results.append(doc)
    
    print(f"Loaded {len(all_results)} document results from {len(RUN_FILES)} runs")
    print(f"Unique docs: {len(set(d['doc_id'] for d in all_results))}")
    
    # Compute correctness scores for each formula
    formulas = {
        "F1": lambda d: f1_correctness(d["tp"], d["fp"], d["fn"]),
        "F2": lambda d: f2_correctness(d["tp"], d["fp"], d["fn"]),
        "Weighted": lambda d: weighted_correctness(d["tp"], d["fp"], d["fn"], d["gt_count"]),
        "PR_Composite": lambda d: precision_recall_composite(d["tp"], d["fp"], d["fn"]),
        "Jaccard": lambda d: jaccard_correctness(d["tp"], d["fp"], d["fn"]),
        "Completeness": lambda d: completeness_penalized(d["tp"], d["fp"], d["fn"], d["gt_count"]),
    }
    
    # Compute confidence scores (current scorer)
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
    
    # Compute all scores
    confidence_scores = [current_confidence(d) for d in all_results]
    binary_labels = [1 if d["pass"] else 0 for d in all_results]
    
    correctness_scores = {}
    for name, formula in formulas.items():
        correctness_scores[name] = [formula(d) for d in all_results]
    
    # =========================================================================
    # PART 1: CORRECTNESS FORMULA EVALUATION
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  PART 1: CORRECTNESS FORMULA EVALUATION")
    print(f"{'='*72}")
    
    # For each formula, show distribution and correlation with binary PASS/FAIL
    print(f"\n  {'Formula':<15} {'Min':>6} {'Max':>6} {'Range':>6} {'Mean':>6} {'Std':>6} {'rho(PASS)':>10}")
    print(f"  {'-'*15} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*10}")
    
    for name, scores in correctness_scores.items():
        min_s = min(scores)
        max_s = max(scores)
        mean_s = sum(scores) / len(scores)
        std_s = math.sqrt(sum((s - mean_s) ** 2 for s in scores) / len(scores))
        rho, _ = spearmanr(scores, binary_labels)
        print(f"  {name:<15} {min_s:>6.3f} {max_s:>6.3f} {max_s-min_s:>6.3f} {mean_s:>6.3f} {std_s:>6.3f} {rho:>+8.4f}")
    
    # Show binary PASS/FAIL for reference
    print(f"\n  {'Binary':<15} {'Min':>6} {'Max':>6} {'Range':>6} {'Mean':>6} {'Std':>6}")
    print(f"  {'-'*15} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    mean_b = sum(binary_labels) / len(binary_labels)
    std_b = math.sqrt(sum((b - mean_b) ** 2 for b in binary_labels) / len(binary_labels))
    print(f"  {'PASS/FAIL':<15} {min(binary_labels):>6} {max(binary_labels):>6} {max(binary_labels)-min(binary_labels):>6} {mean_b:>6.3f} {std_b:>6.3f}")
    
    # =========================================================================
    # PART 2: CONFIDENCE CORRELATION COMPARISON
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  PART 2: CONFIDENCE CORRELATION (binary vs continuous)")
    print(f"{'='*72}")
    
    print(f"\n  Target: Spearman rho (confidence vs correctness)")
    print(f"  Higher = better calibration")
    
    print(f"\n  {'Target':<15} {'Spearman':>10} {'Kendall':>10} {'PASS avg':>10} {'FAIL avg':>10} {'Range':>10}")
    print(f"  {'-'*15} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    
    # Binary PASS/FAIL
    rho_b, _ = spearmanr(confidence_scores, binary_labels)
    tau_b, _ = kendalltau(confidence_scores, binary_labels)
    pass_avg_b = sum(s for s, l in zip(confidence_scores, binary_labels) if l == 1) / max(1, sum(binary_labels))
    fail_avg_b = sum(s for s, l in zip(confidence_scores, binary_labels) if l == 0) / max(1, len(binary_labels) - sum(binary_labels))
    print(f"  {'PASS/FAIL':<15} {rho_b:>+10.4f} {tau_b:>+10.4f} {pass_avg_b:>10.4f} {fail_avg_b:>10.4f} {pass_avg_b-fail_avg_b:>+10.4f}")
    
    # Each continuous correctness formula
    for name, scores in correctness_scores.items():
        rho_c, _ = spearmanr(confidence_scores, scores)
        tau_c, _ = kendalltau(confidence_scores, scores)
        
        # Split by "high correctness" vs "low correctness" using median
        median_c = sorted(scores)[len(scores) // 2]
        high_avg = sum(s for s, c in zip(confidence_scores, scores) if c >= median_c) / max(1, sum(1 for c in scores if c >= median_c))
        low_avg = sum(s for s, c in zip(confidence_scores, scores) if c < median_c) / max(1, sum(1 for c in scores if c < median_c))
        
        print(f"  {name:<15} {rho_c:>+10.4f} {tau_c:>+10.4f} {high_avg:>10.4f} {low_avg:>10.4f} {high_avg-low_avg:>+10.4f}")
    
    # =========================================================================
    # PART 3: PER-DOCUMENT ANALYSIS
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  PART 3: PER-DOCUMENT ANALYSIS (Run 1)")
    print(f"{'='*72}")
    
    # Use only first run for clarity
    run1 = all_results[:10]
    conf_run1 = confidence_scores[:10]
    
    print(f"\n  {'Doc':<10} {'Pass':>5} {'TP':>3} {'FP':>3} {'FN':>3} {'GT':>3} {'Conf':>6} {'F1':>6} {'F2':>6} {'Wgt':>6} {'Jacc':>6} {'Comp':>6}")
    print(f"  {'-'*10} {'-'*5} {'-'*3} {'-'*3} {'-'*3} {'-'*3} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    
    for doc, conf in zip(run1, conf_run1):
        tp, fp, fn, gt = doc["tp"], doc["fp"], doc["fn"], doc["gt_count"]
        f1 = f1_correctness(tp, fp, fn)
        f2 = f2_correctness(tp, fp, fn)
        wgt = weighted_correctness(tp, fp, fn, gt)
        jacc = jaccard_correctness(tp, fp, fn)
        comp = completeness_penalized(tp, fp, fn, gt)
        
        print(f"  {doc['doc_id']:<10} {str(doc['pass']):>5} {tp:>3} {fp:>3} {fn:>3} {gt:>3} {conf:>6.3f} {f1:>6.3f} {f2:>6.3f} {wgt:>6.3f} {jacc:>6.3f} {comp:>6.3f}")
    
    # =========================================================================
    # PART 4: FORMULA QUALITY RANKING
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  PART 4: FORMULA QUALITY RANKING")
    print(f"{'='*72}")
    
    # Rank formulas by multiple criteria
    rankings = {}
    for name, scores in correctness_scores.items():
        # Criteria:
        # 1. Correlation with confidence (higher = formula captures what confidence measures)
        rho_conf, _ = spearmanr(confidence_scores, scores)
        
        # 2. Dynamic range (higher = more discriminative)
        range_s = max(scores) - min(scores)
        
        # 3. Correlation with binary PASS/FAIL (higher = formula agrees with current evaluation)
        rho_bin, _ = spearmanr(scores, binary_labels)
        
        # 4. PASS/FAIL separation (higher = PASS docs score higher)
        median_s = sorted(scores)[len(scores) // 2]
        pass_avg = sum(s for s, l in zip(scores, binary_labels) if l == 1) / max(1, sum(binary_labels))
        fail_avg = sum(s for s, l in zip(scores, binary_labels) if l == 0) / max(1, len(binary_labels) - sum(binary_labels))
        separation = pass_avg - fail_avg
        
        # 5. Intuitive correctness for known cases
        # NDA-02 (TP=1, FP=0, FN=0) should be high
        # EMP-02 (TP=2, FP=0, FN=0) should be highest
        # VEN-02 (TP=1, FP=1, FN=2) should be low
        # EMP-01 (TP=0, FP=2, FN=0) should be low
        
        rankings[name] = {
            "rho_conf": rho_conf,
            "range": range_s,
            "rho_bin": rho_bin,
            "separation": separation,
        }
    
    # Print ranking table
    print(f"\n  {'Formula':<15} {'rho(conf)':>8} {'Range':>8} {'rho(binary)':>10} {'Separation':>12} {'Score':>8}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*10} {'-'*12} {'-'*8}")
    
    # Compute composite ranking score
    for name, r in rankings.items():
        # Normalize each criterion to 0-1
        all_rho_conf = [rankings[n]["rho_conf"] for n in rankings]
        all_range = [rankings[n]["range"] for n in rankings]
        all_rho_bin = [rankings[n]["rho_bin"] for n in rankings]
        all_sep = [rankings[n]["separation"] for n in rankings]
        
        def normalize(val, vals):
            min_v = min(vals)
            max_v = max(vals)
            if max_v == min_v:
                return 0.5
            return (val - min_v) / (max_v - min_v)
        
        score = (
            normalize(r["rho_conf"], all_rho_conf) * 0.25
            + normalize(r["range"], all_range) * 0.15
            + normalize(r["rho_bin"], all_rho_bin) * 0.30
            + normalize(r["separation"], all_sep) * 0.30
        )
        r["composite_score"] = score
    
    # Sort by composite score
    sorted_formulas = sorted(rankings.items(), key=lambda x: x[1]["composite_score"], reverse=True)
    
    for rank, (name, r) in enumerate(sorted_formulas, 1):
        print(f"  {rank}. {name:<15} {r['rho_conf']:>+8.4f} {r['range']:>8.3f} {r['rho_bin']:>+10.4f} {r['separation']:>+12.4f} {r['composite_score']:>8.3f}")
    
    # =========================================================================
    # PART 5: BOTTLENECK ANALYSIS
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  PART 5: BOTTLENECK ANALYSIS")
    print(f"{'='*72}")
    
    best_name = sorted_formulas[0][0]
    best_scores = correctness_scores[best_name]
    
    # Correlation between best correctness and binary PASS/FAIL
    rho_best_vs_bin, _ = spearmanr(best_scores, binary_labels)
    
    # Correlation between confidence and best correctness
    rho_conf_vs_best, _ = spearmanr(confidence_scores, best_scores)
    
    # Correlation between confidence and binary
    rho_conf_vs_bin, _ = spearmanr(confidence_scores, binary_labels)
    
    print(f"""
  Best formula: {best_name}
  
  Correlation matrix:
                        Binary    {best_name}    Confidence
  Binary              1.0000    {rho_best_vs_bin:>+8.4f}    {rho_conf_vs_bin:>+8.4f}
  {best_name:<20} {rho_best_vs_bin:>+8.4f}    1.0000    {rho_conf_vs_best:>+8.4f}
  Confidence          {rho_conf_vs_bin:>+8.4f}    {rho_conf_vs_best:>+8.4f}    1.0000
  
  Bottleneck analysis:
  
  1. If rho(confidence, binary) is LOW but rho(confidence, {best_name}) is HIGH:
     -> The BINARY target is the bottleneck. The scorer is good but binary PASS/FAIL
       loses information that the continuous metric captures.
  
  2. If rho(confidence, binary) is LOW and rho(confidence, {best_name}) is LOW:
     -> The SCORER is the bottleneck. Neither binary nor continuous target
       correlates with confidence, meaning the confidence scorer needs improvement.
  
  3. If rho(confidence, binary) is HIGH but rho(confidence, {best_name}) is LOW:
     -> The FORMULA is the bottleneck. The continuous formula doesn't capture
       what confidence measures, suggesting the formula needs redesign.
""")
    
    # Interpret results
    if abs(rho_conf_vs_bin) < 0.2 and abs(rho_conf_vs_best) > 0.3:
        print(f"  INTERPRETATION: Binary target is the bottleneck.")
        print(f"  The confidence scorer correlates with continuous correctness ({rho_conf_vs_best:+.4f})")
        print(f"  but not with binary PASS/FAIL ({rho_conf_vs_bin:+.4f}).")
        print(f"  Switching to continuous correctness would improve calibration measurement.")
    elif abs(rho_conf_vs_bin) < 0.2 and abs(rho_conf_vs_best) < 0.2:
        print(f"  INTERPRETATION: The scorer is the bottleneck.")
        print(f"  Confidence correlates poorly with both binary ({rho_conf_vs_bin:+.4f})")
        print(f"  and continuous correctness ({rho_conf_vs_best:+.4f}).")
        print(f"  The confidence scorer needs fundamental improvement.")
    elif abs(rho_conf_vs_bin) > 0.3 and abs(rho_conf_vs_best) > 0.3:
        print(f"  INTERPRETATION: Both are reasonable targets.")
        print(f"  Confidence correlates with both binary ({rho_conf_vs_bin:+.4f})")
        print(f"  and continuous correctness ({rho_conf_vs_best:+.4f}).")
        print(f"  The continuous metric adds marginal value for calibration.")
    else:
        print(f"  INTERPRETATION: Mixed results. Further investigation needed.")
    
    # =========================================================================
    # PART 6: RECOMMENDATION
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  PART 6: RECOMMENDATION")
    print(f"{'='*72}")
    
    print(f"""
  Recommended formula: {best_name}
  
  Rationale:
  - Highest composite ranking score ({rankings[best_name]['composite_score']:.3f})
  - Best balance of correlation with confidence, binary PASS/FAIL, and discriminative power
  
  Formula definition:
""")
    
    if best_name == "F1":
        print(f"    correctness = 2 * precision * recall / (precision + recall)")
        print(f"    where precision = TP / (TP + FP)")
        print(f"          recall = TP / (TP + FN)")
    elif best_name == "F2":
        print(f"    correctness = 5 * precision * recall / (4 * precision + recall)")
        print(f"    (recall-weighted: missing issues penalized 2x more than false positives)")
    elif best_name == "Weighted":
        print(f"    correctness = clamp(TP/gt_count - FP*0.15 - FN*0.35)")
        print(f"    (FN penalized 2.3x more than FP)")
    elif best_name == "PR_Composite":
        print(f"    correctness = clamp(precision*0.5 + recall*0.5 - FP*0.05 - FN*0.10)")
    elif best_name == "Jaccard":
        print(f"    correctness = TP / (TP + FP + FN)")
        print(f"    (intersection-over-union)")
    elif best_name == "Completeness":
        print(f"    correctness = clamp(TP/gt - FP_rate*0.25 - FN_rate*0.35 + count_bonus*0.1)")
    
    print(f"""
  Impact on confidence calibration:
  - Current: Spearman(confidence, PASS/FAIL) = {rho_conf_vs_bin:+.4f}
  - Proposed: Spearman(confidence, {best_name}) = {rho_conf_vs_best:+.4f}
  - Improvement: {rho_conf_vs_best - rho_conf_vs_bin:+.4f}
""")


if __name__ == "__main__":
    main()
