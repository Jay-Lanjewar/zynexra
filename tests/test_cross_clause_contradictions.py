"""
Test 10 synthetic contracts with deliberate cross-clause contradictions.
Measures whether the pipeline detects cross-clause contradictions or misses them.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API_BASE = "http://localhost:8000"

CONTRACTS = []

# Helper to indent sections
def _sec(num, title, body):
    return f"{num}. {title}\n{body}"

# ---------------------------------------------------------------------------
# Contract 1: Confidentiality survival vs termination (original issue)
# ---------------------------------------------------------------------------
C1 = """
MASTER SERVICES AGREEMENT

1. Definitions
"Confidential Information" means all non-public business, technical, or financial information disclosed by either party.

2. Scope
Vendor shall provide the Services described in the applicable Statement of Work.

3. Fees
Client shall pay all fees within thirty (30) days of invoice.

4. Confidentiality
Each party shall maintain the confidentiality of Confidential Information. The Receiving Party shall not disclose Confidential Information to third parties.

5. Survival of Confidentiality
The confidentiality obligations shall survive termination of this Agreement for a period of five (5) years.

6. Termination
Either party may terminate this Agreement upon thirty (30) days written notice. Upon termination, all obligations under this Agreement shall immediately cease, including confidentiality obligations.

7. Limitation of Liability
Neither party's aggregate liability shall exceed the fees paid during the preceding twelve (12) months.
"""
CONTRACTS.append(("C01-conflict-survival-vs-termination", C1.strip()))

# ---------------------------------------------------------------------------
# Contract 2: Payment term contradiction
# ---------------------------------------------------------------------------
C2 = """
CONSULTING SERVICES AGREEMENT

1. Services
Consultant shall provide the services described in Exhibit A.

2. Fees
Client shall pay Consultant a flat fee of $50,000 for the Services.

3. Payment Terms
All invoices are due within thirty (30) days of receipt.

4. Late Payment
Late payments shall accrue interest at 1.5% per month.

5. Discount Terms
Client shall receive a 5% discount if payment is made within ten (10) days of invoice.

6. Final Payment
Notwithstanding Section 3, all final invoices are due within sixty (60) days of receipt.

7. General Provisions
This Agreement constitutes the entire agreement between the parties.
"""
CONTRACTS.append(("C02-conflict-payment-terms", C2.strip()))

# ---------------------------------------------------------------------------
# Contract 3: Liability cap vs uncapped indemnification
# ---------------------------------------------------------------------------
C3 = """
SaaS SUBSCRIPTION AGREEMENT

1. Services
Provider shall provide the SaaS platform to Customer.

2. Fees
Customer shall pay the subscription fees set forth in the Order Form.

3. Confidentiality
Each party shall protect the other's Confidential Information.

4. Indemnification
Customer agrees to indemnify, defend, and hold harmless Provider from any claims arising out of Customer's use of the Services, without limitation of liability.

5. Limitation of Liability
Notwithstanding anything to the contrary, Provider's aggregate liability shall not exceed the fees paid by Customer in the preceding twelve (12) months.

6. Mutual Exclusions
Neither party shall be liable for indirect, incidental, or consequential damages.
"""
CONTRACTS.append(("C03-conflict-liability-vs-indemnity", C3.strip()))

# ---------------------------------------------------------------------------
# Contract 4: Governing law contradiction
# ---------------------------------------------------------------------------
C4 = """
PARTNERSHIP AGREEMENT

1. Purpose
The parties shall collaborate on the Development Project.

2. Contributions
Each party shall contribute resources as set forth in Schedule A.

3. Revenue Sharing
Gross revenue shall be split 50/50 between the parties.

4. Governing Law
This Agreement shall be governed by the laws of the State of California.

5. Venue
Any disputes shall be resolved exclusively in the courts of New York, New York.

6. Governing Law (Alternative)
Notwithstanding Section 4, this Agreement shall be governed by the laws of the State of New York.

