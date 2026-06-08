import json, statistics

baseline_files = [
    "tests/validation_corpus/phase1_results_20260603_195714.json",
    "tests/validation_corpus/phase1_results_20260603_194859.json",
    "tests/validation_corpus/phase1_results_20260603_194028.json",
]

baseline_runs = []
for f in baseline_files:
    with open(f) as fh:
        d = json.load(fh)
    o = d["overall"]
    tp = o["total_tp"]
    fp = o["total_fp"]
    fn = o["total_fn"]
    prec = o["precision"]
    rec = o["recall"]
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    comp = o["composite_score"]
    baseline_runs.append({"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1, "composite": comp})

print("Post-Tightened baseline (3 runs):")
for i, r in enumerate(baseline_runs):
    print(f"  Run {i+1}: TP={r['tp']}, FP={r['fp']}, FN={r['fn']}, Prec={r['precision']:.4f}, Rec={r['recall']:.4f}, F1={r['f1']:.4f}, Comp={r['composite']:.2f}")

keys = ["tp", "fp", "fn", "precision", "recall", "f1", "composite"]
for key in keys:
    vals = [r[key] for r in baseline_runs]
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals) if len(vals) > 1 else 0
    print(f"  {key}: mean={mean:.4f}, sd={sd:.4f}")
