# PROGRESS

The coding agent keeps this file current. It is the agent's memory across sessions and context resets. Update it **before** and **after** every phase, and whenever you stop.

## Current state
- **Current phase:** P4 Pipeline & rules
- **Next action:** Implement rules engine, stages C01..C21, matching, reconciliation, runner, and golden pipeline tests per doc 07.
- **Live URLs:** frontend: _tbd_ · backend: _tbd_
- **LLM model in use:** gemini-3.5-flash-lite

## Phase checklist
- [x] P0 Bootstrap
- [x] P1 Data layer
- [x] P2 Fixtures
- [x] P3 Extraction
- [ ] P4 Pipeline & rules
- [ ] P5 API & streaming
- [ ] P6a Tokens, fonts, shell, components
- [ ] P6b Dashboard
- [ ] P6c Process invoice
- [ ] P6d Run detail live view
- [ ] P6e Purchase orders
- [ ] P6f Rules
- [ ] P6g Responsive, a11y, polish
- [ ] P7 Hardening
- [ ] P8 Deploy
- [ ] P9 Demo prep
- [ ] README rewritten for reviewers

## Phase log
### P0 Bootstrap — done
- Built:
  - Repository structure conforming to docs/03 §3.3.
  - Backend setup with Python 3.12 venv, dependencies pinned per docs/03 §3.2, FastAPI app, config with all business thresholds from docs/07 §7.3, `/api/health` and `/api/config` endpoints, and render.yaml.
  - Frontend scaffolded with Vite, React 18, TypeScript, Tailwind CSS v4, Lucide icons, fonts, AppShell placeholder, router, and page placeholders.
  - Git repository initialized on branch main, .gitignore configured.
- Verified:
  - `backend/.venv/Scripts/pytest backend/tests/test_health.py` (2 passed)
  - `backend/.venv/Scripts/ruff check backend` (clean, all checks passed)
  - `npm --prefix frontend run build` (built cleanly in 5.07s)
- Commit: 84b44a7
- Notes for next phase: Proceed with Phase 1 Data layer.

### P1 Data layer — done
- Built:
  - Rules utilities: `backend/app/rules/money.py` (Decimal money parsing, paise round-trip, quantize with ROUND_HALF_UP), `gstin.py` (checksum algorithm, regex, state code extraction), `text.py` (invoice and PO number tokenization/normalization per doc 07 §7.4.0, description similarity via rapidfuzz), `dates.py` (robust day-first date parsing with ISO preservation), `consumption.py` (PO line consumption computation from APPROVED ledger rows).
  - Database layer: `backend/app/db.py` (engine supporting SQLite pragma foreign_keys=ON and Neon PostgreSQL with psycopg connection pooling), `models.py` (all 11 ORM models per doc 04 §4.2), `schemas.py` (Pydantic domain models for extraction, normalization, decisions, and API responses).
  - Seed loader: `backend/app/seed.py` (loads buyer, 6 vendors, 8 POs with lines, and 3 prior approved invoices into ledger; supports force wipe).
  - API endpoints: `backend/app/api/procurement.py` (`/api/vendors` with masked bank accounts `••••` + last 4, `/api/purchase-orders` with cumulative consumption and billing states, `/api/purchase-orders/{po}` with detailed ledger invoice history).
- Verified:
  - `backend/.venv/Scripts/ruff check backend` (clean, all checks passed)
  - `backend/.venv/Scripts/pytest` (17 passed in 1.09s, covering test_money, test_gstin, test_text, test_dates, test_health, test_procurement)
  - SQLite creation and seeding verified (6 vendors, 8 POs, 3 prior invoices)
- Commit: 96002f1
- Notes for next phase: Proceed with Phase 2 Fixtures.

### P2 Fixtures — done
- Built:
  - Fixture generator: `backend/scripts/generate_fixtures.py` supporting deterministic ReportLab generation across classic, modern, and compact layouts, Indian numbering formats, amount in words, bank details, and footer notes.
  - Scanned simulation for F03: 200 DPI rasterization, +0.6° rotation, Gaussian noise (σ=6), paper tint, Gaussian blur (0.4), and zero-text PDF rebuild.
  - Golden extraction JSONs: generated for all 9 fixtures (`backend/fixtures/golden/F0X.json`), validating 100% against `ExtractedInvoice` schema.
  - Visual inspection of PNG previews:
    - **F01 (Classic)**: Boxed header, clear vendor block and invoice metadata, full grid table with right-aligned rupee amounts, right-aligned totals block, amount in words, bank details box, and signature block. Everything fits single A4 page cleanly with zero overlap.
    - **F03 (Compact / Scanned)**: Realistic scanned document texture with subtle rotation (+0.6°), natural grain, paper tint, Order Ref printed in place of PO No., compact dense line item table, and split CGST/SGST without rate. Text layer verified to have exactly 0 characters.
    - **F05 (Classic / Bank Change Alert)**: Distinct highlighted red-bordered box (`#E53E3E`) with bold warning regarding new remittance bank account details. Table and totals aligned cleanly.
    - **F07 (Compact / Tax-Inclusive)**: Line item marked "(incl. GST 5%)", subtotal ₹45,675.00, detailed italic breakdown line ("Includes CGST 2.5% Rs. 1,087.50 and SGST 2.5% Rs. 1,087.50"), Grand Total ₹45,675.00, and explicit tax-inclusive footer note.
