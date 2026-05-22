"""
Zynexra Regression Test Runner

Sends test documents to /ask_file in AUDIT+JSON mode,
validates response fields, and prints PASS/FAIL summary.

Usage:
    python tests/regression_runner.py              (defaults to localhost:8000)
    python tests/regression_runner.py --url http://192.168.1.100:8000
"""

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
TEST_DIR = Path(__file__).resolve().parent / "test_documents"

PASS_ICON = "\u2705"
FAIL_ICON = "\u274C"

results = []


# ---------------------------------------------------------------------------
# Test definitions
# ---------------------------------------------------------------------------

def test_clean_nda():
    filepath = TEST_DIR / "clean_nda.txt"
    data = send_file(filepath)

    name = "clean_nda"
    passed = True
    reasons = []

    score = data.get("confidence_score", 0)
    label = data.get("confidence_label", "N/A")
    issue_count = data.get("issue_count", 0)
    quality_warning = data.get("quality_warning", "")
    issues = data.get("issues", [])

    if label == "LOW":
        passed = False
        reasons.append(f"confidence_label is LOW (expected HIGH)")

    categories = [i.get("category", "") for i in issues]

    contradiction_categories = {"Structural Inconsistency", "Conflicting Structure",
                                "Structural Contradiction", "Contradiction"}
    found_contradictions = [c for c in categories if c in contradiction_categories]
    if found_contradictions:
        passed = False
        reasons.append(f"unexpected contradiction categories: {found_contradictions}")

    return name, passed, reasons, {
        "confidence_score": score,
        "confidence_label": label,
        "issue_count": issue_count,
        "categories": categories,
        "quality_warning": quality_warning,
    }


def test_unlimited_indemnity():
    filepath = TEST_DIR / "unlimited_indemnity.txt"
    data = send_file(filepath)

    name = "unlimited_indemnity"
    passed = True
    reasons = []

    score = data.get("confidence_score", 0)
    label = data.get("confidence_label", "N/A")
    issue_count = data.get("issue_count", 0)
    issues = data.get("issues", [])

    categories = [i.get("category", "") for i in issues]
    indemnity_found = any("indemn" in c.lower() for c in categories)
    if not indemnity_found:
        passed = False
        reasons.append("no Indemnification category found")

    return name, passed, reasons, {
        "confidence_score": score,
        "confidence_label": label,
        "issue_count": issue_count,
        "categories": categories,
        "quality_warning": data.get("quality_warning", ""),
    }


def test_garbage_ocr():
    filepath = TEST_DIR / "garbage_ocr.txt"
    data = send_file(filepath)

    name = "garbage_ocr"
    passed = True
    reasons = []

    score = data.get("confidence_score", 0)
    label = data.get("confidence_label", "N/A")
    quality_warning = data.get("quality_warning", "")

    # Garbage OCR must NEVER return HIGH confidence
    if label == "HIGH":
        passed = False
        reasons.append("confidence_label is HIGH (must never be HIGH for garbage OCR)")

    if not quality_warning:
        passed = False
        reasons.append("no quality_warning returned for degraded input")

    return name, passed, reasons, {
        "confidence_score": score,
        "confidence_label": label,
        "issue_count": data.get("issue_count", 0),
        "categories": [i.get("category", "") for i in data.get("issues", [])],
        "quality_warning": quality_warning,
    }


def test_empty_file():
    filepath = TEST_DIR / "empty_file.txt"
    data = send_file(filepath, expect_error=True)

    name = "empty_file"
    passed = True
    reasons = []

    if data is None:
        passed = False
        reasons.append("no response received")

    if isinstance(data, dict) and data.get("success") is False:
        passed = False
        reasons.append(f"got refusal response: {data.get('legacy_text', '')}")

    issue_count = 0
    if isinstance(data, dict):
        issue_count = data.get("issue_count", 0)

    if issue_count > 0:
        passed = False
        reasons.append(f"hallucinated {issue_count} issues from empty file")

    return name, passed, reasons, {
        "confidence_score": data.get("confidence_score", 0) if isinstance(data, dict) else 0,
        "confidence_label": data.get("confidence_label", "N/A") if isinstance(data, dict) else "N/A",
        "issue_count": issue_count,
        "categories": [],
        "quality_warning": data.get("quality_warning", "") if isinstance(data, dict) else "",
    }


def test_contradictory_clauses():
    filepath = TEST_DIR / "contradictory_clauses.txt"
    data = send_file(filepath)

    name = "contradictory_clauses"
    passed = True
    reasons = []

    score = data.get("confidence_score", 0)
    label = data.get("confidence_label", "N/A")
    issue_count = data.get("issue_count", 0)
    issues = data.get("issues", [])

    categories = [i.get("category", "") for i in issues]

    contradiction_categories = {"Structural Inconsistency", "Conflicting Structure",
                                "Structural Contradiction"}
    found_contradictions = [c for c in categories if c in contradiction_categories]
    if not found_contradictions:
        passed = False
        reasons.append("no structural inconsistency detected for contradictory clauses")

    return name, passed, reasons, {
        "confidence_score": score,
        "confidence_label": label,
        "issue_count": issue_count,
        "categories": categories,
        "quality_warning": data.get("quality_warning", ""),
    }


