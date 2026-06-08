# Hallucination Root-Cause Audit

**Date:** June 5, 2026  
**Input:** 5 real-world contracts (NOT in benchmark corpus)  
**Total findings:** 9  
**Correct findings:** 5  
**Incorrect findings:** 4 (hallucinations)  
**Misclassified findings:** 3 (wrong location/category but partially valid)  
**Hallucination rate:** 44% (4/9)

---

## 1. All Incorrect Findings — Detailed Analysis

### HALLUCINATION #1: "No Service Level Agreement" (TEST-SAAS-01)

| Field | Value |
|-------|-------|
| **Title** | No Service Level Agreement |
| **Severity** | MEDIUM |
| **Category** | Enforceability Weakness |
| **Location** | Clause 6: 'SERVICE LEVELS' |
| **Quoted Text** | "Provider shall use commercially reasonable efforts to make the Services available at least 99.5% of the time in any calendar month, measured on a 24x7 basis, excluding scheduled maintenance windows." |
| **Risk Explanation** | "The absence of an SLA means the customer has no contractual recourse for service interruptions other than termination." |
| **Suggested Fix** | "Include an entire agreement clause to prevent extrinsic claims" |

**Why it's wrong:** The contract HAS an SLA. Clause 6 explicitly states 99.5% uptime. The model's own quoted text proves the SLA exists.

**Root cause:** **Prompt rule over-triggering** (line 136). The rule says: "If a SaaS or cloud services agreement does not include a service level agreement (SLA) guaranteeing uptime, availability, or performance, flag it." The model sees "SaaS" in the title and interprets "commercially reasonable efforts to make available" as not a "guarantee," so it triggers the rule. But 99.5% uptime IS a guarantee.

**Evidence:** The model quoted the exact clause that contains the SLA, then claimed the SLA doesn't exist. This is a direct contradiction.

---

### HALLUCINATION #2: "Restrictive Covenants" — Opposite Interpretation (TEST-LICENSE-03)

| Field | Value |
|-------|-------|
| **Title** | Restrictive Covenants |
| **Severity** | HIGH |
| **Category** | Negotiation Imbalance |
| **Location** | Clause 2 |
| **Quoted Text** | "(c) modify or create derivative works of the Software;" |
| **Risk Explanation** | "The clause allows Licensee to modify and create derivative works, which is a significant restriction that could be seen as an overreach in a software licensing agreement. This imbalance creates a fundamental power imbalance favoring Licensee." |
| **Suggested Fix** | "Ensure remedies, warranties, and limitations apply equally to both parties" |

**Why it's wrong:** The contract says "Licensee **shall not**: ... (c) modify or create derivative works." The model said the clause "allows" modification. This is the EXACT OPPOSITE of what the contract says.

**Root cause:** **Model capability limitation** — negation comprehension failure. The model failed to process the "shall not" negation. This is a known limitation of small language models (3B params). The model sees the phrase "modify or create derivative works" and generates a finding about it, but doesn't process the preceding "shall not."

**Evidence:** The quoted text includes the full prohibition, but the risk explanation contradicts it.

---

### HALLUCINATION #3: "No Service Level Agreement" (TEST-VENDOR-05)

| Field | Value |
|-------|-------|
| **Title** | No Service Level Agreement |
| **Severity** | MEDIUM |
| **Category** | Enforceability Weakness |
| **Location** | Section 4 (SERVICE LEVELS) |
| **Quoted Text** | "Vendor shall maintain: (a) order accuracy of at least 99.5%; (b) on-time shipment rate of at least 98%; (c) inventory accuracy of at least 99%" |
| **Risk Explanation** | "The clause specifies service levels but does not include a Service Level Agreement (SLA), which is necessary for the customer to have contractual recourse in case of service interruptions." |
| **Suggested Fix** | "Include an entire agreement clause to prevent extrinsic claims" |

