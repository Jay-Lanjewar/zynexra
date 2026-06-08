"""
Phase 1 Error Attribution Trace Runner

For every document in the 10-doc corpus, traces the full lifecycle:
  raw_model_output → parse_audit_issues → normalize_severity → normalize_fields →
  document_level_BMI → standard_NDA_suppression → mutual_capped_indemnity_suppression →
  asymmetry_detection → contradiction_detection → contradiction_suppression →
  domain_detection → policy_detection → final_payload

Usage:
    python tests/phase1_trace_runner.py
"""

import json
import sys
import time
import uuid
import re
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
CORPUS_DIR = Path(__file__).resolve().parent / "validation_corpus"

# Import pipeline internals (no code modifications — calling existing functions)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.engines.normalization_engine import (
    parse_audit_issues,
    normalize_audit_issue_severity_fields,
    normalize_audit_issue_fields,
    suppress_balanced_mutual_indemnity_issues,
    _apply_document_level_bmi,
    _apply_standard_nda_suppression,
    _apply_mutual_capped_indemnity_suppression,
    _apply_asymmetry_detection,
    AuditIssue,
)
from backend.engines.contradiction_engine import (
    validate_contradictions,
    apply_contradiction_suppression,
    classify_document_contradictions,
)
from backend.engines.legal_domain_engine import compute_document_domain_confidence
from backend.engines.policy_detection_engine import detect_policy_document


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def send_file_raw(filepath: Path) -> dict:
    """Send document and return the full pipeline response."""
    session_id = f"trace-{uuid.uuid4().hex[:12]}"
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
        return {"error": f"JSON parse: {e}", "raw": resp.text[:500]}


def get_raw_model_output(doc_path: Path) -> str:
    """Make a direct inference call to get the raw LLM output before pipeline processing.
    We call the same endpoint but inspect the legacy_text to reconstruct the raw response.
    """
    resp = send_file_raw(doc_path)
    if "error" in resp:
        return f"<<ERROR: {resp['error']}>>"
    return resp.get("legacy_text", "")


def issue_to_dict(issue) -> dict:
    if isinstance(issue, dict):
        return issue
    return {
        "issue_title": getattr(issue, "issue_title", ""),
        "severity": getattr(issue, "severity", ""),
        "category": getattr(issue, "category", ""),
        "quoted_text": getattr(issue, "quoted_text", ""),
        "risk_explanation": getattr(issue, "risk_explanation", ""),
        "suggested_improvement": getattr(issue, "suggested_improvement", ""),
    }


def parse_legacy_text_to_issues(legacy_text: str):
    """Use the existing JSON parser first; fall back to reconstructing from legacy text."""
    if not legacy_text:
        return []
    issues = parse_audit_issues(legacy_text)
    return issues


def trace_pipeline_stages(user_input: str, raw_issues: list) -> list[dict]:
    """Run each pipeline stage sequentially and return state after each."""
    stages = []

    def snapshot(stage_name: str, issues: list, extra: dict = None):
        stages.append({
            "stage": stage_name,
            "issue_count": len(issues),
            "issues": [issue_to_dict(i) for i in issues],
            **(extra or {}),
        })

    # Stage 0: raw parsed
    snapshot("raw_parsed", raw_issues)

    # Stage 1: severity normalization
    issues = normalize_audit_issue_severity_fields(list(raw_issues))
    snapshot("severity_normalized", issues)

    # Stage 2: field normalization
    issues = normalize_audit_issue_fields(list(issues))
    snapshot("field_normalized", issues)

    # Stage 3: document-level BMI
    _apply_document_level_bmi(issues, user_input)
    snapshot("document_bmi", issues)

    # Stage 4: standard NDA suppression
    _apply_standard_nda_suppression(issues, user_input)
    snapshot("standard_nda_suppression", issues)

    # Stage 5: mutual capped indemnity suppression
    _apply_mutual_capped_indemnity_suppression(issues, user_input)
    snapshot("mutual_capped_indemnity_suppression", issues)

    # Stage 6: asymmetry detection
    _apply_asymmetry_detection(issues, user_input)
    snapshot("asymmetry_detection", issues)

    # Stage 7: contradiction detection + suppression
    contradictions = validate_contradictions(issues, user_input)
    if contradictions:
        snapshot("contradictions_detected", issues, {
            "contradiction_count": len(contradictions),
            "contradictions": [{"type": c.contradiction_type, "index": c.issue_index, "reason": c.reason} for c in contradictions],
        })
        issues = apply_contradiction_suppression(issues, contradictions)
        snapshot("contradiction_suppressed", issues)
    else:
        snapshot("contradictions_detected", issues, {"contradiction_count": 0})

    # Stage 8: contradiction classification
    classify_document_contradictions(issues, user_input)
    snapshot("contradiction_classified", issues)

    # Domain detection
    try:
        domain_result = compute_document_domain_confidence(user_input)
        domain_info = {
            "domain": domain_result.domain.value if hasattr(domain_result.domain, 'value') else str(domain_result.domain),
            "confidence": round(domain_result.confidence, 4),
            "is_non_legal": domain_result.domain.name == "NON_LEGAL",
        }
    except Exception as e:
        domain_info = {"domain": "ERROR", "error": str(e)}
    snapshot("domain_detection", issues, {"domain_info": domain_info})

    # Policy detection
    try:
        policy_result = detect_policy_document(user_input)
        policy_info = {
            "detection": policy_result.detection.value if hasattr(policy_result.detection, 'value') else str(policy_result.detection),
            "policy_type": policy_result.policy_type,
            "confidence": round(policy_result.confidence, 4),
            "is_policy": policy_result.detection.name == "POLICY",
        }
    except Exception as e:
        policy_info = {"detection": "ERROR", "error": str(e)}
    snapshot("policy_detection", issues, {"policy_info": policy_info})

    return stages


