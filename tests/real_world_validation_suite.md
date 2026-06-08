# Real-World Validation Suite

## Design Specification

**Date:** 2026-06-01
**Purpose:** Replace synthetic-only benchmark coverage with a corpus of documents derived from real-world contracts, measured by a rigorous evaluation framework.
**Scope:** Audit pipeline only. Non-legal, policy, and garbage inputs remain covered by existing benchmark.

---

---

## 1. Corpus Specification — 30 Documents

### 1.1 Collection Guidelines

Each document must be:

| Requirement | Detail |
|---|---|
| Source | Anonymized real contract or template based on a real contract. Synthetic-only documents are exempted. |
| Anonymization | Party names → [Disclosing Party]/[Receiving Party], [Company]/[Employee], dollar amounts → [Amount], dates → [Date]. All other substantive terms preserved. |
| Length | 200–5000 words (typical range for a single agreement excerpt)* |
| Format | Plain text, no markdown, no tracked changes. Headings in ALL CAPS or numbered (1.1, 1.2). |
| Metadata | Each document has a companion JSON file (`document_meta.json`) with source category, true clause types present, and known risk flags. |
| License | Must be from public sources or generated from public templates (SEC EDGAR exhibits, open-source legal form repositories, law school clinics). |

*Full agreements can be 10,000+ words; the pipeline already truncates to 4096 tokens. A 2000–5000 word excerpt is the most representative single-input size.

### 1.2 Document Classification Taxonomy

Every document in the corpus is tagged with a multi-axis classification:

| Axis | Values | Example |
|---|---|---|
| **Type** | NDA, EMPLOYMENT, VENDOR_SERVICE, OTHER | NDA |
| **Subtype** | mutual, unilateral, multi-party / executive, at-will, contractor, offer-letter / SaaS, MSA, SOW, DPA, subscription | mutual |
| **Risk Level** | clean, moderate, high-risk | clean |
| **Clause Set** | Comma-separated list of clause types present | confidentiality, indemnification, liability-cap, termination, survival, governing-law, non-compete, invention-assignment, non-solicit, sla, data-processing, assignment |
| **Red Flag** | Boolean: does this document contain a genuine risk that the pipeline must catch? | true |

---

### 1.3 NDA Corpus (10 documents)

| ID | Subtype | Risk | Clause Set | Red Flag | Description |
|---|---|---|---|---|---|
| NDA-01 | Mutual | Clean | confidentiality, exclusions, term, survival, return, no-license, remedy, governing-law, entire-agreement | No | Standard two-way NDA. All protective clauses present. No unusual terms. |
| NDA-02 | Unilateral (discloser-favoring) | Clean | confidentiality, exclusions, term, perpetual-survival, return, remedy, governing-law | No | One-way NDA where disclosing party gets perpetual confidentiality protection. Still standard. |
| NDA-03 | Mutual | Moderate | confidentiality, exclusions (limited), term, survival, return, non-solicit (embedded), governing-law | Potentially | Clean NDA except Section 4 embeds a non-solicitation clause restricting hire of discloser's employees for 18 months. |
| NDA-04 | Unilateral | High-Risk | confidentiality (broad definition), exclusions (none), term, survival, return, assignment, governing-law | Yes | Receiving party has no exclusions to confidentiality. Definition includes "all information" with no exclusions. |
| NDA-05 | Mutual | High-Risk | confidentiality, exclusions, term, survival (5yr), return, jurisdiction (foreign), governing-law | Yes | Governing law is a jurisdiction with weak trade secret protection. Creates enforceability weakness. |
| NDA-06 | Multi-Party | Clean | confidentiality, exclusions, term, survival, return, no-license, remedy, governing-law, entire-agreement | No | Three parties (Discloser A, Discloser B, Recipient). Mutual obligations among all three. |
| NDA-07 | Mutual | Moderate | confidentiality, exclusions, term + auto-renewal, survival, return, remedy, governing-law, entire-agreement | Yes? | Auto-renewal clause buries the surviving obligation past the primary term. Renewed perpetually unless 90-day notice. |
| NDA-08 | Unilateral (mutual-ish framing) | High-Risk | confidentiality (excludes public info only), no-exclusions-for-pre-knowledge, term, survival (indefinite), return, governing-law | Yes | Labeled "Mutual NDA" but obligations flow only one way. No protection for receiving party's pre-existing knowledge. |
| NDA-09 | Mutual | Clean | confidentiality, exclusions, term (1yr), survival (1yr), no-return-if-legal-hold, governing-law, entire-agreement | No | Short-duration NDA with legal-hold exception for document retention. Standard. |
| NDA-10 | Unilateral | Moderate | confidentiality, exclusions, term, survival, return, remedy (uncapped injunctive relief), governing-law | Yes? | Injunctive relief is "without limit and without bond". Uncapped remedy for breach of confidentiality. |

### 1.4 Employment Agreement Corpus (10 documents)

