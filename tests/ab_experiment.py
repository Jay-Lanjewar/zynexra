"""
Controlled A/B experiment: Post-Tightened baseline (A) vs P3-minus-CoC (B).
Alternates runs: A1, B1, A2, B2, A3, B3 in the same server session.
"""
import subprocess, time, json, sys, re, os, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROMPT_FILE = Path(__file__).resolve().parent.parent / "backend" / "prompts" / "audit_prompt.py"
RESULTS_DIR = Path(__file__).resolve().parent / "validation_corpus"

# --- Original negative-framing versions of lines 133, 134, 136 ---

LINE_133_A = r'''- FIRST: Identify whether the document contains a dedicated "Exclusions" or "Exceptions" section in a confidentiality clause that explicitly lists what is NOT covered by the confidentiality obligation. Look for phrases like "Confidential Information does not include" or "The obligations shall not apply to" followed by a lettered list (a), (b), (c), etc. IF no dedicated exclusion list exists: do NOT flag this finding. The absence of an exclusion clause is a different issue. IF an exclusion list exists: count the standard carve-outs present in that specific lettered list: (a) publicly available/known, (b) prior possession, (c) independent development, (d) third-party receipt. If the lettered list has FEWER THAN FOUR of these items (i.e., 2 or 3 are present), flag as "Incomplete Confidentiality Exclusions." If all four are present, do NOT flag. DO NOT apply this finding to employment confidentiality clauses, general confidentiality obligations without exclusion lists, or clauses that list all four carve-outs. Severity: MEDIUM.'''

LINE_134_A = r'''- STEP 1: Locate the confidentiality survival clause. This is typically in a "Term and Survival" or "Term and Termination" section, and will contain language like "confidentiality obligations shall survive termination" or "survive expiration." STEP 2: Read the EXACT duration specified after "survive" or "survival." Only flag if the survival clause uses the word "perpetually," "indefinitely," "in perpetuity," or "without limit" as the duration. A specific number of years (3, 5, 7, 10, etc.) is NEVER perpetual, even if the number is large. DO NOT flag if the survival clause specifies a number of years (e.g., "survive for three (3) years"). DO NOT flag if the word "perpetual" appears in a different clause (e.g., IP license, not confidentiality). Flag as "Perpetual Confidentiality Survival" under "Enforceability Weakness." Severity: MEDIUM.'''

LINE_136_A = r'''- If a SaaS or cloud services agreement does not include a service level agreement (SLA) guaranteeing uptime, availability, or performance, flag it as "No Service Level Agreement" under "Enforceability Weakness." Severity: MEDIUM. The absence of an SLA means the customer has no contractual recourse for service interruptions other than termination. BEFORE generating this finding, scan the ENTIRE contract for: "service level", "uptime", "availability", "99.5%", "98%", "99%", "SLA", "guarantee", "maintain". If ANY of these appear in the contract text, the contract contains an SLA or performance commitment. DO NOT generate "No Service Level Agreement" if any of these words are present. Only generate this finding if NONE of these words appear anywhere in the contract.'''

# --- Current positive-framing versions (B) ---

LINE_133_B = r'''- FIRST: Identify whether the document contains a dedicated "Exclusions" or "Exceptions" section in a confidentiality clause that explicitly lists what is NOT covered by the confidentiality obligation. Look for phrases like "Confidential Information does not include" or "The obligations shall not apply to" followed by a lettered list (a), (b), (c), etc. IF no dedicated exclusion list exists: do NOT flag this finding. The absence of an exclusion clause is a different issue. IF an exclusion list exists: count the standard carve-outs present in that specific lettered list: (a) publicly available/known, (b) prior possession, (c) independent development, (d) third-party receipt. If the lettered list has FEWER THAN FOUR of these items (i.e., 2 or 3 are present), flag as "Incomplete Confidentiality Exclusions." If all four are present, do NOT flag. This finding ONLY applies to commercial agreements (NDAs, vendor agreements, partnership agreements) with a dedicated Exclusions section. It does NOT apply to employment confidentiality clauses or general confidentiality obligations without exclusion lists. Severity: MEDIUM.'''

LINE_134_B = r'''- STEP 1: Locate the confidentiality survival clause. This is typically in a "Term and Survival" or "Term and Termination" section, and will contain language like "confidentiality obligations shall survive termination" or "survive expiration." STEP 2: Read the EXACT duration specified after "survive" or "survival." Only flag if the survival clause uses the word "perpetually," "indefinitely," "in perpetuity," or "without limit" as the duration. A specific number of years (3, 5, 7, 10, etc.) is NEVER perpetual, even if the number is large. This finding ONLY applies when the survival clause explicitly uses "perpetually," "indefinitely," "in perpetuity," or "without limit." A number of years (e.g., "survive for three (3) years") is never perpetual. Flag as "Perpetual Confidentiality Survival" under "Enforceability Weakness." Severity: MEDIUM.'''

