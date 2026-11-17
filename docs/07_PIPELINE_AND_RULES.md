# 07 · Pipeline stages, checks and decision rules

Read in: **Phase 4** (all), Phase 6 (sections 7.1 and 7.6 only, for UI copy).
This is the most important document. Every number, threshold and message here is final. Do not invent new rules; if something is genuinely undefined, add it to `PROGRESS.md › Deviations log` and pick the most conservative behaviour (route to REVIEW).

---

## 7.1 Stages (fixed order, fixed keys)

| # | `stage_key` | UI label | What it does (one-sentence UI description) |
|---|---|---|---|
| 1 | `ingest` | Ingest | Stores the file, fingerprints it and checks whether it has a text layer. |
| 2 | `extract` | Extract | Reads the invoice into structured fields using the text layer or vision. |
| 3 | `normalize` | Normalize & validate | Cleans dates, amounts and IDs, then checks the document is complete and adds up. |
| 4 | `vendor` | Verify vendor | Identifies the vendor in the master and checks status, GSTIN and bank details. |
| 5 | `duplicates` | Detect duplicates | Compares against every invoice already in the ledger. |
| 6 | `po_match` | Match PO | Finds the purchase order, explicitly or by inference, and pairs invoice lines to PO lines. |
| 7 | `reconcile` | Reconcile | Checks price, quantity against what is still unbilled on the PO, and tax. |
| 8 | `decide` | Decide | Combines every check into one decision with reasons and next actions. |

### Stage status values
`PENDING` → `RUNNING` → one of `PASSED` | `FLAGGED` | `FAILED` | `SKIPPED`.

- `PASSED`: stage ran, all its checks are PASS / INFO / SKIP.
- `FLAGGED`: stage ran, at least one check is FLAG.
- `FAILED`: the stage itself crashed or could not produce output (e.g. extraction returned nothing). The run continues only if later stages can run; stages that need the missing output are `SKIPPED` with summary `"Skipped: needs output from <stage label>"`.
- `SKIPPED`: prerequisites missing.

**The pipeline never short-circuits on a REJECT/HOLD flag.** All stages run so the reviewer sees the full picture. The only early stop: if `extract` FAILS, stages 3-7 are SKIPPED and `decide` produces `REVIEW` with reason `"Could not read the invoice. Process manually."`.

### Stage summary line
Every stage, on completion, writes a one-line `summary` (max 90 chars, no em dashes). Exact templates are in 7.5 per stage.

---

## 7.2 Check model

Every check produces a `CheckResult`:

```
check_id: str          # "C01".."C21"
stage_key: str
name: str              # short UI name, from table 7.3
outcome: PASS | INFO | FLAG | SKIP
severity: null | REVIEW | HOLD | REJECT   # required iff outcome == FLAG
message: str           # human sentence, templates in 7.3
evidence: dict         # machine data shown in "Evidence" disclosure
```

Meaning:
- `PASS`: rule satisfied.
- `INFO`: noteworthy, no action required (e.g. "PO line now fully billed").
- `FLAG`: rule violated; `severity` decides routing.
- `SKIP`: could not evaluate (missing input). SKIP never routes on its own; the missing input is caught by C01.

### Decision precedence
`decision = max(severity of all FLAG checks)` using order `REJECT > HOLD > REVIEW`. No FLAG → `APPROVE`.

| Decision | UI label | Meaning | Ledger status | Consumes PO? |
|---|---|---|---|---|
| APPROVE | Approved | Auto-approved, scheduled for payment | APPROVED | Yes |
| REVIEW | Needs review | AP must decide; money not at risk of fraud | IN_REVIEW | No (until human approves) |
| HOLD | On hold | Fraud / identity risk. Payment blocked until verified out-of-band | ON_HOLD | No (until human approves) |
| REJECT | Rejected | Invoice is invalid for this company and should not be paid | REJECTED | No |

---

## 7.3 Check catalogue (all thresholds final)

Config values live in `backend/app/config.py` (`Settings`) with these defaults:

