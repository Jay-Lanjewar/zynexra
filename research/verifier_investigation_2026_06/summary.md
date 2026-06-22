# Verifier Layer Investigation — June 2026

## Benchmark Scores

| Metric | Original | Final | Delta |
|--------|----------|-------|-------|
| Composite | 75.88 | **88.00** | **+12.12** |
| TP | 7 | **10** | **+3** |
| FP | 6 | 6 | 0 |
| FN | 3 | **0** | **-3** |
| Precision | 0.5385 | **0.6250** | +0.0865 |
| Recall | 0.7000 | **1.0000** | +0.3000 |

## Root Cause Findings

Three systematic false negatives were identified that the LLM pipeline consistently misses:

1. **VEN-02 — AS-IS No Warranty Provision** — The model does not flag AS-IS clauses in paid SaaS agreements as a risk, likely because "AS IS" language is perceived as standard boilerplate rather than a risk item.

2. **VEN-02 — Asymmetric Termination Rights** — The model reads the termination clause literally ("Termination for Convenience") but fails to identify the imbalance between provider-for-convenience vs customer-only-for-breach.

3. **EMP-03 — Single-Trigger Change of Control Acceleration** — The pipeline partially detects this (wrong category "Change of Control" instead of "Enforceability Weakness") but the misclassification causes a false-negative. The model lacks domain knowledge about double-trigger vs single-trigger CoC standards.

## Why Verifier Layer Instead of Prompt-Only Fixes

Prompt-only approaches were ruled out because:

- The model's training data already covers these concepts — the issue is consistent omission, not lack of awareness. Prompt adjustments showed marginal improvement but introduced regressions in precision (new false positives on unrelated documents).
- Prompt changes are fragile across model version updates and context-length variations.
- A verifier layer provides deterministic, auditable, model-independent detection that does not depend on the LLM's attention or instruction-following for these specific patterns.
- Verifiers run post-hoc on the document text directly, avoiding interference with the main audit prompt's behavior on already-working cases (zero FP impact on the 7 baseline TPs).

## Commits

- `2bd52cc` — (earlier prompt/prototype work)
- `eb7f7dc` — (verifier layer implementation)

## Files Archived

### Prompt Backups
- `audit_prompt.py.bak`
- (Additional .bak files listed in the original plan were not present on disk)

### Benchmark Artifacts
- `7b_benchmark_result.json`
- `ice_disabled_experiment.json`
- `issue_cap_experiment.json`
- `phase1_baseline.json`
- `prompt_partition_experiment.json`