LINE_136_B = r'''- If a SaaS or cloud services agreement does not include a service level agreement (SLA) guaranteeing uptime, availability, or performance, flag it as "No Service Level Agreement" under "Enforceability Weakness." Severity: MEDIUM. The absence of an SLA means the customer has no contractual recourse for service interruptions other than termination. BEFORE generating this finding, scan the ENTIRE contract for: "service level", "uptime", "availability", "99.5%", "98%", "99%", "SLA", "guarantee", "maintain". This finding ONLY applies when NONE of these words appear anywhere in the contract. If ANY of these words are present, the contract contains an SLA or performance commitment and this finding must NOT be generated.'''


def get_line_133():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"^- FIRST:.*?(?=^- STEP 1:)", content, re.MULTILINE | re.DOTALL)
    return m.group(0).strip() if m else None

def get_line_134():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"^- STEP 1:.*?(?=^- PRE-REQUISITE:)", content, re.MULTILINE | re.DOTALL)
    return m.group(0).strip() if m else None

def get_line_136():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"^- If a SaaS.*?(?=^- If one party)", content, re.MULTILINE | re.DOTALL)
    return m.group(0).strip() if m else None

def set_version(version):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    old_133 = get_line_133()
    old_134 = get_line_134()
    old_136 = get_line_136()

    if version == "A":
        new_133, new_134, new_136 = LINE_133_A, LINE_134_A, LINE_136_A
    else:
        new_133, new_134, new_136 = LINE_133_B, LINE_134_B, LINE_136_B

    content = content.replace(old_133, new_133)
    content = content.replace(old_134, new_134)
    content = content.replace(old_136, new_136)

    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    # Verify
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        verify = f.read()
    if version == "A":
        assert "DO NOT apply this finding to employment" in verify, "Line 133 not set to A"
        assert "DO NOT flag if the survival clause" in verify, "Line 134 not set to A"
        assert "DO NOT generate" in verify and "No Service Level Agreement" in verify, "Line 136 not set to A"
    else:
        assert "ONLY applies to commercial agreements" in verify, "Line 133 not set to B"
        assert "ONLY applies when the survival clause" in verify, "Line 134 not set to B"
        assert "ONLY applies when NONE" in verify, "Line 136 not set to B"

def run_benchmark(run_label):
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "phase1_eval_runner.py"), "--run"],
        capture_output=True, text=True, timeout=600,
        cwd=str(Path(__file__).resolve().parent.parent)
    )
    output = result.stdout

    # Find the results file (most recent)
    json_files = sorted(RESULTS_DIR.glob("phase1_results_*.json"), key=lambda p: p.stat().st_mtime)
    latest = json_files[-1]

    with open(latest) as f:
        data = json.load(f)

    o = data["overall"]
    tp = o["total_tp"]
    fp = o["total_fp"]
    fn = o["total_fn"]
    prec = o["precision"]
    rec = o["recall"]
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    comp = o["composite_score"]
    ta = o.get("title_accuracy", 1.0)

    print(f"  {run_label}: TP={tp} FP={fp} FN={fn} Prec={prec:.4f} Rec={rec:.4f} F1={f1:.4f} Comp={comp:.2f} TA={ta:.4f}")

    return {"run": run_label, "tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1, "composite": comp, "title_accuracy": ta}


def main():
    all_results = []

    sequence = [("A", "A1"), ("B", "B1"), ("A", "A2"), ("B", "B2"), ("A", "A3"), ("B", "B3")]

    for version, label in sequence:
        print(f"\n  Setting prompt to version {version}...")
        set_version(version)
        print(f"  Running {label} ({'baseline' if version == 'A' else 'P3-minus-CoC'})...")
        result = run_benchmark(label)
        all_results.append(result)

    # Restore B at end
    set_version("B")
    print("\n  Restored prompt to version B (P3-minus-CoC).")

    # Save results
    out_path = RESULTS_DIR / "ab_experiment_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Results saved to {out_path}")

    # Print summary
    import statistics
    a_runs = [r for r in all_results if r["run"].startswith("A")]
    b_runs = [r for r in all_results if r["run"].startswith("B")]

    print("\n" + "=" * 72)
    print("  CONTROLLED A/B EXPERIMENT RESULTS")
    print("=" * 72)

    for key, label in [("tp", "TP"), ("fp", "FP"), ("fn", "FN"), ("precision", "Precision"),
                        ("recall", "Recall"), ("f1", "F1"), ("composite", "Composite"),
                        ("title_accuracy", "Title Acc")]:
        a_vals = [r[key] for r in a_runs]
        b_vals = [r[key] for r in b_runs]
        a_mean = statistics.mean(a_vals)
        b_mean = statistics.mean(b_vals)
        a_sd = statistics.stdev(a_vals) if len(a_vals) > 1 else 0
        b_sd = statistics.stdev(b_vals) if len(b_vals) > 1 else 0
        delta = b_mean - a_mean
        fmt = ".4f" if key in ("precision", "recall", "f1", "title_accuracy") else ".2f"
        sign = "+" if delta >= 0 else ""
        print(f"  {label:<16} A: {a_mean:{fmt}} (sd={a_sd:{fmt}})  B: {b_mean:{fmt}} (sd={b_sd:{fmt}})  delta: {sign}{delta:{fmt}}")


if __name__ == "__main__":
    main()
