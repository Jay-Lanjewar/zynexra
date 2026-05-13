# Zynexra

**Zynexra** is a privacy-first offline AI system for analyzing legal documents and identifying structural risks in contracts.

It runs entirely **locally** using Ollama-hosted language models and provides deterministic post-processing and validation to ensure stable outputs.

The system is designed for environments where **confidentiality is critical**, such as legal teams reviewing contracts, NDAs, and agreements.

---

# Key Features

### Offline AI

Zynexra runs fully locally.

* No external APIs
* No cloud processing
* No internet access required
* Documents never leave the machine

---

### Legal Document Risk Analysis

In **AUDIT mode**, Zynexra analyzes contracts to detect:

* Liability exposure
* Indemnification risk
* Structural inconsistencies
* Confidentiality weaknesses
* Governing law issues
* Missing protective clauses

Each issue is returned in a structured format including:

* severity level
* clause location
* quoted text
* risk explanation
* suggested improvement

---

### Privacy Redaction

In **REDACTION mode**, Zynexra detects and removes personally identifiable information (PII).

It automatically redacts:

* names
* email addresses
* phone numbers
* addresses
* other sensitive information

Redacted data is replaced with:

```
[REDACTED]
```

---

### Deterministic Output Controls

Zynexra includes deterministic post-processing layers that normalize model output to maintain stable behavior.

These layers:

* enforce severity overrides
* normalize category names
* prevent invalid rewrites
* ensure confidentiality protections are preserved
* enforce liability cap suggestions when required

This makes the system significantly more reliable than raw LLM output.

---

### Validation Engine

Before any response is returned to the user, a validation engine checks for compliance violations.

Examples of checks include:

* identity disclosure
* creator integrity
* restricted phrasing
* system rule violations

If a violation occurs, the response is rejected.

---

# System Architecture

```
User
 ↓
Streamlit Interface
 ↓
FastAPI Backend
 ↓
Local LLM via Ollama
 ↓
Deterministic Normalization Layer
 ↓
Validation Engine
 ↓
Final Output
```

---

# Components

## FastAPI Backend

Handles:

* AI interaction
* validation
* session management
* file processing
* report generation

Main endpoints:

```
POST /ask
POST /ask_file
POST /set_mode
GET  /get_mode
POST /export_report
POST /reset
```

---

## Streamlit Interface

Provides a simple UI for interacting with Zynexra.

Features:

* chat interface
* file uploads (.txt / .pdf)
* streaming responses
* execution mode switching
* downloadable reports

---

## Local Model Runtime

Zynexra uses Ollama to run language models locally.

Example models:

```
qwen2.5:3b-instruct
qwen2.5:1.5b-instruct
```

The system automatically falls back to the smaller model if the primary model fails.

---

## File Processing

Zynexra supports:

```
.txt
.pdf
```

PDFs are processed using **PyMuPDF** to extract text before analysis.

---

# Optional RAG Support

The project includes a retrieval pipeline built with:

* ChromaDB
* nomic-embed-text embeddings

This allows reference documents to be ingested and retrieved during analysis.

The RAG layer is currently disabled by default.

---

# Installation

## 1. Install Ollama

Download from:

https://ollama.com

Pull the model:

```
ollama pull qwen2.5:3b-instruct
```

---

## 2. Install Python Dependencies

```
pip install -r requirements.txt
```

---

## 3. Start the API

```
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Launch the Interface

```
streamlit run ui_streamlit.py
```

---

# Usage

### Chat Mode

Ask questions directly in the interface.

Example:

```
Explain risks in this NDA clause
```

---

### Document Audit

Upload a contract and Zynexra will generate a structured risk report.

The report can be downloaded using the **Download Last Report** button.

---

# Project Structure

```
app.py
ui_streamlit.py
rag.py
run_regression_tests.py
requirements.txt
README.md
```

---

# Design Principles

### Privacy First

All processing happens locally.

### Deterministic AI

Post-processing ensures stable and predictable outputs.

### Structured Analysis

Outputs follow a strict format to support legal review workflows.

---

# Creator

Zynexra was created by

**Jay Lanjewar**
in collaboration with
**Priyani Patil**

---

# Status

Current stage: **Prototype / Pilot Testing**

The system is functional and designed for local testing and experimentation.
