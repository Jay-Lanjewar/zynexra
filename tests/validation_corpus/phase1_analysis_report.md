# Phase 1 Validation Results — Analysis Report

**Run:** 2026-06-01 18:14  
**Model:** qwen2.5:3b-instruct  
**Pipeline:** Production (no modifications)  
**Corpus:** 10 real-world-style documents (4 NDA, 3 Employment, 3 Vendor)  

---

## 1. Summary

| Metric | Value | Target | Status |
|---|---|---|---|
| Documents passed | 4/10 | — | ❌ |
| Parse success rate | 100.00% | ≥ 95% | ✅ |
| Precision | 0.2000 (2 TP / 10 predicted) | ≥ 0.70 | ❌ |
| Recall | 0.2000 (2 TP / 10 ground truth) | ≥ 0.65 | ❌ |
| False Positive Rate | 0.8000 | ≤ 0.30 | ❌ |
| False Negative Rate | 0.8000 | ≤ 0.35 | ❌ |
| Severity Accuracy | 1.0000 | ≥ 0.75 | ✅ |
| **Composite Score** | **44.00 / 100** | ≥ 70 | ❌ |

**Verdict: NOT READY for production (score 44/100, Needs Improvement tier).**

---

## 2. Per-Type Breakdown

| Type | Precision | Recall | Composite | Parse Rate |
|---|---|---|---|---|
| NDA (4 docs) | 0.000 | 0.000 | 30.0 | 100% |
| Employment (3 docs) | 0.500 | 0.667 | 75.0 | 100% |
| Vendor (3 docs) | 0.000 | 0.000 | 20.0 | 100% |

Employment performs best (75/100) because EMP-02 was perfectly handled. Vendor is worst (20/100): every document failed.

---

## 3. Every False Positive — Detailed

### FP-1: EMP-01 — "Confidentiality" @ HIGH / Confidentiality Risk

| Field | Value |
|---|---|
| Quoted text | `Employee shall hold in confidence and not disclose or use any confidential or proprietary information of Company...` |
| Explanation | "The confidentiality obligation is overbroad as it covers all confidential or proprietary information, regardless of whether the information was developed by Employee on their own time. This could be unenforceable in jurisdictions with statutory protections like California Labor Code 2870." |
| Why it's a FP | The model conflates confidentiality with invention assignment. The confidentiality clause is standard — it protects Company's trade secrets and proprietary info. It does NOT claim ownership of employee inventions. The model hallucinated an overbreadth argument that applies to Section 6 (invention assignment), not Section 5 (confidentiality). **Root cause:** model category confusion between confidentiality and IP assignment. |

### FP-2: EMP-01 — "Non-Competition" @ HIGH / Enforceability Weakness

| Field | Value |
|---|---|
| Quoted text | `For a period of six (6) months following termination of employment, Employee shall not, within a fifty (50) mile radius...` |
| Explanation | "The non-competition restriction extends for 6 months and covers an extensive geographic area, which may be unenforceable under California law. The clause also does not specify the duration of the restrictions after termination, creating ambiguity." |
| Why it's a FP | The non-compete is 6 months / 50 miles in California — this is within the prompt's 6-month threshold and standard for California where non-competes are generally unenforceable anyway. The model's risk explanation is contradictory: if CA law makes non-competes unenforceable, then the restriction itself is void, not "extensive." **Root cause:** model fails to contextualize non-compete within jurisdiction (California = void regardless of scope). |

### FP-3: VEN-01 — "Liability Exposure" @ MEDIUM / Liability Exposure

| Field | Value |
|---|---|
| Quoted text | `Neither party's aggregate liability arising out of or relating to this Agreement shall exceed the total fees paid... Neither party shall be liable for any indirect, incidental, special, consequential, or punitive damages.` |
| Explanation | "The limitation of liability clause does not include a cap on specific types of damages such as indirect, incidental, special, consequential, or punitive damages, which could expose both parties to uncapped financial risk." |
| Why it's a FP | The quoted text EXPLICITLY excludes consequential damages: "Neither party shall be liable for any indirect, incidental, special, consequential, or punitive damages." The model hallucinated that this exclusion does not exist. The clause also caps aggregate liability at 12 months fees. This is a gold-standard SaaS liability clause. **Root cause:** model failed to read its own quoted text correctly — directly contradicts the evidence it cites. |

