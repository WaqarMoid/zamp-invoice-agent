# PROGRESS

The coding agent keeps this file current. It is the agent's memory across sessions and context resets. Update it **before** and **after** every phase, and whenever you stop.

## Current state
- **Current phase:** P8 Deploy
- **Next action:** Deploy to GitHub (WaqarMoid/zamp-invoice-agent), Neon Postgres, Render backend, and Vercel frontend per docs/11.
- **Live URLs:** frontend: _tbd_ · backend: _tbd_
- **LLM model in use:** gemini-3.5-flash-lite

## Phase checklist
- [x] P0 Bootstrap
- [x] P1 Data layer
- [x] P2 Fixtures
- [x] P3 Extraction
- [x] P4 Pipeline & rules
- [x] P5 API & streaming
- [x] P6a Tokens, fonts, shell, components
- [x] P6b Dashboard
- [x] P6c Process invoice
- [x] P6d Run detail live view
- [x] P6e Purchase orders
- [x] P6f Rules
- [x] P6g Responsive, a11y, polish
- [x] P7 Hardening
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
- Commit: 3004b54
- Notes for next phase: Proceed with Phase 4 Pipeline & rules.

### P4 Pipeline & rules — done
- Built:
  - Rules catalogue & messages: `backend/app/rules/messages.py` (C01..C21 names and fixed stage keys).
  - Greedy line matching and PO inference scoring: `backend/app/rules/matching.py` (greedy line pairing by composite score >= 0.60; candidate PO inference scoring based on line coverage, amount fit, and order date bonus).
  - Checks engine: `backend/app/rules/checks.py` (complete implementation of C01..C21 with exact tolerances, regimes, and SQL NULL-safe candidate filtering).
  - Decision aggregation: `backend/app/rules/actions.py` (strict precedence REJECT > HOLD > REVIEW > APPROVE, headline generation, deduplicated ordered action items, due date calculation, key facts).
  - Vendor email draft generator: `backend/app/rules/email_draft.py` (deterministic second-person template for vendor-fixable flags in REVIEW/REJECT; strictly excluded for HOLD).
  - Human review service: `backend/app/rules/review.py` (enforces 409 status checks, 422 minimum note length, and mandatory bank_verified=True guard for HOLD).
  - SSE event broker: `backend/app/pipeline/events.py` (persists contiguous run_events sequence and publishes to active asyncio queues).
  - Pipeline context & stages: `backend/app/pipeline/context.py` and `backend/app/pipeline/stages/` (ingest, extract, normalize, vendor, duplicates, po_match, reconcile, decide).
  - Pipeline runner: `backend/app/pipeline/runner.py` (sequential runner protected by module-level asyncio.Lock, handles stage lifecycles, error boundaries, check persistence, event broadcasting, and ledger entry generation).
  - Unit & regression tests: `backend/tests/test_matching.py`, `backend/tests/test_consumption.py`, `backend/tests/test_checks.py`, `backend/tests/test_email_draft.py`, and `backend/tests/test_golden.py`.
- Verified:
  - Full golden regression suite (`test_golden.py`): all 9 fixture assertions (F01..F09) pass, matching doc 07 §7.9 expected decisions and flag severities.
  - All 4 sequence tests pass (F06 then F02 zero-balance overrun, F01 duplicate resubmission rejection with same-file hash, F02 human approval causing 108% overrun billing, and F05 bank verification validation).
  - `backend/reports/golden_results.md` generated with full status matrix.
  - `backend/.venv/Scripts/ruff check backend` (clean, 0 errors).
  - `backend/.venv/Scripts/pytest` (all 64 tests passed in 6.07s).
- Commit: 5f937be
- Notes for next phase: Proceed with Phase 5 API & streaming.

