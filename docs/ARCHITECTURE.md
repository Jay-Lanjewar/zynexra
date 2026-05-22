# Zynexra Architecture

## Overview

Zynexra is a legal-document analysis system consisting of a **FastAPI Python backend** and a **React TypeScript frontend**. It accepts legal contracts (NDAs, indemnity clauses, etc.), runs them through an LLM-based audit pipeline, and returns structured risk findings with confidence scoring, contradiction detection, and quality safeguards.

```
┌──────────────────────┐      HTTP/JSON       ┌──────────────────────┐
│   React Frontend     │ ◄──────────────────► │   FastAPI Backend    │
│   (Vite + TypeScript │     fetch / SSE      │   (Python 3.11)      │
│    + Tailwind)       │                      │                      │
└──────────────────────┘                      ├──────────────────────┤
                                               │   Ollama (LLM)       │
                                               │   SQLite (history)   │
                                               └──────────────────────┘
```

---

## Backend Architecture

### Directory Layout

```
backend/
├── app.py                          # FastAPI app, endpoints, session management
├── config.py                       # Settings from .env (model names, host, port)
├── logger.py                       # Logging configuration
├── engines/
│   ├── confidence_engine.py        # AuditConfidenceScorer, AdvisoryConfidenceScorer
│   ├── contradiction_engine.py     # Survival clause vs category mismatch detection
│   ├── input_quality_engine.py     # OCR degradation / corrupted text detection
│   ├── legal_domain_engine.py      # Legal vs non-legal document classification
│   ├── normalization_engine.py     # Central pipeline: parse, normalize, suppress, build response
│   ├── redaction_engine.py         # PII detection and redaction
│   ├── response_generator.py       # Ollama LLM wrapper with fallback
│   ├── response_schemas.py         # Dataclass schemas, builders, validators
│   └── validation_engine.py        # Identity disclosure + creator integrity checks
├── prompts/
│   ├── audit_prompt.py             # AUDIT mode system prompt
│   ├── advisory_prompt.py          # ADVISORY mode system prompt
│   ├── redaction_prompt.py         # REDACTION mode system prompt
│   ├── identity_guard.py           # Identity rules prepended to all prompts
│   └── __init__.py                 # Prompt router (build_execution_prompt)
├── services/
│   ├── ollama_service.py           # HTTP client to Ollama inference server
│   ├── db_service.py               # SQLite persistence layer
│   └── pdf_service.py              # PyMuPDF text extraction
└── utils/
    ├── pii.py                      # Deterministic pre-redaction regex patterns
    └── timing.py                   # Timing decorator/helper
```

### Audit Pipeline

The core pipeline transforms a raw LLM response into a structured, normalized, validated audit result.

```
                        ┌─────────────────┐
  User Upload/Query ──► │   LLM Inference  │
                        └────────┬────────┘
                                 │ raw text
                                 ▼
                        ┌─────────────────┐
                        │  Normalization   │  normalize_audit_response()
                        │  Engine          │  - parse JSON issues
                        │                  │  - fallback to text parsing
                        └────────┬────────┘
                                 │ structured issues
                                 ▼
                        ┌─────────────────┐
                        │  Severity Fixes  │  normalize_audit_issue_severity_fields()
                        │                  │  - unlimited → CRITICAL
                        │                  │  - governing law → at least HIGH
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Category Norm   │  normalize_audit_issue_fields()
                        │                  │  - remap categories
                        │                  │  - sanitize language
                        │                  │  - suppress duplicates
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Contradiction   │  validate_contradictions()
                        │  Detection       │  - survival vs category mismatch
                        │                  │  - semantic contradictions
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Input Quality   │  assess_input_quality()
                        │  Assessment      │  - symbol density
                        │                  │  - malformed words
                        │                  │  - OCR noise detection
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Domain Guard    │  compute_document_domain_confidence()
                        │                  │  - legal keyword ratio
                        │                  │  - contract structure score
                        │                  │  - NON_LEGAL → suppress, cap to 0.25
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Confidence      │  audit_scorer.compute()
                        │  Scoring         │  - 6 weighted factors
                        │                  │  - quality caps applied
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Response Build  │  build_audit_response()
                        │                  │  - schema validation
                        │                  │  - metadata assembly
                        └─────────────────┘
```