7. Entire Agreement
This Agreement supersedes all prior understandings.
"""
CONTRACTS.append(("C04-conflict-governing-law", C4.strip()))

# ---------------------------------------------------------------------------
# Contract 5: Notice period contradiction
# ---------------------------------------------------------------------------
C5 = """
VENDOR SERVICES AGREEMENT

1. Services
Vendor shall provide maintenance and support services.

2. Term
The initial term shall be twelve (12) months.

3. Automatic Renewal
This Agreement shall automatically renew for successive one-year terms.

4. Notice of Non-Renewal
Either party may provide notice of non-renewal at least thirty (30) days prior to the end of the then-current term.

5. Termination for Convenience
Either party may terminate this Agreement for any reason upon ninety (90) days written notice.

6. Notice Requirements
Notwithstanding Section 5, all notices of termination must be delivered at least sixty (60) days prior to the intended termination date.

7. Miscellaneous
This Agreement may be amended only by a written instrument signed by both parties.
"""
CONTRACTS.append(("C05-conflict-notice-period", C5.strip()))

# ---------------------------------------------------------------------------
# Contract 6: Data ownership contradiction
# ---------------------------------------------------------------------------
C6 = """
TECHNOLOGY DEVELOPMENT AGREEMENT

1. Project
Developer shall build the Platform for Client.

2. Ownership of Deliverables
All deliverables, including source code, documentation, and designs, shall be the sole and exclusive property of Client.

3. Developer IP
Developer retains all right, title, and interest in its pre-existing intellectual property.

4. Derivative Works
Notwithstanding Section 2, Developer shall own all derivative works, improvements, and modifications to the Developer's pre-existing IP, regardless of whether developed using Client's resources or confidential information.

5. License
Developer grants Client a non-exclusive, royalty-free license to use the derivative works described in Section 4.

6. Survival
The provisions of this Section shall survive termination.
"""
CONTRACTS.append(("C06-conflict-ownership", C6.strip()))

# ---------------------------------------------------------------------------
# Contract 7: Exclusivity contradiction
# ---------------------------------------------------------------------------
C7 = """
DISTRIBUTION AGREEMENT

1. Appointment
Manufacturer appoints Distributor as its exclusive distributor in North America.

2. Exclusive Rights
Distributor shall have the sole and exclusive right to sell the Products in the Territory.

3. Non-Compete
Manufacturer shall not appoint any other distributor or sell Products directly to customers in the Territory.

4. Right to Sell
Notwithstanding the foregoing, Manufacturer retains the right to sell Products to any customer, anywhere, at any time, without restriction.

5. Royalties
Distributor shall pay Manufacturer a royalty of 10% on all sales.

6. Term
This Agreement shall continue for three (3) years.
"""
CONTRACTS.append(("C07-conflict-exclusivity", C7.strip()))

# ---------------------------------------------------------------------------
# Contract 8: Confidentiality definition contradiction
# ---------------------------------------------------------------------------
C8 = """
CONFIDENTIALITY AGREEMENT

1. Definition of Confidential Information
"Confidential Information" means all information disclosed by Disclosing Party to Receiving Party.

2. Exclusions
Confidential Information does not include information that is or becomes publicly available through no fault of Receiving Party.

3. Obligations
Receiving Party shall hold all Confidential Information in confidence.

4. Re-Definition
Notwithstanding Section 2, any information designated as "Confidential" by Disclosing Party shall be treated as Confidential Information regardless of whether it is publicly available.

5. Term
This Agreement shall remain in effect for two (2) years.

6. Return of Materials
Upon termination, Receiving Party shall return or destroy all Confidential Information.
"""
CONTRACTS.append(("C08-conflict-confidentiality-def", C8.strip()))

# ---------------------------------------------------------------------------
# Contract 9: Fee cap vs uncapped liability
# ---------------------------------------------------------------------------
C9 = """
MANAGED SERVICES AGREEMENT

1. Services
Provider shall manage Client's IT infrastructure.