**Why it's wrong:** Section 4 IS an SLA. It specifies three measurable service levels with percentage thresholds. The model's own quoted text proves the SLA exists.

**Root cause:** **Prompt rule over-triggering** (line 136) + **keyword mismatch**. The rule says "SLA guaranteeing uptime, availability, or performance." The model interprets "order accuracy," "on-time shipment," and "inventory accuracy" as not matching "uptime, availability, or performance." But these ARE performance metrics.

**Evidence:** The model quoted the exact SLA clause, then claimed the SLA doesn't exist. Same pattern as H1.

---

### HALLUCINATION #4: "Incomplete Confidentiality Exclusions" (TEST-EMPLOY-04)

| Field | Value |
|-------|-------|
| **Title** | Incomplete Confidentiality Exclusions |
| **Severity** | MEDIUM |
| **Category** | Confidentiality Risk |
| **Location** | 5. CONFIDENTIALITY |
| **Quoted Text** | "Employee agrees to hold in confidence all proprietary and confidential information of the Company. This obligation survives termination of employment." |
| **Risk Explanation** | "The confidentiality clause does not contain a dedicated 'Exclusions' or 'Exceptions' section that explicitly lists what is NOT covered by the confidentiality obligation. The absence of an exclusion list means this finding should be applied to all clauses without exclusions, including this one." |
| **Suggested Fix** | "Ensure confidentiality obligations survive termination and continue after contract expiration." |

**Why it's wrong:** The prompt explicitly says (line 133): "DO NOT apply this finding to employment confidentiality clauses, general confidentiality obligations without exclusion lists." This is an employment confidentiality clause with no exclusion list. The rule says DO NOT flag.

**Root cause:** **Prompt rule conflict** — the model ignored a negative instruction. The pattern recognition rule (line 133) says "DO NOT apply this finding to employment confidentiality clauses." But the model generated the finding anyway. This is consistent with the 16% success rate for negative instructions.

**Evidence:** The prompt explicitly prohibits this finding for employment clauses. The model generated it anyway.

---

## 2. Misclassified Findings (Wrong Location/Category but Partially Valid)

### MISCLASSIFICATION #1: "Limitation of Liability" (TEST-CONSULT-02)

| Field | Value |
|-------|-------|
| **Title** | Limitation of Liability |
| **Severity** | HIGH |
| **Quoted Text** | "CONSULTANT'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED THE TOTAL FEES PAID BY CLIENT UNDER THIS AGREEMENT DURING THE TWELVE (12) MONTHS PRECEDING THE CLAIM." |
| **Risk Explanation** | "The limitation of liability clause does not include any specific monetary cap or exclusion list..." |

**Why it's misclassified:** The clause DOES have a specific monetary cap ("total fees paid in 12 months"). The model says it doesn't. But the finding is partially valid — the cap is based on fees paid, not a fixed dollar amount, which could be interpreted as "no fixed cap."

**Root cause:** **Model capability limitation** — the model doesn't understand that "total fees paid in 12 months" IS a monetary cap. It expects a fixed dollar amount like "$500,000."

---

### MISCLASSIFICATION #2: "Non-Competition Excessive Duration" — Wrong Location (TEST-EMPLOY-04)

| Field | Value |
|-------|-------|
| **Title** | Non-Competition Excessive Duration |
| **Location** | "6. INVENTION ASSIGNMENT" |
| **Quoted Text** | "Employee agrees to assign to the Company all inventions, discoveries, and improvements made during employment that relate to the Company's business." |

**Why it's misclassified:** The non-compete is in Clause 7, not Clause 6. The model quoted the INVENTION ASSIGNMENT clause but labeled it as the NON-COMPETE clause.

**Root cause:** **Normalization error** — the location field is wrong. The finding itself is valid (18-month non-compete is excessive), but the quoted text doesn't match the title.

---

