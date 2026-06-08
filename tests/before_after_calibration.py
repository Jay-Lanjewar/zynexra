"""
Before/After Confidence Calibration Comparison
Aggregates 1 before + 3 after runs and produces comparison tables.
"""

import json
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent / "validation_corpus"
BEFORE_FILE = CORPUS_DIR / "phase1_results_20260601_192253.json"
AFTER_FILES = [
    CORPUS_DIR / "phase1_results_20260601_195526.json",
    CORPUS_DIR / "phase1_results_20260601_200300.json",
    CORPUS_DIR / "phase1_results_20260601_201121.json",
]

with open(BEFORE_FILE) as f:
    before = json.load(f)

after_results = []
for af in AFTER_FILES:
    with open(af) as f:
        after_results.append(json.load(f))

# Per-document confidence aggregation
doc_ids = [r["doc_id"] for r in before["per_document"]]

def avg(lst):
    items = list(lst)
    return sum(items) / len(items) if items else 0

print("=" * 72)
print("  BEFORE / AFTER CONFIDENCE CALIBRATION COMPARISON")
print("=" * 72)
print()
print(f"  BEFORE: {BEFORE_FILE.name}")
print(f"  AFTER:  {', '.join(f.name for f in AFTER_FILES)}")
print()

# 1. Per-document confidence comparison
print("=" * 72)
print("  SECTION 1: PER-DOCUMENT CONFIDENCE BEFORE vs AFTER")
print("=" * 72)
print()
header = f"  {'Doc':<8} {'Before':>8} {'After Avg':>10} {'After1':>8} {'After2':>8} {'After3':>8} {'Delta':>8} {'PASS?'}"
print(header)
print(f"  {'-'*8} {'-'*8} {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6}")

for doc_id in doc_ids:
    b_doc = next(r for r in before["per_document"] if r["doc_id"] == doc_id)
    a_docs = [
        next(r for r in ar["per_document"] if r["doc_id"] == doc_id)
        for ar in after_results
    ]
    before_conf = b_doc["confidence_score"]
    after_confs = [d["confidence_score"] for d in a_docs]
    after_avg = avg(after_confs)
    delta = after_avg - before_conf
    pass_status = b_doc["pass"]
    print(f"  {b_doc['doc_id']:<8} {before_conf:>8.4f} {after_avg:>10.4f} "
          f"{after_confs[0]:>8.4f} {after_confs[1]:>8.4f} {after_confs[2]:>8.4f} "
          f"{delta:>+8.4f} {'PASS' if pass_status else 'FAIL'}")

# Per-document correctness comparison
print()
print("=" * 72)
print("  SECTION 2: PER-DOCUMENT CORRECTNESS BEFORE vs AFTER")
print("=" * 72)
print()
header2 = f"  {'Doc':<8} {'B Prec':>7} {'A1 Prec':>8} {'A2 Prec':>8} {'A3 Prec':>8} {'B Rec':>7} {'A1 Rec':>8} {'A2 Rec':>8} {'A3 Rec':>8}"
print(header2)
print(f"  {'-'*8} {'-'*7} {'-'*8} {'-'*8} {'-'*8} {'-'*7} {'-'*8} {'-'*8} {'-'*8}")

for doc_id in doc_ids:
    b_doc = next(r for r in before["per_document"] if r["doc_id"] == doc_id)
    a_docs = [
        next(r for r in ar["per_document"] if r["doc_id"] == doc_id)
        for ar in after_results
    ]
    print(f"  {b_doc['doc_id']:<8} "
          f"{b_doc['precision']:>7.3f} "
          f"{a_docs[0]['precision']:>8.3f} {a_docs[1]['precision']:>8.3f} {a_docs[2]['precision']:>8.3f} "
          f"{b_doc['recall']:>7.3f} "
          f"{a_docs[0]['recall']:>8.3f} {a_docs[1]['recall']:>8.3f} {a_docs[2]['recall']:>8.3f}")

# 3. Average confidence by pass/fail
print()
print("=" * 72)
print("  SECTION 3: AVERAGE CONFIDENCE BY PASS/FAIL")
print("=" * 72)
print()