### P5 API & streaming — done
- Built:
  - Samples endpoints: `backend/app/api/samples.py` (`GET /api/samples`, `GET /api/samples/{id}/file`).
  - Admin endpoints: `backend/app/api/admin.py` (`POST /api/admin/reset` gated by `DEMO_MODE=true` with foreign key safe deletion sequence).
  - Stats endpoints: `backend/app/api/stats.py` (`GET /api/stats` computing total runs, completed, by_decision, auto_approval_rate, awaiting_action, value_processed in rupees, median duration ms, and 7-day sparkline).
  - Runs endpoints: `backend/app/api/runs.py` (`POST /api/runs` multipart & JSON with mime/magic validation, `GET /api/runs` with filters/search/pagination, `GET /api/runs/{id}`, `GET /api/runs/{id}/events` SSE streaming with `EventSourceResponse`, replay history & live broker subscription, `GET /api/runs/{id}/document`, `GET /api/runs/{id}/pages/{n}.png` rendered via PyMuPDF with LRU memory cache, and `POST /api/runs/{id}/review`).
  - Procurement API alignment: `backend/app/api/procurement.py` and `schemas.py` updated to include exact fields from doc 08 (`net_value`, `billed_net_value`, `billed_pct`, `tax_rate_percent`).
  - Automated verification script: `backend/scripts/verify_phase5.py`.
  - Comprehensive API test suite: `backend/tests/test_api.py`.
- Verified:
  - All 6 acceptance steps from doc 08 §8.5 passed via `backend/scripts/verify_phase5.py`:
    1. `POST /api/admin/reset {"confirm":"RESET"}` -> `200 {"ok":true}`
    2. `POST /api/runs {"sample_id":"F01"}` -> 36 SSE events streamed, `run.completed` with `APPROVE`, `label`: "Approved", `headline`: "Approved for payment. Matches PO-2026-0412 within tolerance. PO-2026-0412 is now fully billed."
    3. F02 -> `REVIEW` (36 events), F05 -> `HOLD` (36 events), F04 -> `REJECT` (36 events).
    4. Re-run F01 -> `REJECT` ("Rejected: Duplicate of SPS/26-27/0512 (approved, dated 2026-11-12, ₹129682.00).")
    5. `GET /api/purchase-orders/PO-2026-0412` -> `billed_pct: 100.0`, `billing_state: FULLY_BILLED`.
    6. Reconnect test: start F03, connect after 2s with `Last-Event-ID: 3` -> events 4..36 received contiguously without gaps (`All event IDs contiguous: True`).
  - Full backend pytest suite: 69/69 passed in 6.77s (`pytest backend/tests`).
  - Ruff formatting & linting: clean (0 errors, `ruff check backend`).
- Commit: 3c5ab95
- Notes for next phase: Proceed with Phase 6 Frontend UI (sub-phases 6a through 6g per doc 09).

### P6a Tokens, fonts, shell, components — done
- Built:
  - Design tokens: `frontend/src/styles/tokens.css` with exact neutrals, semantic tints, and shadows per doc 09 §9.4. Zero gradients, zero neon, zero unassigned hex values.
  - Typography: `frontend/src/styles/globals.css` with self-hosted Raleway, Source Sans 3, and IBM Plex Mono fonts. Added `font-feature-settings: "lnum" 1, "tnum" 1;` for lining figures.
  - TypeScript types: `frontend/src/lib/types.ts` copied verbatim from doc 08 §8.4.
  - API client & formatting: `frontend/src/lib/api.ts` and `frontend/src/lib/format.ts` (INR currency, compact money, relative dates, durations).
  - Shared atomic component library: `frontend/src/components/` (`Button`, `DecisionBadge`, `OutcomeIcon`, `StageMarker`, `KeyValue`, `Money`, `DataTable`, `ConsumptionBar`, `Tabs`, `Disclosure`, `Dialog`, `Toast`, `Skeleton`, `EmptyState`, `Dropzone`, `PageHeader`, `AppShell`).
  - Component gallery: `frontend/src/pages/Gallery.tsx` (`/__gallery`) showcasing all typography tokens, buttons, badges, markers, tables, and dialogs.
- Verified:
  - `npm --prefix frontend run build` (`tsc -b && vite build` built cleanly in 3.54s).
  - All self-hosted font bundles generated and verified.