#### Pipeline Entry Point

`build_audit_json_payload()` in `normalization_engine.py:286` is called by `build_mode_json_payload()` (which is called from `app.py` after LLM generation).

```python
# app.py:734 — JSON response path for file uploads
structured = build_mode_json_payload(
    complete_response, MODEL_NAME, effective_mode,
    user_query=text, fallback_used=fallback_used
)
```

The pipeline is only invoked in **JSON response mode** (`response_format=json`). Streaming mode sends raw text directly to the client.

### Confidence Scoring

Defined in `confidence_engine.py`. Two scorers exist:

#### AuditConfidenceScorer

| Factor | Weight | Computation |
|---|---|---|
| `structured_parse_success` | 0.30 | 1.0 if JSON parse succeeded, else 0.0 |
| `issue_completeness` | 0.20 | 0.3 if zero issues; else 0.4 + (has_title + has_severity + has_quote) / 3 × 0.6 |
| `duplicate_suppression` | 0.10 | max(0.0, 1.0 − suppressed_count × 0.25) |
| `refusal_absent` | 0.15 | 0.0 if refusal patterns found ("I cannot", "insufficient information"), else 1.0 |
| `response_length` | 0.10 | ≥100w → 1.0, ≥50w → 0.8, ≥20w → 0.5, else 0.2 |
| `no_fallback_parser` | 0.15 | 0.0 if fallback model was used, else 1.0 |

**Quality caps** (applied after weighted sum):

| Condition | Cap |
|---|---|
| `input_quality_degraded` only | 0.30 |
| Both `fallback_used` + `input_quality_degraded` | 0.25 |

**Label thresholds:**

| Score Range | Label |
|---|---|
| ≥ 0.75 | HIGH |
| ≥ 0.45, < 0.75 | MEDIUM |
| < 0.45 | LOW |

#### AdvisoryConfidenceScorer

Similar structure but uses `legal_topic_relevance` (keyword matching), `no_generic_penalty` ("it depends", "generally speaking"), and `no_hallucination_warning` ("I believe", "probably").

### Contradiction Engine

Defined in `contradiction_engine.py`. Detects two types of contradictions:

1. **Survival Category Mismatch** — An issue quotes survival language (`"obligations survive termination"`) but the category says the survival clause is missing (e.g., `"confidentiality termination"`, `"missing survival clause"`).

2. **Semantic Contradiction** — Quoted text contains survival language but the risk explanation uses absence indicators (`"missing"`, `"absent"`, `"lacks"`, `"not found"`) or termination indicators (`"terminate"`, `"end"`, `"expire"`).

**Exception**: If the risk explanation references *duration insufficiency* (e.g., "survival period is too short"), the contradiction is not flagged.

Detection uses ~11 `SURVIVAL_PHRASE` regex patterns and ~7 `DURATION_INSUFFICIENCY_CUE` patterns.

When a contradiction is found, the offending issue is removed from the response.

### OCR Degradation Detection

Defined in `input_quality_engine.py`. A multi-factor scoring system that detects corrupted or noise-laden text.

**9 weighted factors:**

| Factor | Weight | What it measures |
|---|---|---|
| `symbol_density` | 0.15 | Non-alphanumeric, non-whitespace characters |
| `non_alphanumeric_ratio` | 0.10 | All non-letter/digit chars including whitespace |
| `repeated_special_chars` | 0.12 | Sequences like `!!!`, `---`, `###` |
| `malformed_words` | 0.20 | Digit-letter mixing, OCR substitutions, symbol bursts |
| `dictionary_word_ratio` | 0.13 | Match rate against ~580 common English/legal words |
| `uppercase_ratio` | 0.10 | Uppercase letter ratio (high → noisy) |
| `vowel_ratio` | 0.08 | Vowel-to-letter ratio (low → corrupted) |
| `symbol_burst_density` | 0.07 | 3+ consecutive symbol clusters |
| `keyword_trust` | 0.05 | Legal keywords discounted if text quality is poor |

**Hard degrade triggers** — if *any* fires, score is capped at 0.20:

| Trigger | Threshold |
|---|---|
| Malformed word ratio | > 15% |
| Symbol density score | < 0.30 |
| Symbol burst density | < 0.30 |
| Digit-letter mixed words | ≥ 2 |
| Repeated special chars | < 0.35 |