# Before
b_pass = [r for r in before["per_document"] if r["pass"]]
b_fail = [r for r in before["per_document"] if not r["pass"]]
b_avg_pass = avg(r["confidence_score"] for r in b_pass)
b_avg_fail = avg(r["confidence_score"] for r in b_fail)

# After (aggregate across 3 runs)
a_all_docs = [r for ar in after_results for r in ar["per_document"]]
a_pass = [r for r in a_all_docs if r["pass"]]
a_fail = [r for r in a_all_docs if not r["pass"]]
a_avg_pass = avg(r["confidence_score"] for r in a_pass)
a_avg_fail = avg(r["confidence_score"] for r in a_fail)

print(f"  {'':15} {'BEFORE':>10} {'AFTER (3-run avg)':>18}")
print(f"  {'-'*15} {'-'*10} {'-'*18}")
print(f"  {'Avg conf (PASS)':15} {b_avg_pass:>10.4f} {a_avg_pass:>18.4f}")
print(f"  {'Avg conf (FAIL)':15} {b_avg_fail:>10.4f} {a_avg_fail:>18.4f}")
print(f"  {'Spread (P-F)':15} {b_avg_pass - b_avg_fail:>+10.4f} {a_avg_pass - a_avg_fail:>+18.4f}")

# 4. Confidence distribution
print()
print("=" * 72)
print("  SECTION 4: CONFIDENCE DISTRIBUTION")
print("=" * 72)
print()

print(f"  {'Range':<12} {'BEFORE':>8} {'AFTER Run1':>11} {'AFTER Run2':>11} {'AFTER Run3':>11}")
print(f"  {'-'*12} {'-'*8} {'-'*11} {'-'*11} {'-'*11}")

bins = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.0)]
for lo, hi in bins:
    counts = []
    label = f"  [{lo:.1f}-{hi:.1f})"
    b_count = sum(1 for r in before["per_document"] if lo <= r["confidence_score"] < hi)
    for ar in after_results:
        counts.append(sum(1 for r in ar["per_document"] if lo <= r["confidence_score"] < hi))
    if b_count == 0 and all(c == 0 for c in counts):
        continue
    s = f"  [{lo:.1f}-{hi:.1f})".ljust(12)
    s += f" {b_count:>8} {counts[0]:>11} {counts[1]:>11} {counts[2]:>11}"
    print(s)

# Count docs with zero correct findings
print()
print("=" * 72)
print("  SECTION 5: HIGH-CONFIDENCE + ZERO-ACCURACY DOCS")
print("=" * 72)
print()
b_zero = [r for r in before["per_document"] if r["precision"] == 0 and r["recall"] == 0 and r["confidence_score"] >= 0.5]
print(f"  BEFORE: {len(b_zero)} docs with conf>=0.5 and zero correct findings")
for r in b_zero:
    print(f"    {r['doc_id']}: conf={r['confidence_score']:.4f}, label={r['confidence_label']}")

for run_idx, ar in enumerate(after_results):
    a_zero = [r for r in ar["per_document"] if r["precision"] == 0 and r["recall"] == 0 and r["confidence_score"] >= 0.5]
    print(f"\n  AFTER run {run_idx+1}: {len(a_zero)} docs with conf>=0.5 and zero correct findings")
    for r in a_zero:
        print(f"    {r['doc_id']}: conf={r['confidence_score']:.4f}, label={r['confidence_label']}")

# 6. Spearman correlation
print()
print("=" * 72)
print("  SECTION 6: SPEARMAN RANK CORRELATION (confidence vs correctness)")
print("=" * 72)
print()

def compute_spearman(docs_in):
    n = len(docs_in)
    correctness = [r["tp"] / r["gt_count"] if r["gt_count"] > 0 else 1.0 for r in docs_in]
    confidences = [r["confidence_score"] for r in docs_in]
    rank_conf = sorted(range(n), key=lambda i: confidences[i])
    rank_corr = sorted(range(n), key=lambda i: correctness[i])
    conf_pos = [0] * n
    corr_pos = [0] * n
    for pos, idx in enumerate(rank_conf):
        conf_pos[idx] = pos
    for pos, idx in enumerate(rank_corr):
        corr_pos[idx] = pos
    d_sq = sum((conf_pos[i] - corr_pos[i]) ** 2 for i in range(n))
    return 1 - (6 * d_sq) / (n * (n * n - 1))

