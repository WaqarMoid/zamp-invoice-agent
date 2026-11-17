# 06 · Extraction (the only place an LLM is used)

Read in: **Phase 3**.

Design principle to say out loud in the demo: *the LLM reads, the rules decide.* The model turns a messy document into a typed object. Every decision after that is deterministic, testable Python. This makes outcomes explainable and repeatable.

## 6.1 Provider
- Primary: **Google Gemini** via the official `google-genai` Python SDK (`from google import genai`). Reason: free tier, native PDF/image input, JSON-schema structured output.
- Env: `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`). **Before coding, check the current Gemini API docs** for the latest Flash-class model ID that supports image input + `response_schema`, and set the default to it. Record the chosen ID in `PROGRESS.md`.
- Optional secondary: OpenAI (`OPENAI_API_KEY`, `OPENAI_MODEL`), behind the same interface, used only if `LLM_PROVIDER=openai`. Implement only after everything else works (stretch).
- Interface (`backend/app/extraction/llm_client.py`):
  ```python
  class Extractor(Protocol):
      name: str; model: str
      def extract_from_text(self, text: str) -> ExtractedInvoice: ...
      def extract_from_images(self, images: list[bytes]) -> ExtractedInvoice: ...
  ```
  Calls are sync; the stage wraps them in `await asyncio.to_thread(...)`.
- Settings: `temperature=0`, response MIME `application/json`, `response_schema` = JSON schema derived from `ExtractedInvoice` (if the SDK rejects Decimal, use a mirror model with `float | None` for numbers and convert to Decimal via `Decimal(str(x))` right after parsing). Timeout 45 s. Retries: 2 (total 3 attempts) on network/5xx/invalid JSON, backoff 1 s, 3 s.

## 6.2 Routing
```
if cache enabled for run and extraction_cache has sha256 → use it (cached=True)
elif document.has_text_layer → text path
else → vision path
on LLM failure after retries:
    if has_text_layer → heuristic path (6.5), method="heuristic"
    else → stage FAILED ("Could not read the scanned invoice: <reason>")
store successful text/vision results in extraction_cache
```

### Text path
`pdfplumber`: for each page `page.extract_text(layout=True)`; join pages with `\n\n--- PAGE BREAK ---\n\n`. Truncate to 30 000 chars. Max 5 pages processed (more → warning).

### Vision path
PyMuPDF: render each page (max 5) at 200 DPI to PNG bytes; send as inline image parts. Images uploaded directly (PNG/JPG) are sent as-is (downscale so the longest side ≤ 2400 px).

## 6.3 System prompt (use verbatim, file `backend/app/extraction/prompt.py`)

```
You extract data from Indian GST vendor invoices for an accounts-payable system.
Return ONLY JSON matching the schema. Rules:

1. Copy values exactly as printed. Never guess or compute a value that is not printed.
   If a field is not on the document, return null. Blank fields such as "Invoice No.: ____" are null.
2. Numbers: plain numbers without currency symbols or thousands separators (1,29,682.00 -> 129682.00).
   "Rs.", "INR" and "₹" all mean currency "INR".
3. invoice_date: convert to YYYY-MM-DD. Indian documents use day-first dates (12/11/2026 is 12 November 2026).
   Also put the date exactly as printed in invoice_date_raw.
4. vendor = the party issuing the invoice (seller). buyer = the "Bill To" party.
   GSTINs are 15 characters; copy them exactly, uppercase, no spaces.
5. po_number: only an explicit purchase order number (labels like PO No., P.O., Purchase Order, Order No. followed by an identifier).
   If the invoice mentions an order without a number (e.g. "as per your order dated 02-Nov-2026"), set po_number null
   and copy that text into po_reference_text.
6. amounts_include_tax: true only if the document states prices or amounts are inclusive of GST/tax.
7. line_items: one entry per printed row. unit_price and line_amount exactly as printed (do not remove tax).
   tax_rate_percent: the GST rate printed for that row, or the single rate stated for the invoice if rows have none.
8. tax: cgst, sgst, igst amounts as printed (null if not printed). total_tax and grand_total as printed.
9. bank_details: only if printed on the invoice.
10. notes: copy any remarks or footer notices verbatim (for example notices about changed bank details).
11. field_confidence: your confidence 0.0-1.0 that each of these was read correctly:
    vendor_name, vendor_gstin, invoice_number, invoice_date, grand_total, po_number, line_items.
    Use 1.0 only for crisp printed text. Lower it for blurry, ambiguous or partially visible values.
    For fields you returned as null because they are absent, give 1.0.
12. warnings: short notes about anything unusual (illegible areas, handwritten edits, multiple totals).
```
User message for text path: `Invoice text extracted from a PDF (layout preserved):\n\n<text>`. For vision: `Invoice page image(s) follow.` + images.

## 6.4 Post-parse guards (deterministic, in `extract` stage)
- GSTIN: strip spaces, uppercase. If length ≠ 15 → keep value, append warning `"GSTIN has {n} characters"` (C06 will FLAG).
- If `grand_total` null but line sums and taxes present, **do not compute it**; leave null (C01 flags it). The model must not invent; neither do we.
- If `line_items` is empty → warning.

## 6.5 Heuristic fallback (`heuristic.py`)
Regex-based reader for text-layer PDFs, used only when the LLM is unavailable. Patterns (case-insensitive): `Invoice No\.?\s*[:#]?\s*(\S+)`, `(Invoice )?Date\s*:?\s*([0-9A-Za-z/\- ]{6,12})`, `GSTIN\s*:?\s*([0-9A-Z]{15})` (first = vendor, the one after "Bill To" = buyer), `PO No\.?\s*:?\s*(\S+)`, `Grand Total\s*(?:Rs\.?)?\s*([\d,]+\.\d{2})`, IFSC `\b([A-Z]{4}0[A-Z0-9]{6})\b`, A/c No. `A/c No\.?\s*:?\s*(\d{6,18})`. Line items: rows from `pdfplumber` `page.extract_tables()`; map columns by header names. All `field_confidence` = 0.60 (so C02 routes to REVIEW: degraded mode is visible and honest). Method `heuristic`.

## 6.6 Phase 3 acceptance: extraction accuracy script
`backend/scripts/eval_extraction.py`: for each fixture, run live extraction with cache disabled, compare to `fixtures/golden/F0X.json` on: vendor_gstin, buyer_gstin, invoice_number, invoice_date, po_number, amounts_include_tax, grand_total, total_tax, bank ifsc/account, line count, each line's quantity / unit_price / line_amount / tax_rate. Print a table: fixture × field ✓/✗ and an overall score. **Target: 100% on F01-F09 critical fields.** If F03 (scanned) fails a field, first increase DPI to 250, then adjust the scan noise in the generator (σ 6 → 4); do not loosen the prompt rules. Save the report to `backend/reports/extraction_eval.md` (committed: good interview evidence).
