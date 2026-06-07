import requests
import json
import uuid
import os

BASE_URL = "http://localhost:8000"
TEST_DIR = "tests/test_contracts"

contracts = [
    ("TEST-SAAS-01.txt", "SaaS Subscription Agreement"),
    ("TEST-CONSULT-02.txt", "Master Services Agreement (Consulting)"),
    ("TEST-LICENSE-03.txt", "Software Licensing Agreement"),
    ("TEST-EMPLOY-04.txt", "Employment Agreement"),
    ("TEST-VENDOR-05.txt", "Vendor Services Agreement"),
]

all_results = []

for filename, contract_type in contracts:
    filepath = os.path.join(TEST_DIR, filename)
    
    print(f"\n{'=' * 72}")
    print(f"  {contract_type}")
    print(f"  File: {filename}")
    print(f"{'=' * 72}")
    
    # Read file content
    with open(filepath, "r") as f:
        content = f.read()
    
    word_count = len(content.split())
    print(f"  Word count: {word_count}")
    
    # Send to pipeline
    session_id = f"test-{uuid.uuid4().hex[:12]}"
    with open(filepath, "rb") as f:
        files = {"file": (filename, f, "text/plain")}
        data = {"session_id": session_id, "mode": "AUDIT", "response_format": "json"}
        
        try:
            resp = requests.post(f"{BASE_URL}/ask_file", files=files, data=data, timeout=180)
            result = resp.json()
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
    
    # Parse results
    issues = result.get("issues", [])
    confidence_score = result.get("confidence_score", 0)
    confidence_label = result.get("confidence_label", "N/A")
    parse_ok = not result.get("structured_parse_failed", False)
    
    print(f"\n  Confidence: {confidence_score:.4f} ({confidence_label})")
    print(f"  Parse OK: {parse_ok}")
    print(f"  Issues found: {len(issues)}")
    
    if issues:
        print(f"\n  RAW FINDINGS:")
        for i, issue in enumerate(issues, 1):
            print(f"\n  {i}. [{issue.get('severity', 'N/A')}] {issue.get('category', 'N/A')}")
            print(f"     Title: {issue.get('issue_title', 'N/A')}")
            print(f"     Location: {issue.get('location', 'N/A')}")
            print(f"     Quoted Text: {issue.get('quoted_text', 'N/A')[:100]}...")
            print(f"     Risk: {issue.get('risk_explanation', 'N/A')[:100]}...")
            print(f"     Fix: {issue.get('suggested_improvement', 'N/A')[:100]}...")
    else:
        print(f"\n  No issues found.")
    
    all_results.append({
        "filename": filename,
        "contract_type": contract_type,
        "word_count": word_count,
        "confidence_score": confidence_score,
        "confidence_label": confidence_label,
        "parse_ok": parse_ok,
        "issue_count": len(issues),
        "issues": issues,
    })

# Save results
with open("tests/test_contracts/results_after_p1.json", "w") as f:
    json.dump(all_results, f, indent=2)

print(f"\n\nResults saved to tests/test_contracts/results_after_p1.json")