**Integrated semantic suppression** (in `normalization_engine.py`): if ALL three of `fallback_used`, `input_quality_degraded`, and poor `_assess_quoted_text_quality()` are true, the response is replaced with:

> "Document quality too degraded for reliable legal analysis."

### Legal-Domain Detection

Defined in `legal_domain_engine.py`. Prevents hallucinated legal analysis on non-legal content (recipes, essays, sports articles, conversational text).

**3 signal factors** combined into a `legal_signal`:

| Factor | Weight | Method |
|---|---|---|
| `legal_keyword_ratio` | 0.40 | Word-level match against ~195 keywords (agreement, party, indemnify, termination, governing, liability, etc.) |
| `contract_structure_score` | 0.35 | Regex match against 29 structural patterns (numbered sections, "WHEREAS", "by and between", signature blocks, defined terms) |
| `legal_phrase_density` | 0.25 | Multi-word phrase match against ~200 phrases (governing law, force majeure, hold harmless, confidential information) |

**Non-legal penalty** subtracts from the signal:
- **Strong patterns** (×0.20 each): recipes (`cup`, `tablespoon`, `preheat`), storytelling (`once upon a time`), casual opinion (`I think`, `in my opinion`), sports terms
- **Weak patterns** (×0.08 each): 1st/2nd person narrative, conversational filler, internet slang, fiction indicators

```
effective_score = max(0.0, legal_signal − non_legal_penalty)

thresholds:
  ≤ 0.10   →  NON_LEGAL       (suppression triggered)
  0.10–0.20 → POSSIBLY_LEGAL  (no suppression)
  ≥ 0.20   →  LEGAL           (no suppression)
```

**When NON_LEGAL**: issues are cleared, response replaced with `"Document does not appear to be a legal contract or agreement."`, confidence capped at ≤ 0.25 / LOW.

### Response Schemas

Defined in `response_schemas.py` (schema version 1).

#### Core Dataclasses

```
AuditIssue
├── issue_title: str
├── severity: str              ("CRITICAL" | "HIGH" | "MEDIUM" | "LOW")
├── category: str              (normalized: "Indemnification", "Structural Inconsistency", etc.)
├── location: str
├── quoted_text: str
├── risk_explanation: str
└── suggested_improvement: str

AuditResponse
├── success: bool
├── model: str
├── mode: str                  ("AUDIT")
├── response_type: str         ("audit")
├── schema_version: int
├── issue_count: int
├── issues: List[Dict]
├── structured_parse_failed: bool
├── legacy_text: str
├── confidence_score: float
├── confidence_label: str
├── fallback_used: bool
├── quality_warning: str
└── metadata: Dict             (model_name, parser_used, domain, domain_confidence, etc.)
```

#### Builder Functions

- `build_audit_response()` → validates via `validate_audit_response()`, falls back to legacy dict on failure
- `build_redaction_response()` → validates via `validate_redaction_response()`
- `build_advisory_response()` → validates via `validate_advisory_response()`
- `build_refusal_response()` → returns `success=False`, `confidence_score=0.0`, `confidence_label="LOW"`
- `convert_history_record_to_response()` → converts DB records to structured responses

### Workspace Persistence

#### Database Structure (SQLite)

File: `./data/zynexra.db`. Three tables:

**`audit_history`**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| filename | TEXT | NOT NULL |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| issue_count | INTEGER | DEFAULT 0 |
| issues_json | TEXT | JSON array of issue dicts |
| raw_response | TEXT | Raw LLM output text |
| mode | TEXT | DEFAULT 'AUDIT' |
| severity_level | TEXT | |

**`redaction_history`**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| filename | TEXT | NOT NULL |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| redaction_count | INTEGER | DEFAULT 0 |
| entities_json | TEXT | JSON of redaction entities |
| redacted_text | TEXT | |
| redaction_types | TEXT | |

**`advisory_sessions`**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| session_id | TEXT | NOT NULL UNIQUE |
| title | TEXT | |
| messages_json | TEXT | JSON array of user/assistant messages |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| message_count | INTEGER | DEFAULT 0 |

The `db_service.available` flag provides graceful degradation — if SQLite init fails, all operations return empty results instead of crashing.