2. Fees
Client shall pay the monthly fees set forth in the Service Schedule.

3. Service Level Commitment
Provider shall maintain 99.9% uptime.

4. Service Credits
If uptime falls below 99.9%, Client shall receive a service credit equal to 5% of monthly fees.

5. Limitation of Liability
Provider's aggregate liability shall not exceed the total fees paid by Client during the three (3) months immediately preceding the claim.

6. Uncap Provision
Notwithstanding Section 5, Provider shall be fully liable for all losses, damages, and costs arising from any service outage, regardless of duration or cause, without any limitation.

7. Disclaimer
Provider disclaims all warranties not expressly set forth herein.
"""
CONTRACTS.append(("C09-conflict-fee-cap-vs-uncap", C9.strip()))

# ---------------------------------------------------------------------------
# Contract 10: Audit rights contradiction
# ---------------------------------------------------------------------------
C10 = """
CLOUD SERVICES AGREEMENT

1. Services
Provider shall provide cloud infrastructure services to Customer.

2. Security Obligations
Provider shall maintain industry-standard security controls.

3. Audit Rights
Customer may audit Provider's facilities and systems upon reasonable notice, no more than once per calendar year.

4. Restrictions
Notwithstanding Section 3, Customer shall not have the right to access, inspect, or audit any of Provider's facilities, systems, or records.

5. Compliance
Provider shall maintain SOC 2 Type II certification.

6. Reporting
Provider shall provide Customer with quarterly security reports.