### MISCLASSIFICATION #3: "Confidentiality Survival" — Suggested Fix Adds Unrelated Language (TEST-CONSULT-02)

| Field | Value |
|-------|-------|
| **Title** | Confidentiality Survival |
| **Quoted Text** | "The obligations of confidentiality shall survive termination for a period of three (3) years." |
| **Suggested Fix** | "The obligations of confidentiality shall survive termination **and any changes in control** for a period of three (3) years." |

**Why it's misclassified:** The suggested fix adds "and any changes in control" which has nothing to do with the original clause. The model is injecting unrelated legal concepts.

**Root cause:** **Model capability limitation** — the model is pattern-matching from training data and adding language that sounds legal but is irrelevant.

---

## 3. Recurring Patterns

### Pattern A: "No SLA" False Positive (2 occurrences)

| Occurrence | Contract | Quoted Text Contains SLA? |
|------------|----------|---------------------------|
| H1 | TEST-SAAS-01 | YES (99.5% uptime) |
| H3 | TEST-VENDOR-05 | YES (99.5% order accuracy, 98% on-time, 99% inventory) |

**Pattern:** The model quotes a clause that IS an SLA, then claims the SLA doesn't exist.

**Trigger:** Prompt rule at line 136. The rule says "SLA guaranteeing uptime, availability, or performance." The model interprets "commercially reasonable efforts to make available" and "order accuracy" as not matching the rule's keywords.

**Root cause:** Keyword over-triggering in prompt rule.

---

### Pattern B: Negation Comprehension Failure (1 occurrence)

| Occurrence | Contract | Negation Type |
|------------|----------|---------------|
| H2 | TEST-LICENSE-03 | "shall not" |

**Pattern:** The model reads a prohibited action and interprets it as a permitted action.

**Trigger:** None — this is a model capability limitation.

**Root cause:** Small model (3B params) fails to process negation.

---

### Pattern C: Ignoring Negative Instructions (1 occurrence)

| Occurrence | Contract | Instruction Violated |
|------------|----------|---------------------|
| H4 | TEST-EMPLOY-04 | "DO NOT apply this finding to employment confidentiality clauses" |

**Pattern:** The model generates a finding that the prompt explicitly prohibits.

**Trigger:** Prompt rule at line 133 says "DO NOT apply this finding to employment confidentiality clauses."

**Root cause:** Model ignores negative instructions (consistent with 16% success rate).

---

### Pattern D: Quoted Text Doesn't Match Title (1 occurrence)

| Occurrence | Contract | Title | Quoted Text |
|------------|----------|-------|-------------|
| MC2 | TEST-EMPLOY-04 | Non-Competition | Invention Assignment clause |

**Pattern:** The model quotes one clause but labels it as a different clause.

**Trigger:** None — this is a normalization error.

**Root cause:** The model selects the wrong text for the title.

---

## 4. Hallucination Taxonomy

| Rank | Pattern | Frequency | Impact | Fixable By |
|------|---------|-----------|--------|------------|
| **1** | **"No SLA" false positive** | 2/5 contracts (40%) | HIGH — user sees wrong finding, loses trust | Prompt change (add positive verification) |
| **2** | **Negation comprehension failure** | 1/5 contracts (20%) | CRITICAL — model says opposite of contract | Larger model (not fixable by prompt/suppression) |
| **3** | **Ignoring negative instructions** | 1/5 contracts (20%) | HIGH — model violates explicit rules | Prompt redesign (convert negative to positive) |
| **4** | **Quoted text/title mismatch** | 1/5 contracts (20%) | MEDIUM — finding is valid but location is wrong | Normalization fix (verify location matches title) |

---

## 5. Root Cause Classification

### 5.1 Prompt Rule Over-Triggering (2 occurrences — Pattern A)

**Mechanism:** The "No SLA" rule (line 136) triggers on keyword matching ("SaaS" + "no SLA") without verifying whether the contract actually contains an SLA.