### FP-4: VEN-02 — "Liability Exposure" @ HIGH / Liability Exposure

| Field | Value |
|---|---|
| Quoted text | `Provider does not guarantee any level of uptime, availability, or performance. Customer's sole remedy for any service interruption is termination of this Agreement.` |
| Explanation | "The clause allows Provider to terminate the agreement without cause and limits Customer's remedies to termination, exposing both parties to potential liability." |
| Why it's a FP | The quoted text is about NO SLA — the model correctly identified a problem (no SLA) but miscategorized it as "Liability Exposure" instead of "Enforceability Weakness." The severity (HIGH) is also too high for this issue. The no-SLA clause IS a real issue, but the model's category and severity are wrong. **Root cause:** category confusion — model maps "bad service term" → "Liability Exposure" instead of "Enforceability Weakness." |

### FP-5: VEN-02 — "Indemnification Risk" @ CRITICAL / Indemnification

| Field | Value |
|---|---|
| Quoted text | `Provider shall have no obligation to indemnify, defend, or hold harmless Customer from any claims arising out of or relating to the Service, including claims of intellectual property infringement.` |
| Explanation | "The clause explicitly excludes Provider's liability for intellectual property infringement and other claims related to the Service, which could expose Customer to significant risk." |
| Why it's a FP | **This is actually a VALID finding that we missed in ground truth.** The no-indemnification clause is a genuine risk. However, it matches none of our 3 expected issues (AS-IS, No SLA, Asymmetric Termination). This is a ground-truth quality issue — our review template was incomplete. The model found a real issue we didn't account for. **Root cause:** ground truth incompleteness. |

### FP-6: VEN-03 — "Confidentiality" @ HIGH / Confidentiality Termination

| Field | Value |
|---|---|
| Quoted text | `Each party shall hold the other's confidential information in confidence for a period of five (5) years.` |
| Explanation | "The confidentiality obligation terminates after five years, which may be insufficient to protect sensitive information over longer periods or under different legal standards." |
| Why it's a FP | A 5-year confidentiality period is standard for professional services agreements. The model flags it as HIGH/Confidentiality Termination, implying the confidentiality term is too short. 5 years is well within standard range (3-7 years common). **Root cause:** model over-sensitivity to any confidentiality time limit, treating reasonable durations as risks. |

### FP-7: VEN-03 — "Liability Exposure" @ MEDIUM / Liability Exposure

| Field | Value |
|---|---|
| Quoted text | `Consultant's aggregate liability arising out of or relating to this Agreement shall not exceed the total fees paid by Client under the applicable SOW. In no event shall Consultant be liable for any indirect, incidental, special, consequential, or punitive damages.` |
| Explanation | "The limitation of liability clause does not address specific types of damages... and may be unenforceable in jurisdictions with statutory limitations on liability." |
| Why it's a FP | This is a standard liability cap (fees-paid + consequential exclusion) for a consulting agreement. The model's explanation is factually incorrect — the clause DOES address specific types (indirect, incidental, special, consequential, punitive). Same hallucination pattern as VEN-01/FP-3. **Root cause:** model hallucinates missing language that is actually present in the quoted text. |

### FP-8: VEN-03 — "Enforceability Weakness" @ MEDIUM / Enforceability Weakness

| Field | Value |
|---|---|
| Quoted text | `Either party may terminate this Agreement for convenience upon thirty (30) days' written notice. Either party may terminate for material breach that remains uncured for thirty (30) days.` |
| Explanation | "The termination provisions are overly permissive and could be seen as weakening the enforceability of the agreement, especially if one party is in a stronger position to negotiate terms..." |
| Why it's a FP | Mutual 30-day termination for convenience is standard for consulting agreements. This is not an enforceable contract — the model is flagging a normal at-will termination clause. **Root cause:** model incorrectly treats at-will/mutual termination as an enforceability risk. |

---

## 4. Every False Negative — Detailed