Legacy JSON repair logic (`parse_legacy_json`, `ast.literal_eval` fallback, auto-repair in DB) handles records from older schema versions.

#### Session Management

In-memory `SessionManager` (in `app.py`):

```python
session = {
    "history": [],        # list of {user, assistant} exchanges
    "mode": "AUDIT",      # current mode
    "created_at": timestamp,
    "last_report": "",    # raw text of last response
    "last_structured_response": {},  # last structured JSON payload
}
```

Only validated responses (passing `ValidationEngine`) are stored in history and persisted to DB.

---

## Frontend Architecture

### Directory Layout

```
frontend-react/src/
├── App.tsx                          # Root component: state, mode switching, API orchestration
├── main.tsx                         # ReactDOM entry point
├── types.ts                         # TypeScript type definitions
├── api.ts                           # API client: auditContractFile, askAdvisoryQuestion, CRUD
├── utils.ts                         # groupIssuesByCategory, getSeverityCounts, formatDate
├── redactionUtils.ts                # Redaction computation utilities
├── redactionHooks.ts                # useRedactionState hook
├── pages/
│   ├── AuditResultsPage.tsx         # Audit/REDACTION/ADVISORY result display
│   ├── RedactionResultsPage.tsx     # Side-by-side redaction preview
│   ├── AdvisoryChatPage.tsx         # Chat-based advisory interface
│   ├── UploadContractPage.tsx       # File upload + mode selection
│   └── WorkspacePage.tsx            # History browsing with filters
├── components/
│   ├── CollapsibleIssueCard.tsx     # Individual audit issue with severity badge
│   ├── ConfidenceBadge.tsx          # Colored badge (HIGH/MEDIUM/LOW) with tooltip
│   ├── ExportButtons.tsx            # JSON + text export
│   ├── FileUploader.tsx             # Drag-and-drop with validation
│   ├── TopNavigation.tsx            # Mode switcher navigation
│   ├── ErrorState.tsx               # Structured error display
│   ├── EmptyState.tsx               # No-file / no-issues states
│   ├── LoadingSkeleton.tsx          # Skeleton loading placeholders
│   ├── HistoryCard.tsx              # Individual history record card
│   ├── HistoryFilter.tsx            # Filter controls for workspace
│   ├── ActivitySummary.tsx          # Statistics summary component
│   ├── RetryButton.tsx              # Retry with attempt counter
│   ├── OfflineIndicator.tsx         # Connection status indicator
│   └── ...redaction components      # EntitySidebar, OriginalTextPanel, etc.
├── contexts/
│   └── ToastContext.tsx             # Toast notification system
└── hooks/
    └── useConnection.ts             # Network connectivity detection
```

### State Management

`App.tsx` uses React state (no external state library) with four view states:

```
appState: "AUDIT" | "REDACTION" | "ADVISORY" | "WORKSPACE"
```

**State flow for file upload:**

```
UploadContractPage
  │  user selects mode + file
  ▼
App.handleSubmit()
  │  calls auditContractFile(file, mode, redactionOptions)
  │  shows LoadingSkeleton with progress
  ▼
App receives AuditResponse
  │  sets result, switches appState to selectedMode
  ▼
AuditResultsPage or RedactionResultsPage
  │  renders issues with severity/category summaries
  │  shows ConfidenceBadge
  │  ExportButtons for JSON/text download
```

**State flow for advisory chat:**

```
AdvisoryChatPage
  │  user types question
  ▼
App.handleAdvisorySend()
  │  calls askAdvisoryQuestion(question, sessionId, history)
  ▼
App receives response
  │  builds ChatMessage for user + assistant
  │  sets confidence metadata on assistant message
  ▼
AdvisoryChatPage re-renders with new messages
```

### Persistence (localStorage)

- `persistence.saveAppState()` / `persistence.loadAppState()` — mode, selectedMode, redactionOptions
- `persistence.saveAdvisoryState()` / `persistence.loadAdvisoryState()` — sessionId, messages

### View Routing (in App.tsx render)

```
appState === "WORKSPACE"          → WorkspacePage
appState === "ADVISORY"           → AdvisoryChatPage
result?.mode === "REDACTION"      → RedactionResultsPage
result exists or apiError         → AuditResultsPage
default                           → UploadContractPage
```

