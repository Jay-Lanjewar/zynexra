# Implementation Rationale

## Why Pipeline Code Instead of Prompt Engineering

The initial approach was to add pattern recognition instructions to the LLM
prompt (Pattern #8: Cross-Clause Contradiction Scan in `audit_prompt.py`).
However, qwen2.5:3b-instruct consistently ignored this instruction — even with
explicit examples and "highest priority" language, the model never generated a
Structural Inconsistency finding based on clause comparison alone.

**Decision:** Move the detection logic to deterministic pipeline code where it
can be tested and trusted independently of model capability.

## Why `_split_into_clauses()` Exists

The original `_scan_document_contradictions` used a simple `\n\s*\n+` split to
separate document clauses. This fails for DOCX-extracted text where paragraphs
are separated by single newlines. The three-strategy fallback handles:

1. **Blank-line separation** — standard for PDF and plain-text extracts
2. **Section-heading boundaries** — `Section/Article/Clause X` or `N. Title`
   patterns common in DOCX extracts
3. **Single-clause fallback** — when no structure is detectable, treating the
   entire document as one clause. This is safer than "one line = one clause"
   which would generate false contradictions from unrelated sentences.

Crucially, Strategy 2 only activates when Strategy 1 produces a result where
survival and termination appear in the same clause (i.e., the blank-line split
under-split the document).

## Why `DocumentContradictionResult` Is Separate

Previously `_scan_document_contradictions` returned only a `Set[str]` of
conflicting domain patterns. To generate a meaningful new issue with actual
clause text, the function now returns a `DocumentContradictionResult` with
the conflicting clauses' text. Backward compatibility is preserved because
the new-issue code path is the only consumer of the text fields; existing
callers that only check `conflicting_domains` are unaffected.

## Same-Clause Guard

The `termination\s+of\s+.*\s+obligations` pattern uses greedy `.*` and can
match across clause boundaries. A single "survive termination" clause can be
incorrectly classified as both a survival AND termination clause. The guard
`survival_clauses[0] != termination_clauses[0]` prevents generating a
contradiction issue when both languages reside in the same clause.

This is a pragmatic compromise: it may miss true contradictions where survival
and termination language appear in the same paragraph, but it prevents the far
more damaging case of false-positive Structural Inconsistency findings.

## Why Not Use the Verifier Layer

The verifier layer (post-pipeline) could theoretically detect cross-clause
contradictions. However, the contradiction engine already has:
- The full document text (`user_input`)
- The obligation domain extraction logic
- The survival/termination language detection patterns

Adding a parallel detection path in the verifier would duplicate this logic.
The contradiction engine is the correct home because it already owns the
detection infrastructure.

## Files Changed

| File | Change |
|------|--------|
| `backend/engines/contradiction_engine.py` | Core: `_split_into_clauses`, `DocumentContradictionResult`, new-issue generation in `classify_document_contradictions` |
| `backend/engines/normalization_engine.py` | Debug: contradiction trace logging in `build_audit_json_payload` |
| `backend/app.py` | Debug: verifier trace logging |
| `backend/verifiers/verifiers.py` | Debug: verifier entry/exit logging |
| `backend/prompts/audit_prompt.py` | Prompt rule for cross-clause contradiction (ineffective with 3B model) |
| `tests/test_document_contradiction_scan.py` | 9 regression tests |