| ID | Subtype | Risk | Clause Set | Red Flag | Description |
|---|---|---|---|---|---|
| EMP-01 | At-Will | Clean | at-will, compensation, duties, benefits, standard-confidentiality, standard-invention-assignment, non-compete (6mo), non-solicit (12mo), governing-law | No | Standard California-style employment agreement. All terms reasonable. |
| EMP-02 | At-Will | High-Risk | at-will, compensation, duties, invention-assignment (overbroad), non-compete (18mo), non-solicit (12mo), governing-law | Yes | Invention assignment covers "all inventions regardless of when created, anywhere in the world, using any resources". Non-compete is 18 months in a state that allows it. |
| EMP-03 | Executive | Clean | term, compensation (salary + bonus + equity), benefits, change-of-control, severance (12mo), non-compete (12mo), non-solicit (12mo), governing-law | No | Executive agreement with golden parachute. Standard protections. |
| EMP-04 | Executive | High-Risk | term, compensation, benefits, invention-assignment (overbroad + assignment-in-future), non-compete (24mo, worldwide), non-solicit (24mo), governing-law | Yes | Non-compete is 24 months with no geographic limitation. Invention assignment includes pre-filing assignments for patents not yet conceived. |
| EMP-05 | Contractor | Clean | scope-of-work, compensation, IP-ownership (work-made-for-hire), confidentiality, non-solicit (12mo), termination, governing-law | No | Standard independent contractor agreement. IP conveyed via work-made-for-hire. |
| EMP-06 | Contractor | High-Risk | scope-of-work, compensation, IP-ownership (overbroad), non-compete (12mo), non-solicit, confidentiality (perpetual), governing-law | Yes | Contractor must assign "all IP conceived during engagement or relating to field". Non-compete on a contractor. Perpetual confidentiality. |
| EMP-07 | At-Will | Moderate | at-will, compensation, duties, invention-assignment, non-compete (12mo, reasonable), non-solicit (6mo), arbitration, class-action-waiver, governing-law | Yes? | Mandatory arbitration with class action waiver. Privacy concerns. Otherwise clean. |
| EMP-08 | Offer Letter | Clean | at-will, compensation, start-date, benefits-summary, standard-invention-assignment, standard-confidentiality, governing-law | No | Short-form offer letter (2 pages). Brief invention assignment and confidentiality. Reasonable scope. |
| EMP-09 | Executive | High-Risk | term, compensation, benefits, change-of-control (single-trigger), severance (24mo), non-compete (18mo), non-disparagement, clawback, governing-law | Yes | Single-trigger change of control (payout on change without termination). Creates perverse incentive. Non-compete accompanies it. |
| EMP-10 | At-Will | Moderate | at-will, compensation, duties, invention-assignment, non-compete (6mo), non-solicit (12mo), arbitration, governing-law | No | Clean agreement except arbitration clause with fee-splitting that could deter legitimate claims. |

### 1.5 Vendor / Service Agreement Corpus (10 documents)

| ID | Subtype | Risk | Clause Set | Red Flag | Description |
|---|---|---|---|---|---|
| VEN-01 | SaaS | Clean | subscription, license-grant, fees, payment-terms, SLA (99.9%), liability-cap (fees-paid), exclusion-of-consequential, mutual-indemnity (capped), termination, data-processing, governing-law | No | Standard B2B SaaS agreement. All protections bilateral and capped. |
| VEN-02 | SaaS | High-Risk | subscription, license-grant, fees, payment-terms, no-SLA, liability-cap (zero — "as-is"), no-indemnity, termination-for-convenience (vendor-only), governing-law | Yes | "AS-IS" with no warranty, no SLA, no indemnity. Vendor can terminate for convenience. Customer has no remedy. |
| VEN-03 | MSA | Clean | scope, fees, payment-terms, liability-cap (1x fees), exclusion-of-consequential, mutual-indemnity (capped), confidentiality, termination, governing-law | No | Standard MSA with SOW attachment mechanism. All terms bilateral. |
| VEN-04 | MSA | High-Risk | scope, fees, payment-terms, liability-cap (3x fees, vendor-only), indemnity (vendor-favoring, uncapped), no-exclusion-of-consequential, confidentiality, governing-law | Yes | Vendor gets capped liability but uncapped indemnity FROM customer. Indemnification covers vendor IP infringement claims. Uncapped customer liability. |
| VEN-05 | SOW | Moderate | scope, deliverables, milestones, payment-schedule, acceptance-criteria, change-order, termination-for-convenience (customer-only), liability-reference-to-MSA | No | Standalone SOW referencing a balanced MSA. No independent risk. |
| VEN-06 | DPA | High-Risk | data-processing-description, data-subject-categories, processing-purposes, sub-processor-list, security-measures (inadequate), data-breach-notification (48hr), international-transfer (SCCs absent), governing-law | Yes | Data Processing Agreement with missing Standard Contractual Clauses for international transfer. Security measures are generic ("industry standard"). |
| VEN-07 | Professional Services | Clean | scope, fees, T&E, liability-cap (1x fees), exclusion-of-consequential, mutual-indemnity (capped), IP-ownership (customer), termination, governing-law | No | Standard PS agreement. Deliverables IP vests in customer. Vendor IP retained. |
| VEN-08 | Professional Services | High-Risk | scope, fees, T&E, liability-cap (fees-paid), no-indemnity, IP-ownership (vendor, customer gets license), no-exclusion-of-consequential, non-compete (customer, 2yr), governing-law | Yes | Customer pays for custom development but vendor owns all IP. Customer gets only a non-exclusive license. Vendor non-compete prevents customer from hiring competitor. |
| VEN-09 | Subscription (Clickwrap) | Moderate | subscription, license-grant (non-exclusive, non-transferable), auto-renewal, fees, liability-cap (fees-paid, 12mo lookback), exclusion-of-consequential, no-indemnity, arbitration, class-action-waiver, governing-law | Yes? | Standard clickwrap but arbitration with class waiver and 12-month liability lookback creates consumer-unfavorable terms. Non-negotiable. |
| VEN-10 | SaaS (Enterprise) | Clean | subscription, license-grant, fees, payment-terms, SLA (99.99%), liability-cap (2x fees), exclusion-of-consequential, mutual-indemnity (capped), data-processing (with SCCs), termination, governing-law | No | Enterprise-grade SaaS agreement with strong SLA, SCCs for EU data, capped mutual indemnity. Gold standard. |

