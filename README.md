# Zynexra

**Zynexra** is a privacy-first offline AI system for analyzing legal documents and identifying structural risks in contracts. It runs entirely **locally** using Ollama-hosted language models with deterministic post-processing and validation for stable outputs.

---

## Features

- **Audit Mode** — Analyzes contracts for liability exposure, indemnification risk, structural inconsistencies, confidentiality weaknesses, governing law issues, and missing protective clauses.
- **Redaction Mode** — Detects and redacts PII (names, emails, phones, addresses, companies).
- **Advisory Mode** — Answers legal-practice questions with context-aware responses.
- **Confidence Scoring** — Multi-factor confidence system with quality/domain-aware caps.
- **Contradiction Detection** — Flags survival-clause vs category mismatches automatically.
- **OCR Degradation Detection** — Identifies corrupted/noisy text and suppresses unreliable analysis.
- **Legal-Domain Guard** — Prevents hallucinated legal analysis on non-legal content (recipes, essays, etc.).

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com)

### 1. Install Ollama & Pull Models

```bash
ollama pull qwen2.5:3b-instruct
ollama pull qwen2.5:1.5b-instruct    # fallback model
```

### 2. Configure Environment

Copy or edit `.env` at the project root:

```env
MODEL_FAST=qwen2.5:3b-instruct
MODEL_FALLBACK=qwen2.5:1.5b-instruct
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd frontend-react
npm install
```

---

## Running Backend

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

The API serves at `http://localhost:8000`. Key endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/ask` | POST | Send text query (all modes) |
| `/ask_file` | POST | Upload file for analysis |
| `/set_mode` | POST | Switch session mode |
| `/get_mode` | GET | Get current session mode |
| `/export_report` | POST | Download last report (JSON or text) |
| `/reset` | POST | Reset session state |
| `/history` | GET | Browse persisted records |
| `/history/stats/summary` | GET | Aggregate statistics |

---

## Running Frontend

```bash
cd frontend-react
npm run dev
```

The React frontend serves at `http://localhost:5173`. It communicates with the backend API at `http://localhost:8000` (configured via `frontend-react/.env`).

### Frontend structure

```
frontend-react/src/
├── App.tsx                   # Root: state management, mode routing
├── api.ts                    # API client (audit, advisory, history CRUD)
├── types.ts                  # TypeScript type definitions
├── main.tsx                  # Entry point
├── styles.css                # Global styles
├── pages/                    # View pages
│   ├── AuditResultsPage.tsx
│   ├── RedactionResultsPage.tsx
│   ├── AdvisoryChatPage.tsx
│   ├── UploadContractPage.tsx
│   └── WorkspacePage.tsx
├── components/               # Reusable UI components
├── hooks/                    # Custom React hooks
├── contexts/                 # React contexts (Toast)
└── utils/                    # Helpers (persistence, logger, formatting)
```

---

## Regression Tests

```bash
python tests/regression_runner.py
```

Runs 7 tests against the live API (`http://localhost:8000` by default):

| Test | Input | Pass Criteria |
|---|---|---|
| Clean NDA | Standard mutual NDA | Label != LOW, no hallucinated contradictions |
| Unlimited Indemnity | Clause with uncapped indemnity | Indemnification category found |
| Garbage OCR | Scrambled noise | Label != HIGH, quality_warning present |
| Empty File | Zero bytes | issue_count == 0 |
| Contradictory Clauses | Conflicting terms | Structural Inconsistency found |
| Non-Legal Text | Cookie recipe | Label != HIGH |
| Duplicate Spam | Same clause x20+ | issue_count <= 10 |

```bash
python tests/regression_runner.py --url http://192.168.1.100:8000
```

---

## Architecture Overview

```
User / Frontend
       │
       ▼
   FastAPI App (app.py)
       │
       ├─ SessionManager (in-memory sessions)
       ├─ ResponseGenerator (Ollama LLM with model fallback)
       │
       ▼
   Normalization Pipeline (normalization_engine.py)
       │
       ├─ 1. Parse issues (JSON → text fallback)
       ├─ 2. Normalize severities (unlimited → CRITICAL, etc.)
       ├─ 3. Normalize categories (remap + sanitize language)
       ├─ 4. Suppress duplicates (dedup by quoted text)
       ├─ 5. Detect contradictions (survival vs category mismatch)
       ├─ 6. Assess input quality (OCR noise, corruption)
       ├─ 7. Detect legal domain (keyword ratio, structure score)
       └─ 8. Compute confidence (6 weighted factors + quality caps)
               │
               ▼
         Response Schema (response_schemas.py)
               │
               ▼
         Validation Engine (validation_engine.py)
               │
               ▼
         SQLite Persistence (db_service.py)
               │
               ▼
         Frontend (React) / Export
```

### Key Backend Modules

| Module | Purpose |
|---|---|
| `backend/engines/confidence_engine.py` | AuditConfidenceScorer, AdvisoryConfidenceScorer |
| `backend/engines/contradiction_engine.py` | Survival-clause vs category contradictions |
| `backend/engines/input_quality_engine.py` | 9-factor input quality scoring, hard-degrade caps |
| `backend/engines/legal_domain_engine.py` | Legal/possibly-legal/non-legal classification |
| `backend/engines/normalization_engine.py` | Central pipeline: parse, normalize, suppress, build |
| `backend/engines/redaction_engine.py` | Regex-based PII detection and redaction |
| `backend/engines/response_schemas.py` | Dataclass schemas, builders, validators |
| `backend/engines/validation_engine.py` | Identity disclosure and creator-integrity checks |
| `backend/prompts/` | Mode-specific LLM system prompts |
| `backend/services/db_service.py` | SQLite persistence (3 tables, legacy repair) |
| `backend/services/ollama_service.py` | Ollama HTTP client with automatic model fallback |

See `docs/ARCHITECTURE.md` for the full architecture documentation.

---

## Design Principles

- **Privacy First** — All processing is local; no data leaves the machine.
- **Deterministic** — Post-processing ensures stable, predictable outputs from non-deterministic LLMs.
- **Structured Analysis** — Outputs follow a strict schema for legal review workflows.
- **Graceful Degradation** — Quality checks, domain detection, and fallback models ensure the system handles edge cases without hallucination.

---

## Creator

Zynexra was created by **Jay Lanjewar**.

---

## Status

Current stage: **Prototype / Pilot Testing**
