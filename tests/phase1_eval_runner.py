"""
Phase 1 Validation Suite — Evaluation Runner

Runs 10 documents through the pipeline, computes precision/recall/FPR/FNR/
severity accuracy / composite, and identifies every FP and FN.

Usage:
    python tests/phase1_eval_runner.py
"""

import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
CORPUS_DIR = Path(__file__).resolve().parent / "validation_corpus"


# ---------------------------------------------------------------------------
# 0. Title rewrite layer (mirrors normalization_engine.rewrite_mislabeled_titles)
# ---------------------------------------------------------------------------

def rewrite_issue_titles(raw_response: dict) -> dict:
    """Apply deterministic title rewrites to raw LLM issues.
    This mirrors the rewrite_mislabeled_titles function in normalization_engine
    so that the eval runner measures post-rewrite title accuracy.
    """
    issues = raw_response.get("issues", [])
    if not issues:
        return raw_response

    for issue in issues:
        old_title = issue.get("issue_title", "")
        qt = (issue.get("quoted_text", "") or "").lower()

        # Rule 1: Non-solicitation mislabeled as Single-Trigger CoC
        if old_title == "Single-Trigger Change of Control Acceleration":
            if "solicit" in qt and "change of control" not in qt:
                issue["issue_title"] = "Non-Solicitation Clause in NDA"
                continue

        # Rule 2: Non-compete mislabeled as Single-Trigger CoC
        if old_title == "Single-Trigger Change of Control Acceleration":
            if ("non-compete" in qt or "compete" in qt) and "change of control" not in qt:
                months_match = re.search(r"(\d+)\s*\)?\s*month", qt)
                if months_match and int(months_match.group(1)) > 6:
                    issue["issue_title"] = "Excessive Non-Compete Duration"
                    continue

        # Rule 3: Generic "Non-Competition" with excessive duration
        if old_title == "Non-Competition":
            months_match = re.search(r"(\d+)\s*\)?\s*month", qt)
            if months_match and int(months_match.group(1)) > 6:
                issue["issue_title"] = "Excessive Non-Compete Duration"
                continue

        # Rule 4: Generic "IP Ownership" in consultant context
        if old_title == "Intellectual Property Ownership":
            cat = (issue.get("category", "") or "").lower()
            if "intellectual property" in cat and "consultant" in qt and "retain" in qt:
                issue["issue_title"] = "Consultant Retains All Deliverable IP"
                continue

    return raw_response


# ---------------------------------------------------------------------------
# 0b. Mismatched title suppression layer (mirrors normalization_engine)
# ---------------------------------------------------------------------------

_TITLE_TOPIC_WORDS = {
    "non-compete": ["non-compete", "compete", "competition", "non-competition", "restrictive"],
    "non-solicitation": ["solicit", "solicitation", "recruit", "hire", "poach"],
    "confidentiality": ["confidential", "confidentiality", "disclosure", "proprietary", "trade secret"],
    "indemnification": ["indemnif", "hold harmless", "defend"],
    "liability": ["liability", "damages", "loss", "indirect", "consequential", "cap", "exceed"],
    "intellectual property": ["intellectual property", "patent", "copyright", "invention", "deliverable", "ip "],
    "change of control": ["change of control", "merger", "acquisition", "consolidation", "coc"],
    "termination": ["termination", "terminate", "cancel", "expire"],
    "governing law": ["governing law", "jurisdiction", "venue", "forum"],
    "warranty": ["warranty", "warrant", "guarantee", "representation", "fitness"],
    "survival": ["survive", "survival", "surviving", "remain in effect"],
    "excessive duration": ["excessive", "unreasonable", "duration", "eighteen", "twelve", "months"],
    "asymmetric": ["asymmetric", "one-sided", "unilateral", "unequal"],
    "perpetual": ["perpetual", "perpetually", "indefinite", "in perpetuity", "without limit"],
    "no sla": ["service level", "uptime", "availability", "sla"],
}

_STOP_WORDS = {
    "the", "a", "an", "in", "of", "for", "to", "and", "or", "is", "are", "was",
    "be", "this", "that", "with", "from", "on", "at", "by", "as", "not", "no",
    "agreement", "clause", "section", "provision", "risk", "weakness", "improper",
    "weakness", "exposure", "omission", "termination", "failure",
}