---

---

## 2. Review Templates

### 2.1 Template Format

Each of the 30 documents has a companion `review.json` file containing:

```json
{
  "document_id": "NDA-01",
  "title": "Standard Mutual Non-Disclosure Agreement",
  "model_under_test": "qwen2.5:3b-instruct",
  "ground_truth": {
    "parse_should_succeed": true,
    "expected_issue_count": 0,
    "max_allowed_issues": 1,
    "expected_confidence_label": "HIGH",
    "min_confidence_score": 0.75,
    "issues": []
  },
  "evaluation_weights": {
    "parse_success": 1.0,
    "precision": 0.0,
    "recall": 0.0,
    "severity_accuracy": 0.0,
    "false_positive_penalty": 1.0,
    "false_negative_penalty": 0.0
  }
}
```

For documents with expected findings, the template includes an `issues` array:

```json
{
  "document_id": "EMP-02",
  "title": "Employment Agreement with Overbroad Invention Assignment",
  "model_under_test": "qwen2.5:3b-instruct",
  "ground_truth": {
    "parse_should_succeed": true,
    "expected_issue_count": 2,
    "max_allowed_issues": 3,
    "expected_confidence_label": "HIGH",
    "min_confidence_score": 0.65,
    "issues": [
      {
        "id": "EMP-02-A",
        "expected_issue_title": "Overbroad Invention Assignment",
        "expected_severity": "HIGH",
        "allowed_severities": ["HIGH"],
        "expected_category": "Intellectual Property",
        "allowed_categories": ["Intellectual Property", "Enforceability Weakness"],
        "must_contain_quoted_text_pattern": ["all inventions", "regardless of when", "anywhere in the world", "any resources"],
        "must_not_contain_quoted_text_pattern": [],
        "must_contain_explanation_pattern": ["overbroad", "invention", "assignment"],
        "must_not_contain_explanation_pattern": [],
        "rationale": "The clause claims ownership of all inventions regardless of when created, location, or resources used — goes far beyond the scope of employment. California Labor Code §2870 would void this, but model should flag it."
      },
      {
        "id": "EMP-02-B",
        "expected_issue_title": "Excessive Non-Compete Duration",
        "expected_severity": "MEDIUM",
        "allowed_severities": ["MEDIUM", "HIGH"],
        "expected_category": "Enforceability Weakness",
        "allowed_categories": ["Enforceability Weakness", "Negotiation Imbalance"],
        "must_contain_quoted_text_pattern": ["18", "month", "non-compete", "noncompete"],
        "must_not_contain_quoted_text_pattern": [],
        "must_contain_explanation_pattern": ["non-compete", "noncompete", "duration", "18"],
        "must_not_contain_explanation_pattern": [],
        "rationale": "18-month non-compete exceeds the 6-month threshold defined in prompt rules. Should be flagged as MEDIUM risk."
      }
    ]
  },
  "evaluation_weights": {
    "parse_success": 1.0,
    "precision": 1.0,
    "recall": 1.0,
    "severity_accuracy": 1.0,
    "false_positive_penalty": 1.0,
    "false_negative_penalty": 2.0
  }
}
```

### 2.2 Per-Document Review Template Values

#### NDA Templates (10)

| ID | Parse | Exp Count | Max | Conf | Issues | Notes |
|---|---|---|---|---|---|---|
| NDA-01 | true | 0 | 1 | HIGH | [] | Clean mutual NDA. No findings expected. |
| NDA-02 | true | 0 | 1 | HIGH | [] | Standard unilateral. Perpetual survival is standard. |
| NDA-03 | true | 1 | 2 | HIGH | Embedded non-solicit → Negotiation Imbalance (LOW-MEDIUM) or buried non-standard term. |
| NDA-04 | true | 1 | 2 | HIGH | Missing exclusions → Enforceability Weakness (MEDIUM-HIGH). Broad conf. definition also flaggable. |
| NDA-05 | true | 1 | 2 | HIGH | Foreign jurisdiction with weak protection → Enforceability Weakness (MEDIUM). Or jurisdiction risk. |
| NDA-06 | true | 0 | 1 | HIGH | [] | Three-party. Still clean. |
| NDA-07 | true | 1 | 2 | HIGH | Auto-renewal burying survival → Enforceability Weakness (LOW-MEDIUM). Perpetual obligation risk. |
| NDA-08 | true | 1 | 2 | MED-HIGH | Labeled mutual but one-way → Negotiation Imbalance (MEDIUM). No pre-knownledge exclusion. |
| NDA-09 | true | 0 | 1 | HIGH | [] | Short duration with legal hold carveout. Standard. |
| NDA-10 | true | 1 | 2 | HIGH | Uncapped injunctive relief → Enforceability Weakness or Liability Exposure (LOW-MEDIUM). Bondless remedy. |

