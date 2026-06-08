# Zynexra Implementation Plan (3-sprint sequencing)

Date: 2026-06-07
Source: `tests/product_audit_20260607.md`
Constraint: no code changes yet. This is sequencing + sizing only. No benchmark-research work is included.

---

## 1. Ranking method

Each item from the audit is scored 1-5 on three axes:

- **User impact (UI)** — how much a contract reviewer feels this on a normal run. 5 = top-of-mind complaint; 1 = barely noticed.
- **Engineering effort (EE)** — wall-clock time including code + tests + UI. 1 = hours, 5 = 1+ month. *Lower is better*; the formula inverts it.
- **Risk reduction (RR)** — how much the change prevents a real harm (data loss, wrong legal output, broken promise). 5 = prevents the worst case; 1 = cosmetic.

Composite score:
```
score = 0.45 * UI + 0.35 * RR + 0.20 * (5 - EE)
```

Weights favour user impact and risk reduction over effort, which matches the brief ("shipping improvements, not additional benchmark research"). Effort still breaks ties.

### Capacity assumption

2-week sprint, 1 engineer at ~80% capacity = **8 working days/sprint**. Each sprint is sized to land a tight 7-8 day plan with 0-1 day of slack for code review, bug fixes, and shipping.

---

## 2. Full ranking (audit items C1-C5, H1-H7, M1-M7, L1-L6)

| # | Item | UI | EE | RR | Score | Notes |
|---|------|----|----|----|----:|-------|
| 1 | C2 — Surface truncation in result payload | 5 | 2 | 5 | **4.60** | Worst-case legal harm (silent dropped content) |
| 2 | H1 — Confidence popover + invalid-category rejection | 4 | 3 | 5 | **3.95** | Closes the "Change of Control"-style hallucination hiding |
| 3 | C3 — Pre-flight document stats | 4 | 2 | 4 | **3.80** | Users know what they are about to get |
| 4 | M3 — OCR fallback for scanned PDFs | 4 | 3 | 4 | **3.60** | Prevents silent zero-issue audit on scanned PDFs |
| 5 | C5 — Disambiguate OfflineIndicator (backend health) | 4 | 2 | 3 | **3.45** | Real bug; users can't tell when local server is down |
| 6 | H5 — Domain-rejection explainability | 4 | 2 | 3 | **3.45** | Tied with C5; users need to know why they were bounced |
| 7 | M5 — Confidence feedback loop | 3 | 4 | 5 | **3.30** | Closes the loop on reviewer-corrected data; big effort |
| 8 | C4 — Confirm history delete | 3 | 1 | 3 | **3.20** | Cheap; prevents irreversible data loss |
| 9 | M2 — Streaming partial results | 5 | 4 | 2 | **3.15** | Best perceived-latency win; too large for 3-sprint window |
| 10 | H6 — History clickable / re-openable | 4 | 2 | 2 | **3.10** | Broken feature is worse than missing |
| 11 | H3 — Eliminate always-retry path | 3 | 2 | 3 | **3.00** | Faster audits, less GPU pressure |
| 12 | H7 — Error copy mapping | 3 | 2 | 3 | **3.00** | "Retry" alone is not enough; tells users *what* failed |
| 13 | H4 — Sample document / "Try it" CTA | 4 | 1 | 1 | **2.95** | High first-run impact, very cheap |
| 14 | H2 — End-to-end request id | 2 | 2 | 4 | **2.90** | Mostly internal; big debugging payoff |
| 15 | M4 — Batch upload | 4 | 3 | 1 | **2.55** | Real workflow for paralegals |
| 16 | C1 — Fix duplicate Export button | 3 | 1 | 1 | **2.50** | Trivial; do alongside C4 |
| 17 | M1 — Cross-tab persistence | 3 | 3 | 2 | **2.45** | sessionStorage → localStorage; BroadcastChannel sync |
| 18 | L6 — Confidence calibration dashboard | 2 | 4 | 3 | **2.15** | Internal tool; needs labelled data |
| 19 | M6 — Onboarding tour | 3 | 3 | 1 | **2.10** | H4 partially substitutes |
| 20 | M7 — Mobile/tablet design pass | 3 | 3 | 1 | **2.10** | Defer until a mobile persona is validated |
| 21 | L1 — Theme / dark-mode preference | 1 | 1 | 1 | **1.60** | Always-dark today; not blocking |
| 22 | L2 — Export to PDF | 2 | 2 | 1 | **1.55** | Nice-to-have |
| 23 | L3 — Share / Cite-this affordance | 2 | 3 | 1 | **1.55** | Research-workflow feature |
| 24 | L4 — Localisable error copy | 2 | 3 | 1 | **1.55** | English-only today |
| 25 | L5 — History search | 2 | 2 | 1 | **1.55** | HistoryFilter exists; needs full-text backend hookup |