```
PRICE_TOLERANCE_PCT = 1.0          # percent
PRICE_TOLERANCE_ABS_INR = 1000.00  # rupees; line tolerance = min(pct, abs)
ROUNDING_TOLERANCE_INR = 1.00
EXTRACTION_MIN_CONFIDENCE = 0.80
VENDOR_NAME_MATCH_MIN = 88         # rapidfuzz token_set_ratio, 0-100
LINE_MATCH_MIN_SCORE = 0.60
PO_INFER_MIN_SCORE = 0.75
PO_INFER_MIN_MARGIN = 0.15
NEAR_DUP_WINDOW_DAYS = 30
MAX_INVOICE_AGE_DAYS = 365
AUTO_APPROVE_INFERRED_PO = False
BUYER_STATE_CODE = "29"
```

| ID | Stage | Name (UI) | Rule | Outcome / severity | Message template |
|---|---|---|---|---|---|
| C01 | normalize | Required fields | Required: `vendor_name`, `invoice_number`, `invoice_date`, `grand_total`, ≥1 line item. | Any missing → FLAG REVIEW | `Missing {fields_csv}. Request a corrected tax invoice.` / PASS: `All required fields present.` |
| C02 | normalize | Extraction confidence | For each of `vendor_name, vendor_gstin, invoice_number, invoice_date, grand_total, po_number, line_items`: if the value is present and `field_confidence[field] < 0.80`. | FLAG REVIEW | `Low read confidence on {fields_csv} ({min_conf:.0%}). Verify against the document.` / PASS: `All key fields read with ≥80% confidence.` |
| C03 | normalize | Billed to us | `buyer_gstin` equals our GSTIN `29AAACK4521M1ZD`. | Mismatch → FLAG REJECT. Missing → FLAG REVIEW. | `Invoice is billed to GSTIN {buyer_gstin}, not Kestrel Foods.` / `Buyer GSTIN not printed.` / PASS `Billed to Kestrel Foods (29AAACK4521M1ZD).` |
| C04 | normalize | Arithmetic | (a) every line: `abs(qty*unit_price - line_amount) ≤ 1.00`; (b) `abs(sum(line_amount) - subtotal) ≤ 1.00`; (c) tax-exclusive: `abs(net + total_tax - grand_total) ≤ 1.00`; tax-inclusive: `abs(sum(line_amount) - grand_total) ≤ 1.00`. | Any fail → FLAG REVIEW | `Totals do not add up: {which} off by ₹{diff}.` / PASS `Lines, subtotal, tax and total reconcile.` |
| C05 | vendor | Vendor status | Matched vendor `status == ACTIVE`. | INACTIVE → FLAG REJECT | `{vendor} was deactivated on {date}. Do not pay.` / PASS `{vendor} is an active approved vendor.` |
| C06 | vendor | Vendor identity | See 7.4.1. | Unknown vendor → FLAG REJECT. GSTIN on invoice ≠ master GSTIN, or invalid GSTIN checksum → FLAG HOLD. | `No approved vendor matches "{name}" / {gstin}. Onboard the vendor first.` / `Invoice GSTIN {inv} does not match master GSTIN {master} for {vendor}.` / `GSTIN {gstin} fails checksum validation.` / PASS `Matched {vendor} by {method}.` |
| C07 | vendor | Bank details | If invoice prints bank details: compare IFSC (uppercase) and account number (digits only) with master. | Either differs → FLAG HOLD. Not printed → INFO. | `Bank details on invoice ({ifsc} / ••••{last4}) differ from vendor master ({m_ifsc} / ••••{m_last4}). Verify by phone with the contact on file before paying.` / INFO `No bank details printed. Payment will use the vendor master account.` / PASS `Bank details match the vendor master.` |
| C08 | normalize | Invoice date | Date not in future (vs server date IST), not older than 365 days, not before PO date (evaluated in po_match, see C20). | Future / too old → FLAG REVIEW | `Invoice date {date} is in the future.` / `Invoice date {date} is more than 365 days old.` / PASS `Invoice date {date} is valid.` / SKIP if no date. |
| C09 | duplicates | Duplicate check | See 7.4.2. | Exact → FLAG REJECT. Near → FLAG REVIEW. No invoice number → exact part SKIPPED, near part still runs; if nothing found outcome is INFO. | see 7.4.2 |
| C10 | po_match | PO identified | See 7.4.3. | Explicit found → PASS. Inferred → FLAG REVIEW (or PASS if `AUTO_APPROVE_INFERRED_PO`). Printed but not found / not inferable → FLAG REVIEW. | see 7.4.3 |
| C11 | po_match | PO belongs to vendor | `po.vendor_id == vendor.vendor_id`. | Mismatch → FLAG REVIEW | `{po} belongs to {po_vendor}, not {vendor}.` / PASS `{po} is issued to {vendor}.` |
| C12 | po_match | PO status | `po.status == OPEN`. | CLOSED or CANCELLED → FLAG REJECT | `{po} is {status}. No further invoices can be paid against it.` / PASS `{po} is open.` |
| C13 | po_match | Line matching | See 7.4.4. Any invoice line unmatched → FLAG REVIEW. PO lines not on invoice → INFO only. | | `{n} invoice line(s) not on {po}: {descs}.` / PASS `All {n} invoice lines matched to {po} lines.` |
| C14 | reconcile | Price variance | For each matched line: `expected = inv_qty * po_unit_price`; `actual = inv_net_line_amount`; `tolerance = min(expected * 0.01, 1000.00)`; `actual - expected > tolerance` → violation. `actual < expected - tolerance` → INFO (under-billed). | Violation → FLAG REVIEW | `{desc}: billed ₹{actual} vs PO ₹{expected} (+{pct:.2f}%, tolerance ₹{tol}).` / PASS `All prices within tolerance (min of 1% or ₹1,000 per line).` |
| C15 | reconcile | Quantity vs unbilled | For each matched line: `remaining = po_line.quantity - consumed_qty(po_line)` where consumed = sum of `ledger_lines.quantity` whose ledger entry status is `APPROVED`. `inv_qty > remaining` → violation (zero quantity tolerance). | Violation → FLAG REVIEW. If `inv_qty == remaining` → also emit INFO in evidence `fully_billed_after: true`. | `{desc}: billing {inv_qty} {uom}, only {remaining} unbilled of {ordered} ordered ({consumed} already billed on {inv_list}). Over by {over} {uom} = ₹{over_value} net.` / PASS `Quantities within unbilled balance. {po} will be {pct_after}% billed.` |
| C16 | reconcile | Tax | (a) regime: vendor state code (first two chars of vendor GSTIN) == "29" → expect CGST = SGST and IGST = 0; else expect IGST > 0 (if taxable) and CGST = SGST = 0. (b) each matched line's `tax_rate_percent` equals PO line's. (c) `abs(sum(line_net * rate/100) - total_tax) ≤ 1.00`. | Any fail → FLAG REVIEW | `Wrong tax type: interstate supply should be IGST, invoice charges CGST+SGST.` (and inverse) / `{desc}: GST {inv_rate}% vs PO {po_rate}%.` / `Tax total ₹{printed} differs from computed ₹{computed}.` / PASS `{regime} at correct rates. Tax ₹{tax} verified.` |
| C17 | normalize | Currency | `currency == "INR"`. | Else FLAG REVIEW | `Invoice is in {cur}. Only INR invoices are auto-processed.` / PASS `INR.` |
| C20 | po_match | PO validity window | `po.po_date ≤ invoice_date ≤ po.valid_until`. | Outside → FLAG REVIEW | `Invoice dated {date}, outside {po} validity {from} to {to}.` / PASS `Within PO validity.` / SKIP if no date or no PO. |
| C21 | normalize | Tax-inclusive pricing | If `amounts_include_tax`: convert every line to net (see 7.4.5). | Always INFO when applicable, else not emitted. | `Prices are GST-inclusive. Converted to net: {desc} ₹{gross_unit} → ₹{net_unit} per {uom}.` |