- Commit: 5bf05bb
- Notes for next phase: Proceed with Phase 6b Dashboard (`/`).

### P6b Dashboard — done
- Built:
  - Dashboard page: `frontend/src/pages/Dashboard.tsx` at `/`.
  - Single-card 5-column KPI strip (Processed, Auto-approved, Awaiting action, Value processed, Median time) with matching typography tokens, lining figures, and responsive layout.
  - Segmented status filters (All, Approved, Needs review, On hold, Rejected) with real-time counts, URL query parameter synchronization, and 240px search input.
  - Runs data table with relative timestamps, mono invoice/PO identifiers, inferred badge, money formatting, decision badges, cleaned headline reasons, durations, and AP review statuses.
  - Dynamic polling (2 s when active runs exist, 15 s when idle).
  - Empty states and loading skeletons.
- Verified:
  - `npm --prefix frontend run build` clean build in 3.40s.
- Commit: a2281c2
- Notes for next phase: Proceed with Phase 6c Process invoice (`/new`).

### P6c Process invoice — done
- Built:
  - Process invoice page: `frontend/src/pages/NewRun.tsx` at `/new` with `/runs/new` redirect.
  - Two-column responsive layout (7/5 grid on desktop, stacked on mobile).
  - Drag-and-drop file upload with format and 10 MB size validation, instant run initiation, and cache toggle checkbox.
  - Grouped sample invoices list (Happy path, Edge cases, More scenarios) with expected decision badges, descriptions, run trigger, and 720px iframe PDF preview dialog.
- Verified:
  - `npm --prefix frontend run build` clean build in 3.09s.
- Commit: 7d6f1f8
- Notes for next phase: Proceed with Phase 6d Run detail live view (`/runs/:id`).

### P6d Run detail live view — done
- Built:
  - Run detail page: `frontend/src/pages/RunDetail.tsx` at `/runs/:id`.
  - SSE real-time stream consumer hook: `frontend/src/lib/useRunStream.ts` with honest 300 ms minimum stage pacing, live millisecond elapsed timer, event log capture, and auto-fallback polling on disconnect.
  - Decision panel: 4 px semantic left rule, display decision heading, headline, ordered action items, key financial facts, AP review approval/rejection modal with 5-character audit note validation and mandatory phone verification confirmation for HOLD invoices.
  - Vendor email draft modal with one-click copy and fraud callout guard.
  - Pipeline 8-stage stepper card with vertical progress connector lines and real duration badges.
  - Detail tabs: Stage checks & evidence disclosure, Extracted fields & line items table, and auto-scrolling execution event log.
  - Diagnostic StageOutputView for all 8 stages (diagnostics, parameters, normalizations, bank comparison, duplicate hits, candidate PO scoring, line consumption, and decision synthesis).
  - 560 px document drawer with rendered PNG page rasterization and original file download link.
- Verified:
  - `npm --prefix frontend run build` clean build in 3.23s.
- Commit: 05c965f
- Notes for next phase: Proceed with Phase 6e Purchase orders (`/purchase-orders`).

### P6e Purchase orders — done
- Built:
  - Purchase orders page: `frontend/src/pages/PurchaseOrders.tsx` at `/purchase-orders`.
  - Open commitments table with cumulative ConsumptionBars (160 px), open/closed status indicator, and net rupee values.
  - Interactive row expansion revealing detailed line breakdown (ordered, billed, remaining, unit price, tax rate) and linked invoice billing history.
  - Master vendor registry card displaying active/inactive status, legal name, GSTIN, masked bank account numbers, and credit terms.
- Verified:
  - `npm --prefix frontend run build` clean build in 3.26s.
- Commit: 62baab4
- Notes for next phase: Proceed with Phase 6f Rules (`/rules`).

### P6f Rules — done
- Built:
  - Rules and policy reference page: `frontend/src/pages/Rules.tsx` at `/rules`.
  - How decisions are made section: decision taxonomy with badges, explanation copy, and strict precedence rule ("Reject outranks Hold, Hold outranks Review").
  - Complete automated check catalogue table for all 21 checks (C01 through C21) with stage categorization, route-to badges, and policy descriptions.
  - System thresholds grid populated dynamically from `/api/config`.
  - Demo data management card with guarded confirmation modal requiring typing `RESET`.
