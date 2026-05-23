import requests, uuid, sys

filepath = sys.argv[1] if len(sys.argv) > 1 else "tests/test_documents/unlimited_indemnity.txt"

with open(filepath, "rb") as f:
    files = {"file": (filepath, f, "text/plain")}
    data = {"session_id": "debug-" + uuid.uuid4().hex[:8], "mode": "AUDIT", "response_format": "json"}
    resp = requests.post("http://localhost:8000/ask_file", files=files, data=data, timeout=120)

print("Status:", resp.status_code)
result = resp.json()
print("Keys:", list(result.keys()))
print("issue_count:", result.get("issue_count"))
print("confidence_score:", result.get("confidence_score"))
print("confidence_label:", result.get("confidence_label"))
print("structured_parse_failed:", result.get("structured_parse_failed"))
print("fallback_used:", result.get("fallback_used"))
print("quality_warning:", result.get("quality_warning"))
print("metadata:", result.get("metadata"))
legacy = result.get("legacy_text", "")
print("legacy_text (first 800):", legacy[:800])
print("---")
issues = result.get("issues", [])
print("issues count:", len(issues))
if issues:
    for i, iss in enumerate(issues):
        print(f"Issue {i}: category={iss.get('category')}, severity={iss.get('severity')}, title={iss.get('issue_title')[:60]}")