(IDs C18, C19 intentionally unused. Keep IDs stable; tests reference them.)

---

## 7.4 Algorithms

### 7.4.0 Shared utilities (`backend/app/rules/`)

- `money.py`: all money in **Decimal**, quantized to `0.01` with `ROUND_HALF_UP`. Never float. Parse helper accepts `"1,29,682.00"`, `"₹ 1,29,682"`, `129682`, returns Decimal.
- `gstin.py`: `is_valid_gstin(s)` = regex `^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$` AND checksum:
  ```python
  CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  def checksum(first14):
      s = 0
      for i, c in enumerate(first14):
          p = CH.index(c) * (1 if i % 2 == 0 else 2)
          s += p // 36 + p % 36
      return CH[(36 - s % 36) % 36]
  ```
  `state_code(gstin) = gstin[:2]`.
- `text.py`:
  - `normalize_invoice_number(s)`:
    1. uppercase; 2. split into tokens with regex `[A-Z]+|[0-9]+` (this splits on every non-alphanumeric char AND on letter/digit boundaries); 3. for numeric tokens: strip leading zeros (`"0089"→"89"`, `"0"→"0"`); if the token is exactly 4 digits and starts with `"20"` replace with last two digits (`"2026"→"26"`); 4. join with `"-"`.
    Examples (put these in tests verbatim): `BIS-INV-2026-0089 → BIS-INV-26-89`; `BIS/INV/26/89 → BIS-INV-26-89`; `SPS/26-27/0512 → SPS-26-27-512`; `DCC/2627/0788 → DCC-2627-788`; `INV0045 → INV-45`.
  - `normalize_po_number(s)`: same tokenizer; result must equal a PO's normalized `po_number`. `PO 2026/412`, `po-2026-0412`, `PO#2026-0412` all → `PO-26-412`. PO numbers in DB get normalized the same way for lookup.
  - `desc_similarity(a, b)` = `rapidfuzz.fuzz.token_set_ratio(clean(a), clean(b)) / 100` where `clean` lowercases, replaces `&` with `and`, strips punctuation, collapses `5 ply`/`5-ply` style by removing hyphens, and removes stopwords `{"the","of","for","per","and","with","a","an"}`.

