# 10 · Testing

Read in: **Phase 1** (§10.1 for the utils you build), **Phase 4** (§10.2), **Phase 7** (all).

## 10.1 Unit tests (`backend/tests/`)
| File | Must cover |
|---|---|
| `test_money.py` | parse `"1,29,682.00"`, `"Rs. 45,675"`, `"₹ 1,18,000"`, `129682`; paise round-trip; ROUND_HALF_UP on .005 |
| `test_gstin.py` | all 7 seed GSTINs valid; flip last char → invalid; lowercase input normalised; 14-char invalid |
| `test_text.py` | the 5 invoice-number examples in doc 07 §7.4.0 exactly; PO normalisation of `PO 2026/412`, `po-2026-0412`, `PO#2026-0412`; desc_similarity("5-ply corrugated box 18x12x12 in", "Corrugated Box 5 Ply (18x12x12 inch)") ≥ 0.75 |
| `test_matching.py` | F01 3/3 lines paired to correct PO lines; F03 inference scores (0431 = 1.000, 0427 < 0.05) |
| `test_consumption.py` | after seed, PO-2026-0418 line 1 consumed 40, remaining 10; REVIEW ledger rows do not consume |
| `test_checks.py` | one test per check id C01-C17, C20, C21, positive and negative, using small hand-built NormalizedInvoice objects |
| `test_dates.py` | `12/11/2026` → 2026-11-12 (day-first), `10-Nov-26`, `15 Nov 2026` |
| `test_email_draft.py` | F02 draft mentions "10" remaining and "credit note for 4"; HOLD never produces a draft |

## 10.2 Golden pipeline tests (`test_golden.py`) — the core regression suite
- Fixture `golden_extractor`: an `Extractor` implementation that returns `fixtures/golden/{sample_id}.json` for the matching sha256 (map built from the fixture PDFs). Injected via dependency override; **never used outside tests**.
- For each F01-F09: fresh in-memory SQLite, `seed(force=True)`, create a run from the sample, `await execute_run`, assert:
  - decision equals doc 07 §7.9;
  - each "Must FLAG" check has outcome FLAG with that severity;
  - each "Must PASS" check has outcome PASS;
  - all 8 stages are in a terminal status; events seq is contiguous 1..n.
- Sequence tests:
  - F06 then F02 → F02 C15 evidence `remaining == 0`, `over_by == 14`.
  - F01 then F01 again → second run REJECT via C09 exact, evidence contains `same_file_as_run`.
  - F02 then human approve → PO-2026-0418 billing_state `OVERBILLED`, billed_pct 108.
  - F05 approve without `bank_verified` → 422.
- Write a markdown summary to `backend/reports/golden_results.md` (fixture, decision, flags) via a pytest session finish hook.

## 10.3 API tests (`test_api.py`, httpx `AsyncClient` against the app with golden extractor)
Upload validation (txt file → 415, 11 MB → 413), sample run lifecycle, `/api/runs` filters and search, SSE replay with `after_seq`, review endpoint rules, reset gated by DEMO_MODE.

## 10.4 Live LLM check (manual, Phase 3 and before demo)
`python scripts/eval_extraction.py` (doc 06 §6.6). Not part of `pytest` (needs API key, costs quota). Mark any pytest that calls the real API with `@pytest.mark.llm` and skip by default.

## 10.5 Frontend
- `vitest`: `format.ts` (INR formatting incl. lakh/crore compact, dates IST), the run-stream reducer (apply events out of order / duplicated → idempotent by seq).
- Playwright smoke (`frontend/e2e/smoke.spec.ts`), run against local stack: open `/new`, run F01, wait for "Approved" text on run page (timeout 60 s), go to `/`, see the row. Second test: F05 shows "On hold" and the callout text.

## 10.6 Phase 7 exit criteria
`pytest` green (excluding `llm`), `npm run test` green, Playwright smoke green locally, `eval_extraction.py` 100% on critical fields, no console errors in the browser during a full F01-F09 sweep.