def _extract_topic_words_eval(title: str):
    title_lower = title.lower()
    words = re.findall(r"[a-z][a-z-]+", title_lower)
    return [w for w in words if w not in _STOP_WORDS and len(w) > 2]


def suppress_mismatched_title_findings_eval(raw_response: dict) -> dict:
    """Suppress findings where quoted text shares no topic words with the title."""
    issues = raw_response.get("issues", [])
    if not issues:
        return raw_response

    kept = []
    for issue in issues:
        title = (issue.get("issue_title", "") or "").lower()
        qt = (issue.get("quoted_text", "") or "").lower()
        if not qt or not title:
            kept.append(issue)
            continue
        topic_words = _extract_topic_words_eval(title)
        if not topic_words:
            kept.append(issue)
            continue
        qt_tokens = set(re.findall(r"[a-z][a-z-]+", qt))
        matched = False
        for tw in topic_words:
            if tw in qt_tokens:
                matched = True
                break
            tw_parts = tw.split("-")
            for qt_tok in qt_tokens:
                if qt_tok.startswith(tw) or tw.startswith(qt_tok):
                    matched = True
                    break
                qt_parts = qt_tok.split("-")
                for tp in tw_parts:
                    for qp in qt_parts:
                        if len(tp) > 3 and len(qp) > 3:
                            if tp.startswith(qp) or qp.startswith(tp):
                                matched = True
                                break
                            min_len = min(len(tp), len(qp))
                            root_len = max(5, min_len - 2)
                            if tp[:root_len] == qp[:root_len]:
                                matched = True
                                break
                    if matched:
                        break
                if matched:
                    break
            if matched:
                break
        if matched:
            kept.append(issue)

    raw_response["issues"] = kept
    return raw_response


# ---------------------------------------------------------------------------
# 1. Pipeline adapter
# ---------------------------------------------------------------------------

def send_document(filepath: Path) -> dict:
    session_id = f"phase1-{uuid.uuid4().hex[:12]}"
    with open(filepath, "rb") as f:
        files = {"file": (filepath.name, f, "text/plain")}
        data = {"session_id": session_id, "mode": "AUDIT", "response_format": "json"}
        try:
            resp = requests.post(f"{BASE_URL}/ask_file", files=files, data=data, timeout=180)
        except Exception as e:
            return {"error": str(e)}
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:500]}
    try:
        return resp.json()
    except Exception as e:
        return {"error": f"JSON parse failed: {e}", "raw": resp.text[:500]}


# ---------------------------------------------------------------------------
# 2. Ground-truth matching logic
# ---------------------------------------------------------------------------

