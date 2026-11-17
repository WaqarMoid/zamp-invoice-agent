# PROGRESS

The coding agent keeps this file current. It is the agent's memory across sessions and context resets. Update it **before** and **after** every phase, and whenever you stop.

## Current state
- **Current phase:** P3 Extraction (not started)
- **Next action:** Read docs/06, configure Gemini LLM extraction client, prompt, fallback heuristic, extraction cache, and evaluate accuracy with eval_extraction.py.
- **Live URLs:** frontend: _tbd_ · backend: _tbd_
- **LLM model in use:** _tbd (set in P3)_

## Phase checklist
- [x] P0 Bootstrap
- [x] P1 Data layer
- [x] P2 Fixtures
- [ ] P3 Extraction
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
- Commit: pending commit
- Notes for next phase: Proceed with Phase 3 Extraction.

## Handoff notes (for a fresh session with empty context)
- P0, P1, and P2 are complete and all 21 pytest tests pass.
- Generated PDFs and golden files live in `backend/fixtures/` and `backend/fixtures/golden/`.
- Visual inspection verified for F01, F03, F05, F07.
- Ready to start Phase 3 Extraction (doc 06).

## Handoff notes (for a fresh session with empty context)
- P0 and P1 are complete and all tests pass (17/17 pytest).
- DB models in `backend/app/models.py`, seed script in `backend/app/seed.py`.
- Rules utilities in `backend/app/rules/` (money, gstin, text, dates, consumption).
- Procurement endpoints active in `backend/app/api/procurement.py`.
- Generating F01..F09 invoice PDFs and golden JSONs.

## Deviations log
<!-- Any place the implementation differs from docs/, with reason. Spec gaps you resolved and how. -->

## Waiting on Waqar (HUMAN steps)
<!-- e.g. "GEMINI_API_KEY needed in backend/.env", "gh auth login", Render/Vercel/Neon clicks from docs/11 -->