All wrapped in `TopNavigation`, `ErrorBoundary`, `ToastProvider`, `OfflineIndicator`.

### API Client (`api.ts`)

| Function | Endpoint | Purpose |
|---|---|---|
| `auditContractFile()` | POST `/ask_file` | Upload + analyze file |
| `askAdvisoryQuestion()` | POST `/ask?response_format=json` | Send advisory query |
| `getHistoryRecords()` | GET `/history` | Fetch history with filters |
| `getRecordDetail()` | GET `/history/{id}` | Get single record |
| `deleteRecord()` | DELETE `/history/{id}` | Delete record |
| `getHistorySummary()` | GET `/history/stats/summary` | Get aggregate stats |
| `validateFile()` | (client-side) | Check size/type before upload |

All API calls use 120-second timeouts via `AbortController`. Errors are categorized into `ApiError` codes: `NETWORK_ERROR`, `SERVER_ERROR`, `TIMEOUT_ERROR`, `FILE_TOO_LARGE`, `INVALID_FILE_TYPE`, `ENCRYPTED_PDF`, `VALIDATION_ERROR`, `PARSE_ERROR`, `REQUEST_ERROR`.

### Key Frontend Types (`types.ts`)

```typescript
type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNRATED"
type AppMode = "AUDIT" | "REDACTION" | "ADVISORY"
type ConfidenceLabel = "HIGH" | "MEDIUM" | "LOW"

interface AuditIssue {
  issue_title: string;  severity: string;  category: string;
  location: string;     quoted_text: string;
  risk_explanation: string;  suggested_improvement: string;
}

interface AuditResponse {
  success: boolean;     model: string;     issue_count: number;
  issues: AuditIssue[]; confidence_score?: number;
  confidence_label?: ConfidenceLabel;  metadata?: ConfidenceMetadata;
  legacy_text?: string; redacted_text?: string; advisory_text?: string;
  structured_parse_failed?: boolean;  fallback_used?: boolean;
}
```

---

## Regression Infrastructure

Defined in `tests/regression_runner.py`. Sends each test document to the live API (`/ask_file` with AUDIT+JSON mode) and validates the response.

### Test Registry

| Test | Input | Pass Criteria |
|---|---|---|
| Clean NDA | Standard mutual NDA | Label != LOW, no hallucinated contradictions |
| Unlimited Indemnity | Clause with unlimited indemnification | "Indemnification" category found |
| Garbage OCR | Scrambled symbols + noise | Label != HIGH, quality_warning present |
| Empty File | Zero-byte file | issue_count == 0 |
| Contradictory Clauses | Two directly conflicting clauses | Structural Inconsistency category found |
| Non-Legal Text | Chocolate chip cookie recipe | Label != HIGH |
| Duplicate Clause Spam | Same clause ×20+ | issue_count <= 10 |

### Usage

```bash
python tests/regression_runner.py
python tests/regression_runner.py --url http://192.168.1.100:8000
```

---

## Data Flow Summary

```
User uploads file
  │
  ▼
app.py (/ask_file)
  ├─ validate file type (.txt/.pdf) and size (≤20K chars)
  ├─ extract text (PyMuPDF for PDF, UTF-8 for TXT)
  ├─ build system prompt from mode
  ├─ call LLM (ResponseGenerator → OllamaService)
  │    ├─ try MODEL_FAST
  │    └─ fallback to MODEL_FALLBACK on failure
  ├─ normalize (normalize_audit_response)
  ├─ validate (ValidationEngine)
  ├─ build structured payload (build_mode_json_payload)
  │    ├─ parse issues (JSON first, text fallback)
  │    ├─ normalize severity and categories
  │    ├─ detect contradictions
  │    ├─ assess input quality
  │    ├─ detect legal domain
  │    ├─ compute confidence (with quality/domain caps)
  │    └─ assemble response with metadata
  ├─ persist to SQLite
  └─ return JSON to frontend
        │
        ▼
Frontend receives AuditResponse
  ├─ render severity summary (colored pills)
  ├─ render category summary
  ├─ render issue cards (CollapsibleIssueCard)
  ├─ show confidence badge (ConfidenceBadge)
  ├─ warn on LOW/MEDIUM confidence
  └─ enable JSON/text export
```