### 7.4.1 Vendor identification (C06)
1. If invoice `vendor_gstin` present and valid format → look up `vendors.gstin` exact. Found → method `"GSTIN"`.
2. Else (or not found) → fuzzy: best `token_set_ratio` of invoice `vendor_name` against each vendor's `legal_name` and every alias. Best ≥ 88 → method `"name (score {s})"`.
3. Neither → FLAG REJECT "unknown vendor". `vendor` = null; later vendor-dependent checks SKIP.
4. If matched by name **and** invoice printed a GSTIN that ≠ master GSTIN → FLAG HOLD (identity mismatch).
5. If invoice GSTIN present but fails checksum → FLAG HOLD.
6. C05 status and C07 bank only run if vendor matched.

### 7.4.2 Duplicate detection (C09)
Candidates = `invoice_ledger` rows with `status IN (APPROVED, IN_REVIEW, ON_HOLD)` (REJECTED ignored) and `id != current ledger row`.
- **Exact**: same `vendor_id` AND same `invoice_number_norm`. → FLAG REJECT.
  Message: `Duplicate of {orig_number} ({orig_status_label}, dated {orig_date}, ₹{orig_total}). Invoice number differs only in formatting.` If raw numbers are identical, drop the "differs only in formatting" clause.
- **Near** (only if no exact hit): same `vendor_id` AND `abs(grand_total - cand.grand_total) ≤ 1.00` AND (both dates present → `abs(days) ≤ 30`; if either date missing, date condition is considered satisfied) → FLAG REVIEW.
  Message: `Possible duplicate of {orig_number}: same vendor and amount ₹{total}, {days} days apart.`
- **File hash**: if any previous run had the same `documents.sha256`, add `evidence.same_file_as_run = <run_id>` and append ` The identical file was processed in run {short_id}.` to whichever message is emitted. On its own (no exact/near hit) → INFO `This exact file was processed before in run {short_id}.`
- Nothing found → PASS `No duplicate among {n} ledger invoices from {vendor}.`
- No vendor → SKIP.

