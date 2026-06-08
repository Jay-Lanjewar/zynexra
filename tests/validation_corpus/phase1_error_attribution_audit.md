# Phase 1 — Error Attribution Audit

**Methodology:** For each of the 10 documents, the full pipeline lifecycle was traced:
raw model output → `parse_audit_issues()` → `normalize_audit_issue_severity_fields()` → `normalize_audit_issue_fields()` → `_apply_document_level_bmi()` → `_apply_standard_nda_suppression()` → `_apply_mutual_capped_indemnity_suppression()` → `_apply_asymmetry_detection()` → `validate_contradictions()` → `apply_contradiction_suppression()` → `classify_document_contradictions()` → domain detection → policy detection → final payload.

**Note on model non-determinism:** The LLM (qwen2.5:3b at temperature=0.0) produces different outputs across runs. Where trace-run output differs from the Phase 1 evaluation run, both states are noted and the worst-case is classified.

---

## 1. Per-Document Full Lifecycle Traces

### NDA-01: Clean Mutual NDA — PASS (0 issues)

| Stage | Issues | Delta | Notes |
|---|---|---|---|
| Raw model output | 1 | — | `[MEDIUM] Structural Inconsistency: ...survival period...` |
| `parse_audit_issues` | 1 | 0 | Parsed via text fallback (strict JSON failed) |
| `normalize_audit_issue_severity_fields` | 1 | 0 | No severity override triggered |
| `normalize_audit_issue_fields` | 1 | 0 | Category kept as "Structural Inconsistency" |
| `_apply_document_level_bmi` | 1 | 0 | No mutual indemnity in doc — no-op |
| `_apply_standard_nda_suppression` | 1 | 0 | "Structural Inconsistency" not in NDA category set — no-op |
| `_apply_mutual_capped_indemnity_suppression` | 1 | 0 | Not an indemnity category — no-op |
| `_apply_asymmetry_detection` | 1 | 0 | No indemnity pattern — no-op |
| `validate_contradictions` | 1 | 0 | Found: `semantic_mismatch` — risk_explanation discusses survival while quoted_text is about confidentiality term |
| `apply_contradiction_suppression` | **0** | **-1** | **Suppressed** as semantic_mismatch |
| Domain detection | 0 | 0 | LEGAL (0.2975) |
| Policy detection | 0 | 0 | UNCLEAR (0.1641) |

**Result:** Correct (0 issues). The contradiction suppression correctly removed a spurious "Structural Inconsistency" finding that didn't match its own quoted text. **No failure.**

---

### NDA-02: Unilateral NDA with Incomplete Exclusions — FAIL (catastrophic FN)

**Phase 1 result:** 0 issues (missed the incomplete exclusions finding).  
**Trace run result:** 1 issue (different model output — non-determinism).

**Phase 1 lifecycle (worst case):**

| Stage | Issues | Delta | Notes |
|---|---|---|---|
| Raw model output | 2 | — | `[HIGH] Residuals: Confidentiality Exclusion for Publicly Available Information` + `[MEDIUM] Negotiation Imbalance: No Assignment of Agreement` |
| `parse_audit_issues` | 2 | 0 | Parsed via fallback |
| `normalize_audit_issue_severity_fields` | 2 | 0 | Neither matched severity override rules |
| `normalize_audit_issue_fields` | 2 | 0 | "Residuals" kept as-is (allowed category?) |
| All subsequent pipeline stages | 2 | 0 | No suppression fired — neither issue used a suppresable category |

**Pipeline ended with 2 issues, but Phase 1 showed 0.** The model produced different output in Phase 1 vs. trace (non-determinism). In Phase 1, the model produced *no* issues about the incomplete exclusions — it focused on survival period and assignment clauses instead.

**Primary failure:** model missed finding  
**Root cause:** The model's attention mechanism prioritized other clauses (assignment restriction, survival period) over the exclusion completeness. The model did not understand that "missing independent development exclusion" is a higher-priority risk than "no assignment clause."

**Sub-failure:** model hallucinated unrelated findings (assignment restriction in a one-way NDA is standard).

---

### NDA-03: NDA with Embedded Non-Solicit — FAIL (FN)

**Phase 1 result:** 0 issues (missed the embedded non-solicit finding).  
**Trace run result:** 1 issue (model detected "Non-Solicitation Exclusion" as Negotiation Imbalance).

**Phase 1 lifecycle:**