---

## 3. Recommended 3-sprint plan

### Sprint 1 (Foundation & trust) — 8 days

| Item | Effort | Why first |
|------|-------:|-----------|
| **C2** Surface truncation in result payload | 3 | Worst legal-harm risk; needs the analysis_metadata contract to exist before C3 can build on it. |
| **C5** Disambiguate OfflineIndicator | 2 | Real bug; new indicator also becomes the diagnostic for C2/H7 errors. |
| **C4** Confirm history delete | 1 | Trivial; ship alongside C1. |
| **C1** Fix duplicate Export button | 1 | Trivial; visible bug fix; pairing nicely with C4. |
| Reserve | 1 | Slack for review + bugfix. |

**Outcome after Sprint 1:** no more silent truncation in the response, no more misleading "offline" state, no more accidental history loss, no more duplicate-JSON download.

### Sprint 2 (Transparency & onboarding) — 8 days

| Item | Effort | Why now |
|------|-------:|---------|
| **C3** Pre-flight document stats | 2 | Builds on C2's `analysis_metadata`; users see pages/chars/expected coverage before clicking Run. |
| **H1** Confidence popover + invalid-category rejection | 3 | Engine data is already there; UI surfaces it and the backend filters out-of-vocabulary categories. |
| **H5** Domain-rejection explainability | 2 | High impact, low cost; surfaces the four `*_confidence` signals. |
| **H4** Sample document / "Try it" CTA | 1 | Cheap onboarding win; helps first-time users experience the full pipeline. |
| Reserve | 0 | Tight; risks slipping one item to Sprint 3. |

**Outcome after Sprint 2:** users can preview what an audit will cover, see *why* a finding has its confidence, understand *why* their non-legal document was rejected, and try the system with a sample before bringing real material in.

### Sprint 3 (Quality of life & large-doc) — 8 days

| Item | Effort | Why now |
|------|-------:|---------|
| **M3** OCR fallback for scanned PDFs | 3 | Prevents silent zero-issue audits on scanned contracts; the only "Medium" item in the top 4 of the ranking. |
| **H6** History clickable / re-openable | 2 | The History card is currently a dead-end; needs a `/api/history/{id}/result` endpoint. |
| **H3** Eliminate always-retry path | 2 | Cuts roughly 50-100% of audits by removing the 768→1024 retry; promotes 1024 to the primary call. |
| **H7** Error copy mapping | 1 | With C2's metadata and C5's accurate indicator, error copy can name the actual cause. |
| Reserve | 0 | Tight. |

**Outcome after Sprint 3:** scanned PDFs work end-to-end, history records actually re-open, audits are faster on average, and error toasts name a cause the user can act on.

### Items deliberately *not* in the 3-sprint window

