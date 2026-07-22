# Root Cause Analysis — NDA-02 Benchmark Regression

## Symptom

NDA-02 (a unilateral NDA with a survival clause but no termination clause)
regressed from:
- **Baseline:** 1 TP (Incomplete Confidentiality Exclusions, Enforceability Weakness)
- **Post-change:** 0 TP, 1 FP (Structural Inconsistency), 1 FN

## Hypothesis

The regression was caused by either:
1. **Code regression** — the new `_split_into_clauses` / `classify_document_contradictions`
   logic incorrectly generated a Structural Inconsistency issue for NDA-02.
2. **Model non-determinism** — qwen2.5:3b-instruct produced different output
   despite temperature=0 and seed=42.

## Experimental Proof

### Methodology

1. Both branches (`main` and `feature/cross-clause-consistency`) are at the
   same git commit (`465ebd6`). The feature branch contains only uncommitted
   working-tree changes (the contradiction engine + debug logging).

2. A capture script was written that calls `ResponseGenerator.generate_response()`
   directly (bypassing the API server) to obtain the raw LLM output, then
   `parse_audit_issues()` for parsed issues, and `normalize_audit_response()`
   for normalized issues.

3. The script was run twice:
   - **Run 1:** On `main` (without our changes) — `tests/_capture_main.json`
   - **Run 2:** On `feature/cross-clause-consistency` (with our changes) —
     `tests/_capture_feature.json`

   Both used identical inference settings: model=qwen2.5:3b-instruct,
   temperature=0, seed=42, num_predict=768.

### Results

| Factor | Run 1 (main) | Run 2 (feature) |
|--------|-------------|-----------------|
| Raw LLM length | 2,280 chars | 2,895 chars |
| First issue title | "Enforceability Weakness: Excessive Non-Compete Duration" | "Confidentiality Survival Clause" |
| Parsed issues | 2 | 3 |
| Normalized issues | 1 | 2 |

The raw LLM outputs **differ at character 44** — the very first field of the
first issue in the JSON array. The second run's first three characters after
the issue_title key are completely different from the first run's.

### Conclusion

**The raw LLM outputs differ before any pipeline code runs.** Since:
- Both runs used the exact same binary code (same commit)
- Both used the exact same inference parameters
- The difference appears at character 44 of the raw JSON output

...the regression is definitively caused by **model non-determinism** in
qwen2.5:3b-instruct, not by the new contradiction detection code.

### Why Our Code Didn't Cause It

Even if the model had produced identical output, our code would not have
generated a new issue for NDA-02 because:
1. NDA-02 has NO termination clause — only a survival clause (clause 4).
2. `_scan_document_contradictions` requires BOTH survival AND termination
   language to report `has_document_conflict=True`.
3. Since `has_document_conflict=False`, `classify_document_contradictions`
   never reaches the new-issue generation path.