### FN-1: NDA-02 — "Incomplete Confidentiality Exclusions" (MEDIUM / Enforceability Weakness)

| Field | Value |
|---|---|
| Expected | Model should flag that exclusions are limited to public availability and prior knowledge only — missing independent development and third-party receipt. |
| Reality | Model produced 0 issues. The pipeline received a valid "Confidentiality Termination" finding from the model at CRITICAL severity, but it was about the 5-year survival period, not the incomplete exclusions. |
| Root cause | The model detected the survival period but completely missed the exclusion deficiency. The model's attention is drawn to term/survival clauses rather than exclusion clauses. The pipeline's StandardNDA suppression may also have suppressed the survival finding (Confidentiality Termination → capped to LOW). |
| Severity | Catastrophic (red flag document, 0 issues) |

### FN-2: NDA-03 — "Non-Solicitation Clause in NDA" (LOW / Negotiation Imbalance)

| Field | Value |
|---|---|
| Expected | Model should optionally flag that a non-solicit clause embedded in an NDA is unusual. |
| Reality | Model produced 0 issues. NDA-03's non-solicit was not flagged. |
| Root cause | **Acceptable miss.** This was marked as an optional finding with evaluation weight 0.5. The model produced a "Confidentiality Exclusion" finding (about survival period) that was suppressed by StandardNDA rules. The non-solicit finding is borderline and most legal reviewers would not flag it. |
| Severity | Low (optional finding, expected weight 0.5) |

### FN-3: NDA-04 — "Perpetual Confidentiality Survival" (MEDIUM / Enforceability Weakness)

| Field | Value |
|---|---|
| Expected | Model should flag perpetual confidentiality survival and auto-renewal with 90-day notice as an enforceability risk. |
| Reality | **Document classified as NON_LEGAL** ("Uncategorized Non-Legal"). The domain classifier determined this was non-legal text with confidence 0.0646 and suppressed all pipeline processing. |
| Root cause | **Domain detection failure.** A confidentiality agreement with clear contractual structure (sections, definitions, obligations, governing law) was classified as non-legal. The domain confidence (0.0646) and legal keyword ratio (0.212) are suspiciously low. The `non_legal_penalty` of 0.2 suggests something in the document structure triggered the non-legal penalty. Possible causes: (1) the word "perpetually" is rare in contracts and triggered a negative signal, (2) the short document length (280 words) lowered structure_score below threshold. |
| Severity | Catastrophic (red flag document, 0 issues, domain detection failure) |

### FN-4: EMP-03 — "Single-Trigger Change of Control Acceleration" (MEDIUM / Enforceability Weakness)

| Field | Value |
|---|---|
| Expected | Model should flag single-trigger CIC (full acceleration without termination) as unusual. |
| Reality | **Document classified as POLICY** ("Rebate Policy"). The policy detector identified this executive employment agreement as a "Rebate Policy" with confidence 0.2545 (policy_keyword_score=0.0484, contractual_signal_score=0.0161). |
| Root cause | **Policy detection failure.** An executive employment agreement with term, compensation, CIC, non-compete, and governing law was classified as a "Rebate Policy" — possibly because of the word "equity" and "awards" in the equity compensation section. The extremely low contractual_signal_score (0.0161) is suspicious and suggests a bug in the contractual signal detection heuristic. This is the most dangerous failure mode because it silently suppresses all pipeline processing without any indication to the user. |
| Severity | Catastrophic (red flag document, 0 issues, policy detection failure) |

### FN-5: VEN-02 — "AS-IS No Warranty Provision" (MEDIUM / Enforceability Weakness)

| Field | Value |
|---|---|
| Expected | Model should flag AS-IS/no-warranty disclaimer in a paid SaaS agreement. |
| Reality | Model produced no finding for the AS-IS clause. Instead, it produced "Liability Exposure" (about the no-SLA) and "Indemnification Risk" (about no-indemnification). |
| Root cause | The model treated the no-SLA as a Liability Exposure issue (FP-4) and the no-indemnification as Indemnification (valid finding, not in GT), but completely ignored the AS-IS clause despite it being the most prominent risk. The words "AS IS" and "AS AVAILABLE" in ALL CAPS were not flagged. |
| Severity | High (missed the clearest risk in the document) |