### 7.4.3 PO resolution (C10)
1. If `po_number` extracted → normalize → look up. Found → PASS `Invoice references {po}.` method `"explicit"`.
2. If printed but not found → run inference (step 3); message prefix `PO number {printed} not found.` → always FLAG REVIEW regardless of inference result; include suggestion if inference succeeded.
3. **Inference** (also when no PO number printed). Candidates: POs of the matched vendor with `status == OPEN` and remaining net value > 0.
   For each candidate:
   - `coverage` = fraction of invoice lines whose best line-match score (7.4.4) against this PO's lines is ≥ 0.60.
   - `amount_fit` = `1 - min(1, abs(inv_net - po_remaining_net) / po_remaining_net)`.
   - `date_bonus` = 0.10 if a date parsed from `po_reference_text` equals `po.po_date`, else 0.
   - `score = min(1.0, 0.6*coverage + 0.4*amount_fit + date_bonus)` rounded to 3 dp.
   Sort desc. Best is selected iff `best ≥ 0.75` and `best - second ≥ 0.15` (second = 0 if only one candidate).
   Selected → FLAG REVIEW (unless `AUTO_APPROVE_INFERRED_PO`, then PASS) with message `No PO number on invoice. Inferred {po} (match {score:.0%}{date_clause}). Confirm before paying.` where date_clause = `, order date matches` when bonus applied. Evidence includes the full candidate table (po, coverage, amount_fit, date_bonus, score).
   Not selected → FLAG REVIEW `No PO number and no confident match among {n} open POs for {vendor}.` and stages C11-C16, C20 SKIP.
   Expected for F03: PO-2026-0431 score 1.000; PO-2026-0427 ≈ 0.002.
4. No vendor → SKIP.

### 7.4.4 Line matching (C13)
For each (invoice line i, PO line j):
```
desc  = desc_similarity(inv.description, po.description)          # 0..1
hsn   = 1.0 if inv.hsn_sac and inv.hsn_sac == po.hsn_sac else 0.0
price = 1 - min(1, abs(inv_net_unit - po.unit_price) / po.unit_price * 10)   # 10% off → 0
score = 0.5*desc + 0.3*hsn + 0.2*price
```
Greedy assignment: list all pairs, sort by score desc, assign pair if neither side assigned and `score ≥ 0.60`. Evidence: per invoice line → matched `po_line_no`, score, components.

### 7.4.5 Tax-inclusive normalisation (C21)
If `amounts_include_tax`: for each line, `net_unit = round(unit_price / (1 + rate/100), 2)`, `net_line = round(line_amount / (1 + rate/100), 2)`. Header `net = grand_total - total_tax` (if total_tax printed) else `sum(net_line)`. All downstream checks use net values. F07: 3045.00 / 1.05 = 2900.00 exactly.

### 7.4.6 Vision vs text path
Decided in `ingest`: `has_text_layer = len(pdfplumber text of all pages stripped) ≥ 40 chars`. Images (PNG/JPG) → always vision.

---

## 7.5 Stage-by-stage contract

Each stage = one module in `backend/app/pipeline/stages/`, exposing `async def run(ctx: RunContext) -> StageOutcome`. `StageOutcome = {status, summary, output: dict, checks: list[CheckResult]}`. The runner (7.7) handles timing, events and persistence; stages never touch the DB session for run bookkeeping, only for reads (vendors, POs, ledger).

**1 ingest** · output `{sha256, filename, mime, size_bytes, page_count, has_text_layer, text_chars}`. Reject non-PDF/PNG/JPG or >10 MB at the API, not here. Summary: `PDF, {n} page(s), text layer found` | `PDF, {n} page(s), no text layer (scanned)` | `Image upload, vision path`.

**2 extract** · see doc 06. Output `{method: "text"|"vision"|"heuristic", model, cached: bool, latency_ms, extraction: ExtractedInvoice}`. Summary: `Read {k} fields and {m} line items via {method}{" (cached)" if cached}`.

**3 normalize** · produce `NormalizedInvoice` (doc 04 §4.3). Checks: C01, C02, C03, C04, C08, C17, C21. Summary: `{grand_total_inr} total, {m} lines, {flag_count} issue(s)` or `Clean: {grand_total_inr}, {m} lines`.

**4 vendor** · Checks C06, C05, C07 (in that order). Output `{vendor_id, vendor_name, method, master_bank_masked}`. Summary: `{vendor_name} · {status}` or `Unknown vendor`.

**5 duplicates** · Check C09. Output `{candidates_checked, exact_hit, near_hit, same_file_run}`. Summary: `No duplicates in {n} invoices` | `Duplicate of {orig}` | `Possible duplicate of {orig}`.

