# 08 · API contract

Read in: **Phase 5** (all). Phase 6 (types only: copy §8.4 into `frontend/src/lib/types.ts`).

Base path `/api`. JSON everywhere except file uploads/downloads and SSE. Errors: `{"error": {"code": "SNAKE_CASE", "message": "Human sentence."}}` with proper HTTP status. CORS: allow origins from env `ALLOWED_ORIGINS` (comma-separated; local default `http://localhost:5173`), methods GET/POST, headers `Content-Type, Last-Event-ID`.

## 8.1 Endpoints

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/api/health` | | `200 {"status":"ok","db":"ok","llm_configured":bool,"model":"...","version":"<git sha or 'dev'>"}` |
| GET | `/api/config` | | Thresholds and policies from Settings: `{price_tolerance_pct, price_tolerance_abs_inr, rounding_tolerance_inr, extraction_min_confidence, vendor_name_match_min, line_match_min_score, po_infer_min_score, po_infer_min_margin, near_dup_window_days, max_invoice_age_days, auto_approve_inferred_po, buyer:{name,gstin}, llm:{provider, model}, demo_mode}` |
| GET | `/api/samples` | | `Sample[]` (doc 05 §5.5) |
| GET | `/api/samples/{id}/file` | | `application/pdf` |
| POST | `/api/runs` | **either** `multipart/form-data` with `file` (+ optional `use_cache` = "true"/"false") **or** JSON `{"sample_id":"F01","use_cache":true}` | `202 {"run_id":"uuid","status":"QUEUED"}`. Validation: mime in pdf/png/jpeg (check magic bytes too: `%PDF`, PNG sig, JPEG `FFD8`), size ≤ 10 MB → else `415 UNSUPPORTED_FILE` / `413 FILE_TOO_LARGE`. Unknown sample → `404`. |
| GET | `/api/runs` | `decision`=APPROVE\|REVIEW\|HOLD\|REJECT (optional), `status`, `q` (matches vendor_name, invoice_number, po_number, case-insensitive substring), `limit` (default 50, max 200), `offset` | `{"items": RunSummary[], "total": int}` newest first |
| GET | `/api/runs/{id}` | | `RunDetail` |
| GET | `/api/runs/{id}/events` | header `Last-Event-ID` optional, or query `after_seq` | SSE stream (§8.3) |
| GET | `/api/runs/{id}/document` | | original file bytes with its mime |
| GET | `/api/runs/{id}/pages/{n}.png` | `n` 1-based, `?dpi=110` default | PNG render (PyMuPDF). Cache in memory LRU(64). |
| POST | `/api/runs/{id}/review` | `{"action":"approve"\|"reject","note":str,"reviewer":str?,"bank_verified":bool?}` | `200 RunDetail`. `409 REVIEW_NOT_ALLOWED` if not pending. `422` on validation (doc 07 §7.8). |
| GET | `/api/stats` | | `Stats` |
| GET | `/api/vendors` | | `Vendor[]` (bank account masked) |
| GET | `/api/purchase-orders` | | `PurchaseOrder[]` with consumption |
| GET | `/api/purchase-orders/{po}` | | `PurchaseOrder` + `invoices: LedgerEntry[]` (all ledger rows for this PO, any status) |
| POST | `/api/admin/reset` | `{"confirm":"RESET"}` | Only if `DEMO_MODE=true` else `403`. Re-seeds (force). `200 {"ok":true}` |

## 8.2 Behaviour notes
- `POST /api/runs` creates document (if same sha256 + bytes already stored, still create a new `documents` row; simplicity over dedup), run row, 8 `run_stages` rows (PENDING), commits, then `asyncio.create_task(execute_run(id))`.
- Runs execute one at a time (doc 07 §7.7 lock). A second run waits in `QUEUED`; UI shows "Queued".
- `GET /api/runs/{id}` must be complete at any moment (works while running): stages with statuses, checks so far, result if done.

## 8.3 Server-Sent Events
Use `sse-starlette` `EventSourceResponse`. Headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

Algorithm per connection:
1. `last = int(Last-Event-ID or after_seq or 0)`.
2. Replay all `run_events` with `seq > last` from DB, in order.
3. Subscribe to the in-memory broker (`backend/app/pipeline/events.py`: `dict[run_id, set[asyncio.Queue]]`) and forward new events. To avoid a gap between replay and subscribe: subscribe **first**, then replay, then drop queued events with `seq ≤` the last replayed seq.
4. Send a comment ping `: ping` every 15 s.
5. After sending `run.completed` or `run.failed`, close the stream.
6. If the run is already finished on connect: replay everything, then close.

Every event: `id: {seq}`, `event: {type}`, `data: {json}`. Event types and `data`:

| type | data |
|---|---|
| `run.started` | `{run_id, started_at}` |
| `stage.started` | `{stage_key, position, label, started_at}` |
| `check.result` | `{stage_key, check_id, name, outcome, severity, message}` |
| `stage.completed` | `{stage_key, position, status, summary, duration_ms, output}` (`output` is the stage output, masked) |
| `run.completed` | `{decision, label, headline, duration_ms}` |
| `run.failed` | `{message}` |
| `run.reviewed` | `{review_status, reviewer, note, reviewed_at}` (emitted later; clients connected at that time get it, the stream is not reopened for it) |

Events are persisted to `run_events` **before** being published.

## 8.4 Response types (TypeScript, copy verbatim to `frontend/src/lib/types.ts`)

```ts
export type Decision = "APPROVE" | "REVIEW" | "HOLD" | "REJECT";
export type RunStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
export type StageStatus = "PENDING" | "RUNNING" | "PASSED" | "FLAGGED" | "FAILED" | "SKIPPED";
export type Outcome = "PASS" | "INFO" | "FLAG" | "SKIP";
export type Severity = "REVIEW" | "HOLD" | "REJECT";
export type StageKey = "ingest" | "extract" | "normalize" | "vendor" | "duplicates" | "po_match" | "reconcile" | "decide";