#### Employment Templates (10)

| ID | Parse | Exp Count | Max | Conf | Issues | Notes |
|---|---|---|---|---|---|---|
| EMP-01 | true | 0 | 1 | HIGH | [] | Standard, all reasonable. Standard confidentiality is not a risk per prompt. |
| EMP-02 | true | 2 | 3 | HIGH | Invention assignment (HIGH/IP) + non-compete (MEDIUM/Enforceability) | Overbroad + excessive duration. |
| EMP-03 | true | 0 | 1 | HIGH | [] | Standard executive. No overreach. |
| EMP-04 | true | 2 | 3 | HIGH | Invention assignment (HIGH/IP) + non-compete 24mo (HIGH/Enforceability) | Overbroad + worldwide 24mo non-compete. Both severe. |
| EMP-05 | true | 0 | 1 | HIGH | [] | Standard IC agreement. |
| EMP-06 | true | 2 | 3 | HIGH | Overbroad IP (MED-HIGH/IP) + contractor non-compete (MED/Enforceability) | Non-compete on contractor is unusual. Perpetual conf. also flaggable. |
| EMP-07 | true | 1 | 2 | HIGH | Arbitration + class waiver → Enforceability Weakness (LOW-MEDIUM) or Privacy Risk | Otherwise clean. The forced arbitration with class waiver is a consumer protection concern. |
| EMP-08 | true | 0 | 1 | HIGH | [] | Short offer letter. Standard assignment. |
| EMP-09 | true | 1 | 2 | HIGH | Single-trigger change-of-control → Enforceability Weakness (MEDIUM) | Creates conflicts of interest. Unusual. |
| EMP-10 | true | 1 | 2 | HIGH | Arbitration fee-splitting → Enforceability Weakness (LOW-MEDIUM) | Fee-splitting deters claims. |

#### Vendor Templates (10)

| ID | Parse | Exp Count | Max | Conf | Issues | Notes |
|---|---|---|---|---|---|---|
| VEN-01 | true | 0 | 1 | HIGH | [] | Gold-standard SaaS. All bilateral, capped. |
| VEN-02 | true | 3 | 4 | MED-HIGH | (a) No warranty/SLA → Enforceability Weakness MED, (b) vendor-only termination → Negotiation Imbalance MED, (c) no-indemnity → Liability Exposure MED |
| VEN-03 | true | 0 | 1 | HIGH | [] | Balanced MSA. |
| VEN-04 | true | 2 | 3 | HIGH | (a) Vendor-favoring uncapped indemnity → Negotiation Imbalance HIGH, (b) asymmetric liability cap → Negotiation Imbalance MED |
| VEN-05 | true | 0 | 1 | HIGH | [] | SOW referencing balanced MSA. No independent risk. |
| VEN-06 | true | 2 | 3 | HIGH | (a) Missing SCCs → Privacy Risk CRITICAL, (b) inadequate security → Enforceability Weakness MED |
| VEN-07 | true | 0 | 1 | HIGH | [] | Standard PS agreement. |
| VEN-08 | true | 2 | 3 | HIGH | (a) Vendor owns custom IP → Intellectual Property HIGH, (b) customer non-compete → Negotiation Imbalance MED |
| VEN-09 | true | 1 | 2 | HIGH | Arbitration + class waiver + 12mo lookback → Enforceability Weakness MED or Negotiation Imbalance |
| VEN-10 | true | 0 | 1 | HIGH | [] | Enterprise-grade. Gold standard. |

---

### 2.3 Evaluation Weights (All Documents)

Default weights per metric that apply to every evaluation run:

| Metric | Default Weight | When Overridden |
|---|---|---|
| `parse_success` | 1.0 | Always 1.0 — parse failure is always a defect |
| `precision` | 1.0 | Reduced to 0.5 when ground_truth.issues is empty (no findings expected — all issues are FP) |
| `recall` | 1.0 | Reduced to 0.0 when ground_truth.issues is empty (no findings to recall) |
| `severity_accuracy` | 1.0 | Reduced to 0.0 when ground_truth.issues is empty |
| `false_positive_penalty` | 1.0 | Increased to 2.0 for clean documents (NDA-01, EMP-01, etc.) |
| `false_negative_penalty` | 1.0 | Increased to 2.0 for high-risk documents (NDA-04, EMP-02, VEN-02, etc.) |

---

---

## 3. Validation Framework

### 3.1 Architecture

```
validation_runner.py               ← orchestrator
  │
  ├── corpus/
  │   ├── nda/
  │   │   ├── NDA-01.txt + NDA-01.review.json
  │   │   ├── NDA-02.txt + NDA-02.review.json
  │   │   └── ...
  │   ├── employment/
  │   │   └── ...
  │   └── vendor/
  │       └── ...
  │
  ├── pipeline_adapter.py           ← calls /ask_file endpoint, returns parsed response
  ├── evaluator.py                  ← compares pipeline output to ground truth
  ├── metrics.py                    ← aggregates per-document metrics into corpus-wide scores
  └── report.py                     ← produces human-readable and JSON reports
```

### 3.2 Metric Definitions

#### 3.2.1 Parse Success Rate

```
parse_success_rate = successful_parses / total_documents

Where:
  successful_parses = count of documents where:
    - JSON was returned from the pipeline
    - The "issues" field is a valid list (possibly empty)
    - parse_failed flag is false in the response metadata

Documents where the pipeline returns an error, a refusal, or unparseable text
count as parse failures.
```

