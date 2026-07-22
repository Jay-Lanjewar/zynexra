"""
Isolated reproduction: Confidentiality Survival Clause rule-following test.

Tests 7 durations across two prompt regimes:
  1. Isolated rule – only the specific rule text from audit_prompt.py:134
  2. Full production prompt – the entire audit_prompt.py system prompt

Usage:
    # Ensure server + Ollama are running, then:
    python tests/test_survival_rule_reproduction.py
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OLLAMA_BASE = "http://localhost:11434"
API_BASE = "http://localhost:8000"
MODEL = None  # will be read from settings

# Single rule text (excerpt from audit_prompt.py line 134)
SINGLE_RULE = (
    "STEP 1: Locate the confidentiality survival clause. "
    "This is typically in a 'Term and Survival' or 'Term and Termination' section, "
    "and will contain language like 'confidentiality obligations shall survive termination' "
    "or 'survive expiration.' "
    "STEP 2: Read the EXACT duration specified after 'survive' or 'survival.' "
    "Only flag if the survival clause uses the word 'perpetually,' 'indefinitely,' "
    "'in perpetuity,' or 'without limit' as the duration. "
    "A specific number of years (3, 5, 7, 10, etc.) is NEVER perpetual, "
    "even if the number is large. "
    "This finding ONLY applies when the survival clause explicitly uses "
    "'perpetually,' 'indefinitely,' 'in perpetuity,' or 'without limit.' "
    "A number of years (e.g., 'survive for three (3) years') is never perpetual. "
    "Flag as 'Perpetual Confidentiality Survival' under 'Enforceability Weakness.' "
    "Severity: MEDIUM."
)

ISOLATED_SYSTEM_PROMPT = (
    "You are a contract audit assistant. Apply the following rule strictly:\n\n"
    + SINGLE_RULE
    + "\n\n"
    "Read the clause below. Respond with a JSON object with keys: "
    '"flags" (boolean), "issue_title" (string or null), "reason" (string).'
)

# Test clauses — each embeds the survival duration
CLAUSES = {
    "3 years": (
        "Section 4. Term and Survival. "
        "This Agreement shall commence on the Effective Date and continue for a period of two (2) years. "
        "The confidentiality obligations shall survive termination of this Agreement "
        "for a period of three (3) years."
    ),
    "5 years": (
        "4. Term. "
        "The confidentiality obligations shall survive termination for a period of five (5) years."
    ),
    "10 years": (
        "10. Survival. "
        "All confidentiality obligations shall survive termination or expiration of this Agreement "
        "and continue for a period of ten (10) years."
    ),
    "indefinite": (
        "Section 4. Term and Survival. "
        "Confidentiality obligations shall survive termination or expiration of this Agreement "
        "and shall continue in full force and effect indefinitely."
    ),
    "perpetually": (
        "4. Term and Survival. "
        "Confidentiality obligations shall survive termination or expiration of this Agreement "
        "perpetually and shall continue in full force and effect indefinitely."
    ),
    "in perpetuity": (
        "Section 4. Survival. "
        "The confidentiality obligations set forth herein shall survive the termination "
        "or expiration of this Agreement in perpetuity."
    ),
    "without limit": (
        "4. Term. "
        "Confidentiality obligations shall survive termination without limit."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ollama_request(messages: list, model: str, seed: int = 42) -> str:
    """Call Ollama chat endpoint directly."""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "options": {"temperature": 0, "seed": seed, "num_predict": 768},
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read().decode())
    return data["message"]["content"]


def _pipeline_ask(contract_text: str, session_id: str) -> str:
    """Send via /ask AUDIT pipeline."""
    body = json.dumps({
        "question": contract_text,
        "session_id": session_id,
        "mode": "AUDIT",
    }).encode()
    req = urllib.request.Request(
        f"{API_BASE}/ask",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=180)
    return resp.read().decode()


def _has_survival_finding(response_text: str) -> bool:
    """Check if the response contains a Confidentiality Survival finding."""
    lower = response_text.lower()
    # Various title forms the model sometimes uses
    survival_titles = [
        "confidentiality survival",
        "perpetual confidentiality",
        "survival clause",
    ]
    for t in survival_titles:
        if t in lower:
            return True
    # Also check for issue_title JSON key
    try:
        parsed = json.loads(response_text)
        issues = parsed.get("issues", [])
        for iss in issues:
            title = (iss.get("issue_title") or "").lower()
            for t in survival_titles:
                if t in title:
                    return True
    except (json.JSONDecodeError, TypeError):
        pass
    return False


def _extract_flags_from_isolated(response_text: str) -> dict:
    """Parse isolated-test JSON response."""
    # Try to find JSON in the response
    match = re.search(r'\{[^{}]*"flags"[^{}]*\}', response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    # Fallback: look for YES/NO or flag keywords
    lower = response_text.lower()
    flags = "yes" in lower[:20] or '"flags": true' in lower
    return {"flags": flags, "issue_title": None, "reason": response_text[:200]}


def _resolve_model() -> str:
    """Read model name from the backend settings."""
    from backend.config import settings
    return settings.MODEL_FAST


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_isolated_tests(model: str) -> dict:
    """Test each clause with only SINGLE_RULE as the system prompt."""
    results = {}
    for label, clause in CLAUSES.items():
        messages = [
            {"role": "system", "content": ISOLATED_SYSTEM_PROMPT},
            {"role": "user", "content": f"Clause:\n{clause}\n\nDoes this clause trigger the rule?"},
        ]
        try:
            raw = _ollama_request(messages, model, seed=42)
            parsed = _extract_flags_from_isolated(raw)
            results[label] = {
                "flags": parsed.get("flags", False),
                "raw_response": raw,
            }
            status = "FLAGS" if parsed.get("flags") else "OK"
            print(f"  [Isolated] {label:15s} -> {status}")
        except Exception as e:
            results[label] = {"flags": None, "raw_response": f"ERROR: {e}"}
            print(f"  [Isolated] {label:15s} -> ERROR: {e}")
    return results


def run_pipeline_tests() -> dict:
    """Test each clause via the full /ask AUDIT pipeline."""
    results = {}
    for label, clause in CLAUSES.items():
        # Construct a minimal realistic contract around the clause
        contract = (
            "CONFIDENTIALITY AGREEMENT\n\n"
            "1. Confidential Information. Confidential Information includes all non-public "
            "information disclosed by one party to the other.\n\n"
            "2. Obligations. The receiving party shall hold Confidential Information in confidence "
            "and shall not disclose it to any third party without the disclosing party's consent.\n\n"
            "3. Exclusions. Confidential Information does not include information that: "
            "(a) is or becomes publicly available without breach;\n"
            "(b) was in the receiving party's lawful possession prior to disclosure;\n"
            "(c) is independently developed; or\n"
            "(d) is received from a third party without restriction.\n\n"
            f"{clause}\n\n"
            "5. Return of Materials. Upon termination of this Agreement, "
            "each party shall return or destroy all Confidential Information "
            "and certify such return or destruction in writing."
        )
        session_id = f"test-survival-{label.lower().replace(' ', '-')}-{int(time.time())}"
        body = json.dumps({
            "question": contract,
            "session_id": session_id,
            "mode": "AUDIT",
            "response_format": "json",
        }).encode()
        try:
            req = urllib.request.Request(
                f"{API_BASE}/ask",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=180)
            raw = resp.read().decode()
            parsed = json.loads(raw)
            issues = parsed.get("issues", [])
            titles = [i.get("issue_title", "") for i in issues]
            flags = bool(titles)
            results[label] = {
                "flags": flags,
                "issue_titles": titles,
                "response": raw[:500],
            }
            status = "FLAGS" if flags else "OK"
            if flags:
                status += f" ({titles[0]})"
            print(f"  [Pipeline] {label:15s} -> {status}")
        except Exception as e:
            results[label] = {"flags": None, "issue_titles": [], "response": f"ERROR: {e}"}
            print(f"  [Pipeline] {label:15s} -> ERROR: {e}")
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print("  Confidentiality Survival Clause — Rule Following Reproduction")
    print("=" * 72)

    try:
        model = _resolve_model()
        print(f"\n  Model: {model}")
    except Exception as e:
        print(f"\n  Could not read model config: {e}")
        sys.exit(1)

    # Verify Ollama is reachable
    try:
        urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=5)
        print("  Ollama: reachable")
    except Exception as e:
        print(f"  Ollama: NOT reachable ({e})")
        sys.exit(1)

    # Verify API is reachable
    try:
        urllib.request.urlopen(f"{API_BASE}/docs", timeout=5)
        print("  API: reachable")
    except Exception as e:
        print(f"  API: NOT reachable ({e})")
        sys.exit(1)

    # ---- Isolated tests ----
    print("\n" + "-" * 72)
    print("  PHASE 1: ISOLATED RULE (single rule as system prompt)")
    print("-" * 72)
    isolated = run_isolated_tests(model)

    # ---- Pipeline tests ----
    print("\n" + "-" * 72)
    print("  PHASE 2: FULL PRODUCTION PROMPT (/ask AUDIT pipeline)")
    print("-" * 72)
    pipeline = run_pipeline_tests()

    # ---- Matrix ----
    print("\n" + "=" * 72)
    print("  RESULTS MATRIX")
    print("=" * 72)
    print(f"  {'Duration':20s} {'Isolated':12s} {'Pipeline':12s} {'Expected':12s}")
    print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*12}")
    expected_correct = {
        "3 years":       ("OK",    "Finite years, never perpetual"),
        "5 years":       ("OK",    "Finite years, never perpetual"),
        "10 years":      ("OK",    "Finite years, never perpetual"),
        "indefinite":    ("FLAG",  "Uses 'indefinitely' — triggers rule"),
        "perpetually":   ("FLAG",  "Uses 'perpetually' — triggers rule"),
        "in perpetuity": ("FLAG",  "Uses 'in perpetuity' — triggers rule"),
        "without limit": ("FLAG",  "Uses 'without limit' — triggers rule"),
    }

    correct_iso = 0
    correct_pipe = 0
    total = len(CLAUSES)
    for label in CLAUSES:
        exp, reason = expected_correct[label]
        iso_flag = isolated.get(label, {}).get("flags")
        pipe_flag = pipeline.get(label, {}).get("flags")

        iso_ok = (iso_flag is False and exp == "OK") or (iso_flag is True and exp == "FLAG")
        pipe_ok = (pipe_flag is False and exp == "OK") or (pipe_flag is True and exp == "FLAG")

        if iso_flag is True:
            iso_str = "FLAG"
        elif iso_flag is False:
            iso_str = "OK"
        else:
            iso_str = "ERR"
        if pipe_flag is True:
            pipe_str = "FLAG"
        elif pipe_flag is False:
            pipe_str = "OK"
        else:
            pipe_str = "ERR"

        correct_iso += 1 if iso_ok else 0
        correct_pipe += 1 if pipe_ok else 0

        marker_iso = "" if iso_ok else "  <-- WRONG"
        marker_pipe = "" if pipe_ok else "  <-- WRONG"
        print(f"  {label:20s} {iso_str:12s}{marker_iso} {pipe_str:12s}{marker_pipe} Expected: {exp:6s}")

    print()
    print(f"  Isolated rule-following:  {correct_iso}/{total} correct")
    print(f"  Pipeline rule-following:  {correct_pipe}/{total} correct")
    print()

    # Show model self-contradictions in pipeline FPs
    print("  --- Pipeline false-positive detail ---")
    for label in CLAUSES:
        exp, _ = expected_correct[label]
        pipe_flag = pipeline.get(label, {}).get("flags")
        if exp == "OK" and pipe_flag:
            titles = pipeline.get(label, {}).get("issue_titles", [])
            resp_preview = pipeline.get(label, {}).get("response", "")[:300]
            print(f"  {label}: titles={titles}")
            print(f"    response_preview={resp_preview[:200]}")
        elif exp == "FLAG" and not pipe_flag:
            resp_preview = pipeline.get(label, {}).get("response", "")[:300]
            print(f"  {label}: MISSED — resp={resp_preview[:200]}")


if __name__ == "__main__":
    main()
