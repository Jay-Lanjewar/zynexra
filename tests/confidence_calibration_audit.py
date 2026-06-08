"""
Confidence Calibration Audit — Phase 1

Usage:
    python tests/confidence_calibration_audit.py
"""

import json
from pathlib import Path

RESULTS_FILE = Path(__file__).resolve().parent / "validation_corpus" / "phase1_results_20260601_192253.json"
CORPUS_DIR = Path(__file__).resolve().parent / "validation_corpus"

with open(RESULTS_FILE) as f:
    data = json.load(f)

docs = data["per_document"]

# ---------------------------------------------------------------------------
# 1. Per-document table: confidence, TP, FP, FN, correctness rate
# ---------------------------------------------------------------------------
print("=" * 72)
print("  SECTION 1: PER-DOCUMENT CONFIDENCE vs ACCURACY")
print("=" * 72)
print()
print(f"  {'Doc':<8} {'Pass':<5} {'Conf':>7} {'TP':>4} {'FP':>4} {'FN':>4} "
      f"{'Prec':>6} {'Rec':>6} {'Correct':>8} {'Label':>12} {'#Issues':>8}")
print(f"  {'-'*8} {'-'*5} {'-'*7} {'-'*4} {'-'*4} {'-'*4} "
      f"{'-'*6} {'-'*6} {'-'*8} {'-'*12} {'-'*8}")

pass_docs = []
fail_docs = []

for r in docs:
    gt_count = r["gt_count"]
    corr = r["tp"] / gt_count if gt_count > 0 else 1.0
    status = "PASS" if r["pass"] else "FAIL"
    print(f"  {r['doc_id']:<8} {status:<5} {r['confidence_score']:>7.2f} {r['tp']:>4} {r['fp']:>4} {r['fn']:>4} "
          f"{r['precision']:>6.3f} {r['recall']:>6.3f} {corr:>8.3f} {r['confidence_label']:>12} {r['issue_count']:>8}")

    if r["pass"]:
        pass_docs.append(r)
    else:
        fail_docs.append(r)

print()

# ---------------------------------------------------------------------------
# 2. Average confidence by pass/fail
# ---------------------------------------------------------------------------
avg_conf_pass = sum(r["confidence_score"] for r in pass_docs) / len(pass_docs) if pass_docs else 0
avg_conf_fail = sum(r["confidence_score"] for r in fail_docs) / len(fail_docs) if fail_docs else 0

print("=" * 72)
print("  SECTION 2: AVERAGE CONFIDENCE BY PASS/FAIL")
print("=" * 72)
print(f"  PASS docs ({len(pass_docs)}): avg confidence = {avg_conf_pass:.4f}")
print(f"  FAIL docs ({len(fail_docs)}): avg confidence = {avg_conf_fail:.4f}")
print(f"  DIFFERENCE (PASS - FAIL) = {avg_conf_pass - avg_conf_fail:.4f}")
print(f"  Expected: PASS >> FAIL if calibration is working")
print()

# ---------------------------------------------------------------------------
# 3. Confidence distribution histogram & calibration table
# ---------------------------------------------------------------------------
print("=" * 72)
print("  SECTION 3: CONFIDENCE DISTRIBUTION")
print("=" * 72)
print()

bins = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 1.0), (1.0, 1.01)]
for lo, hi in bins:
    bin_docs = [r for r in docs if lo <= r["confidence_score"] < hi]
    if not bin_docs:
        continue
    n = len(bin_docs)
    tps = sum(r["tp"] for r in bin_docs)
    fps = sum(r["fp"] for r in bin_docs)
    fns = sum(r["fn"] for r in bin_docs)
    gts = sum(r["gt_count"] for r in bin_docs)
    precision = tps / (tps + fps) if (tps + fps) else 0
    recall = tps / (tps + fns) if (tps + fns) else 0
    bar = "#" * n
    label = f"  [{lo:.1f}-{hi:.1f})".ljust(10)
    print(f"{label} {bar} ({n} docs)  precision={precision:.3f} recall={recall:.3f} TP={tps} FP={fps} FN={fns}")

print()

# Calibration table
print("=" * 72)
print("  SECTION 4: CALIBRATION TABLE")
print("=" * 72)
print()
print(f"  {'Conf Range':<12} {'Docs':>5} {'TP':>4} {'FP':>4} {'FN':>4} "
      f"{'Prec':>7} {'Rec':>7} {'Avg Prec':>9} {'Avg Rec':>9}")
print(f"  {'-'*12} {'-'*5} {'-'*4} {'-'*4} {'-'*4} "
      f"{'-'*7} {'-'*7} {'-'*9} {'-'*9}")

for lo, hi in bins:
    bin_docs = [r for r in docs if lo <= r["confidence_score"] < hi]
    if not bin_docs:
        continue
    n = len(bin_docs)
    tps = sum(r["tp"] for r in bin_docs)
    fps = sum(r["fp"] for r in bin_docs)
    fns = sum(r["fn"] for r in bin_docs)
    gts = sum(r["gt_count"] for r in bin_docs)
    precision = tps / (tps + fps) if (tps + fps) else 0
    recall = tps / (tps + fns) if (tps + fns) else 0
    avg_prec = sum(r["precision"] for r in bin_docs) / n
    avg_rec = sum(r["recall"] for r in bin_docs) / n
    label = f"  [{lo:.1f}-{hi:.1f})".ljust(12)
    print(f"{label} {n:>5} {tps:>4} {fps:>4} {fns:>4} "
          f"{precision:>7.3f} {recall:>7.3f} {avg_prec:>9.3f} {avg_rec:>9.3f}")

print()