**Acceptable threshold:** ≥ 95% (at most 1-2 parse failures across 30 documents).

---

#### 3.2.2 Issue Precision

For each document d:

```
FP_d = count of issues in pipeline output that do NOT match ANY issue in ground_truth for d
TP_d = count of issues in pipeline output that DO match at least one issue in ground_truth for d

precision_d = TP_d / (TP_d + FP_d)   if TP_d + FP_d > 0
precision_d = 1.0                     if pipeline output is empty AND ground truth is empty
precision_d = 0.0                     if pipeline output has issues but ground truth has none
```

**Issue matching rules:**
An issue from the pipeline **matches** a ground-truth issue when:

| Condition | Weight | Description |
|---|---|---|
| **Category match** | Required | Pipeline category is in `allowed_categories` of any ground-truth issue |
| **Severity match** | Required | Pipeline severity is in `allowed_severities` of that ground-truth issue |
| **Title content match** | Bonus | Pipeline `issue_title` contains >=1 word from ground-truth `expected_issue_title` |
| **Quoted text match** | Required for non-empty | If ground-truth specifies `must_contain_quoted_text_pattern`, at least one pattern must match pipeline's `quoted_text` |
| **Explanation match** | Required for non-empty | If ground-truth specifies `must_contain_explanation_pattern`, at least one pattern must match pipeline's `risk_explanation` |

An issue is a **true positive** if all Required conditions are satisfied **for at least one** ground-truth issue.

**Corpus-wide precision:**

```
overall_precision = sum(TP_d across all d) / sum((TP_d + FP_d) across all d)
```

**Acceptable threshold:** ≥ 0.70 (at most 30% of pipeline issues are false positives).

---

#### 3.2.3 Issue Recall

For each document d:

```
FN_d = count of ground-truth issues that have NO matching pipeline issue
TP_d = count of ground-truth issues that HAVE at least one matching pipeline issue

recall_d = TP_d / (TP_d + FN_d)   if TP_d + FN_d > 0
recall_d = 1.0                     if ground truth is empty
```

**Corpus-wide recall:**

```
overall_recall = sum(TP_d across all d) / sum((TP_d + FN_d) across all d)
```

**Acceptable threshold:** ≥ 0.65 (at most 35% of genuine issues are missed).

---

#### 3.2.4 Severity Accuracy

Only computed for true-positive issues (issues that match a ground-truth issue):

```
severity_accuracy_d = count(TP issues where severity ∈ allowed_severities) / TP_d
```

If a ground-truth issue permits multiple severities (e.g., `["MEDIUM", "HIGH"]`), any of them count as correct.

Severity accuracy is **binned**:

| Bin | Label | Interpretation |
|---|---|---|
| 1.0 | Exact | All TP issues have exact or allowed-range severity |
| ≥ 0.75 | Good | Most TP issues correctly graded |
| ≥ 0.50 | Fair | About half correct |
| < 0.50 | Poor | Systematic mis-grading |

**Acceptable threshold:** ≥ 0.75 (good or exact).

---

#### 3.2.5 False Positive Rate

```
FPR = total_FP_across_all_documents / total_pipeline_issues_across_all_documents
```

This is the complement of precision (1 - overall_precision). Included as a separate metric for independent weighting.

**Acceptable threshold:** ≤ 0.30.

---

#### 3.2.6 False Negative Rate

```
FNR = total_FN_across_all_documents / total_ground_truth_issues_across_all_documents
```

This is the complement of recall (1 - overall_recall).

**Acceptable threshold:** ≤ 0.35.

---

### 3.3 Composite Score (Weighting Scheme)

```
parse_weight = 0.20
precision_weight = 0.20
recall_weight = 0.25
severity_weight = 0.15
fpr_penalty_weight = 0.10       ← inverted: FPR ≤ 0.30 scores full, >0.60 scores zero
fnr_penalty_weight = 0.10       ← inverted: FNR ≤ 0.35 scores full, >0.70 scores zero

composite = (
    parse_success_rate * parse_weight +
    overall_precision * precision_weight +
    overall_recall * recall_weight +
    overall_severity_accuracy * severity_weight +
    (1.0 - min(max(FPR - 0.30, 0.0) / 0.30, 1.0)) * fpr_penalty_weight +
    (1.0 - min(max(FNR - 0.35, 0.0) / 0.35, 1.0)) * fnr_penalty_weight
)
```

The FPR/FNR penalty logic:
- FPR ≤ 0.30 → full weight (1.0)
- FPR 0.30–0.60 → linear decay from 1.0 to 0.0
- FPR > 0.60 → zero weight
- Same for FNR with threshold 0.35–0.70.

**Composite ranges from 0.0 (worst) to 1.0 (perfect). Scale to 0-100 by multiplying by 100.**

### 3.4 Per-Document-Type Scores

In addition to overall composite, the framework reports separate scores for each type:

| Sub-corpus | Documents | Purpose |
|---|---|---|
| NDA | NDA-01 through NDA-10 | Measure NDA-specific performance |
| Employment | EMP-01 through EMP-10 | Measure employment-specific performance |
| Vendor | VEN-01 through VEN-10 | Measure vendor agreement performance |

Each sub-corpus uses the same metrics (parse rate, precision, recall, severity, FPR, FNR) applied to its 10 documents only.

### 3.5 Model Comparison

