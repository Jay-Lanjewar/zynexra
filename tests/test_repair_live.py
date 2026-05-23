import json

from backend.engines.normalization_engine import repair_json, _try_parse_json, extract_json_payload_candidates, parse_audit_issues

# Simulate the truncated model output from the live run
truncated = '{"issues":[{"issue_title":"Indemnification Risk","severity":"CRITICAL","category":"Indemnification Risk","location":"Section 12 Indemnification","quoted_text":"Such indemnification obligations shall be without limit and without cap. Vendor\'s indemnification obligations under this Section 12 shall survive any termination or expiration of this Agreement and shall continue in full force and effect indefinitely.","risk_explanation":"The indemnification obligations are unlimited in duration and amount, which creates an uncontrolled risk for the Company if Vendor breaches the agreement. The lack of a cap on damages also exposes the Company to potentially unlimited liability.","suggested_improvement":"Vendor\'s indemnification obligations under this Section 12 shall be capped at $500,000 per claim'

print('Input len:', len(truncated))
print('Input ends with:', repr(truncated[-80:]))
print()

# Test 1: repair_json directly
repaired = repair_json(truncated)
print('Repair output len:', len(repaired))
print('Repair ends with:', repr(repaired[-80:]))
print()
try:
    parsed = json.loads(repaired)
    issues = parsed.get('issues', [])
    print('Test 1 - JSON valid! Issues:', len(issues))
    for iss in issues:
        print(' -', iss.get('issue_title'), '|', iss.get('severity'), '|', iss.get('category'))
except json.JSONDecodeError as e:
    print('Test 1 - JSON still invalid:', e)

print()

# Test 2: _try_parse_json
result = _try_parse_json(truncated)
print('Test 2 - _try_parse_json result:', result)

print()

# Test 3: extract_json_payload_candidates
candidates = extract_json_payload_candidates(truncated)
print('Test 3 - candidates:', len(candidates))
for i, c in enumerate(candidates):
    print(f'  [{i}] len={len(c)}, first 80={c[:80]}')

print()

# Test 4: parse_audit_issues
issues = parse_audit_issues(truncated)
print('Test 4 - parse_audit_issues issues:', len(issues))
for iss in issues:
    print(' -', iss.get('issue_title'), '|', iss.get('severity'))
