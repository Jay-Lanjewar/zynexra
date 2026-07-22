# Future Work: Deterministic Pipeline Testing Plan

## Problem

The Phase 1 benchmark runs NDA-02 and other documents through the full
LLM+processing pipeline. Since qwen2.5:3b-instruct is non-deterministic
(even with temperature=0 and seed=42), consecutive runs produce different
raw LLM output. This means:

- **Pipeline code changes cannot be cleanly benchmarked.**
  A regression in metrics after a code change might be caused by the code
  change OR by the model producing different output.
- **Reproducibility is impossible.**
  Two runs on the same commit with identical settings produce different results.
- **Flaky tests.**
  Tests that depend on the full pipeline may pass or fail unpredictably.

## Solution: Frozen Raw LLM Outputs

Create a "frozen" benchmark mode where the raw LLM response for each
document is pre-recorded and served from disk instead of calling the
model. This separates testing of:

1. **Pipeline processing logic** (parsing → normalization → contradiction →
   domain detection → verifiers → scoring) — tested deterministically with
   frozen inputs.
2. **Model behavior** (LLM generation quality) — tested separately using
   prompt evaluation and held-out test sets.

### Implementation Plan

#### Phase 1: Capture Raw Responses (estimate: 2-3 hours)

1. Create `tests/freeze_corpus.py` that:
   - Reads each document in `tests/validation_corpus/*.txt`
   - Calls `ResponseGenerator.generate_response()` with the document
   - Saves the raw response text to `tests/frozen_responses/{doc_name}.json`
   - Runs 3 times per document and warns if outputs differ (non-determinism check)

2. Create `tests/frozen_responses/` directory for captured outputs.

#### Phase 2: Frozen Benchmark Mode (estimate: 3-4 hours)

1. Add a `frozen` parameter (or `--frozen` CLI flag) to `phase1_eval_runner.py`
   that, when set:
   - Skips model inference
   - Loads pre-recorded raw LLM response from `tests/frozen_responses/`
   - Feeds it to the rest of the pipeline (parse → normalize → process)
   - Reports metrics

2. Implementation sketch in `phase1_eval_runner.py`:

   ```python
   def run_document_frozen(doc_name: str, doc_text: str) -> dict:
       """Run document through pipeline using pre-recorded raw LLM response."""
       frozen_path = FROZEN_DIR / f"{doc_name}.json"
       if not frozen_path.exists():
           raise FileNotFoundError(f"No frozen response for {doc_name}")
       raw_response = json.loads(frozen_path.read_text())["raw_response"]
       # same processing as normal path starting from raw_response
       issues = parse_audit_issues(raw_response)
       # ... remainder of pipeline ...
       return results
   ```

3. The frozen runner should expose the same JSON output format as the live
   runner so that the same comparison/analysis tools work on both.

#### Phase 3: CI Integration (estimate: 1-2 hours)

1. Add a CI workflow (`.github/workflows/pipeline-tests.yml`) that:
   - Runs `python tests/phase1_eval_runner.py --frozen`
   - Fails if composite score drops below a threshold
   - Archives frozen results as workflow artifacts

2. Optionally add a second workflow that runs the live benchmark and
   reports metric drift as a warning (not a hard failure).

### Which Tests to Freeze

| Test Suite | Current Status | Recommended Action |
|-----------|---------------|-------------------|
| `test_document_contradiction_scan.py` | Already deterministic (no model calls) | Keep as-is |
| `phase1_eval_runner.py` | Non-deterministic | Add `--frozen` mode |
| `phase1_eval_runner.py` (live) | Non-deterministic | Keep for drift monitoring |
| Prompt acceptance tests | Non-deterministic | Freeze or convert to minimal test |

## Alternative: Approximate Matching

An alternative to freezing is to accept the non-determinism and use
approximate matching for evaluation (e.g., "at least N out of M ground
truth findings detected, regardless of exact title"). However, this:

- Makes it harder to detect subtle regressions
- Requires updating thresholds when the model improves
- Doesn't help with debugging pipeline logic

## Recommendation

Implement freezing as described above. The overhead is small (~5-8 hours
total) and the benefit is large: fully deterministic pipeline testing that
can be run in CI with reliable pass/fail results.

---

## Appendix: Non-Determinism Root Cause

qwen2.5:3b-instruct is non-deterministic despite `temperature=0` and
`seed=42`. This is a known behavior of small quantized models:

- **Quantization noise:** 4-bit or 8-bit quantization introduces floating-point
  non-determinism that seed-based RNG cannot control.
- **GPU kernel non-determinism:** cuBLAS and other GPU libraries use
  non-deterministic algorithms by default for performance.
- **Ollama implementation:** Even with `seed` set, the model backend may
  not fully deterministic due to parallelism in attention computation.

Possible mitigations (beyond freezing):
- Switch to a larger model (e.g., 7B) that may be more consistent
- Use `OLLAMA_NUM_THREADS=1` to reduce parallelism
- Upgrade to GGUF models that support deterministic mode
- Accept non-determinism and run multi-sample evaluation (avg of 3 runs)