The framework supports running the same 30 documents across multiple models:

| Model | Config | Purpose |
|---|---|---|
| qwen2.5:3b | temperature=0.0, num_predict=4096 | Current primary. Baseline score. |
| qwen2.5:7b | temperature=0.0, num_predict=4096 | Candidate upgrade. Compare composite. |
| gemma4:E4B | temperature=0.0, num_predict=4096 | Alternative. Compare composite. |

If a model fails on ≥3 parse failures across 30 documents, its results are flagged with ⚠️ low-reliability and the model should not be promoted to production.

### 3.6 Output Report Format

The framework produces two outputs:

**JSON (machine-readable):** `/reports/validation_run_{timestamp}.json`

```json
{
  "run_id": "2026-06-01_1430",
  "model": "qwen2.5:3b-instruct",
  "timestamp": "2026-06-01T14:30:00Z",
  "corpus": {
    "total_documents": 30,
    "nda": 10,
    "employment": 10,
    "vendor": 10
  },
  "overall": {
    "parse_success_rate": 0.967,
    "precision": 0.733,
    "recall": 0.688,
    "severity_accuracy": 0.818,
    "false_positive_rate": 0.267,
    "false_negative_rate": 0.312,
    "composite_score": 77
  },
  "by_type": {
    "NDA": { "parse_success_rate": 1.0, "precision": 0.8, "recall": 0.75, "composite": 82 },
    "Employment": { "parse_success_rate": 0.9, "precision": 0.7, "recall": 0.6, "composite": 70 },
    "Vendor": { "parse_success_rate": 1.0, "precision": 0.7, "recall": 0.71, "composite": 78 }
  },
  "per_document": [
    {
      "id": "NDA-01",
      "pass": true,
      "parse_success": true,
      "issues_found": 0,
      "issues_expected": 0,
      "false_positives": 0,
      "false_negatives": 0,
      "precision": 1.0,
      "recall": 1.0,
      "details": []
    },
    {
      "id": "EMP-02",
      "pass": false,
      "parse_success": true,
      "issues_found": 1,
      "issues_expected": 2,
      "false_positives": 0,
      "false_negatives": 1,
      "precision": 1.0,
      "recall": 0.5,
      "severity_accuracy": 1.0,
      "details": [
        {
          "expected_issue": "Overbroad Invention Assignment",
          "matched": true,
          "found_severity": "HIGH",
          "expected_severity": "HIGH",
          "severity_correct": true
        },
        {
          "expected_issue": "Excessive Non-Compete Duration",
          "matched": false,
          "reason": "Model did not produce a non-compete finding"
        }
      ]
    }
  ]
}
```

**Markdown (human-readable):** `/reports/validation_run_{timestamp}.md`

A formatted table of per-document results, summary scores by type, per-model comparison if multi-model run, and a PASS/FAIL determination.

### 3.7 Pass / Fail Determination

A validation run **PASSES** if:

1. **Overall composite ≥ 70** (out of 100)
2. **Parse success rate ≥ 90%** (≥27 of 30 documents parse successfully)
3. **No sub-corpus composite ≤ 50** (every document type scores at least 50)
4. **Zero catastrophic failures** (a document with a red flag = true in the corpus that the pipeline returns 0 issues on — counts as a high-severity false negative)

A validation run **FAILS** if any of the above conditions are not met.

---

---

## 4. Benchmark Assumptions Not Represented in Real Contracts

### 4.1 Current Benchmark Documents vs. Real-World

| Current Benchmark | Format | Real-World Gap |
|---|---|---|
| `clean_nda.txt` | 9 clean sections, single-purpose, perfectly formatted, exact clause naming (Section 1, 2...) | Real NDAs use numbering like 1.1, 1.1.1, rarely have all 9 sections, often embed terms in odd places (indemnity in a "Miscellaneous" section) |
| `unlimited_indemnity.txt` | Single clause, clearly labeled "Section 12 Indemnification", explicit "without limit and without cap" | Real unlimited indemnity is often disguised: "Vendor shall defend and hold harmless Company from any and all claims" with no cap mention anywhere → model must infer absence of cap |
| `balanced_mutual_indemnity.txt` | Clean labeling, all protections in one section | Real balanced indemnity often splits across sections: mutual language in one place, cap buried in "Limitation of Liability" section, exclusion in "Consequential Damages" section |
| `contradictory_clauses.txt` | Directly adjacent, explicitly contradicting, numbered to make conflict obvious | Real contradictions are subtle: one clause says "5 years from Effective Date", another says "until termination", with no explicit conflict marker |
| `non_legal_text.txt` | Cookie recipe — clearly non-legal | Real non-legal texts that arrive at the pipeline (user uploads wrong file) are more ambiguous: an invoice, a product spec sheet, an email thread about contract terms |
| `duplicate_clause_spam.txt` | Exact verbatim repetition 20× | Real duplication uses slight variation: same clause rephrased in different sections, or copy-paste with renamed party names |
| `empty_file.txt` | Zero bytes | Real empty inputs: whitespace-only, ASCII control characters, BOM-only, PDF with no extractable text |
| `garbage_ocr.txt` | Leet-speak substitutions | Real OCR garbage: merged words ("ConfidentialInformation"), split words ("Confiden tial"), missing punctuation, substituted Unicode (em-dash vs hyphen, non-breaking spaces) |

### 4.2 Specific Assumptions Built into Current Benchmarks