- Verified:
  - `npm --prefix frontend run build` clean build in 3.38s.
- Commit: 0b0aa41
- Notes for next phase: Proceed with Phase 6g Responsive, a11y, polish.

### P6g Responsive, a11y, polish — done
- Built:
  - Accessible 404 page: `frontend/src/pages/NotFound.tsx` aligned with tokens and anti-slop rules.
  - Keyboard navigation: `j` / `k` (or arrow keys) stage stepping and `Escape` drawer close in `RunDetail.tsx`.
  - Global visible focus rings (`outline: 2px solid var(--focus); outline-offset: 2px`) and `prefers-reduced-motion` handling in `globals.css`.
  - Strict color isolation check: zero hex colors outside `tokens.css`.
  - Accessible aria attributes, live status regions, and Indian numbering currency formatting.
- Verified:
  - `npm --prefix frontend run build` clean build in 3.05s.
- Commit: 810876c
- Notes for next phase: Proceed with Phase 7 Hardening per doc 10.

### P7 Hardening — done
- Built:
  - Frontend unit test suite: `frontend/src/tests/format.test.ts` (10 tests covering INR money, compact lakh/crore formatting, ISO dates, relative times, and durations).
  - Stream reducer idempotency test: `frontend/src/tests/stream_reducer.test.ts` (verified deduplication and out-of-order event resilience).
  - Playwright end-to-end smoke test spec: `frontend/e2e/smoke.spec.ts` (F01 happy path to Approved, F05 fraud alert to On hold with phone verification callout).
  - Dedicated configuration for test runners: `frontend/vitest.config.ts` and `frontend/playwright.config.ts`.
- Verified:
  - `npm --prefix frontend run test` (11/11 Vitest tests passed in 512ms).
  - `backend/.venv/Scripts/pytest backend/tests` (69/69 Pytest tests passed in 7.25s).
  - `backend/.venv/Scripts/ruff check backend` (clean, 0 errors).
  - `npm --prefix frontend run build` (clean production build in 3.43s).
- Commit: dbc24a4
- Notes for next phase: Proceed with Phase 8 Deploy per docs/11.

## Handoff notes (for a fresh session with empty context)
- P0 through P5 are complete and 100% verified (69/69 pytest tests passing).
- API backend is fully operational: sample catalog, run execution, live SSE streaming with disconnect replay, document page rasterization, decision synthesis, human review override, ledger recording, and procurement analytics.
- Next step: Phase 6a (Design tokens, fonts, layout shell, shared component library, and `/__gallery` page).

## Deviations log
- **Model selection**: Switched default LLM from `gemini-2.5-flash` to `gemini-3.5-flash-lite`. Gemini Developer API Free Tier capped `gemini-2.5-flash` at 20 requests per day (`RESOURCE_EXHAUSTED`). `gemini-3.5-flash-lite` provides high free-tier limits, fast response times (2-4s), and achieved 100% extraction accuracy on both text and vision/scanned invoices.
- **Gemini response schema**: Pydantic's `dict[str, float]` causes `additionalProperties` error on Google AI Studio API. Replaced with `MirrorFieldConfidence` explicit float fields.
- **Duplicate query SQL NULL safety**: In SQL, `run_id != current_run_id` evaluates to NULL/false when `run_id` is NULL (such as seed ledger rows). Updated `check_c09` filter to `or_(InvoiceLedger.run_id.is_(None), InvoiceLedger.run_id != current_run_id)` so prior seed invoices are correctly checked.
- **Seed wipe order**: Corrected deletion sequence in `seed(db, force=True)` to delete `LedgerLine` and `InvoiceLedger` before `Run` to satisfy SQLite foreign key constraints.

## Waiting on Waqar (HUMAN steps)
<!-- None at this time. All API keys and environment configurations are in place. -->