### FN-6: VEN-02 — "No Service Level Agreement" (MEDIUM / Enforceability Weakness)

| Field | Value |
|---|---|
| Expected | Model should flag absence of SLA as an Enforceability Weakness. |
| Reality | Model DID flag the no-SLA clause, but as "Liability Exposure" @ HIGH (FP-4) instead of "Enforceability Weakness" @ MEDIUM. |
| Root cause | **Category mismatch.** The model correctly identified the problem (no SLA = risk) but used the wrong category (Liability Exposure vs. Enforceability Weakness). If the severity and category were different, this could match our GT issue VEN-02-B. The category must be Enforceability Weakness per our template. |
| Severity | Medium (found the issue, wrong category/severity) |

### FN-7: VEN-02 — "Asymmetric Termination Rights" (MEDIUM / Negotiation Imbalance)

| Field | Value |
|---|---|
| Expected | Model should flag that provider can terminate for convenience but customer cannot. |
| Reality | Model produced no finding about the asymmetric termination clause. |
| Root cause | Model focused on the no-SLA (FP-4) and no-indemnification (FP-5) and did not read Section 7 (Termination for Convenience). This is a **clause selection failure** — the model chose 2 findings and stopped, missing a third genuine issue. |
| Severity | High (missed a clear power imbalance) |

### FN-8: VEN-03 — "Consultant Retains All Deliverable IP" (HIGH / Intellectual Property)

| Field | Value |
|---|---|
| Expected | Model should flag that consultant owns all deliverables, client gets only a non-exclusive license. |
| Reality | Model produced "Confidentiality Termination," "Liability Exposure," and "Enforceability Weakness" (all FPs) but completely missed the IP ownership clause (Section 3). |
| Root cause | **Critical miss.** The model read the confidentiality section (5-year term) and the liability section (standard cap) and the termination section (mutual for convenience), but skipped Section 3 — the most important clause in the entire agreement. The model's attention mechanism prioritized standard boilerplate over the one genuinely problematic clause. This is a systematic weakness: the model flags standard terms and misses unusual ones. |
| Severity | Catastrophic (red flag document, missed HIGH/IP finding) |

---

## 5. Root Cause Analysis by Failure Pattern

### Pattern A: Domain/Policy Detection Failure (2/10 documents)

**Affected:** NDA-04 (NON_LEGAL), EMP-03 (POLICY)

Two documents were completely removed from the pipeline by upstream classifiers — one classified as non-legal, one as a rebate policy. These are **hard failures** that prevent the audit pipeline from running at all.

- NDA-04: A confidentiality agreement with "CONFIDENTIALITY AGREEMENT" in the title, 8 numbered sections, standard contractual language. Classifier scored it as non-legal with confidence 0.0646.
- EMP-03: An executive employment agreement with term, compensation, CIC, non-compete. Classifier scored it as "Rebate Policy" with policy_confidence 0.2545.

**Recommendation:** The domain detector needs a threshold review. A document containing "GOVERNING LAW", "ENTIRE AGREEMENT", and numbered sections should never score below 0.15 for non-legal. The policy detector's keyword "awards" (from equity awards) triggered a false positive.

### Pattern B: Standard-Boilerplate Hallucination (4/8 pipeline-processed docs)

**Affected:** EMP-01 (2 FPs), VEN-01 (1 FP), VEN-03 (2 FPs)

The model flags standard, well-formed clauses as risks. Common triggers:
- **Confidentiality clauses** → flagged as HIGH regardless of reasonableness
- **Liability caps** → flagged as MEDIUM-Liability Exposure even when they have `fees-paid + consequential exclusion`
- **Non-competes** → flagged as HIGH-Enforceability Weakness even when within prompt thresholds
- **Mutual termination for convenience** → flagged as Enforceability Weakness

**Sub-pattern:** The model contradicts its own quoted text (VEN-01, VEN-03): it quotes text that contains a consequential damages exclusion, then says the clause lacks one.