b_spear = compute_spearman(before["per_document"])
print(f"  BEFORE: Spearman = {b_spear:.4f}")
for run_idx, ar in enumerate(after_results):
    a_spear = compute_spearman(ar["per_document"])
    print(f"  AFTER run {run_idx+1}: Spearman = {a_spear:.4f}")

# 7. Mann-Whitney U test
print()
print("=" * 72)
print("  SECTION 7: MANN-WHITNEY U (PASS > FAIL confidence)")
print("=" * 72)
print()

def mann_whitney(docs_in):
    pass_confs = [r["confidence_score"] for r in docs_in if r["pass"]]
    fail_confs = [r["confidence_score"] for r in docs_in if not r["pass"]]
    u = 0
    for pc in pass_confs:
        for fc in fail_confs:
            if pc > fc:
                u += 1
            elif pc == fc:
                u += 0.5
    total = len(pass_confs) * len(fail_confs)
    return u / total if total > 0 else 0

b_mw = mann_whitney(before["per_document"])
print(f"  BEFORE: U/total = {b_mw:.3f}")
for run_idx, ar in enumerate(after_results):
    a_mw = mann_whitney(ar["per_document"])
    print(f"  AFTER run {run_idx+1}: U/total = {a_mw:.3f}")

# 8. Composite score
print()
print("=" * 72)
print("  SECTION 8: OVERALL METRICS")
print("=" * 72)
print()
print(f"  {'Metric':<25} {'BEFORE':>10} {'AFTER R1':>10} {'AFTER R2':>10} {'AFTER R3':>10}")
print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
metrics = ["precision", "recall", "composite_score"]
for m in metrics:
    vals = [before["overall"][m]]
    for ar in after_results:
        vals.append(ar["overall"][m])
    print(f"  {m:<25} {vals[0]:>10.4f} {vals[1]:>10.4f} {vals[2]:>10.4f} {vals[3]:>10.4f}")

print()
print("=" * 72)
print("  VERDICT")
print("=" * 72)
print()

# Summary of changes
b_floor = min(r["confidence_score"] for r in before["per_document"])
b_ceiling = max(r["confidence_score"] for r in before["per_document"])
a_floors = [min(r["confidence_score"] for r in ar["per_document"]) for ar in after_results]
a_ceilings = [max(r["confidence_score"] for r in ar["per_document"]) for ar in after_results]

print(f"  BEFORE: dynamic range = {b_floor:.2f} - {b_ceiling:.2f}")
print(f"  AFTER:  dynamic range = {min(a_floors):.2f} - {max(a_ceilings):.2f}")
a_spears = [f"{compute_spearman(ar['per_document']):.3f}" for ar in after_results]
print(f"  Correlation: BEFORE={b_spear:.3f}, AFTER runs={a_spears}")
a_gaps = []
for ar in after_results:
    p_conf = avg(r['confidence_score'] for r in ar['per_document'] if r['pass'])
    f_conf = avg(r['confidence_score'] for r in ar['per_document'] if not r['pass'])
    a_gaps.append(f"{p_conf - f_conf:.4f}")
print(f"  Calibration gap (PASS conf - FAIL conf): BEFORE={b_avg_pass - b_avg_fail:.4f}, "
      f"AFTER runs={a_gaps}")

nda02_avg = avg(r['confidence_score'] for r in a_all_docs if r['doc_id']=='NDA-02')
ven01_avg = avg(r['confidence_score'] for r in a_all_docs if r['doc_id']=='VEN-01')
emp01_avg = avg(r['confidence_score'] for r in a_all_docs if r['doc_id']=='EMP-01')
print(f"\n  Key behavioral changes:")
print(f"    - NDA-02 conf dropped to {nda02_avg:.3f} (was 1.00) — issues empty or partial-match quoted text")
print(f"    - VEN-01 conf dropped to {ven01_avg:.3f} (was 1.00) — internal consistency penalty")
print(f"    - EMP-01 conf dropped to {emp01_avg:.3f} (was 1.00) — internal consistency penalty")
