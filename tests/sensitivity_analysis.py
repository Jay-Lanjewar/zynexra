"""
Sensitivity Analysis: Weighted Correctness Formula
Tests all combinations of FP penalty and FN penalty.
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

# Parameter grid
FP_PENALTIES = [0.05, 0.10, 0.15, 0.20, 0.25]
FN_PENALTIES = [0.15, 0.25, 0.35, 0.45, 0.55]


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def spearmanr(x, y):
    n = len(x)
    if n < 2:
        return 0.0
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
        return 0.0
    return cov / (std_x * std_y)


def kendalltau(x, y):
    n = len(x)
    if n < 2:
        return 0.0
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
    return (concordant - discordant) / (concordant + discordant) if (concordant + discordant) > 0 else 0


def weighted_correctness(tp, fp, fn, gt_count, fp_penalty, fn_penalty):
    if gt_count == 0:
        return 0.0 if fp > 0 else 1.0
    return clamp(tp / gt_count - fp * fp_penalty - fn * fn_penalty)


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
        + 1.0 * WEIGHTS["duplicate_suppression"]
        + 1.0 * WEIGHTS["refusal_absent"]
        + 1.0 * WEIGHTS["response_length"]
    )
    penalty_mult = 1.0
    if meta.get("policy_detection") not in ("NOT_POLICY", "UNKNOWN"):
        penalty_mult *= 0.30
    if meta.get("domain") == "NON_LEGAL":
        penalty_mult *= 0.30
    return clamp(base) * penalty_mult


def main():
    all_results = []
    for run_file in RUN_FILES:
        with open(CORPUS_DIR / run_file) as f:
            data = json.load(f)
        for doc in data["per_document"]:
            all_results.append(doc)

    confidence_scores = [current_confidence(d) for d in all_results]
    binary_labels = [1 if d["pass"] else 0 for d in all_results]

    results = []

    for fp_pen in FP_PENALTIES:
        for fn_pen in FN_PENALTIES:
            correctness = [weighted_correctness(d["tp"], d["fp"], d["fn"], d["gt_count"], fp_pen, fn_pen) for d in all_results]

            rho_conf = spearmanr(confidence_scores, correctness)
            tau_conf = kendalltau(confidence_scores, correctness)
            rho_bin = spearmanr(correctness, binary_labels)

            mean_c = sum(correctness) / len(correctness)
            std_c = math.sqrt(sum((c - mean_c) ** 2 for c in correctness) / len(correctness))
            range_c = max(correctness) - min(correctness)

            median_c = sorted(correctness)[len(correctness) // 2]
            high_avg = sum(c for c in correctness if c >= median_c) / max(1, sum(1 for c in correctness if c >= median_c))
            low_avg = sum(c for c in correctness if c < median_c) / max(1, sum(1 for c in correctness if c < median_c))

            pass_avg = sum(c for c, l in zip(correctness, binary_labels) if l == 1) / max(1, sum(binary_labels))
            fail_avg = sum(c for c, l in zip(correctness, binary_labels) if l == 0) / max(1, len(binary_labels) - sum(binary_labels))

            # Ranking stability: how often does the formula agree with other formulas?
            agreement_scores = []
            for other_fp in FP_PENALTIES:
                for other_fn in FN_PENALTIES:
                    if other_fp == fp_pen and other_fn == fn_pen:
                        continue
                    other_correctness = [weighted_correctness(d["tp"], d["fp"], d["fn"], d["gt_count"], other_fp, other_fn) for d in all_results]
                    rank_corr = spearmanr(correctness, other_correctness)
                    agreement_scores.append(rank_corr)
            avg_agreement = sum(agreement_scores) / len(agreement_scores) if agreement_scores else 0

            # Robustness: std of rho_conf across nearby parameter values
            nearby_rhos = []
            for dfp in [-0.05, 0, 0.05]:
                for dfn in [-0.10, 0, 0.10]:
                    nfp = fp_pen + dfp
                    nfn = fn_pen + dfn
                    if nfp < 0.05 or nfp > 0.25 or nfn < 0.15 or nfn > 0.55:
                        continue
                    n_correctness = [weighted_correctness(d["tp"], d["fp"], d["fn"], d["gt_count"], nfp, nfn) for d in all_results]
                    n_rho = spearmanr(confidence_scores, n_correctness)
                    nearby_rhos.append(n_rho)
            robustness = 1.0 - (max(nearby_rhos) - min(nearby_rhos)) if nearby_rhos else 0

            # Composite score
            composite = (
                rho_conf * 0.35
                + avg_agreement * 0.25
                + robustness * 0.20
                + (pass_avg - fail_avg) * 0.10
                + std_c * 0.10
            )

            results.append({
                "fp_pen": fp_pen,
                "fn_pen": fn_pen,
                "rho_conf": rho_conf,
                "tau_conf": tau_conf,
                "rho_bin": rho_bin,
                "mean": mean_c,
                "std": std_c,
                "range": range_c,
                "pass_avg": pass_avg,
                "fail_avg": fail_avg,
                "separation": pass_avg - fail_avg,
                "avg_agreement": avg_agreement,
                "robustness": robustness,
                "composite": composite,
                "correctness": correctness,
            })

    # Sort by composite
    results.sort(key=lambda x: x["composite"], reverse=True)

    # =========================================================================
    # HEATMAP TABLE
    # =========================================================================
    print(f"{'='*72}")
    print(f"  SENSITIVITY ANALYSIS: Weighted Correctness Formula")
    print(f"  correctness = clamp(TP/gt - FP*fp_pen - FN*fn_pen)")
    print(f"{'='*72}")

    print(f"\n  SPEARMAN RHO (confidence vs correctness)")
    print(f"  Higher = better calibration")
    fpfn = "FP\\FN"
    print(f"\n  {fpfn:>8}", end="")
    for fn in FN_PENALTIES:
        print(f"  {fn:>6.2f}", end="")
    print()
    print(f"  {'-'*8}", end="")
    for _ in FN_PENALTIES:
        print(f"  {'-'*6}", end="")
    print()

    for fp in FP_PENALTIES:
        print(f"  {fp:>6.2f}  ", end="")
        for fn in FN_PENALTIES:
            r = [x for x in results if x["fp_pen"] == fp and x["fn_pen"] == fn][0]
            print(f"  {r['rho_conf']:>+5.3f}", end="")
        print()

    # =========================================================================
    # HEATMAP: AGREEMENT
    # =========================================================================
    print(f"\n  AVERAGE RANKING AGREEMENT WITH OTHER FORMULAS")
    print(f"  Higher = more stable ranking")
    print(f"\n  {fpfn:>8}", end="")
    for fn in FN_PENALTIES:
        print(f"  {fn:>6.2f}", end="")
    print()
    print(f"  {'-'*8}", end="")
    for _ in FN_PENALTIES:
        print(f"  {'-'*6}", end="")
    print()

    for fp in FP_PENALTIES:
        print(f"  {fp:>6.2f}  ", end="")
        for fn in FN_PENALTIES:
            r = [x for x in results if x["fp_pen"] == fp and x["fn_pen"] == fn][0]
            print(f"  {r['avg_agreement']:>+5.3f}", end="")
        print()

    # =========================================================================
    # HEATMAP: ROBUSTNESS
    # =========================================================================
    print(f"\n  ROBUSTNESS (1 - rho range across nearby parameters)")
    print(f"  Higher = more stable across parameter changes")
    print(f"\n  {fpfn:>8}", end="")
    for fn in FN_PENALTIES:
        print(f"  {fn:>6.2f}", end="")
    print()
    print(f"  {'-'*8}", end="")
    for _ in FN_PENALTIES:
        print(f"  {'-'*6}", end="")
    print()

    for fp in FP_PENALTIES:
        print(f"  {fp:>6.2f}  ", end="")
        for fn in FN_PENALTIES:
            r = [x for x in results if x["fp_pen"] == fp and x["fn_pen"] == fn][0]
            print(f"  {r['robustness']:>5.3f}", end="")
        print()

    # =========================================================================
    # HEATMAP: COMPOSITE
    # =========================================================================
    print(f"\n  COMPOSITE SCORE (weighted average of all criteria)")
    print(f"  Higher = better overall")
    print(f"\n  {fpfn:>8}", end="")
    for fn in FN_PENALTIES:
        print(f"  {fn:>6.2f}", end="")
    print()
    print(f"  {'-'*8}", end="")
    for _ in FN_PENALTIES:
        print(f"  {'-'*6}", end="")
    print()

    for fp in FP_PENALTIES:
        print(f"  {fp:>6.2f}  ", end="")
        for fn in FN_PENALTIES:
            r = [x for x in results if x["fp_pen"] == fp and x["fn_pen"] == fn][0]
            print(f"  {r['composite']:>5.3f}", end="")
        print()

    # =========================================================================
    # TOP 10 PARAMETER COMBINATIONS
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  TOP 10 PARAMETER COMBINATIONS")
    print(f"{'='*72}")

    print(f"\n  {'Rank':>4} {'FP':>5} {'FN':>5} {'rho(conf)':>10} {'Agree':>7} {'Robust':>7} {'Sep':>7} {'Std':>6} {'Score':>7}")
    print(f"  {'-'*4} {'-'*5} {'-'*5} {'-'*10} {'-'*7} {'-'*7} {'-'*7} {'-'*6} {'-'*7}")

    for rank, r in enumerate(results[:10], 1):
        print(f"  {rank:>4} {r['fp_pen']:>5.2f} {r['fn_pen']:>5.2f} {r['rho_conf']:>+10.4f} {r['avg_agreement']:>7.4f} {r['robustness']:>7.4f} {r['separation']:>+7.4f} {r['std']:>6.3f} {r['composite']:>7.4f}")

    # =========================================================================
    # WINNER ANALYSIS
    # =========================================================================
    winner = results[0]

    print(f"\n{'='*72}")
    print(f"  WINNER: FP={winner['fp_pen']:.2f}, FN={winner['fn_pen']:.2f}")
    print(f"{'='*72}")

    print(f"""
  Metrics:
    Spearman rho(conf, correctness): {winner['rho_conf']:+.4f}
    Kendall tau(conf, correctness):  {winner['tau_conf']:+.4f}
    Spearman rho(correctness, binary): {winner['rho_bin']:+.4f}
    Average ranking agreement:       {winner['avg_agreement']:.4f}
    Robustness:                      {winner['robustness']:.4f}
    PASS avg:                        {winner['pass_avg']:.4f}
    FAIL avg:                        {winner['fail_avg']:.4f}
    Separation:                      {winner['separation']:+.4f}
    Std dev:                         {winner['std']:.4f}
    Dynamic range:                   {winner['range']:.4f}
    Composite score:                 {winner['composite']:.4f}
