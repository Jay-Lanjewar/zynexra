# Zynexra Evaluation Matrix

Tracks system quality over time across regression test cases.

| Test Name | Input Type | Expected Behavior | Expected Confidence | Actual Result | Pass/Fail |
|---|---|---|---|---|---|
| Clean NDA | Standard mutual NDA text | Correctly identifies standard confidentiality obligations; no hallucinated issues | HIGH (≥0.75) | | |
| Unlimited Indemnity | Contract clause with unlimited indemnification | Detects indemnification risk with uncapped liability; flags severity HIGH/CRITICAL | HIGH (≥0.75) | | |
| Garbage OCR | Scrambled symbols, digits, and noise | Returns LOW quality warning; does NOT return HIGH confidence | LOW (<0.45) | | |
| Empty File | Blank/zero-byte content | Returns validation error or empty rejection; does not hallucinate issues | LOW (0.0) | | |
| Contradictory Clauses | Two clauses with directly conflicting terms | Detects structural inconsistency or contradiction between clauses | MEDIUM–HIGH (≥0.45) | | |
| Non-Legal Text | Recipe or general prose | Returns LOW confidence or appropriately handles as non-legal | LOW–MEDIUM (<0.75) | | |
| Duplicate Clause Spam | Same clause repeated 20+ times | Detects issue without duplicate explosion; suppressed count reflects dedup | MEDIUM–HIGH (≥0.45) | | |

## Legend

| Confidence Label | Score Range |
|---|---|
| HIGH | ≥ 0.75 |
| MEDIUM | ≥ 0.45, < 0.75 |
| LOW | < 0.45 |