# ---------------------------------------------------------------------------
# Trace per document
# ---------------------------------------------------------------------------

def trace_document(doc_id: str):
    doc_path = CORPUS_DIR / f"{doc_id}.txt"
    meta_path = CORPUS_DIR / f"{doc_id}.meta.json"
    review_path = CORPUS_DIR / f"{doc_id}.review.json"

    with open(doc_path, "r", encoding="utf-8") as f:
        user_input = f.read()

    meta = {}
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)

    review = {}
    if review_path.exists():
        with open(review_path) as f:
            review = json.load(f)

    gt_issues = review.get("ground_truth", {}).get("issues", []) if review else []
    gt_count = len(gt_issues)
    red_flag = meta.get("red_flag", False)

    print(f"\n{'='*72}")
    print(f"  TRACE: {doc_id} — {meta.get('title', '')}")
    print(f"  Risk: {meta.get('risk_level', 'N/A')}  Red Flag: {red_flag}  GT Issues: {gt_count}")
    print(f"{'='*72}")

    # Step 1: Get pipeline response
    print("\n[STAGE 0] Pipeline call...")
    pipeline_result = send_file_raw(doc_path)

    if "error" in pipeline_result:
        print(f"  ERROR: {pipeline_result['error']}")
        return {
            "doc_id": doc_id,
            "error": pipeline_result["error"],
        }

    final_issues = pipeline_result.get("issues", [])
    response_type = pipeline_result.get("response_type", "audit")
    parse_failed = pipeline_result.get("structured_parse_failed", True)
    legacy_text = pipeline_result.get("legacy_text", "")
    conf_score = pipeline_result.get("confidence_score", 0)
    conf_label = pipeline_result.get("confidence_label", "N/A")

    print(f"  Response type: {response_type}")
    print(f"  Final issues: {len(final_issues)}")
    print(f"  Confidence: {conf_score:.4f} / {conf_label}")
    print(f"  Parse failed: {parse_failed}")
    print(f"  Legacy text length: {len(legacy_text)} chars")

    # Step 2: Inspect the upstream classifiers if response is non-audit
    if response_type == "non_legal":
        print(f"\n  [!!] DOMAIN DETECTION: Non-legal detected")
        print(f"    Content type: {pipeline_result.get('content_type', 'N/A')}")
        print(f"    Domain confidence: {pipeline_result.get('domain_confidence', 'N/A')}")
        print(f"    Legal keyword ratio: {pipeline_result.get('legal_keyword_ratio', 'N/A')}")
        print(f"    Structure score: {pipeline_result.get('structure_score', 'N/A')}")

        # Trace domain detection explicitly
        print(f"\n  [Manual domain trace...]")
        try:
            domain_result = compute_document_domain_confidence(user_input)
            print(f"    Domain: {domain_result.domain}")
            print(f"    Confidence: {domain_result.confidence:.4f}")
            print(f"    Legal keyword ratio: {domain_result.legal_keyword_ratio:.4f}")
            print(f"    Structure score: {domain_result.structure_score:.4f}")
            print(f"    Legal phrase density: {domain_result.legal_phrase_density:.4f}")
            print(f"    Non-legal penalty: {domain_result.non_legal_penalty:.4f}")
        except Exception as e:
            print(f"    Domain trace error: {e}")

        return {
            "doc_id": doc_id,
            "response_type": response_type,
            "failure_type": "domain_detection_failure",
            "pipeline_result": pipeline_result,
        }

    if response_type == "policy":
        print(f"\n  [!!] POLICY DETECTION: Policy detected")
        print(f"    Policy type: {pipeline_result.get('policy_type', 'N/A')}")
        print(f"    Policy confidence: {pipeline_result.get('policy_confidence', 'N/A')}")
        print(f"    Policy explanation: {pipeline_result.get('policy_explanation', 'N/A')}")

        print(f"\n  [Manual policy trace...]")
        try:
            policy_result = detect_policy_document(user_input)
            print(f"    Detection: {policy_result.detection}")
            print(f"    Policy type: {policy_result.policy_type}")
            print(f"    Confidence: {policy_result.confidence:.4f}")
            print(f"    Policy keyword score: {policy_result.policy_keyword_score:.4f}")
            print(f"    Contractual signal score: {policy_result.contractual_signal_score:.4f}")
            print(f"    Matched keywords: {policy_result.matched_policy_keywords}")
            print(f"    Matched contractual: {policy_result.matched_contractual_signals}")
        except Exception as e:
            print(f"    Policy trace error: {e}")

        return {
            "doc_id": doc_id,
            "response_type": response_type,
            "failure_type": "policy_detection_failure",
            "pipeline_result": pipeline_result,
        }

    # Step 3: For audit responses, trace the pipeline stages
    print(f"\n  [Parsing legacy_text for raw model output...]")
    raw_issues = parse_legacy_text_to_issues(legacy_text)
    print(f"  Raw model issues (parsed): {len(raw_issues)}")
    for i, iss in enumerate(raw_issues[:5]):
        d = issue_to_dict(iss)
        print(f"    [{i}] [{d['severity']}] {d['category']}: {d['issue_title'][:70]}")

    # Step 4: Run full pipeline trace
    print(f"\n  [Running pipeline stage trace...]")
    stages = trace_pipeline_stages(user_input, raw_issues)

    print(f"\n  {'Stage':<40} {'Issues':<7} {'Change':<10}")
    print(f"  {'-'*40} {'-'*7} {'-'*10}")
    prev_count = len(raw_issues)
    for s in stages:
        count = s["issue_count"]
        change = count - prev_count
        change_str = f"{'+' if change > 0 else ''}{change}" if change != 0 else "—"
        print(f"  {s['stage']:<40} {count:<7} {change_str:<10}")
        prev_count = count

        if s["stage"] == "standard_nda_suppression" and s.get("domain_info"):
            di = s["domain_info"]
            print(f"  {'':>42} Domain: {di['domain']} (conf={di['confidence']})")
        if s["stage"] == "policy_detection" and s.get("policy_info"):
            pi = s["policy_info"]
            print(f"  {'':>42} Policy: {pi['detection']} (conf={pi['confidence']}) type={pi['policy_type']}")

    # Show contradiction info if present
    contradictions_stage = next((s for s in stages if s["stage"] == "contradictions_detected"), None)
    if contradictions_stage and contradictions_stage.get("contradiction_count", 0) > 0:
        print(f"\n  Contradictions detected: {contradictions_stage['contradiction_count']}")
        for c in contradictions_stage.get("contradictions", []):
            print(f"    Type: {c['type']}  Index: {c['index']}  Reason: {c['reason'][:80]}")

    return {
        "doc_id": doc_id,
        "response_type": response_type,
        "final_issues": len(final_issues),
        "raw_issues": len(raw_issues),
        "stages": stages,
        "pipeline_result": pipeline_result,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    doc_ids = [
        "NDA-01", "NDA-02", "NDA-03", "NDA-04",
        "EMP-01", "EMP-02", "EMP-03",
        "VEN-01", "VEN-02", "VEN-03",
    ]

    traces = {}
    for doc_id in doc_ids:
        trace = trace_document(doc_id)
        traces[doc_id] = trace

    # Save full trace
    output_path = CORPUS_DIR / f"phase1_traces_{time.strftime('%Y%m%d_%H%M%S')}.json"
    # Convert non-serializable items
    def prepare(obj):
        if isinstance(obj, dict):
            return {k: prepare(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [prepare(v) for v in obj]
        elif isinstance(obj, AuditIssue):
            return issue_to_dict(obj)
        return obj

    with open(output_path, "w") as f:
        json.dump(prepare(traces), f, indent=2)
    print(f"\nTraces saved: {output_path}")


if __name__ == "__main__":
    main()