export interface Sample { id: string; filename: string; title: string; scenario: string; description: string; expected_decision: Decision; group: "Happy path" | "Edge cases" | "More scenarios"; }

export interface RunSummary {
  id: string; short_id: string; status: RunStatus; current_stage: StageKey | null;
  decision: Decision | null; label: string | null; headline: string | null;
  vendor_name: string | null; invoice_number: string | null; po_number: string | null; po_method: "explicit" | "inferred" | "none" | null;
  grand_total: string | null; flags_count: number; sample_id: string | null; filename: string;
  review_status: "NOT_REQUIRED" | "PENDING" | "APPROVED" | "REJECTED";
  created_at: string; completed_at: string | null; duration_ms: number | null;
}

export interface Check { stage_key: StageKey; check_id: string; name: string; outcome: Outcome; severity: Severity | null; message: string; evidence: Record<string, unknown>; }

export interface Stage { stage_key: StageKey; position: number; label: string; description: string; status: StageStatus; summary: string | null; started_at: string | null; completed_at: string | null; duration_ms: number | null; output: Record<string, unknown> | null; checks: Check[]; }

export interface DecisionResult {
  decision: Decision; label: string; headline: string;
  reasons: { check_id: string; name: string; severity: Severity; message: string }[];
  recommended_actions: string[]; payment_block: boolean; due_date: string | null;
  vendor_email: { subject: string; body: string } | null;
  key_facts: { vendor: string | null; po: string | null; po_method: string; invoice_number: string | null; invoice_date: string | null; grand_total: string | null };
}

export interface RunDetail extends RunSummary {
  document: { filename: string; mime: string; size_bytes: number; page_count: number; has_text_layer: boolean; sha256: string };
  use_cache: boolean; extraction_method: string | null;
  stages: Stage[];
  result: { extraction: Record<string, unknown> | null; normalized: Record<string, unknown> | null; decision: DecisionResult } | null;
  reviewer: string | null; review_note: string | null; reviewed_at: string | null;
}

export interface Stats {
  total_runs: number; completed_runs: number;
  by_decision: Record<Decision, number>;
  auto_approval_rate: number;          // APPROVE / completed, 0..1
  awaiting_action: number;             // review_status == PENDING
  value_processed: string;             // sum grand_total of completed runs, rupees
  median_duration_ms: number | null;
  runs_last_7_days: { date: string; count: number }[];
}

export interface Vendor { vendor_id: string; legal_name: string; gstin: string; state_code: string; status: "ACTIVE" | "INACTIVE"; bank_name: string; bank_ifsc: string; bank_account_masked: string; payment_terms_days: number; }

export interface POLine { line_no: number; description: string; hsn_sac: string; uom: string; quantity: string; unit_price: string; tax_rate_percent: string; billed_quantity: string; remaining_quantity: string; }

export interface PurchaseOrder {
  po_number: string; vendor_id: string; vendor_name: string; po_date: string; valid_until: string; status: "OPEN" | "CLOSED" | "CANCELLED";
  net_value: string; billed_net_value: string; billed_pct: number;   // 0..100+, can exceed 100 after an override
  billing_state: "UNBILLED" | "PARTIALLY_BILLED" | "FULLY_BILLED" | "OVERBILLED";
  lines: POLine[];
}

export interface LedgerEntry { id: number; source: "seed" | "run"; run_id: string | null; invoice_number: string | null; invoice_date: string | null; grand_total: string; status: "APPROVED" | "IN_REVIEW" | "ON_HOLD" | "REJECTED"; created_at: string; }
```

Stage `label`/`description` come from doc 07 §7.1 (served by the API so the UI never hardcodes copy twice).

## 8.5 Phase 5 acceptance (run with curl, paste outputs into PROGRESS.md)
1. `POST /api/admin/reset` → ok.
2. `POST /api/runs {"sample_id":"F01"}` → run_id; `curl -N /api/runs/{id}/events` shows 8 stage.started/completed pairs and `run.completed` with `APPROVE`.
3. Same for F02 → REVIEW, F05 → HOLD, F04 → REJECT.
4. Re-run F01 → REJECT (exact duplicate of the first F01, same file hash note).
5. `GET /api/purchase-orders/PO-2026-0412` → billed_pct 100.
6. Reconnect test: start F03, connect SSE after 2 s with `Last-Event-ID: 3`, verify events 4..n arrive with no gaps.