**Why it happens:** The rule is written as a negative check: "If a SaaS agreement does not include an SLA..." But the model doesn't verify the absence — it just sees "SaaS" and generates the finding.

**Fixable by:** Prompt change — add a positive verification step:
- BEFORE generating "No SLA," scan the contract for words like "service level," "uptime," "availability," "performance," "99.5%," "SLA"
- If any of these are found, DO NOT generate "No SLA"
- This converts the negative instruction to a positive check

**Estimated fix effort:** LOW (1-2 hours of prompt editing)

---

### 5.2 Model Capability Limitation (2 occurrences — Patterns B and D)

**Mechanism:** The model (3B params) fails to:
1. Process negation ("shall not" → interpreted as "shall")
2. Match quoted text to the correct clause title

**Why it happens:** Small language models have limited reasoning capacity. Negation comprehension requires understanding logical operators, which is a known weakness of models under 10B params.

**Fixable by:** Larger model (7B+ params). Cannot be fixed by prompt changes, suppression, or normalization.

**Estimated fix effort:** HIGH (requires model upgrade or fine-tuning)

**Workaround:** Add a post-processing check:
- For every finding, verify that the quoted text contains words from the title
- If the title says "Non-Competition" but the quoted text doesn't contain "non-compete," "competition," or "compete," flag as mismatch
- This catches the location error but not the negation error

---

### 5.3 Ignoring Negative Instructions (1 occurrence — Pattern C)

**Mechanism:** The model generates a finding that the prompt explicitly prohibits ("DO NOT apply this finding to employment confidentiality clauses").

**Why it happens:** Negative instructions have a 16% success rate (from earlier audit). The model sees "Confidentiality" + "Exclusions" and generates the finding, ignoring the "DO NOT" prefix.

**Fixable by:** Prompt redesign — convert negative instructions to positive instructions:
- Instead of "DO NOT apply this finding to employment confidentiality clauses"
- Use: "Only apply this finding to: (1) commercial/NDAs, (2) vendor agreements, (3) partnership agreements. NEVER apply to employment agreements."
- This converts a negative instruction to a positive constraint

**Estimated fix effort:** MEDIUM (requires identifying all negative instructions and rewriting)

---

### 5.4 Normalization Error (1 occurrence — Pattern D)

**Mechanism:** The model selects the wrong quoted text for the title. It quotes the Invention Assignment clause but labels it as the Non-Competition clause.

**Why it happens:** The model processes multiple clauses and sometimes associates the wrong text with the wrong title. This is a common issue with small models.

**Fixable by:** Normalization fix — add a post-processing check:
- For every finding, verify that the quoted text contains words from the title
- If the title says "Non-Competition" but the quoted text doesn't contain "non-compete," "competition," or "compete," flag as mismatch
- This catches the location error

**Estimated fix effort:** LOW (1-2 hours of normalization code)

---

## 6. Prioritized Remediation Plan

### Priority 1: Fix "No SLA" False Positive (Pattern A)

**Impact:** Eliminates 40% of hallucinations (2/5 contracts)  
**Effort:** LOW (prompt change)  
**Fix type:** Prompt change

**Approach:** Add a positive verification step before generating "No SLA":
```
Before generating "No Service Level Agreement":
1. Scan the ENTIRE contract for: "service level", "uptime", "availability", 
   "performance", "99.5%", "SLA", "guarantee"
2. If ANY of these are found, DO NOT generate "No SLA"
3. Only generate "No SLA" if NONE of these words appear anywhere in the contract
```

**Risk:** May miss legitimate "No SLA" cases where the contract mentions "service levels" but doesn't define specific metrics. Mitigate by checking for percentage thresholds (99.5%, 98%, etc.).

---

### Priority 2: Fix Quoted Text/Title Mismatch (Pattern D)

**Impact:** Eliminates 20% of hallucinations (1/5 contracts)  
**Effort:** LOW (normalization code)  
**Fix type:** Normalization fix