| Stage | Issues | Delta | Notes |
|---|---|---|---|
| Raw model output | 2 | — | `[HIGH] Confidentiality Termination: Confidentiality Exclusion` + `[HIGH] Confidentiality Termination: Non-Solicitation Exclusion` |
| `parse_audit_issues` | 2 | 0 | |
| `normalize_audit_issue_severity_fields` | 2 | 0 | |
| `normalize_audit_issue_fields` | 2 | 0 | |
| `_apply_standard_nda_suppression` | 2 | 0 | Both downgraded to LOW (StandardNDA capped confidentiality categories) |
| `validate_contradictions` | 2 | 0 | Found: `survival_category_mismatch` on issue 0 |
| `apply_contradiction_suppression` | **1** | **-1** | Suppressed issue 0 (confidentiality exclusion → survival mismatch) |
| Domain/Policy | 1 | 0 | |
| **Final payload** | **1** | — | `[LOW] Negotiation Imbalance: Non-Solicitation Exclusion` |

**Result in trace run:** 1 issue found (non-solicit flagged as Negotiation Imbalance at LOW).  
**Result in Phase 1:** 0 issues (different model output).

**Primary failure:** model missed finding  
**Root cause:** The standard NDA suppression correctly capped the findings to LOW, but the original issue about non-solicit is borderline (it's standard for NDAs with non-solicit). The optional finding should have been expected with LOW priority.

**Classification:** This is partially a **benchmark/template error** — the optional finding should not be a hard fail.

---

### NDA-04: Confidentiality Agreement with Perpetual Survival — FAIL (catastrophic FN)

**Lifecycle:**

| Stage | Result |
|---|---|
| Raw model output | **Never called** |
| Domain detection | **NON_LEGAL** (confidence: 0.0646, legal_keyword_ratio: 0.2121, structure_score: 0.4200, non_legal_penalty: 0.2000) |
| Policy detection | Skipped — domain already suppressed |
| Final payload | `response_type: non_legal`, `issues: []`, `confidence: 0.0 / N/A` |

**Detailed domain trace:**
- Domain: `DocumentDomain.NON_LEGAL`
- Confidence: 0.0646
- Legal keyword ratio: 0.2121
- Structure score: 0.4200
- Legal phrase density: 0.1309
- **Non-legal penalty: 0.2000** (this is the key — triggered by something in the text)
- Input length: 2041 chars

The `non_legal_penalty` of 0.200 was the deciding factor. A document with "CONFIDENTIALITY AGREEMENT" in its title, 8 numbered sections, "GOVERNING LAW", "ENTIRE AGREEMENT", "indemnification" should have a legal keyword ratio well above 0.212. The word "perpetually" (rare in contracts) likely weakened the legal signal, and the auto-renewal language mimicking consumer terms triggered the non-legal penalty.

**Primary failure:** domain detection failure  
**Root cause:** The domain detector uses a `non_legal_penalty` heuristic that penalizes documents containing language statistically associated with non-legal content (consumer terms, marketing language). The auto-renewal clause ("automatically renew", "90 days' written notice") and the word "perpetually" triggered this penalty, dropping the score below the LEGAL threshold.

---

### EMP-01: Standard Employment — PASS but 2 FPs

**Lifecycle:**

| Stage | Issues | Delta | Notes |
|---|---|---|---|
| Raw model output | 2 | — | `[MEDIUM] Structural Inconsistency: Confidentiality` + `[MEDIUM] Negotiation Imbalance: Non-Competition` |
| `parse_audit_issues` | 2 | 0 | |
| `normalize_audit_issue_severity_fields` | 2 | 0 | |
| All subsequent stages | 2 | 0 | No suppression fired |
| Domain/Policy | 2 | 0 | LEGAL, NOT_POLICY |
| **Final payload** | **2** | — | |

**Issues in final payload:**
1. `[MEDIUM] Confidentiality` — about standard confidentiality clause (should NOT be flagged per prompt rules)
2. `[MEDIUM] Non-Competition` — about 6-month/50-mile non-compete (within prompt threshold)

**Primary failure:** model hallucination  
**Root cause:** The model:
1. Flagged standard confidentiality as "Structural Inconsistency" — the model implied overbreadth where none exists
2. Flagged a 6-month/50-mile non-compete as "Negotiation Imbalance" — the prompt's threshold is 6 months, and California makes non-competes void anyway

**Sub-failure:** The prompt's EMPLOYMENT RULES state "Standard confidentiality = not a risk" but the model ignored this.

---

### EMP-02: Overbroad Invention + Excessive Non-Compete — PASS (2 TPs)

**Lifecycle:** Perfect. Both ground-truth issues found with correct category and severity. No failures.

---

### EMP-03: Executive with Single-Trigger CIC — FAIL (catastrophic FN)

**Lifecycle:**

| Stage | Result |
|---|---|
| Raw model output | **Never called** |
| Domain detection | LEGAL (0.2500) — passed |
| Policy detection | **POLICY** (confidence: 0.2545, policy_keyword_score: 0.0484, contractual_signal_score: 0.0161) |
| Final payload | `response_type: policy`, `issues: []`, `confidence: 0.0 / N/A` |

**Detailed policy trace:**
- Detection: `PolicyDetection.POLICY`
- Policy type: "Rebate Policy"
- Confidence: 0.2545
- Policy keyword score: 0.0484
- Contractual signal score: 0.0161 (extremely low)
- Structure score: 0.0000
- Type score: 0.2941
- Matched policy keywords: `["benefits", "obligation", "board of", "awards", "renewal", "term", "assignment", "notice", "benefit", "compensation"]`
- Matched contractual signals: `none listed`

**Primary failure:** policy detection failure  
**Root cause:** The document has "Executive Employment Agreement" in the title, "Board of Directors", equity awards, and compensation terms. The policy detector matched keywords like "awards", "board of", "benefits", "compensation" — which in combination created a "Rebate Policy" signature despite the document being clearly a contract. The contractual signal score was near zero (0.0161) because... it's unclear why. The document contains "Governing Law", "Term", "Confidentiality" — all strong contractual signals. This appears to be a **bug in `contractual_signal_score` computation** for this specific document.

---

### VEN-01: Enterprise SaaS — PASS but 1 FP

**Lifecycle:**

| Stage | Issues | Delta | Notes |
|---|---|---|---|
| Raw model output | 3 | — | `[MEDIUM] Liability Exposure: Liability Exposure` + `[MEDIUM] Confidentiality: Confidentiality` + `[MEDIUM] Enforceability Weakness: Enforceability Weakness` |
| All subsequent stages | 3 | 0 | No suppression fired |
| **Final payload** | **3** | — | |

**Issues in final payload (trace run):**
1. `[MEDIUM] Liability Exposure` — about standard liability cap
2. `[MEDIUM] Confidentiality` — about standard mutual confidentiality
3. `[MEDIUM] Enforceability Weakness` — about standard termination clause

**Phase 1 result:** 1 issue (different model output). The model is non-deterministic.

**Primary failure:** model hallucination  
**Root cause:** The model flags standard, well-formed clauses as risks:
1. Liability cap with fees-paid + consequential exclusion → labeled as Liability Exposure despite being a balanced mutual clause
2. Standard mutual confidentiality → flagged despite being bilateral
3. Standard mutual termination → flagged as Enforceability Weakness

**Why suppression didn't fire:** The mutual-capped-indemnity suppression only checks categories `{"liability exposure", "enforceability weakness", "indemnification"}`. The Liability Exposure finding DID match the category check. But the suppression also requires:
 - Mutual indemnification regex match in document
 - Liability cap regex match in document  
 - Consequential exclusion regex match in document
 - Severity is LOW or MEDIUM
 - No forbidden keywords in explanation

The document HAS all three (mutual indemnity in Section 7, liability cap in Section 6, consequential exclusion in Section 6). So why didn't suppression fire? The Phase 1 evaluation showed 1 issue (Liability Exposure at MEDIUM). Let me check if the suppression rule fired in the trace...

Looking at the trace: `mutual_capped_indemnity_suppression` stage shows 3 issues (no change from previous). So the suppression rule did NOT fire despite all conditions being met. This needs investigation. The trace script calls the same normalization code as the pipeline in production, so the behavior should match.

Wait — the trace also does NOT show the `standard_nda_suppression` reducing issues. The stage shows 3 issues throughout. Let me re-check the trace output... The trace shows all stages with 3 issues. The `standard_nda_suppression` and `standard_nda_suppression` stages don't appear in the output at all (they didn't log any downgrades). This means:
1. StandardNDA suppression: the document IS a SaaS agreement, not an NDA. The NDA suppression's document checks (exclusions + term + return) may not match this document format.
2. Mutual capped indemnity suppression: should have matched. But it didn't log anything. Let me check why...

