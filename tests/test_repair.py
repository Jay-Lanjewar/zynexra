import json
import sys
sys.path.insert(0, "D:\\Projects\\Zynexra")
from backend.engines.normalization_engine import repair_json, parse_audit_issues, extract_json_payload_candidates

# Simulate truncated model output (from actual debug log)
truncated = '{"issues":[{"issue_title":"Indemnification Risk","severity":"CRITICAL","category":"Indemnification Risk","location":"Section 12 Indemnification","quoted_text":"Such indemnification obligations shall be without limit and without cap.","risk_explanation":"The indemnification obligations are unlimited in duration.","suggested_improvement":"Vendor indemnification shall be capped at $500,000 per incident and aggreg'

print("=== Testing repair_json ===")
repaired = repair_json(truncated)
if repaired:
    print(f"repaired: {repaired[:100]}...")
    print(f"repaired ends: {repaired[-30:]}")
    try:
        parsed = json.loads(repaired)
        print("json.loads SUCCESS")
        if "issues" in parsed:
            print(f"Issues: {len(parsed['issues'])}")
            for i, iss in enumerate(parsed["issues"]):
                print(f"  Issue {i}: {iss.get('issue_title','')[:40]}")
    except json.JSONDecodeError as e:
        print(f"json.loads FAILED: {e}")
else:
    print("repair_json returned None")
    # Test with raw text candidate
    candidates = extract_json_payload_candidates(truncated)
    print(f"Candidates: {len(candidates)}")
    for i, c in enumerate(candidates):
        print(f"  Candidate {i}: {c[:50]}...")

print()
print("=== Testing parse_audit_issues ===")
issues = parse_audit_issues(truncated)
print(f"Issues found: {len(issues)}")
for iss in issues:
    print(f"  {iss.category}: {iss.severity}")