- Verified:
  - `backend/.venv/Scripts/ruff check backend` (clean, all checks passed)
  - `backend/.venv/Scripts/pytest` (21 passed in 1.93s, including `test_fixtures.py`)
  - All 9 PDFs exist in `backend/fixtures/` and 9 golden JSONs exist in `backend/fixtures/golden/`
- Commit: 1a69890
- Notes for next phase: Proceed with Phase 3 Extraction.

### P3 Extraction — done
- Built:
  - System prompt: `backend/app/extraction/prompt.py` (verbatim from doc 06 §6.3 with layout instructions).
  - Text layer extraction: `backend/app/extraction/text_layer.py` (layout=True extraction via pdfplumber, page break markers, 30k char truncation, text layer detection).
  - Vision rendering: `backend/app/extraction/render.py` (PyMuPDF 200 DPI rendering to PNG bytes, 2400px downscaling).
  - Heuristic fallback: `backend/app/extraction/heuristic.py` (regex + table parser emitting confidence 0.60).
  - LLM client: `backend/app/extraction/llm_client.py` (Protocol) and `backend/app/extraction/gemini.py` (GeminiExtractor using `google-genai` SDK with `MirrorInvoice` float-safe schema, temperature=0, structured JSON output, post-parse guards, and 3 retry attempts with exponential backoff).
  - Model selection: Switched default from `gemini-2.5-flash` to `gemini-3.5-flash-lite` because Google AI Studio enforces an aggressive 20 RPD cap on `gemini-2.5-flash` Free Tier, whereas `gemini-3.5-flash-lite` provides generous free tier quotas, rapid 2-4s latency, and full multimodal vision support for scanned PDFs.
  - Cache layer: `backend/app/extraction/cache.py` (SHA-256 caching for `ExtractionCache`).
  - Evaluation tool: `backend/scripts/eval_extraction.py` (evaluates critical fields across F01..F09 against golden JSONs and outputs markdown report).
  - Unit tests: `backend/tests/test_extraction_utils.py` and `backend/tests/test_extraction_cache.py`.
- Verified:
  - `eval_extraction.py` executed live with `gemini-3.5-flash-lite`: 100.0% accuracy across F01..F09 (90/90 checks passed). Detailed report saved at `backend/reports/extraction_eval.md`.
  - Scanned invoice F03 (0 text characters) was rendered to 200 DPI PNG and read via the multimodal vision path with 10/10 accuracy.
  - Extraction caching verified with live test: second invocation returns cache hit with `cached=True`.
  - `backend/.venv/Scripts/ruff check backend` (clean, all checks passed).
  - `backend/.venv/Scripts/pytest` (26 passed in 2.27s).
- Commit: (recorded below)
- Notes for next phase: Proceed with Phase 4 Pipeline & rules.

### P4 Pipeline & rules — in progress
- Plan:
  - Implement rules messages (`messages.py`) for C01..C21.
  - Implement PO line matching and PO inference scoring (`matching.py`).
  - Implement all 21 checks C01..C21 (`checks.py`) returning CheckResult schemas.
  - Implement decision resolution (`actions.py`) and email draft generator (`email_draft.py`).
  - Implement SSE event broker (`events.py`), context (`context.py`), stages (`stages/`), and pipeline runner (`runner.py`).
  - Write test suite `test_golden.py` verifying all 9 fixtures (F01..F09) and sequential balance tests against expected decisions per doc 07, producing `backend/reports/golden_results.md`.

## Handoff notes (for a fresh session with empty context)
- P0, P1, P2, and P3 are completely done and all tests pass (26/26 pytest).
- Model in use: `gemini-3.5-flash-lite` configured in `backend/.env`, `app/config.py`, and `render.yaml`.
- Extraction evaluation report at `backend/reports/extraction_eval.md` achieves 100% (90/90 checks).
- Ready for Phase 4 implementation (rules engine, stages, runner, golden tests).

## Deviations log
- **Model selection**: Switched default LLM from `gemini-2.5-flash` to `gemini-3.5-flash-lite`. Gemini Developer API Free Tier capped `gemini-2.5-flash` at 20 requests per day (`RESOURCE_EXHAUSTED`). `gemini-3.5-flash-lite` has higher free-tier limits, fast response times (2-4s), and achieved 100% extraction accuracy on both text and vision/scanned invoices.
- **Gemini response schema**: Pydantic's `dict[str, float]` causes `additionalProperties` error on Google AI Studio API. Replaced with `MirrorFieldConfidence` explicit float fields.

## Waiting on Waqar (HUMAN steps)
<!-- None at this time. All API keys and environment configurations are in place. -->