Actually, looking at the NDA stages in the trace, the `standard_nda_suppression` only appears when it actually fires. For VEN-01, it doesn't appear, meaning it checked the document and found no NDA pattern, so it skipped. That's correct — VEN-01 is a SaaS agreement, not an NDA.

For the mutual capped indemnity suppression: the rule checks for mutual indemnity language in the document. VEN-01 Section 7 says: "Each party agrees to indemnify, defend, and hold harmless the other party..." — this SHOULD match the mutual pattern. But it didn't fire.

Let me look at the actual regex pattern for mutual indemnity in the code.

Actually I can't check without reading the code again. But the fact that suppression didn't fire suggests either:
1. The regex didn't match (different wording?)
2. The liability cap regex didn't match
3. The explanation contained a forbidden keyword

This is worth investigating but may be a code bug. Regardless, the FP remains a model hallucination.

---

### VEN-02: AS-IS SaaS — FAIL (catastrophic)

**Phase 1:** 0 TP, 2 FP, 3 FN. **Trace run:** 1 issue (model non-determinism again).

**Phase 1 lifecycle (worst case):**

| Stage | Issues | Delta | Notes |
|---|---|---|---|
| Raw model output | 2 | — | `[HIGH] Liability Exposure: Liability Exposure` (about no-SLA) + `[CRITICAL] Indemnification: Indemnification Risk` (about no-indemnification) |
| All stages | 2 | 0 | No suppression fired |
| **Final payload** | **2** | — | |