**Recommendation:** The prompt's StandardNDA and mutual-capped-indemnity suppression rules should have fired on VEN-01 (Liability Exposure finding on a capped mutual indemnity clause). They did not. Check why — possibly because the category was "Liability Exposure" not "Indemnification."

### Pattern C: Missing Genuine Risk (3/8 pipeline-processed docs)

**Affected:** NDA-02 (0 issues), VEN-02 (0 correct issues), VEN-03 (0 correct issues)

The model detects something (survival period, no-SLA, confidentiality term) but misses the actual risk:
- NDA-02: flagged 5-year survival instead of incomplete exclusions
- VEN-02: flagged no-SLA as Liability Exposure (wrong category) and no-indemnification (valid but not in GT), missed AS-IS and asymmetric termination  
- VEN-03: flagged boilerplate, missed IP ownership

**Recommendation:** The model needs document-level attention guidance. The prompt should explicitly instruct to check certain clause types in priority order (e.g., "First check: are exclusions complete? Second: is IP ownership reasonable?") rather than leaving it to the model to decide what to look for.

### Pattern D: Ground Truth Incompleteness

**Affected:** VEN-02 (no-indemnification finding)

VEN-02's model output included a valid "Indemnification Risk" finding about the no-indemnification clause. This is a genuine risk that our ground truth did not include. Our review template for VEN-02 was incomplete — we missed this expected finding.

**Recommendation:** The review templates should be reviewed and potentially expanded. The no-indemnification risk is real and should be added to VEN-02's expected findings.

---

## 6. Statistical Summary

| Metric | Value |
|---|---|
| Pipeline documents processed | 8/10 (2 blocked by upstream classifiers) |
| Pipeline documents with correct parse | 8/8 (100%) |
| Pipeline documents with ≥1 correct finding | 1/8 (EMP-02 only, 12.5%) |
| Pipeline documents with 0 correct findings | 5/8 (62.5%) |
| Model-produced issues total | 10 |
| Model-produced issues that are valid | 3 (EMP-02 x2, VEN-02 no-indemnification) |
| Model-produced issues that are FP | 7 |
| Ground truth issues total | 10 |
| Ground truth issues found by model | 2 (EMP-02 A+B) |
| Ground truth issues missed by model | 8 |
| Domain/policy detection failures | 2/10 documents (20%) |

---

## 7. Recommendations

### Immediate (before next evaluation run)

1. **Fix domain detection for EMP-03** — An executive employment agreement being classified as "Rebate Policy" is a critical bug. Investigate why `contractual_signal_score` was 0.0161. The word "awards" in the equity section likely triggered policy_keywords.

2. **Fix domain detection for NDA-04** — Investigate why `legal_keyword_ratio` was 0.212 for a standard confidentiality agreement. The perpetual/auto-renewal language may have confused the domestic classifier.

3. **Update VEN-02 ground truth** — Add no-indemnification as a 4th expected finding (CRITICAL, Indemnification). The model correctly identified this risk.

### Short-term (before next pipeline release)

4. **Add explicit attention guidance to the prompt** — Instruct the model to check for specific clause types in priority order: (1) exclusion completeness, (2) IP ownership, (3) termination asymmetry, (4) warranty disclaimers. Current prompt leaves it up to the model's attention.

5. **Investigate why mutual-capped-indemnity suppression did not fire on VEN-01** — The model produced a "Liability Exposure" finding on a document with mutual indemnity + cap + exclusion. The suppression rule should have caught this. Check if the rule checks for specific categories that don't include "Liability Exposure."

6. **Fix model's text-reading hallucination** — The model incorrectly states that VEN-01's limitation clause lacks a consequential damages exclusion, when the quoted text clearly includes one. This is a reading comprehension failure, not a categorization issue.

### Medium-term

7. **Add clause-selection diversity metric** — The model tends to find 2-3 issues from the same clause family (confidentiality/liability/indemnification) and ignore structurally different clauses (IP ownership, termination asymmetry). A prompt-time diversity check could help.

8. **Re-evaluate after prompt fixes** — Run Phase 1 again after fixing patterns A and B (domain detection + boilerplate suppression). Target: composite score ≥ 70.
