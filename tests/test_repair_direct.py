import json, re, sys
sys.path.insert(0, "D:\\Projects\\Zynexra")
from backend.logger import logger
import logging
logging.basicConfig(level=logging.DEBUG)

from backend.engines.normalization_engine import repair_json, extract_json_payload_candidates, _try_parse_json, parse_audit_issues

# Simulate the actual truncated output from the model
# (taken from the debug request output - truncated version)
text = '{\n  "issues": [\n    {\n      "issue_title": "Indemnification Risk",\n      "severity": "CRITICAL",\n      "category": "Indemnification Risk",\n      "location": "Section 12. Indemnification",\n      "quoted_text": "Such indemnification obligations shall be without limit and without cap.",\n      "risk_explanation": "The clause provides unlimited and uncapable indemnification obligations.",\n      "suggested_improveme'

print("=== extract_json_payload_candidates ===")
candidates = extract_json_payload_candidates(text)
print(f"Candidates: {len(candidates)}")
for i, c in enumerate(candidates):
    print(f"  [{i}] len={len(c)}, starts={repr(c[:30])}, ends={repr(c[-30:])}")

print()
print("=== repair_json on raw text ===")
repaired = repair_json(text)
if repaired:
    print(f"repaired len={len(repaired)}")
    print(f"repaired starts: {repr(repaired[:60])}")
    print(f"repaired ends:   {repr(repaired[-60:])}")
    try:
        obj = json.loads(repaired)
        print("json.loads SUCCESS")
        if "issues" in obj:
            print(f"Issues found: {len(obj['issues'])}")
            for i, iss in enumerate(obj["issues"]):
                print(f"  [{i}] title={iss.get('issue_title','')[:30]}, severity={iss.get('severity')}")
    except json.JSONDecodeError as e:
        print(f"json.loads FAILED: {e}")
        print(f"Error near: ...{repaired[max(0, e.pos-40):e.pos+40]}...")
else:
    print("repair_json returned None")

print()
print("=== _try_parse_json ===")
result = _try_parse_json(text)
if result:
    print(f"Found {len(result)} issues")
    for iss in result:
        print(f"  {iss.category}: {iss.severity}")
else:
    print("_try_parse_json returned None")

print()
print("=== parse_audit_issues ===")
issues = parse_audit_issues(text)
print(f"Issues: {len(issues)}")
for iss in issues:
    print(f"  {iss.category}: {iss.severity}, title={iss.issue_title[:30]}, improvement={iss.suggested_improvement[:20]}")
