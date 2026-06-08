import json

with open("tests/validation_corpus/phase1_results_20260605_210035.json") as f:
    before = json.load(f)
with open("tests/validation_corpus/phase1_results_20260606_152435.json") as f:
    after = json.load(f)

b = before["overall"]
a = after["overall"]

print("BEFORE P3 (P1+P2 only) run 20260605_210035:")
print(f"  TP={b['total_tp']}, FP={b['total_fp']}, FN={b['total_fn']}")
print(f"  Precision={b['precision']:.4f}, Recall={b['recall']:.4f}")
print(f"  Composite={b['composite_score']:.2f}")
print(f"  Title Accuracy={b['title_accuracy']:.4f}")
print(f"  Pass: {sum(1 for d in before['per_document'] if d['pass'])}/10")
print()
print("AFTER P3 (P1+P2+P3) run 20260606_152435:")
print(f"  TP={a['total_tp']}, FP={a['total_fp']}, FN={a['total_fn']}")
print(f"  Precision={a['precision']:.4f}, Recall={a['recall']:.4f}")
print(f"  Composite={a['composite_score']:.2f}")
print(f"  Title Accuracy={a['title_accuracy']:.4f}")
print(f"  Pass: {sum(1 for d in after['per_document'] if d['pass'])}/10")
print()
print("DELTA:")
print(f"  TP: {b['total_tp']} -> {a['total_tp']} ({a['total_tp']-b['total_tp']:+d})")
print(f"  FP: {b['total_fp']} -> {a['total_fp']} ({a['total_fp']-b['total_fp']:+d})")
print(f"  FN: {b['total_fn']} -> {a['total_fn']} ({a['total_fn']-b['total_fn']:+d})")
print(f"  Precision: {b['precision']:.4f} -> {a['precision']:.4f} ({a['precision']-b['precision']:+.4f})")
print(f"  Recall: {b['recall']:.4f} -> {a['recall']:.4f} ({a['recall']-b['recall']:+.4f})")
print(f"  Composite: {b['composite_score']:.2f} -> {a['composite_score']:.2f} ({a['composite_score']-b['composite_score']:+.2f})")
print(f"  Title Acc: {b['title_accuracy']:.4f} -> {a['title_accuracy']:.4f} ({a['title_accuracy']-b['title_accuracy']:+.4f})")