| Assumption | Current Benchmark | Real-World Counterexample |
|---|---|---|
| Documents have 1–3 clauses | Every benchmark document is single-issue or simple | Real contracts have 15–50 clauses, many irrelevant to the pipeline's scope. Model must filter noise. |
| No crossed-out or amended text | All documents are clean, final versions | Real contracts have strikethrough, underline, bracketed "[INTENTIONALLY OMITTED]", handwritten margin notes |
| No exhibits or schedules | Only the main body | Real NDAs have Exhibit A (Confidential Info list), employment agreements have Schedule 1 (Stock Options), MSAs have multiple SOWs |
| No formatting surprises | Plain paragraphs | Real contracts use tables, bullet points, ALL CAPS headers, signature blocks, notary blocks, continuation sheets |
| No cross-references | No "as defined in Section 3.1(b)" | Real contracts heavily cross-reference, sometimes to non-existent sections |
| English only | All documents in clean English | Real contracts may have dual-language provisions, defined terms in foreign language |
| No embedded urls or email | No references to external sources | Real contracts reference URLs (DPA available at ...), email addresses for notices |
| Severity is binary (risk/no risk) | Each document is expected to pass or fail cleanly | Real contracts are a spectrum: the same clause may be acceptable to one firm and unacceptable to another |
| No temporal drift | Static documents | Real contracts reference dates, "within 30 days of signing", "as of January 1, 2023". Model must not confuse dates with obligations. |
| No party name confusion | [Disclosing Party] / [Receiving Party] | Real contracts have 15+ defined terms mixed with non-defined references: "Company", "Client", "Customer", "You", "Licensor" |

### 4.3 Systematic Weaknesses in Coverage

The current benchmark does not test:

1. **Negative-space reasoning:** The model must detect the absence of a clause (e.g., "no data processing addendum" in a SaaS agreement that clearly processes personal data). The benchmarks only test presence of problematic clauses.

2. **Clause interaction:** A liability cap of $50,000 may be fine for a $10,000 SaaS subscription but grossly inadequate for a $5M services engagement. The model must understand proportionality.

3. **Jurisdiction-specific knowledge:** A 24-month non-compete in Georgia might be enforceable; in California it's void. The current prompt doesn't encode jurisdiction rules, and benchmarks don't test for it.

4. **Industry-specific nuance:** HIPAA business associate agreements, FINRA compliance, GDPR data processing — each has unique requirements. Benchmarks do not include industry-specific documents.

5. **Multi-party complexity:** Only one benchmark (balanced_mutual_indemnity) involves two parties. No test for three-party NDAs, subcontractor chains, or assignment chains.

6. **Ambiguous risk:** Documents where the correct answer depends on who is asking (buyer vs seller, employer vs employee). Current benchmarks assume a fixed "risk" perspective.

7. **Document version comparison:** The pipeline only sees one document at a time. Real-world use often involves comparing "our standard form" vs "their proposed changes", which the pipeline cannot detect without a diff input.

---

---

## 5. Deployment Readiness Score

### 5.1 Formula

```
Deployment Readiness = composite_score - penalties + bonuses

Where:
  composite_score = weighted composite from Section 3.3 (0-100)
  penalties = sum of penalty points (see below, max -25)
  bonuses = sum of bonus points (see below, max +10)

Final clamped to [0, 100]
```

### 5.2 Penalty Conditions

| Condition | Points | Trigger |
|---|---|---|
| Sub-corpus below threshold | -10 | Any one of NDA/Employment/Vendor composite < 60 |
| Catastrophic false negative | -15 per doc | Red flag document returns 0 issues (missed a critical risk) |
| Parse failure on clean document | -5 per doc | NDA-01, EMP-01, EMP-03, VEN-01, VEN-10 fail to parse |
| Model non-determinism | -5 | Same run with same model produces different results on ≥3 documents (requires 2 runs) |
| Recall < 50% on red-flag documents | -10 | Subset of documents where red_flag=true have recall < 50% |
| Precision < 50% on clean documents | -10 | Subset of documents where red_flag=false have precision < 50% |

### 5.3 Bonus Conditions

| Condition | Points | Trigger |
|---|---|---|
| Sub-corpus excellence | +3 per sub | NDA, Employment, AND Vendor each have composite ≥ 85 |
| No parse failures | +3 | All 30 documents parse successfully |
| Recall > 75% on red-flag documents | +4 | Red flag recall exceeds 75% |

### 5.4 Readiness Tiers

| Score Range | Tier | Meaning | Recommended Action |
|---|---|---|---|
| 90–100 | **Production-Ready** | Pipeline meets all quality thresholds on real-world documents | Deploy with monitoring. Run validation monthly. |
| 75–89 | **Conditional Pass** | Acceptable but has known gaps | Deploy with guardrails (human review on flagged docs). Fix penalties before full rollout. |
| 50–74 | **Needs Improvement** | Pipeline has systematic issues | Do not deploy to production. Address sub-corpus deficits and rerun. |
| 0–49 | **Not Ready** | Fundamental failures present | Redesign approach. Current pipeline is insufficient for real-world use. |

### 5.5 Current Estimated Score

Based on the existing benchmark performance (8 synthetic documents only):