def normalize_text(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").lower()).strip()


def issue_matches_ground_truth(issue: dict, gt_issue: dict) -> tuple[bool, dict]:
    """Check if a pipeline issue matches a ground-truth issue.
    Returns (matched, details).
    """
    issue_cat = issue.get("category", "")
    issue_sev = issue.get("severity", "").upper()
    issue_title = issue.get("issue_title", "")
    issue_qt = normalize_text(issue.get("quoted_text", ""))
    issue_exp = normalize_text(issue.get("risk_explanation", ""))

    details = {
        "category_match": False,
        "severity_match": False,
        "title_match": False,
        "quoted_text_match": True,  # default true if no patterns
        "explanation_match": True,  # default true if no patterns
    }

    # Category check
    allowed_cats = [c.lower() for c in gt_issue.get("allowed_categories", [])]
    details["category_match"] = issue_cat.lower() in allowed_cats

    # Severity check
    allowed_sevs = [s.upper() for s in gt_issue.get("allowed_severities", [])]
    details["severity_match"] = issue_sev in allowed_sevs

    # Title content match (bonus, not required)
    expected_title_words = gt_issue.get("expected_issue_title", "").lower().split()
    details["title_match"] = any(w in issue_title.lower() for w in expected_title_words)

    # Quoted text patterns (required if specified)
    must_contain_qt = gt_issue.get("must_contain_quoted_text_pattern", [])
    if must_contain_qt:
        qt_ok = any(p.lower() in issue_qt for p in must_contain_qt)
        details["quoted_text_match"] = qt_ok

    must_not_contain_qt = gt_issue.get("must_not_contain_quoted_text_pattern", [])
    if must_not_contain_qt:
        qt_not_ok = any(p.lower() in issue_qt for p in must_not_contain_qt)
        if qt_not_ok:
            details["quoted_text_match"] = False

    # Explanation patterns (required if specified)
    must_contain_exp = gt_issue.get("must_contain_explanation_pattern", [])
    if must_contain_exp:
        exp_ok = any(p.lower() in issue_exp for p in must_contain_exp)
        details["explanation_match"] = exp_ok

    must_not_contain_exp = gt_issue.get("must_not_contain_explanation_pattern", [])
    if must_not_contain_exp:
        exp_not_ok = any(p.lower() in issue_exp for p in must_not_contain_exp)
        if exp_not_ok:
            details["explanation_match"] = False

    required_ok = (
        details["category_match"]
        and details["severity_match"]
        and details["quoted_text_match"]
        and details["explanation_match"]
    )

    return required_ok, details


def classify_title_match(issue_title: str, gt_title: str) -> str:
    """Classify the title relationship between a pipeline issue and ground truth.
    Returns: 'exact', 'partial', or 'category_only'.
    """
    issue_norm = normalize_text(issue_title)
    gt_norm = normalize_text(gt_title)
    if issue_norm == gt_norm:
        return "exact"
    gt_words = set(gt_norm.split())
    issue_words = set(issue_norm.split())
    if gt_words & issue_words:
        return "partial"
    return "category_only"


# ---------------------------------------------------------------------------
# 3. Evaluator
# ---------------------------------------------------------------------------

def evaluate_document(doc_id: str, pipeline_result: dict, review_data: dict) -> dict:
    gt = review_data["ground_truth"]
    weights = review_data["evaluation_weights"]

    # Parse check
    parse_ok = (
        "error" not in pipeline_result
        and pipeline_result.get("structured_parse_failed") is False
    )
    parse_should_succeed = gt.get("parse_should_succeed", True)

    pipeline_issues = pipeline_result.get("issues", [])
    gt_issues = gt.get("issues", [])

    # Match each pipeline issue to a ground-truth issue
    tp_issues = []  # pipeline issues that matched
    fp_issues = []  # pipeline issues that did not match
    matched_gt_indices = set()

    for p_issue in pipeline_issues:
        best_match = None
        best_details = None
        for gt_idx, gt_issue in enumerate(gt_issues):
            matched, details = issue_matches_ground_truth(p_issue, gt_issue)
            if matched:
                best_match = gt_idx
                best_details = details
                break  # first match wins

        if best_match is not None:
            gt_title = gt_issues[best_match].get("expected_issue_title", "")
            title_class = classify_title_match(p_issue.get("issue_title", ""), gt_title)
            best_details["title_classification"] = title_class
            tp_issues.append((p_issue, best_match, best_details))
            matched_gt_indices.add(best_match)
        else:
            fp_issues.append(p_issue)

    # False negatives: ground-truth issues that were not matched
    fn_issues = []
    for gt_idx, gt_issue in enumerate(gt_issues):
        if gt_idx not in matched_gt_indices:
            fn_issues.append(gt_issue)

    # Metrics
    tp = len(tp_issues)
    fp = len(fp_issues)
    fn = len(fn_issues)
    gt_total = len(gt_issues)

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if gt_total == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if gt_total == 0 else 0.0)

    # Severity accuracy: among TPs, how many have correct severity
    sev_correct = 0
    for _, gt_idx, det in tp_issues:
        if det["severity_match"]:
            sev_correct += 1
    severity_accuracy = sev_correct / tp if tp > 0 else 1.0

    # Title accuracy: among TPs, how many have correct/matching title
    title_exact = sum(1 for _, _, det in tp_issues if det.get("title_classification") == "exact")
    title_partial = sum(1 for _, _, det in tp_issues if det.get("title_classification") == "partial")
    title_cat_only = sum(1 for _, _, det in tp_issues if det.get("title_classification") == "category_only")
    title_accuracy = (title_exact + title_partial) / tp if tp > 0 else 1.0
    title_overlap_rate = title_accuracy

    pass_flag = True
    fail_reasons = []

    if parse_should_succeed and not parse_ok:
        pass_flag = False
        fail_reasons.append("parse_failed")

    # Check for catastrophic FN on red-flag docs
    review_meta = review_data
    if review_meta:
        meta_path = CORPUS_DIR / f"{doc_id}.meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            if meta.get("red_flag") and tp == 0 and gt_total > 0:
                pass_flag = False
                fail_reasons.append("catastrophic_false_negative")

    if gt_total > 0:
        if tp < gt_total:
            pass_flag = False
            fail_reasons.append(f"missing {gt_total - tp}/{gt_total} findings")
        if fp > 0:
            pass_flag = False
            fail_reasons.append(f"{fp} false positive(s)")

    return {
        "doc_id": doc_id,
        "pass": pass_flag,
        "fail_reasons": fail_reasons,
        "parse_ok": parse_ok,
        "issue_count": len(pipeline_issues),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "gt_count": gt_total,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "severity_accuracy": round(severity_accuracy, 4),
        "title_accuracy": round(title_accuracy, 4),
        "exact_title_matches": title_exact,
        "partial_title_matches": title_partial,
        "title_mismatched_tps": title_cat_only,
        "title_overlap_rate": round(title_overlap_rate, 4),
        "confidence_score": pipeline_result.get("confidence_score", 0),
        "confidence_label": pipeline_result.get("confidence_label", "N/A"),
        "categories": [i.get("category", "") for i in pipeline_issues],
        "false_positives": [
            {
                "issue_title": i.get("issue_title", ""),
                "severity": i.get("severity", ""),
                "category": i.get("category", ""),
            }
            for i in fp_issues
        ],
        "false_negatives": [
            {
                "expected_issue_title": i.get("expected_issue_title", ""),
                "expected_severity": i.get("expected_severity", ""),
                "expected_category": i.get("expected_category", ""),
                "rationale": i.get("rationale", ""),
            }
            for i in fn_issues
        ],
        "true_positives": [
            {
                "issue_title": p[0].get("issue_title", ""),
                "severity": p[0].get("severity", ""),
                "category": p[0].get("category", ""),
                "matched_gt_id": gt_issues[p[1]].get("id", ""),
                "matched_gt_title": gt_issues[p[1]].get("expected_issue_title", ""),
                "title_classification": p[2].get("title_classification", "unknown"),
                "details": p[2],
            }
            for p in tp_issues
        ],
        "raw_response": pipeline_result,
    }