- **M2** Streaming partial results (1-2 weeks). Best perceived-latency win, but too large to fit alongside M3 in Sprint 3. **Sprint 4 candidate.**
- **M5** Confidence feedback loop (1-2 weeks). Big value (closes the loop on hallucination data) but needs a store + UI flow. **Sprint 5-6 candidate**, sequenced after H1 has shipped and the team has seen the popover in production.
- **H2** End-to-end request id. Internal-only, but high debugging payoff. **Sprint 4** if a real latency complaint surfaces, otherwise later.
- **M1** Cross-tab persistence. **Sprint 5** with the persistence refactor.
- **M4** Batch upload. **Sprint 6+**; needs workflow validation.
- **M6** Onboarding tour. **Sprint 5+**; H4 partially covers the gap.
- **M7** Mobile design pass. Defer until a mobile persona is validated.
- **L1-L5** Theme/PDF-export/share/localisation/history-search. Parking lot; revisit quarterly.

---

## 4. Per-item detail (3-sprint items)

### C2 — Surface truncation in result payload
- **Priority:** Critical, ranked #1 (4.60).
- **Effort:** 3 days (1 day backend: thread `was_truncated`, `kept_chars`, `dropped_chars`, `context_utilization_pct`, `pages_seen` through `build_mode_json_payload`; 1 day API type changes; 1 day UI banner on `AuditResultsPage` + `NonLegalDocumentPage` + `PolicyNoticePage`).
- **Dependencies:** None. The data already exists in logs; the change is plumbing it to the response.
- **Expected user benefit:** Users see "We analysed 72% of this document" instead of a complete-looking report that quietly omitted pages. Eliminates the worst legal-tech failure mode (silent content drop).
- **Acceptance test:** A 200-page PDF and a 25MB PDF both surface `was_truncated=true` and a `dropped_chars > 0` banner in the result page.

### C5 — Disambiguate OfflineIndicator
- **Priority:** Critical, ranked #5 (3.45).
- **Effort:** 2 days (half-day backend `/health` ping; half-day hook into `useConnection`; 1 day UI: 3 states → "online", "backend unreachable", "browser offline").
- **Dependencies:** None.
- **Expected user benefit:** When the local FastAPI is down, users see "Backend unreachable" and an actionable message, not a silent "Retry" that fails for unknown reasons.
- **Acceptance test:** Stop the backend; the indicator shows "Backend unreachable" within 5s of the next page load; restart the backend; the indicator clears on the next ping.

### C4 — Confirm history delete
- **Priority:** Critical, ranked #8 (3.20).
- **Effort:** 1 day (use the existing `Toast` system for an "Undo" toast, or a native `confirm()` for now; replace with a styled dialog in Sprint 4 if time).
- **Dependencies:** None.
- **Expected user benefit:** Accidental clicks on the trash icon no longer destroy data.
- **Acceptance test:** Click delete → confirm dialog or 5-second "Undo" toast; cancelling restores the record.

### C1 — Fix duplicate Export button
- **Priority:** Critical, ranked #16 (2.50). Low composite, but trivial to ship in the same PR as C4.
- **Effort:** 0.5-1 day. Either remove the icon button (`ExportButtons.tsx:111-118`) or wire it to a Markdown export.
- **Dependencies:** None.
- **Expected user benefit:** The export row has two distinct actions (JSON + Text) and no mystery third button.
- **Acceptance test:** Only two export buttons visible; both produce the format their label promises.

### C3 — Pre-flight document stats
- **Priority:** Critical, ranked #3 (3.80).
- **Effort:** 2 days (1 day backend: pre-extract + return `{pages, characters, estimated_tokens, will_truncate}` from a new `GET /api/preflight` endpoint; 1 day UI: a card on `UploadContractPage` that updates when a file is dropped).
- **Dependencies:** C2's `analysis_metadata` shape, so the preflight numbers match what the audit will actually use.
- **Expected user benefit:** Users see "47 pages, ~210k characters, will be fully analysed" before they commit. No more click-and-pray.
- **Acceptance test:** Drop a 200-page PDF → preflight card shows correct page count and `will_truncate=false` if it fits, `true` if not. Numbers match the audit's `analysis_metadata` afterwards.