**Approach:** Add a post-processing check in `normalization_engine.py`:
```python
def verify_title_text_match(issue):
    title_words = set(issue.title.lower().split())
    text_words = set(issue.quoted_text.lower().split())
    overlap = title_words & text_words
    if len(overlap) < 2:  # At least 2 words must match
        return False  # Mismatch
    return True
```

**Risk:** May reject valid findings where the title uses different words than the quoted text. Mitigate by using a synonym dictionary.

---

### Priority 3: Convert Negative Instructions to Positive (Pattern C)

**Impact:** Eliminates 20% of hallucinations (1/5 contracts)  
**Effort:** MEDIUM (prompt rewrite)  
**Fix type:** Prompt change

**Approach:** Find all negative instructions in the prompt and convert to positive constraints:
- "DO NOT apply this finding to employment confidentiality clauses" → "Only apply this finding to: commercial NDAs, vendor agreements, partnership agreements"
- "DO NOT generate multiple issues for the same clause" → "Generate at most one issue per clause"
- "DO NOT flag if the survival clause specifies a number of years" → "Only flag if the survival clause uses 'perpetually,' 'indefinitely,' or 'in perpetuity'"

**Risk:** May be more verbose. Mitigate by keeping positive instructions concise.

---

### Priority 4: Negation Comprehension (Pattern B)

**Impact:** Eliminates 20% of hallucinations (1/5 contracts)  
**Effort:** HIGH (requires model upgrade)  
**Fix type:** Larger model or fine-tuning

**Approach:** This cannot be fixed by prompt changes or post-processing. The model fundamentally fails to process "shall not" negation. Options:
1. **Upgrade to 7B+ model** — better negation comprehension
2. **Fine-tune on negation examples** — train the model to process "shall not" correctly
3. **Post-processing heuristic** — for every finding, check if the quoted text contains "shall not" and the finding says "allows" or "permits," flag as likely hallucination

**Workaround (immediate):** Add a post-processing check:
```python
def check_negation_conflict(issue):
    if "shall not" in issue.quoted_text.lower():
        if any(word in issue.risk_explanation.lower() for word in ["allows", "permits", "grants"]):
            return True  # Likely hallucination
    return False
```

**Risk:** May catch legitimate findings where the quoted text contains "shall not" but the finding is about a different aspect. Mitigate by only flagging when the finding directly contradicts the negation.

---

## 7. Summary

### Hallucination Rate by Pattern

| Pattern | Frequency | Impact | Fixable By | Priority |
|---------|-----------|--------|------------|----------|
| "No SLA" false positive | 40% (2/5) | HIGH | Prompt change | **P1** |
| Negation comprehension | 20% (1/5) | CRITICAL | Larger model | P4 |
| Ignoring negative instructions | 20% (1/5) | HIGH | Prompt redesign | **P3** |
| Quoted text/title mismatch | 20% (1/5) | MEDIUM | Normalization fix | **P2** |

### Estimated Total Fix Effort

| Priority | Pattern | Effort | Impact |
|----------|---------|--------|--------|
| P1 | "No SLA" false positive | 2 hours | Eliminates 40% of hallucinations |
| P2 | Quoted text/title mismatch | 2 hours | Eliminates 20% of hallucinations |
| P3 | Negative instructions | 4 hours | Eliminates 20% of hallucinations |
| P4 | Negation comprehension | N/A (model upgrade) | Eliminates 20% of hallucinations |

**If P1-P3 are implemented:** Hallucination rate drops from 44% to ~11% (only negation failures remain).

**If P4 is also implemented:** Hallucination rate drops to ~0%.

### Key Insight

**3 of 4 hallucination patterns are fixable by prompt/normalization changes (P1-P3).** Only 1 pattern (negation comprehension) requires a model upgrade. This means the system can be significantly improved without changing the model.