**6 po_match** · Checks C10, C11, C12, C20, C13. Output `{po_number, method: explicit|inferred|none, candidates: [...], line_matches: [...]}`. Summary: `{po} (explicit), {k}/{m} lines matched` | `{po} inferred at {score:.0%}` | `No PO identified`.

**7 reconcile** · Checks C14, C15, C16. Output per line `{inv_line, po_line_no, ordered, consumed, remaining, billed_now, over_by, expected_amount, actual_amount, variance_pct, tolerance}` plus `{po_billed_pct_before, po_billed_pct_after}`. Summary: `Price, quantity and tax verified` or `{n} variance(s) found`.

**8 decide** · Aggregates. Output = `Decision` object (doc 04 §4.4). Also writes the ledger row (doc 04) and returns. Summary: `{Decision label}: {headline}` truncated to 90.

---

## 7.6 Decision output content

### Headlines (exact)
- APPROVE: `Approved for payment. Matches {po} within tolerance.` If any INFO about full consumption: append ` {po} is now fully billed.`
- REVIEW: `Needs review: {top_flag_message_short}` + (` and {n-1} more issue(s).` if n>1).
- HOLD: `Payment on hold: {top_hold_message_short}`
- REJECT: `Rejected: {top_reject_message_short}`

`top_*` = first FLAG of the decisive severity in stage order. `_short` = the message's first sentence.

### Reasons list
All FLAG checks sorted by severity (REJECT, HOLD, REVIEW) then stage order. Each: `{check_id, name, severity, message}`.

### Recommended actions (map by check_id when FLAGged; de-duplicate; keep order of reasons)
| Check | Action text |
|---|---|
| C01 | Ask the vendor for a corrected tax invoice with the missing fields. |
| C02 | Compare the low-confidence fields with the document before deciding. |
| C03 | Return the invoice to the vendor; it is not billed to Kestrel Foods. |
| C04 | Ask the vendor to correct the arithmetic and reissue. |
| C05 | Do not pay. Confirm with procurement why an inactive vendor is billing. |
| C06 (REJECT) | Route to procurement to onboard the vendor, or reject. |
| C06 (HOLD) | Verify the vendor's GSTIN on the GST portal and by phone before paying. |
| C07 | Call the vendor on the number in the vendor master (not the invoice) to confirm the bank change. Update the master only after confirmation. |
| C08 | Confirm the invoice date with the vendor. |
| C09 (REJECT) | Do not pay again. Reply to the vendor with the original invoice's status. |
| C09 (REVIEW) | Compare with the possible duplicate before paying. |
| C10 | Confirm the PO with the requester, then approve. |
| C11 | Check with procurement which PO this invoice belongs to. |
| C12 | Do not pay against a closed PO. Ask procurement whether a new PO is needed. |
| C13 | Ask the requester whether the unmatched items were ordered. |
| C14 | Ask the vendor for a credit note for the price difference, or approve the variance. |
| C15 | Approve only the unbilled quantity, or ask procurement to amend the PO. |
| C16 | Ask the vendor to reissue with the correct GST. |
| C17 | Process manually; foreign-currency invoices are out of scope. |
| C20 | Confirm with procurement whether the PO validity can be extended. |

For APPROVE: single action `Schedule payment for {due_date} ({terms} days from invoice date).` `due_date = invoice_date + vendor.payment_terms_days`.

### `payment_block`
`true` for HOLD and REJECT, `false` otherwise.