### H1 — Confidence popover + invalid-category rejection
- **Priority:** High, ranked #2 (3.95).
- **Effort:** 3 days (1 day backend: reject or remap categories not in the allowed vocabulary, with a logged reason; 1 day UI: replace the static `ConfidenceBadge` with a clickable popover listing the 9 factors; 0.5 day tests; 0.5 day accessibility).
- **Dependencies:** None. The 9-factor scorer is already in `engines/confidence_engine.py`; the rejection is a small change in `engines/normalization_engine.py` near the title-rewrite pass.
- **Expected user benefit:** A "MEDIUM" badge becomes actionable. Out-of-vocabulary categories like "Change of Control" no longer hide behind a 0.0 category factor and a still-passing `qt_match` factor.
- **Acceptance test:** A prompt-engineered test case that emits `"category": "Change of Control"` results in (a) the issue being dropped or remapped, (b) a `[Normalization] category_out_of_vocabulary` log, (c) the audit composite no longer than the current behaviour. A "MEDIUM" badge in the UI reveals a popover with 9 factor rows.

### H5 — Domain-rejection explainability
- **Priority:** High, ranked #6 (3.45).
- **Effort:** 2 days (1 day UI: surface `domain_confidence`, `legal_keyword_ratio`, `structure_score`, `policy_confidence` on `NonLegalDocumentPage` and `PolicyNoticePage`; 0.5 day copy; 0.5 day tests).
- **Dependencies:** None — `response_type` and the four metrics are already on the response.
- **Expected user benefit:** A user whose contract is bounced to "Non-legal document" can see "domain_confidence: 0.42, structure_score: 0.18" and decide whether to try a different file or rephrase.
- **Acceptance test:** Upload a policy doc; the page shows all four metrics with bars or numbers; the existing "this is not a contract" copy stays.

### H4 — Sample document / "Try it" CTA
- **Priority:** High, ranked #13 (2.95). High first-run impact, very cheap.
- **Effort:** 1 day (commit a 2-paragraph synthetic contract under `samples/`; add a "Try with example" button to `DashboardPage` that calls the same `/ask_file` endpoint with the bundled file).
- **Dependencies:** None. Backend file upload already accepts PDFs/DOCX; can add a `.txt` sample or a tiny PDF.
- **Expected user benefit:** A new user can experience the full pipeline in under a minute without bringing real legal material.
- **Acceptance test:** Fresh user clicks "Try with example"; an audit completes and renders without any file upload step.

### M3 — OCR fallback for scanned PDFs
- **Priority:** Medium, ranked #4 (3.60). Promoted into the 3-sprint plan because of its high risk-reduction score.
- **Effort:** 3 days (1 day backend: integrate an OCR path in `services/pdf_service.py` when the extracted text is empty or below a threshold; 1 day: thread `ocr_used=true/false` and `ocr_engine=tesseract` (or chosen engine) into the response; 0.5 day UI: a "Scanned document — OCR was used; results may be less precise" banner; 0.5 day tests).
- **Dependencies:** C2's `analysis_metadata` shape (to carry `ocr_used`).
- **Expected user benefit:** Scanned contracts no longer return zero issues silently. Users see a banner so they know to expect lower precision.
- **Acceptance test:** Upload a scanned 10-page PDF; the audit completes with a non-empty issue list and an "OCR was used" banner; `analysis_metadata.ocr_used=true` is in the response.

### H6 — History clickable / re-openable
- **Priority:** High, ranked #10 (3.10).
- **Effort:** 2 days (1 day backend: new `GET /api/history/{id}/result` returning the stored `AuditResponse`; 0.5 day UI: `HistoryCard` opens the result; 0.5 day tests).
- **Dependencies:** None; uses the existing `audit_history` table.
- **Expected user benefit:** Clicking a history record actually re-opens the audit, fixing a current dead-end.
- **Acceptance test:** Delete the in-memory state; click a history record; the result page renders the original issues and the original confidence scores.