# ---------------------------------------------------------------------------
# 4. Aggregation
# ---------------------------------------------------------------------------

def compute_corpus_metrics(results: list) -> dict:
    total_tp = sum(r["tp"] for r in results)
    total_fp = sum(r["fp"] for r in results)
    total_fn = sum(r["fn"] for r in results)
    total_gt = sum(r["gt_count"] for r in results)

    parse_success_count = sum(1 for r in results if r["parse_ok"] and "error" not in str(r.get("raw_response", {})))
    parse_success_rate = parse_success_count / len(results) if results else 0

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    fpr = total_fp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    fnr = total_fn / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0

    # Severity accuracy: weighted average across docs
    sev_total_tp = sum(
        r["tp"] for r in results
    )
    sev_correct = sum(
        r["tp"] * r["severity_accuracy"] for r in results
    )
    severity_accuracy = sev_correct / sev_total_tp if sev_total_tp > 0 else 0

    # Title accuracy: weighted average across docs
    total_exact = sum(r["exact_title_matches"] for r in results)
    total_partial = sum(r["partial_title_matches"] for r in results)
    total_cat_only = sum(r["title_mismatched_tps"] for r in results)
    title_accuracy = (total_exact + total_partial) / sev_total_tp if sev_total_tp > 0 else 0

    # Composite (same weighting as design spec)
    parse_weight = 0.20
    precision_weight = 0.20
    recall_weight = 0.25
    severity_weight = 0.15
    fpr_penalty_weight = 0.10
    fnr_penalty_weight = 0.10

    fpr_penalty = 1.0 - min(max(fpr - 0.30, 0.0) / 0.30, 1.0)
    fnr_penalty = 1.0 - min(max(fnr - 0.35, 0.0) / 0.35, 1.0)

    composite = (
        parse_success_rate * parse_weight
        + precision * precision_weight
        + recall * recall_weight
        + severity_accuracy * severity_weight
        + fpr_penalty * fpr_penalty_weight
        + fnr_penalty * fnr_penalty_weight
    )

    return {
        "parse_success_rate": round(parse_success_rate, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "severity_accuracy": round(severity_accuracy, 4),
        "title_accuracy": round(title_accuracy, 4),
        "exact_title_matches": total_exact,
        "partial_title_matches": total_partial,
        "title_mismatched_tps": total_cat_only,
        "composite_score": round(composite * 100, 2),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "total_gt": total_gt,
        "documents_parsed": parse_success_count,
        "documents_total": len(results),
    }


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------

WARMUP_DOC = "NDA-01"


def warmup_inference() -> None:
    """Run one warm-up inference to eliminate GPU cold-start variance."""
    doc_path = CORPUS_DIR / f"{WARMUP_DOC}.txt"
    if not doc_path.exists():
        return
    print(f"  Warming up model (sending {WARMUP_DOC})...")
    try:
        result = send_document(doc_path)
        n = len(result.get("issues", []))
        print(f"  Warm-up done ({n} issues, parse_ok={not result.get('structured_parse_failed', False)}).")
    except Exception:
        print("  Warm-up failed (continuing anyway).")


def main():
    print("=" * 72)
    print("  ZYNEXRA — PHASE 1 VALIDATION SUITE")
    print(f"  Target: {BASE_URL}")
    print(f"  Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    warmup_inference()

    # Load document order
    doc_ids = [
        "NDA-01", "NDA-02", "NDA-03", "NDA-04",
        "EMP-01", "EMP-02", "EMP-03",
        "VEN-01", "VEN-02", "VEN-03",
    ]

    results = []
    errors = []

    for doc_id in doc_ids:
        doc_path = CORPUS_DIR / f"{doc_id}.txt"
        review_path = CORPUS_DIR / f"{doc_id}.review.json"

        if not doc_path.exists():
            print(f"  [SKIP] {doc_id}: document file not found")
            continue
        if not review_path.exists():
            print(f"  [SKIP] {doc_id}: review file not found")
            continue

        with open(review_path) as f:
            review_data = json.load(f)

        print(f"\n--- {doc_id} {'-' * (66 - len(doc_id))}")
        print(f"  Sending to pipeline...")

        pipeline_result = send_document(doc_path)

        if "error" in pipeline_result:
            print(f"  ERROR: {pipeline_result['error']}")
            errors.append((doc_id, pipeline_result["error"]))
            results.append({
                "doc_id": doc_id,
                "pass": False,
                "fail_reasons": [pipeline_result["error"]],
                "parse_ok": False,
                "issue_count": 0,
                "tp": 0, "fp": 0, "fn": 0, "gt_count": len(review_data["ground_truth"].get("issues", [])),
                "precision": 0, "recall": 0, "severity_accuracy": 0,
                "title_accuracy": 1.0, "exact_title_matches": 0,
                "partial_title_matches": 0, "title_mismatched_tps": 0,
                "title_overlap_rate": 1.0,
                "confidence_score": 0, "confidence_label": "ERROR",
                "categories": [],
                "false_positives": [], "false_negatives": [], "true_positives": [],
                "raw_response": pipeline_result,
            })
            continue

        issues = pipeline_result.get("issues", [])
        print(f"  Issues: {len(issues)}  Score: {pipeline_result.get('confidence_score', 0):.4f}  "
              f"Label: {pipeline_result.get('confidence_label', 'N/A')}")

        # Apply title rewrites to match normalization layer behavior
        pipeline_result = rewrite_issue_titles(pipeline_result)
        pipeline_result = suppress_mismatched_title_findings_eval(pipeline_result)

        result = evaluate_document(doc_id, pipeline_result, review_data)
        results.append(result)

        icon = "PASS" if result["pass"] else "FAIL"
        print(f"  [{icon}]  TP={result['tp']} FP={result['fp']} FN={result['fn']}  "
              f"Prec={result['precision']:.3f} Rec={result['recall']:.3f} SevAcc={result['severity_accuracy']:.3f}")

        if result["false_positives"]:
            print(f"    FALSE POSITIVES:")
            for fp in result["false_positives"]:
                print(f"      - [{fp['severity']}] {fp['category']}: {fp['issue_title'][:80]}")

        if result["false_negatives"]:
            print(f"    FALSE NEGATIVES:")
            for fn in result["false_negatives"]:
                print(f"      - [{fn['expected_severity']}] {fn['expected_category']}: {fn['expected_issue_title'][:80]}")

        if result["true_positives"]:
            for tp in result["true_positives"]:
                tc = tp.get("title_classification", "?")
                print(f"    TP: [{tp['severity']}] {tp['category']}: {tp['issue_title'][:70]} -> {tp['matched_gt_id']} ({tc})")

        if result["fail_reasons"]:
            for r in result["fail_reasons"]:
                print(f"    reason: {r}")

    # Compute corpus-wide metrics
    print(f"\n{'=' * 72}")
    print("  CORPUS-WIDE RESULTS")
    print(f"{'=' * 72}")

    metrics = compute_corpus_metrics(results)
    passed = sum(1 for r in results if r["pass"])
    failed = sum(1 for r in results if not r["pass"])

    print(f"  Documents: {passed}/{len(results)} passed, {failed}/{len(results)} failed")
    print(f"  Parse success rate:  {metrics['parse_success_rate']:.2%}")
    print(f"  Precision:           {metrics['precision']:.4f}  ({metrics['total_tp']} TP / {metrics['total_tp'] + metrics['total_fp']} predicted)")
    print(f"  Recall:              {metrics['recall']:.4f}  ({metrics['total_tp']} TP / {metrics['total_gt']} ground truth)")
    print(f"  False Positive Rate: {metrics['false_positive_rate']:.4f}")
    print(f"  False Negative Rate: {metrics['false_negative_rate']:.4f}")
    print(f"  Severity Accuracy:   {metrics['severity_accuracy']:.4f}")
    print(f"  Title Accuracy:      {metrics['title_accuracy']:.4f}  ({metrics['exact_title_matches']} exact + {metrics['partial_title_matches']} partial / {metrics['total_tp']} TP)")
    print(f"  Title Mismatched:    {metrics['title_mismatched_tps']}  (category-only matches)")
    print(f"  Composite Score:     {metrics['composite_score']:.2f} / 100")

    # Per-type breakdown
    print(f"\n{'=' * 72}")
    print("  PER-TYPE BREAKDOWN")
    print(f"{'=' * 72}")

    for dtype, prefix in [("NDA", "NDA"), ("Employment", "EMP"), ("Vendor", "VEN")]:
        type_results = [r for r in results if r["doc_id"].startswith(prefix)]
        if type_results:
            type_metrics = compute_corpus_metrics(type_results)
            print(f"  {dtype} ({len(type_results)} docs): "
                  f"Prec={type_metrics['precision']:.3f} Rec={type_metrics['recall']:.3f} "
                  f"TitleAcc={type_metrics['title_accuracy']:.3f} "
                  f"Comp={type_metrics['composite_score']:.1f} "
                  f"Parse={type_metrics['parse_success_rate']:.0%}")

    # Summary per-document
    print(f"\n{'=' * 72}")
    print("  PER-DOCUMENT RESULTS")
    print(f"{'=' * 72}")
    print(f"  {'ID':<8} {'Result':<6} {'Issues':<7} {'TP':<4} {'FP':<4} {'FN':<4} {'Prec':<6} {'Rec':<6} {'Sev':<6}")
    print(f"  {'-'*8} {'-'*6} {'-'*7} {'-'*4} {'-'*4} {'-'*4} {'-'*6} {'-'*6} {'-'*6}")
    for r in results:
        status = "PASS" if r["pass"] else "FAIL"
        cat_list = ", ".join(r["categories"][:3]) if r["categories"] else "(none)"
        print(f"  {r['doc_id']:<8} {status:<6} {r['issue_count']:<7} {r['tp']:<4} "
              f"{r['fp']:<4} {r['fn']:<4} {r['precision']:<6.3f} {r['recall']:<6.3f} "
              f"{r['severity_accuracy']:<6.3f}  [{cat_list}]")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for doc_id, err in errors:
            print(f"    {doc_id}: {err}")

    print(f"\n{'=' * 72}")

    # Save results
    output = {
        "run_id": f"phase1-{time.strftime('%Y%m%d_%H%M%S')}",
        "model": "qwen2.5:3b-instruct",
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "corpus": {"documents": len(results), "nda": 4, "employment": 3, "vendor": 3},
        "overall": metrics,
        "per_document": results,
    }

    output_path = CORPUS_DIR / f"phase1_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Results saved: {output_path}")
    print()

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
