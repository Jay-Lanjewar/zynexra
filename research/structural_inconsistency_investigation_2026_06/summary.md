# Structural Inconsistency Cross-Clause Contradiction — Investigation Summary

**Date:** 2026-07-01  
**Branch:** `feature/cross-clause-consistency` → merged to `main`  
**Commit:** `e769668`  
**Previous baseline commit:** `465ebd6` (merge-base)

## Objective

Implement pipeline-level cross-clause contradiction detection that generates new
Structural Inconsistency audit issues independently of the LLM, so that
contradictions between survival and termination clauses are reliably detected
even when the 3B model fails to produce this finding on its own.

## Approach

Rather than relying on the LLM prompt to generate Structural Inconsistency
findings (which the 3B model ignores despite explicit instructions), the
detection logic operates at the pipeline level in `contradiction_engine.py`:

1. **`_split_into_clauses()`** — a multi-strategy clause splitter that handles
   blank-line-separated paragraphs (PDF/text extracts), section-heading
   boundaries (DOCX extracts), and falls back to the entire document as a
   single clause when no structure is detectable.

2. **`DocumentContradictionResult`** — a structured dataclass that returns clause
   excerpts alongside conflicting domain sets, enabling precise issue generation.

3. **`classify_document_contradictions()` new-issue path** — when a document-level
   contradiction is detected but no existing issue domain overlaps with the
   conflicting domains, a fresh `AuditIssue` is created with both conflicting
   clauses in `quoted_text`, categorized as `Structural Inconsistency`.

4. **Same-clause safeguard** — prevents generating issues when survival and
   termination language reside in the same clause (e.g., "survive termination"
   matched by a greedy termination pattern).

## Key Results

| Metric | Baseline (2026-06-24) | Final (2026-07-01) | Delta |
|--------|----------------------|-------------------|-------|
| TP     | 10                   | 9                  | -1    |
| FP     | 6                    | 7                  | +1    |
| FN     | 0                    | 1                  | +1    |
| Precision | 0.625            | 0.5625             | -0.0625 |
| Recall | 1.000               | 0.9000             | -0.1   |
| Composite | 88.00            | 84.17              | -3.83 |

## NDA-02 Regression

The sole regression (NDA-02: lost TP, gained FP + FN) is **confirmed model
non-determinism**, not a code regression. See `root_cause_analysis.md` for
the full experimental proof.

The regression was reproduced by running the identical pipeline code on
the same commit (`465ebd6`) twice with identical inference settings
(temperature=0, seed=42, num_predict=768). The two runs produced different
raw LLM JSON output (different first issue title, different issue count),
proving the model is inherently non-deterministic.