def test_non_legal_text():
    filepath = TEST_DIR / "non_legal_text.txt"
    data = send_file(filepath)

    name = "non_legal_text"
    passed = True
    reasons = []

    label = data.get("confidence_label", "N/A")
    quality_warning = data.get("quality_warning", "")

    if label == "HIGH":
        passed = False
        reasons.append("confidence_label is HIGH for non-legal text")

    return name, passed, reasons, {
        "confidence_score": data.get("confidence_score", 0),
        "confidence_label": label,
        "issue_count": data.get("issue_count", 0),
        "categories": [i.get("category", "") for i in data.get("issues", [])],
        "quality_warning": quality_warning,
    }


def test_duplicate_clause_spam():
    filepath = TEST_DIR / "duplicate_clause_spam.txt"
    data = send_file(filepath)

    name = "duplicate_clause_spam"
    passed = True
    reasons = []

    issue_count = data.get("issue_count", 0)
    issues = data.get("issues", [])

    # Duplicate spam must not create duplicate explosion
    # If there are 10+ copies of the same text, issue_count should still be small
    if issue_count > 10:
        passed = False
        reasons.append(f"issue_count={issue_count} suggests duplicate explosion (expected <= 10)")

    return name, passed, reasons, {
        "confidence_score": data.get("confidence_score", 0),
        "confidence_label": data.get("confidence_label", "N/A"),
        "issue_count": issue_count,
        "categories": [i.get("category", "") for i in issues],
        "quality_warning": data.get("quality_warning", ""),
    }


# ---------------------------------------------------------------------------
# Runner helpers
# ---------------------------------------------------------------------------

TEST_REGISTRY = [
    ("Clean NDA", test_clean_nda),
    ("Unlimited Indemnity", test_unlimited_indemnity),
    ("Garbage OCR", test_garbage_ocr),
    ("Empty File", test_empty_file),
    ("Contradictory Clauses", test_contradictory_clauses),
    ("Non-Legal Text", test_non_legal_text),
    ("Duplicate Clause Spam", test_duplicate_clause_spam),
]


def send_file(filepath: Path, expect_error: bool = False) -> dict:
    session_id = f"regression-{uuid.uuid4().hex[:12]}"

    if not filepath.exists():
        return {"error": f"file not found: {filepath}"}

    with open(filepath, "rb") as f:
        files = {"file": (filepath.name, f, "text/plain")}
        data = {
            "session_id": session_id,
            "mode": "AUDIT",
            "response_format": "json",
        }
        try:
            resp = requests.post(f"{BASE_URL}/ask_file", files=files, data=data, timeout=120)
        except requests.exceptions.ConnectionError:
            return {"error": f"Cannot connect to {BASE_URL}"}
        except requests.exceptions.Timeout:
            return {"error": "request timed out"}
        except Exception as e:
            return {"error": str(e)}

    if expect_error and resp.status_code != 200:
        return {"status_code": resp.status_code, "detail": resp.text}

    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        return {"error": f"HTTP {resp.status_code}", "detail": detail}

    try:
        return resp.json()
    except Exception as e:
        return {"error": f"JSON parse failed: {e}", "raw": resp.text[:500]}


def run_tests():
    os.system("cls" if os.name == "nt" else "clear")

    print("=" * 72)
    print("  ZYNEXRA REGRESSION TEST SUITE")
    print(f"  Target: {BASE_URL}")
    print(f"  Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    overall_pass = True
    total = len(TEST_REGISTRY)
    passed_count = 0
    failed_count = 0

    for display_name, test_fn in TEST_REGISTRY:
        print(f"\n--- {display_name} {'-' * (60 - len(display_name))}")

        try:
            name, passed, reasons, fields = test_fn()
        except Exception as e:
            print(f"  {FAIL_ICON}  EXCEPTION: {e}")
            failed_count += 1
            overall_pass = False
            continue

        icon = PASS_ICON if passed else FAIL_ICON
        status = "PASS" if passed else "FAIL"
        print(f"  {icon}  {status}  |  score={fields['confidence_score']:.4f}  label={fields['confidence_label']}  "
              f"issues={fields['issue_count']}")

        if fields["quality_warning"]:
            print(f"       warning: {fields['quality_warning']}")

        if fields["categories"]:
            cats = ", ".join(fields["categories"])
            print(f"       categories: {cats}")

        if reasons:
            for r in reasons:
                print(f"       reason: {r}")

        if passed:
            passed_count += 1
        else:
            failed_count += 1
            overall_pass = False

    print()
    print("=" * 72)
    print(f"  SUMMARY: {passed_count}/{total} passed, {failed_count}/{total} failed")
    print(f"  OVERALL: {'ALL PASS' if overall_pass else 'SOME FAILURES'}")
    print("=" * 72)

    return 0 if overall_pass else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zynexra Regression Test Runner")
    parser.add_argument("--url", default=BASE_URL, help="Base URL of the Zynexra API")
    args = parser.parse_args()

    BASE_URL = args.url.rstrip("/")
    sys.exit(run_tests())