| Metric | 3b Estimate | 7b Estimate | gemma4 Estimate | Notes |
|---|---|---|---|---|
| composite | ~77 | ~75 | ~65 | 7b has hallucination risk, gemma4 has employment failure |
| parse_success_rate | 1.0 (8/8) | 1.0 (8/8) | 0.875 (7/8) | gemma4 safe_mutual_nda parse failure |
| precision | 0.667 | 0.667 | ~0.4 | Precision on synthetic docs not directly comparable to real |
| recall | 0.308 | 0.308 | ~0.3 | Very low recall even on synthetic |
| severity_acc | ~0.9 | ~0.9 | ~0.7 | Category + severity matching on synthetic is well-calibrated |
| FPR | ~0.20 | ~0.20 | ~0.15 | Low false positives are a strength |
| FNR | ~0.60 | ~0.60 | ~0.65 | But high false negatives (low recall) means many real risks missed |

**Estimated Readiness Score (Pre-Validation-Suite): ~55–65 / 100**

The low recall (0.308) is the primary drag. The pipeline is precise but not comprehensive. When run against real-world documents with more complex clauses, recall will likely drop further (more findings to miss). The estimate of 55–65 places the pipeline in the **Needs Improvement** tier.

### 5.6 Target Score for Production Deployment

| Condition | Minimum Target | Rationale |
|---|---|---|
| Composite score | ≥ 80 | Weighted metrics must be strong overall |
| Parse success rate | ≥ 95% (≥28.5/30) | Only GDPR-level complexity should cause parse issues |
| NDA sub-corpus | ≥ 80 | NDAs are the most common input. Must be reliable. |
| Employment sub-corpus | ≥ 70 | Known weakness (gemma4). Must be ≤15 points behind NDA. |
| Vendor sub-corpus | ≥ 75 | Complex agreements. Noise tolerance higher but not unlimited. |
| Catastrophic FNs | 0 | Every red-flag document must produce at least one issue. |

**Target: 80 / 100 to pass Conditional Pass tier.**
**Target: 90 / 100 to pass Production-Ready tier.**

---

---

## Appendix A: Corpus Metadata JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["document_id", "title", "source", "type", "subtype", "risk_level", "clause_set", "red_flag"],
  "properties": {
    "document_id": { "type": "string", "pattern": "^(NDA|EMP|VEN)-\\d{2}$" },
    "title": { "type": "string" },
    "source": {
      "type": "object",
      "required": ["type", "description"],
      "properties": {
        "type": { "type": "string", "enum": ["public_filing", "open_source_template", "anonymized_real", "synthetic_from_template"] },
        "description": { "type": "string" },
        "url": { "type": "string" }
      }
    },
    "type": { "type": "string", "enum": ["NDA", "EMPLOYMENT", "VENDOR_SERVICE"] },
    "subtype": { "type": "string" },
    "risk_level": { "type": "string", "enum": ["clean", "moderate", "high-risk"] },
    "clause_set": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1
    },
    "red_flag": { "type": "boolean" },
    "word_count": { "type": "integer", "minimum": 100 },
    "jurisdiction": { "type": "string", "default": "unspecified" }
  }
}
```

## Appendix B: Review JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["document_id", "title", "model_under_test", "ground_truth", "evaluation_weights"],
  "properties": {
    "document_id": { "type": "string" },
    "title": { "type": "string" },
    "model_under_test": { "type": "string" },
    "ground_truth": {
      "type": "object",
      "required": ["parse_should_succeed", "expected_issue_count", "max_allowed_issues", "expected_confidence_label", "min_confidence_score", "issues"],
      "properties": {
        "parse_should_succeed": { "type": "boolean" },
        "expected_issue_count": { "type": "integer", "minimum": 0 },
        "max_allowed_issues": { "type": "integer", "minimum": 0 },
        "expected_confidence_label": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH"] },
        "min_confidence_score": { "type": "number", "minimum": 0, "maximum": 1 },
        "issues": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "expected_issue_title", "expected_severity", "allowed_severities", "expected_category", "allowed_categories", "rationale"],
            "properties": {
              "id": { "type": "string" },
              "expected_issue_title": { "type": "string" },
              "expected_severity": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
              "allowed_severities": {
                "type": "array",
                "items": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] }
              },
              "expected_category": { "type": "string" },
              "allowed_categories": {
                "type": "array",
                "items": { "type": "string" }
              },
              "must_contain_quoted_text_pattern": { "type": "array", "items": { "type": "string" } },
              "must_not_contain_quoted_text_pattern": { "type": "array", "items": { "type": "string" } },
              "must_contain_explanation_pattern": { "type": "array", "items": { "type": "string" } },
              "must_not_contain_explanation_pattern": { "type": "array", "items": { "type": "string" } },
              "rationale": { "type": "string" }
            }
          }
        }
      }
    },
    "evaluation_weights": {
      "type": "object",
      "required": ["parse_success", "precision", "recall", "severity_accuracy", "false_positive_penalty", "false_negative_penalty"],
      "properties": {
        "parse_success": { "type": "number", "minimum": 0, "maximum": 1 },
        "precision": { "type": "number", "minimum": 0, "maximum": 1 },
        "recall": { "type": "number", "minimum": 0, "maximum": 1 },
        "severity_accuracy": { "type": "number", "minimum": 0, "maximum": 1 },
        "false_positive_penalty": { "type": "number", "minimum": 0, "maximum": 2 },
        "false_negative_penalty": { "type": "number", "minimum": 0, "maximum": 2 }
      }
    }
  }
}
```
