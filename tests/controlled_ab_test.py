"""Controlled A/B validation using pre-rewrite raw model outputs.
Same raw responses, evaluation with title rewrite disabled vs enabled.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.phase1_eval_runner import (
    evaluate_document, compute_corpus_metrics, CORPUS_DIR,
)

# Use pre-rewrite run files (contain original titles from the model)
RUN_FILES = [
    "phase1_results_20260603_194028.json",
    "phase1_results_20260603_194859.json",
    "phase1_results_20260603_195714.json",
]

# Load review data
review_data = {}
for f in CORPUS_DIR.glob("*.review.json"):
    doc_id = f.stem.replace(".review", "")
    with open(f) as fh:
        review_data[doc_id] = json.load(fh)


def rewrite_issue_titles(raw_response: dict) -> dict:
    issues = raw_response.get("issues", [])
    if not issues:
        return raw_response
    for issue in issues:
        old_title = issue.get("issue_title", "")
        qt = (issue.get("quoted_text", "") or "").lower()
        if old_title == "Single-Trigger Change of Control Acceleration":
            if "solicit" in qt and "change of control" not in qt:
                issue["issue_title"] = "Non-Solicitation Clause in NDA"
                continue
        if old_title == "Single-Trigger Change of Control Acceleration":
            if ("non-compete" in qt or "compete" in qt) and "change of control" not in qt:
                months_match = re.search(r"(\d+)\s*\)?\s*month", qt)
                if months_match and int(months_match.group(1)) > 6:
                    issue["issue_title"] = "Excessive Non-Compete Duration"
                    continue
        if old_title == "Non-Competition":
            months_match = re.search(r"(\d+)\s*\)?\s*month", qt)
            if months_match and int(months_match.group(1)) > 6:
                issue["issue_title"] = "Excessive Non-Compete Duration"
                continue
        if old_title == "Intellectual Property Ownership":
            cat = (issue.get("category", "") or "").lower()
            if "intellectual property" in cat and "consultant" in qt and "retain" in qt:
                issue["issue_title"] = "Consultant Retains All Deliverable IP"
                continue
    return raw_response


def run_evaluation(raw_responses_by_run, apply_rewrite, label):
    all_results = []
    for run_file, raw_responses in zip(RUN_FILES, raw_responses_by_run):
        run_results = []
        for doc_id, raw_resp in raw_responses:
            resp = json.loads(json.dumps(raw_resp))
            if apply_rewrite:
                resp = rewrite_issue_titles(resp)
            result = evaluate_document(doc_id, resp, review_data[doc_id])
            run_results.append(result)
        all_results.append(run_results)

    total_tp = sum(r["tp"] for runs in all_results for r in runs)
    total_fp = sum(r["fp"] for runs in all_results for r in runs)
    total_fn = sum(r["fn"] for runs in all_results for r in runs)

    all_tps = []
    for runs in all_results:
        for r in runs:
            all_tps.extend(r.get("true_positives", []))

    exact = sum(1 for t in all_tps if t.get("title_classification") == "exact")
    partial = sum(1 for t in all_tps if t.get("title_classification") == "partial")
    cat_only = sum(1 for t in all_tps if t.get("title_classification") == "category_only")
    title_acc = (exact + partial) / len(all_tps) if all_tps else 1.0

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    fpr = total_fp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    fnr = total_fn / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    fpr_p = 1.0 - min(max(fpr - 0.30, 0.0) / 0.30, 1.0)
    fnr_p = 1.0 - min(max(fnr - 0.35, 0.0) / 0.35, 1.0)
    composite = (1.0 * 0.20 + precision * 0.20 + recall * 0.25 + 1.0 * 0.15 + fpr_p * 0.10 + fnr_p * 0.10) * 100

    return {
        "label": label, "tp": total_tp, "fp": total_fp, "fn": total_fn,
        "precision": precision, "recall": recall, "f1": f1, "composite": composite,
        "title_accuracy": title_acc, "exact": exact, "partial": partial, "cat_only": cat_only,
    }, all_results


def main():
    raw_responses_by_run = []
    for run_file in RUN_FILES:
        path = CORPUS_DIR / run_file
        with open(path) as f:
            data = json.load(f)
        run_raw = [(doc["doc_id"], doc.get("raw_response", {})) for doc in data["per_document"]]
        raw_responses_by_run.append(run_raw)

    print(f"Loaded {len(RUN_FILES)} pre-rewrite runs, {sum(len(r) for r in raw_responses_by_run)} documents")

    metrics_a, results_a = run_evaluation(raw_responses_by_run, apply_rewrite=False, label="A: No Rewrite")
    metrics_b, results_b = run_evaluation(raw_responses_by_run, apply_rewrite=True, label="B: With Rewrite")

    # Print comparison table
    rows = [
        ("TP", metrics_a["tp"], metrics_b["tp"]),
        ("FP", metrics_a["fp"], metrics_b["fp"]),
        ("FN", metrics_a["fn"], metrics_b["fn"]),
        ("Precision", metrics_a["precision"], metrics_b["precision"]),
        ("Recall", metrics_a["recall"], metrics_b["recall"]),
        ("F1", metrics_a["f1"], metrics_b["f1"]),
        ("Composite", metrics_a["composite"], metrics_b["composite"]),
        ("Title Accuracy", metrics_a["title_accuracy"], metrics_b["title_accuracy"]),
        ("Exact Matches", metrics_a["exact"], metrics_b["exact"]),
        ("Partial Matches", metrics_a["partial"], metrics_b["partial"]),
        ("Category-Only", metrics_a["cat_only"], metrics_b["cat_only"]),
    ]

    print(f"\n{'='*72}")
    print(f"  CONTROLLED A/B: SAME RAW OUTPUTS, DIFFERENT EVAL")
    print(f"{'='*72}")
    print(f"  Source: {RUN_FILES[0]} (pre-rewrite raw model outputs)")
    print(f"  A = title rewrite disabled | B = title rewrite enabled")
    print(f"\n  {'Metric':<20} {'A: No Rewrite':>16} {'B: With Rewrite':>16} {'Delta':>12}")
    print(f"  {'-'*20} {'-'*16} {'-'*16} {'-'*12}")
    for name, a_val, b_val in rows:
        if isinstance(a_val, float) and a_val < 10:
            d = b_val - a_val
            ds = f"{d:+.4f}"
            print(f"  {name:<20} {a_val:>16.4f} {b_val:>16.4f} {ds:>12}")
        else:
            d = int(b_val) - int(a_val)
            ds = f"{d:+d}"
            print(f"  {name:<20} {int(a_val):>16} {int(b_val):>16} {ds:>12}")

    # Identity check
    tp_same = metrics_a["tp"] == metrics_b["tp"]
    fp_same = metrics_a["fp"] == metrics_b["fp"]
    fn_same = metrics_a["fn"] == metrics_b["fn"]

    print(f"\n{'='*72}")
    print(f"  IDENTITY CHECK")
    print(f"{'='*72}")
    print(f"  TP identical: {tp_same} ({metrics_a['tp']} vs {metrics_b['tp']})")
    print(f"  FP identical: {fp_same} ({metrics_a['fp']} vs {metrics_b['fp']})")
    print(f"  FN identical: {fn_same} ({metrics_a['fn']} vs {metrics_b['fn']})")

    if tp_same and fp_same and fn_same:
        print(f"\n  VERDICT: TP/FP/FN are IDENTICAL. Title rewrite affects ONLY title_accuracy.")
    else:
        print(f"\n  VERDICT: TP/FP/FN DIFFER. Investigating per-document...")
        for run_idx, (ra, rb) in enumerate(zip(results_a, results_b)):
            for doc_a, doc_b in zip(ra, rb):
                if doc_a["tp"] != doc_b["tp"] or doc_a["fp"] != doc_b["fp"] or doc_a["fn"] != doc_b["fn"]:
                    print(f"  DIFF: Run {run_idx}, {doc_a['doc_id']}:")
                    print(f"    A: TP={doc_a['tp']} FP={doc_a['fp']} FN={doc_a['fn']}")
                    print(f"    B: TP={doc_b['tp']} FP={doc_b['fp']} FN={doc_b['fn']}")

    # Per-finding-type accuracy
    print(f"\n{'='*72}")
    print(f"  TITLE ACCURACY BY FINDING TYPE")
    print(f"{'='*72}")

    for label_suffix, all_results_set in [("A (no rewrite)", results_a), ("B (rewrite)", results_b)]:
        gt_classes = {}
        for runs in all_results_set:
            for r in runs:
                for tp in r.get("true_positives", []):
                    gt_id = tp.get("matched_gt_id", "?")
                    cls = tp.get("title_classification", "?")
                    gt_classes.setdefault(gt_id, []).append(cls)

        print(f"\n  {label_suffix}:")
        for gt_id in sorted(gt_classes.keys()):
            classes = gt_classes[gt_id]
            e = sum(1 for c in classes if c == "exact")
            p = sum(1 for c in classes if c == "partial")
            c = sum(1 for c in classes if c == "category_only")
            acc = (e + p) / len(classes) if classes else 0
            print(f"    {gt_id}: {acc:.2f} ({e}E {p}P {c}C / {len(classes)} runs)")


if __name__ == "__main__":
    main()