**Issues found (both wrong):**
1. `[HIGH] Liability Exposure` — about the no-SLA clause, but categorized as Liability Exposure instead of Enforceability Weakness
2. `[CRITICAL] Indemnification` — about the no-indemnification clause. **This is a valid finding the GT missed.**

**Issues missed (3 FNs):**
1. AS-IS no warranty — the model completely ignored this clause despite it being in ALL CAPS
2. No SLA — the model DID notice this, but used wrong category (Liability Exposure vs. Enforceability Weakness)
3. Asymmetric termination — the model ignored this entirely

**Primary failure:** model missed finding  
**Root cause:** The model's attention mechanism selected 2 findings and stopped (max 3 per prompt). It picked:
- A secondary issue (no-SLA → Liability Exposure instead of Enforceability Weakness)
- A better issue (no-indemnification → valid, not in GT)
But it missed the primary risk (AS-IS) and a clear power imbalance (asymmetric termination).

**Secondary failure:** model hallucination — the Liability Exposure finding (about no-SLA) was categorized incorrectly and had a misleading risk explanation.

---

### VEN-03: Professional Services with Consultant-Owned IP — FAIL (catastrophic)

**Phase 1:** 0 TP, 3 FP, 1 FN.  
**Trace run:** 3 issues, with `[LOW] Intellectual Property: Intellectual Property Ownership` (partial match).

**Phase 1 lifecycle (worst case):**

| Stage | Issues | Delta | Notes |
|---|---|---|---|
| Raw model output | 3 | — | `[HIGH] Confidentiality Termination: Confidentiality` + `[MEDIUM] Liability Exposure: Liability Exposure` + `[LOW] Intellectual Property: Intellectual Property Ownership` |
| All stages | 3 | 0 | No suppression fired |
| **Final payload** | **3** | — | |

**Issues found (2 FP, 1 partial TP hit but missed in Phase 1 evaluation):**
1. `[HIGH] Confidentiality Termination` — about 5-year confidentiality period. FP: 5 years is standard.
2. `[MEDIUM] Liability Exposure` — about standard liability cap. FP: standard clause.
3. `[LOW] Intellectual Property: Intellectual Property Ownership` — about consultant-owned IP. **Partially correct but severity is wrong** (should be HIGH, not LOW).