# ---------------------------------------------------------------------------
# 5. Trace confidence generation
# ---------------------------------------------------------------------------
print("=" * 72)
print("  SECTION 5: CONFIDENCE GENERATION PATH (code trace)")
print("=" * 72)
print()

# Count high-confidence failures
high_conf_fails = [(r["doc_id"], r["confidence_score"], r["precision"], r["recall"], r["fp"], r["fn"])
                   for r in docs if r["confidence_score"] >= 0.8 and not r["pass"]]
print(f"  High-confidence FAIL docs (conf >= 0.8): {len(high_conf_fails)}")
for doc_id, conf, prec, rec, fp, fn in high_conf_fails:
    print(f"    {doc_id}: conf={conf:.2f}, prec={prec:.3f}, rec={rec:.3f}, FP={fp}, FN={fn}")

print()

# docs with confidence=1.0 but prec=0, rec=0
zero_correct_high_conf = [(r["doc_id"], r["confidence_score"], r["confidence_label"])
                          for r in docs if r["precision"] == 0 and r["recall"] == 0 and r["confidence_score"] >= 0.5]
print(f"  Docs with zero correct findings but conf >= 0.5: {len(zero_correct_high_conf)}")
for doc_id, conf, label in zero_correct_high_conf:
    print(f"    {doc_id}: conf={conf:.2f}, label={label}")

print()

# ---------------------------------------------------------------------------
# 7. Per-document raw data dump for key anomalous docs
# ---------------------------------------------------------------------------
print("=" * 72)
print("  SECTION 6: ANOMALOUS DOCUMENT RAW DATA")
print("=" * 72)
print()

for r in docs:
    if r["confidence_score"] >= 0.8 and (r["precision"] == 0 or r["recall"] == 0):
        print(f"  {r['doc_id']}:")
        print(f"    confidence_score  = {r['confidence_score']}")
        print(f"    confidence_label  = {r['confidence_label']}")
        print(f"    pass              = {r['pass']}")
        print(f"    fail_reasons      = {r['fail_reasons']}")
        print(f"    tp                = {r['tp']}")
        print(f"    fp                = {r['fp']}")
        print(f"    fn                = {r['fn']}")
        print(f"    precision         = {r['precision']}")
        print(f"    recall            = {r['recall']}")
        print(f"    issue_count       = {r['issue_count']}")
        print(f"    gt_count          = {r['gt_count']}")
        print(f"    false_positives   = {json.dumps(r['false_positives'], indent=4)}")
        print(f"    false_negatives   = {json.dumps(r['false_negatives'], indent=4)}")
        print(f"    true_positives    = {json.dumps(r['true_positives'], indent=4)}")
        print()

# ---------------------------------------------------------------------------
# 8. Correlation coefficient
# ---------------------------------------------------------------------------
print("=" * 72)
print("  SECTION 7: SPEARMAN CORRELATION (confidence vs correctness)")
print("=" * 72)
print()

# correctness = tp / gt_count (or 1.0 if gt_count=0)
correctness = [r["tp"] / r["gt_count"] if r["gt_count"] > 0 else 1.0 for r in docs]
confidences = [r["confidence_score"] for r in docs]

n = len(docs)
rank_conf = sorted(range(n), key=lambda i: confidences[i])
rank_corr = sorted(range(n), key=lambda i: correctness[i])
rank_conf_pos = [0] * n
rank_corr_pos = [0] * n
for pos, idx in enumerate(rank_conf):
    rank_conf_pos[idx] = pos
for pos, idx in enumerate(rank_corr):
    rank_corr_pos[idx] = pos

d_sq = sum((rank_conf_pos[i] - rank_corr_pos[i]) ** 2 for i in range(n))
spearman = 1 - (6 * d_sq) / (n * (n * n - 1))
print(f"  Spearman rank correlation (confidence vs accuracy): {spearman:.4f}")
print(f"  Range: -1 (anti-correlated) to +1 (perfectly correlated)")
print(f"  Interpretation: {'Positive (good)' if spearman > 0.3 else 'Weak' if spearman > 0 else 'Negative (inverse!)'}")
print()

# Mann-Whitney U: is confidence distribution different for pass vs fail?
from itertools import combinations

print("=" * 72)
print("  SECTION 8: MANN-WHITNEY U TEST")
print("=" * 72)
pass_confs = [r["confidence_score"] for r in pass_docs]
fail_confs = [r["confidence_score"] for r in fail_docs]
print(f"  PASS confidences: {sorted(pass_confs)}")
print(f"  FAIL confidences: {sorted(fail_confs)}")

# Simple count: how many PASS-fail pairs have PASS conf > fail conf?
u = 0
for pc in pass_confs:
    for fc in fail_confs:
        if pc > fc:
            u += 1
        elif pc == fc:
            u += 0.5
total_pairs = len(pass_confs) * len(fail_confs)
print(f"  Mann-Whitney U = {u} / {total_pairs} pairs")
print(f"  Proportion where PASS conf > FAIL conf: {u / total_pairs:.3f}")
print(f"  Expected: 0.500 if random, 1.000 if perfectly calibrated")
print()

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("=" * 72)
print("  SUMMARY")
print("=" * 72)
print(f"  Total docs: {len(docs)}")
print(f"  PASS: {len(pass_docs)}, FAIL: {len(fail_docs)}")
print(f"  Average confidence (PASS): {avg_conf_pass:.4f}")
print(f"  Average confidence (FAIL): {avg_conf_fail:.4f}")
print(f"  Spearman correlation: {spearman:.4f}")
print(f"  Mann-Whitney U proportion: {u / total_pairs:.3f}")
print(f"  Overall precision: {data['overall']['precision']:.4f}")
print(f"  Overall recall: {data['overall']['recall']:.4f}")
print(f"  Overall composite: {data['overall']['composite_score']:.2f}")