7. Confidentiality
Each party shall protect the other's Confidential Information.
"""
CONTRACTS.append(("C10-conflict-audit-rights", C10.strip()))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def _run_contract_test(contract_id: str, text: str) -> dict:
    session_id = f"xclause-{contract_id}-{int(time.time())}"
    body = json.dumps({
        "question": text,
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
        resp = urllib.request.urlopen(req, timeout=300)
        data = json.loads(resp.read().decode())
        issues = data.get("issues", [])
        legacy = data.get("legacy_text", "")
        return {"contract_id": contract_id, "issues": issues, "legacy": legacy, "error": None}
    except Exception as e:
        return {"contract_id": contract_id, "issues": [], "legacy": "", "error": str(e)}


def classify_outcome(contract_id: str, issues: list) -> dict:
    """Classify whether the pipeline detected the cross-clause contradiction.

    Returns dict with flags for detection quality.
    """
    titles = [i.get("issue_title", "") for i in issues]
    cats = [i.get("category", "") for i in issues]
    exps = [i.get("risk_explanation", "") for i in issues]
    qt = [i.get("quoted_text", "") for i in issues]
    all_text = " ".join(titles + cats + exps + qt).lower()

    outcome = {
        "issue_count": len(issues),
        "titles": titles,
        "categories": cats,
        "has_structural_inconsistency": any("structural" in c.lower() for c in cats),
        "mentions_contradiction": any(w in all_text for w in
            ["contradict", "conflict", "inconsistent", "inconsistency", "oppos",
             "nullif", "negate", "undermine", "conflicting"]),
        "mentions_both_clauses": False,  # Checked per-contract below
        "missed": False,
        "false_positive_risk": False,
    }

    # Per-contract specific signals
    if "c01" in contract_id:
        outcome["mentions_both_clauses"] = (
            "surviv" in all_text and "cease" in all_text
        ) or (
            "section 5" in all_text and "section 6" in all_text
        )
        outcome["missed"] = not outcome["mentions_contradiction"]

    elif "c02" in contract_id:
        outcome["mentions_both_clauses"] = "30" in all_text and "60" in all_text
        outcome["missed"] = not outcome["mentions_contradiction"] and not (
            "inconsistent" in all_text or "conflict" in all_text
        )

    elif "c03" in contract_id:
        outcome["mentions_both_clauses"] = "indemnif" in all_text and "cap" in all_text
        outcome["missed"] = not outcome["mentions_contradiction"]

    elif "c04" in contract_id:
        outcome["mentions_both_clauses"] = ("california" in all_text and "new york" in all_text)
        outcome["missed"] = not outcome["mentions_contradiction"]

    elif "c05" in contract_id:
        outcome["mentions_both_clauses"] = "30" in all_text and "60" in all_text
        outcome["missed"] = not outcome["mentions_contradiction"]

    elif "c06" in contract_id:
        outcome["mentions_both_clauses"] = "client" in all_text and "developer" in all_text
        outcome["missed"] = not outcome["mentions_contradiction"]

    elif "c07" in contract_id:
        outcome["mentions_both_clauses"] = "exclusive" in all_text or "right to sell" in all_text
        outcome["missed"] = not outcome["mentions_contradiction"]

    elif "c08" in contract_id:
        outcome["mentions_both_clauses"] = "exclusion" in all_text or "publicly" in all_text
        outcome["missed"] = not outcome["mentions_contradiction"]

    elif "c09" in contract_id:
        outcome["mentions_both_clauses"] = "cap" in all_text and "uncap" in all_text
        outcome["missed"] = not outcome["mentions_contradiction"]

    elif "c10" in contract_id:
        outcome["mentions_both_clauses"] = "audit" in all_text
        outcome["missed"] = not outcome["mentions_contradiction"]

    return outcome


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 72)
    print("  CROSS-CLAUSE CONTRADICTION DETECTION — 10 Synthetic Contracts")
    print("=" * 72)

    # Verify API
    try:
        urllib.request.urlopen(f"{API_BASE}/docs", timeout=5)
        print("  API: reachable\n")
    except Exception as e:
        print(f"  API: NOT reachable ({e})")
        sys.exit(1)

    results = []
    for cid, text in CONTRACTS:
        print("-" * 72)
        print(f"  Testing: {cid}")
        print(f"  Text length: {len(text)} chars")
        print(f"  Preview: {text[:120].replace(chr(10), ' | ')}...")
        result = _run_contract_test(cid, text)
        outcome = classify_outcome(result["contract_id"], result["issues"])
        result["outcome"] = outcome
        results.append(result)

        print(f"  Issues: {outcome['issue_count']}")
        for t in outcome["titles"]:
            print(f"    - {t}")
        print(f"  Structural Inconsistency: {outcome['has_structural_inconsistency']}")
        print(f"  Mentions contradiction: {outcome['mentions_contradiction']}")
        print(f"  Missed: {outcome['missed']}")

        # Show raw LLM response (from legacy_text, first 400 chars)
        legacy = result.get("legacy", "")
        if legacy:
            print(f"  Legacy preview: {legacy[:400].replace(chr(10), ' | ')}")
        if result.get("error"):
            print(f"  ERROR: {result['error']}")
        print()

    # Summary table
    print("=" * 72)
    print("  SUMMARY MATRIX")
    print("=" * 72)
    print(f"  {'Contract':35s} {'Issues':6s} {'Detected?':10s} {'Struct.Incon.':13s}")
    print(f"  {'-'*35} {'-'*6} {'-'*10} {'-'*13}")

    detected_count = 0
    for r in results:
        o = r["outcome"]
        detected = "YES" if not o["missed"] else "NO"
        if not o["missed"]:
            detected_count += 1
        si = "YES" if o["has_structural_inconsistency"] else "no"
        print(f"  {r['contract_id']:35s} {o['issue_count']:6d} {detected:10s} {si:13s}")

    print()
    print(f"  Cross-clause contradictions detected: {detected_count}/{len(CONTRACTS)}")
    print()
    print("  --- Missed contradiction details ---")
    for r in results:
        o = r["outcome"]
        if o["missed"]:
            print(f"  {r['contract_id']}:")
            for t, c, e in zip(o["titles"], o["categories"], [i.get("risk_explanation","") for i in r["issues"]]):
                print(f"    Title: {t}")
                print(f"    Cat:   {c}")
                print(f"    Exp:   {e[:200]}")


if __name__ == "__main__":
    main()