### Vendor email draft
Generated (template, **no LLM**) only when decision ∈ {REVIEW, REJECT} AND at least one FLAG is in {C01, C04, C09(REJECT), C14, C15, C16}. **Never generated for HOLD** (the vendor's email channel may be compromised; the UI shows the callback instruction instead). Template:

```
Subject: Invoice {invoice_number or "dated " + date or "received " + today}: action needed

Hello {vendor_short_name} team,

We received your invoice {ref} for ₹{grand_total} against {po or "our order"}. Before we can process it, we need the following:

{bullet list: one line per vendor-fixable flag, rewritten in second person:
 C01 → "- Please include the {fields} on the invoice."
 C04 → "- The totals do not add up ({which}). Please correct and reissue."
 C09 → "- This appears to be a copy of invoice {orig_number}, which is already {status_label_lower}. No further payment is due for it."
 C14 → "- {desc} is billed at ₹{inv_unit} per {uom}; the PO rate is ₹{po_unit}. Please issue a credit note or a corrected invoice."
 C15 → "- {desc}: {inv_qty} {uom} billed, but only {remaining} remain on {po}. We can pay for {remaining} now; please send a credit note for {over}."
 C16 → "- GST is charged incorrectly ({detail}). Please reissue."}

Thank you,
Accounts Payable, Kestrel Foods Pvt. Ltd.
```
For C09 REJECT the closing line before "Thank you" is `No action is needed if this was a reminder.`

---

## 7.7 Runner (`backend/app/pipeline/runner.py`)

```
async def execute_run(run_id):
    async with PIPELINE_LOCK:                 # one run at a time (ledger consistency)
        ctx = RunContext.load(run_id)
        emit("run.started", {...})
        set run.status = RUNNING
        for stage in STAGES:
            if stage prerequisites missing: mark SKIPPED, emit, continue
            mark RUNNING, emit("stage.started")
            t0 = perf_counter()
            try:
                outcome = await stage.run(ctx)
            except Exception as e:
                outcome = StageOutcome(status=FAILED, summary=f"Error: {short(e)}", output={"error": repr(e)}, checks=[])
                log full traceback
            for check in outcome.checks: persist; emit("check.result", check)
            persist stage (duration_ms); emit("stage.completed", {...})
        set run.status = COMPLETED (or FAILED only if decide itself failed), decision fields, completed_at, duration_ms
        emit("run.completed", {decision, headline})
```
- `PIPELINE_LOCK` = module-level `asyncio.Lock()`.
- Launch from the API with `asyncio.create_task(execute_run(run_id))` **after** committing the run row; keep a reference set to avoid GC.
- On server startup, any run left in RUNNING/QUEUED (crash/restart) is marked FAILED with summary `Interrupted by server restart` and emits nothing.
- Stage prerequisites: `extract` needs ingest OK; `normalize` needs extraction; `vendor`, `duplicates` need normalized; `po_match` needs normalized (+vendor for inference); `reconcile` needs po_match with a PO; `decide` always runs.

---

## 7.8 Human review (`POST /api/runs/{id}/review`)
Allowed only when run decision ∈ {REVIEW, HOLD} and `review_status == PENDING`.
- `approve`: requires `note` (≥5 chars). For HOLD also requires `bank_verified: true` (UI checkbox: "I confirmed the bank change by calling the number on the vendor master"). Sets ledger status APPROVED (now consumes PO), `review_status=APPROVED`, records reviewer name ("AP reviewer" default), timestamp.
- `reject`: requires note. Ledger REJECTED, `review_status=REJECTED`.
- Emits `run.reviewed` event. The original automated decision is never overwritten; UI shows both ("Automated: Needs review · AP: Approved by AP reviewer, 18 Nov 14:02").
- Approving F02 (over-billing) is allowed; consumption may exceed ordered quantity; PO page then shows the overrun in red.

---

## 7.9 Expected results matrix (golden tests assert these)

| Fixture | Decision | Must FLAG (severity) | Must PASS |
|---|---|---|---|
| F01 | APPROVE | none | C01 C03 C04 C05 C06 C07 C09 C10 C11 C12 C13 C14 C15 C16 C20 |
| F02 | REVIEW | C15 (REVIEW) | C10 C13 C14 C16 |
| F03 | REVIEW | C10 (REVIEW, inferred PO-2026-0431) | C13 C14 C15 C16 |
| F04 | REJECT | C09 (REJECT), C15 (REVIEW) | C06 C13 C14 C16 |
| F05 | HOLD | C07 (HOLD) | C10 C13 C14 C15 C16 |
| F06 | APPROVE | none (C15 PASS, evidence fully_billed_after=true) | C15 |
| F07 | APPROVE | none (C21 INFO) | C14 |
| F08 | REJECT | C05 (REJECT), C12 (REJECT), C20 (REVIEW) | C06 |
| F09 | REVIEW | C01 (REVIEW) | C10 C14 |

Golden tests run each fixture **against a freshly seeded DB** (independent of order).