""")

    # Per-document scores for winner
    print(f"  Per-document correctness (winner):")
    print(f"  {'Doc':<10} {'Pass':>5} {'TP':>3} {'FP':>3} {'FN':>3} {'GT':>3} {'Conf':>6} {'Correct':>8}")
    print(f"  {'-'*10} {'-'*5} {'-'*3} {'-'*3} {'-'*3} {'-'*3} {'-'*6} {'-'*8}")

    for doc, conf, corr in zip(all_results, confidence_scores, winner["correctness"]):
        print(f"  {doc['doc_id']:<10} {str(doc['pass']):>5} {doc['tp']:>3} {doc['fp']:>3} {doc['fn']:>3} {doc['gt_count']:>3} {conf:>6.3f} {corr:>8.3f}")

    # =========================================================================
    # SENSITIVITY INSIGHTS
    # =========================================================================
    print(f"\n{'='*72}")
    print(f"  SENSITIVITY INSIGHTS")
    print(f"{'='*72}")

    # Find best for each FP penalty
    print(f"\n  Best FN penalty for each FP penalty:")
    for fp in FP_PENALTIES:
        best = max([r for r in results if r["fp_pen"] == fp], key=lambda x: x["composite"])
        print(f"    FP={fp:.2f}: FN={best['fn_pen']:.2f} (rho={best['rho_conf']:+.4f}, score={best['composite']:.4f})")

    # Find best for each FN penalty
    print(f"\n  Best FP penalty for each FN penalty:")
    for fn in FN_PENALTIES:
        best = max([r for r in results if r["fn_pen"] == fn], key=lambda x: x["composite"])
        print(f"    FN={fn:.2f}: FP={best['fp_pen']:.2f} (rho={best['rho_conf']:+.4f}, score={best['composite']:.4f})")

    # FN/FP ratio analysis
    print(f"\n  FN/FP penalty ratio analysis:")
    for r in results[:5]:
        ratio = r["fn_pen"] / r["fp_pen"]
        print(f"    FP={r['fp_pen']:.2f}, FN={r['fn_pen']:.2f}: ratio={ratio:.1f}x, rho={r['rho_conf']:+.4f}")

    # Sensitivity to FP penalty (holding FN constant at winner)
    print(f"\n  Sensitivity to FP penalty (FN fixed at {winner['fn_pen']:.2f}):")
    for fp in FP_PENALTIES:
        r = [x for x in results if x["fp_pen"] == fp and x["fn_pen"] == winner["fn_pen"]][0]
        delta = r["rho_conf"] - winner["rho_conf"]
        print(f"    FP={fp:.2f}: rho={r['rho_conf']:+.4f} (delta={delta:+.4f})")

    # Sensitivity to FN penalty (holding FP constant at winner)
    print(f"\n  Sensitivity to FN penalty (FP fixed at {winner['fp_pen']:.2f}):")
    for fn in FN_PENALTIES:
        r = [x for x in results if x["fn_pen"] == fn and x["fp_pen"] == winner["fp_pen"]][0]
        delta = r["rho_conf"] - winner["rho_conf"]
        print(f"    FN={fn:.2f}: rho={r['rho_conf']:+.4f} (delta={delta:+.4f})")


if __name__ == "__main__":
    main()