### H3 — Eliminate always-retry path
- **Priority:** High, ranked #11 (3.00).
- **Effort:** 2 days (1 day config: rework `services/ollama_service.py` so the default generation budget is 1024 and 768 is reserved for short prompts; 0.5 day tests; 0.5 day verification by re-running the Phase 1 benchmark on the same corpus to confirm we do not regress accuracy).
- **Dependencies:** The uncommitted `num_predict=768` change in `ollama_service.py` is already in working copy. Plan locks the new default at 1024 with prompt-size awareness.
- **Expected user benefit:** Most audits finish in one model call instead of two, halving wall time on the unhappy path.
- **Acceptance test:** Phase 1 corpus run after the change shows fewer `[InferenceRetry]` log lines and lower `inference_ms` p50/p95.

### H7 — Error copy mapping
- **Priority:** High, ranked #12 (3.00).
- **Effort:** 1 day (a small error-to-message map in `api.ts` or a new `errorMessages.ts`; add `[Perf]` failure-mode codes; map them to user-readable copy with an action).
- **Dependencies:** C5 (so the indicator and the toast agree on backend health) and C2 (so the result can name the truncation cause).
- **Expected user benefit:** "Retry" alone is replaced by messages like "The document is too large to analyse in one pass. Try splitting it into sections under 100 pages." or "The local analysis server isn't responding. Make sure the backend is running."
- **Acceptance test:** Trigger each known failure mode (timeout, model error, parse failure, backend down, file too large) and confirm the toast and the retry-button copy match the cause.

---

## 5. Out-of-window items (sized for the next planning round)

| Item | Effort | Planned sprint | Notes |
|------|-------:|----------------|-------|
| M2 — Streaming partial results | 4 (1-2 weeks) | Sprint 4 | Best perceived-latency win; needs NDJSON or SSE plumbing on `/ask_file`. |
| H2 — End-to-end request id | 2 (1-2 days) | Sprint 4 if a complaint lands, else 5 | Mostly internal; pairs well with M2. |
| M1 — Cross-tab persistence | 3 (2-3 days) | Sprint 5 | Refactor `persistence.ts` to `localStorage` + `BroadcastChannel`. |
| M5 — Confidence feedback loop | 4 (1-2 weeks) | Sprint 5-6 | Sequence after H1 has been in production. |
| M6 — Onboarding tour | 3 (3-5 days) | Sprint 6 | H4 partially covers the gap for now. |
| M4 — Batch upload | 3 (1 week) | Sprint 6+ | Needs workflow validation. |
| M7 — Mobile/tablet design pass | 3 (1 week) | Sprint 7+ | Defer until a mobile persona is validated. |
| L1, L2, L3, L4, L5, L6 | 1-4 each | Quarterly | Parking lot. |

---

## 6. Risks and assumptions

- **Single-engineer capacity.** If a second engineer joins, Sprint 3 can absorb M2 (streaming) by splitting OCR (M3) and streaming (M2) in parallel. With one engineer, M2 stays in Sprint 4.
- **No benchmark regression.** The H3 change will re-run Phase 1 to confirm the new default doesn't regress accuracy. The plan does not allocate any sprint capacity to ongoing benchmark research, per the brief.
- **PDF service not yet audited in detail.** M3 (OCR) needs a quick pass on `backend/services/pdf_service.py` to confirm the integration point. If the existing extraction is a one-shot pass, OCR may need a fallback module.
- **Persistence refactor is not free.** M1 (cross-tab) may surface other places that assume `sessionStorage`. Plan to keep that in Sprint 5 with a 1-day buffer.
- **Confidence feedback loop (M5) needs a labelled-data strategy.** Without reviewer-corrected findings, the loop is theatre. Sequence M5 after at least one sprint of H1 popover usage.
- **"Offline legal analysis" branding.** The header pill on `UploadContractPage` makes a strong privacy promise. None of the planned items weaken that promise, but a future feature that adds cloud-side processing must update the copy.