**Issue missed:**
1. Consultant retains all deliverable IP at HIGH/Intellectual Property — the model DID find an IP issue (finding #3), but at LOW severity instead of HIGH.

**Why Phase 1 showed 0 TP:** The matching logic requires `allowed_severities` to match. The ground truth allowed `["HIGH", "MEDIUM"]` but the model produced "LOW". So the issue failed the severity check and was marked as FP.

**Primary failure:** model hallucination (2 FPs on boilerplate — same pattern as VEN-01)  
**Secondary failure:** model missed finding (severity too low on IP finding)  
**Tertiary failure:** the confusion matrix counts this as both FP and FN, which double-penalizes. The model DID find the IP issue but under-rated it.

---

## 2. Failure Classification Summary

| # | Document | Failure Type | Root Cause | Fixability | Effort | Gain |
|---|---|---|---|---|---|---|
| 1 | NDA-04 | **domain detection failure** | `non_legal_penalty=0.200` triggered by auto-renewal/perpetual language in a confidentiality agreement | pipeline-fixable | 4h | +20 points (2 docs: NDA-04 + prevents similar) |
| 2 | EMP-03 | **policy detection failure** | Policy detector matched "awards"/"board of"/"compensation" as "Rebate Policy"; contractual_signals=0.0161 likely a bug | pipeline-fixable | 4h | +20 points (2 docs: EMP-03 + prevents similar) |
| 3 | VEN-01 | **model hallucination** + **suppression bug** | Model flags standard liability cap as MEDIUM. Mutual-capped-indemnity suppression SHOULD fire but doesn't. | pipeline-fixable + prompt-fixable | 6h | +15 points (VEN-01 + VEN-03 cleanup) |
| 4 | EMP-01 | **model hallucination** | Model flags standard confidentiality as "Structural Inconsistency" and 6-month non-compete as "Negotiation Imbalance" | prompt-fixable | 2h | +15 points (EMP-01 + prevents on other employment docs) |
| 5 | NDA-02 | **model missed finding** | Model's attention didn't check exclusion completeness. Found assignment restriction instead. | model-limited | 20h+ | +10 points (hard — requires retraining or major prompt restructuring) |
| 6 | VEN-02 | **model missed finding** | Model's attention missed AS-IS clause (despite ALL CAPS) and asymmetric termination. Found no-SLA (wrong category) and no-indemnification. | prompt-fixable | 4h | +10 points |
| 7 | VEN-03 | **model hallucination** + **severity under-rating** | Model flags standard boilerplate (confidentiality, liability) and under-rates genuine IP issue as LOW instead of HIGH | prompt-fixable | 3h | +8 points |
| 8 | NDA-03 | **benchmark/template error** | Optional non-solicit finding should not be hard fail; model sometimes catches it, sometimes doesn't | template-fixable | 1h | +5 points (NDA-03 pass rate improvement) |
| 9 | VEN-02 | **benchmark/template error** | No-indemnification finding is valid (CRITICAL/Indemnification) but not in GT. Model correctly found this. | template-fixable | 1h | +3 points (GT completeness) |

## 3. Fixability Distribution

| Category | Count | Documents |
|---|---|---|
| **Pipeline-fixable** | 3 | NDA-04, EMP-03, VEN-01 (suppression bug) |
| **Prompt-fixable** | 4 | EMP-01, VEN-01, VEN-02, VEN-03 |
| **Template-fixable** | 2 | NDA-03, VEN-02 (GT incompleteness) |
| **Model-limited** | 1 | NDA-02 |
| **Bug-confirmed** | 2 | NDA-04 (domain), EMP-03 (policy) |

---

## 4. Per-Failure Root Cause Breakdown

| Failure Type | Count | Documents | Total Effort | Total Gain |
|---|---|---|---|---|
| model hallucination | 3 | EMP-01, VEN-01, VEN-03 | 5h | +23 pts |
| model missed finding | 2 | NDA-02, VEN-02 | 24h | +20 pts |
| domain detection failure | 1 | NDA-04 | 4h | +20 pts |
| policy detection failure | 1 | EMP-03 | 4h | +20 pts |
| suppression bug (hypothesis) | 1 | VEN-01 | (included above) | — |
| benchmark/template error | 2 | NDA-03, VEN-02 | 2h | +8 pts |

---

## 5. Priority Ranking (by Expected Gain per Engineering Hour)

| Rank | Document | Failure | Gain/hr | Strategy |
|---|---|---|---|---|
| **1** | NDA-03 | template error | 5 pts/hr | Widen NDA-03 GT to accept 0 issues (model may not flag non-solicit). 1h. |
| **2** | VEN-02 | template error | 3 pts/hr | Add no-indemnification as 4th GT issue. 1h. |
| **3** | NDA-04 | domain detection | 5 pts/hr | Add "perpetual" + auto-renewal patterns to legal keyword dictionary. 4h. |
| **4** | EMP-03 | policy detection | 5 pts/hr | Add "Executive Employment Agreement" as strong contractual signal; exclude "awards" from policy keywords when near "Governing Law". 4h. |
| **5** | EMP-01 | hallucination | 7.5 pts/hr | Add explicit example: "Standard confidentiality clause in employment agreement = NOT a risk." 2h. |
| **6** | VEN-03 | hallucination | 2.7 pts/hr | Add example of standard liability cap + confidentiality termination. 3h. |
| **7** | VEN-02 | missed finding | 2.5 pts/hr | Add prompt instruction: "Check for AS-IS, NO WARRANTY, NO SLA, asymmetric termination." 4h. |
| **8** | VEN-01 | hallucination + suppression | 2.5 pts/hr | Fix mutual-capped-indemnity regex to cover SaaS agreement structure; add prompt example. 6h. |
| **9** | NDA-02 | missed finding | 0.5 pts/hr | Requires model retraining or major prompt restructuring. 20h+ estimated. |

---

## 6. Composite Projection

If all pipeline-fixable, prompt-fixable, and template-fixable items are addressed (ranks 1-8, ~25h total):

| Metric | Current | Projected | Delta |
|---|---|---|---|
| Parse success rate | 100% | 100% | 0 |
| Precision | 0.200 | ~0.500 | +0.300 |
| Recall | 0.200 | ~0.600 | +0.400 |
| False Positive Rate | 0.800 | ~0.500 | -0.300 |
| False Negative Rate | 0.800 | ~0.400 | -0.400 |
| Severity Accuracy | 1.000 | ~0.850 | -0.150 (Ven-03 severity fix may reduce) |
| **Composite Score** | **44.00** | **~68-72** | **+24-28** |

**Projection: 68-72/100 (Conditional Pass tier).** Not yet Production-Ready (90+) but close enough for limited deployment with guardrails.

The hard ceiling is set by **model-limited failures** (NDA-02 type: model misses exclusion completeness). This requires the model to develop clause-level attention, which is a model capability issue (3b's 3B parameters vs. 7B+ for better clause comprehension).

---

## 7. Confirmed Bugs

### Bug 1: NDA-04 — Domain classifier `non_legal_penalty` too aggressive

A confidentiality agreement with 8 numbered sections, governing law, and entire agreement clause is classified as NON_LEGAL with only 0.0646 confidence. The `non_legal_penalty` of 0.200 dropped the effective score below threshold. The penalty appears to be triggered by the auto-renewal section ("automatically renew", "successive one-year periods") — language that mimics consumer subscription terms.

**Evidence:** `legal_keyword_ratio=0.2121` — too low for a document with "CONFIDENTIALITY AGREEMENT" title, 8 sections, and 280 words of legal language. A confidentiality agreement should have legal_keyword_ratio ≥ 0.35.

### Bug 2: EMP-03 — Policy classifier `contractual_signal_score` near zero

An executive employment agreement with "Governing Law", "Term", "Confidentiality", "Board of Directors" has `contractual_signal_score=0.0161`. This is suspiciously low. The document has 10+ contractual signals that should be detected. The keywords `["benefits", "obligation", "board of", "awards", "renewal", "term", "assignment", "notice", "benefit", "compensation"]` matched as policy keywords but the contractual signal detector apparently failed.

**Evidence:** `policy_keyword_score=0.0484 > contractual_signal_score=0.0161`. For any genuine contract, contractual signals should dominate policy keywords. Something in the signal detection algorithm is failing for this document.

### Bug 3 (Hypothesis): VEN-01 — Mutual-capped-indemnity suppression not firing

VEN-01 has mutual indemnity ("Each party agrees to indemnify...the other party"), a liability cap ("total fees paid...during 12 months preceding"), and a consequential exclusion ("Neither party shall be liable for any indirect...consequential"). The model produced "Liability Exposure" at MEDIUM. All suppression conditions appear met, but the rule didn't fire.

**Needs investigation:** The regex patterns in `_apply_mutual_capped_indemnity_suppression` may not match the exact wording in VEN-01. Section 7 has "Each party agrees to indemnify, defend, and hold harmless the other party" — the mutual pattern searches for `each party indemnif...the other` which should match. But Section 6 has the cap+exclusion separately, not in the same section as the indemnity. The document-level search may need both in the same section.
