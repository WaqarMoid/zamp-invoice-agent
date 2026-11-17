# 05 · Seed data and invoice fixtures

Read in: **Phase 1** (§5.1-5.2), **Phase 2** (§5.3-5.6).

All data is already written and arithmetically verified. Files live in `backend/app/seed_data/`:

| File | Contents |
|---|---|
| `buyer.json` | Our company: Kestrel Foods Pvt. Ltd., GSTIN `29AAACK4521M1ZD`, Karnataka (state 29) |
| `vendors.json` | 6 vendors (V001-V006). V006 is INACTIVE. All GSTINs have valid checksums. |
| `purchase_orders.json` | 8 POs with lines and `computed_totals` (reference only, do not load into DB) |
| `prior_invoices.json` | 3 historical APPROVED invoices (seeded into the ledger) |
| `fixtures.json` | 9 invoice specifications, each with exact printed content and expected decision |

**Do not edit these numbers.** If a test disagrees with them, the code is wrong.

## 5.1 Seeder (`backend/app/seed.py`)
`seed(session, force=False)`:
1. If `force` → delete all rows from: run_events, run_checks, run_stages, runs, ledger_lines, invoice_ledger, documents, po_lines, purchase_orders, vendors (in that order). Never delete `extraction_cache`.
2. If vendors table non-empty and not force → return.
3. Insert vendors, POs (`po_number_norm` computed), po_lines (`unit_price_paise = round(unit_price*100)`).
4. Insert each prior invoice as `invoice_ledger` (source `seed`, status `APPROVED`, `invoice_number_norm` computed, amounts from `computed_totals`) with `ledger_lines` linked to `po_number` + `po_line_no`.
5. Called on startup (`force=False`) and by `POST /api/admin/reset` (`force=True`).

## 5.2 Reference: state after seeding
| PO | Vendor | Ordered | Billed (approved) | Remaining |
|---|---|---|---|---|
| PO-2026-0377 | V006 Metro Office | 100 reams | 0 | 100 (but PO CLOSED) |
| PO-2026-0398 | V003 Bluepeak | 120 licences + 1 LS | 120 + 1 | 0 (fully billed by BIS-INV-2026-0089) |
| PO-2026-0412 | V001 Sharma | 2000 / 2000 / 300 | 0 | all |
| PO-2026-0418 | V002 Deccan | 50 trips | 40 (DCC/2627/0611, DCC/2627/0702) | 10 trips |
| PO-2026-0427 | V004 GreenLeaf | 15 kg | 0 | 15 |
| PO-2026-0431 | V004 GreenLeaf | 40 bags + 20 bags | 0 | all |
| PO-2026-0440 | V005 Annapurna | 60 bags | 0 | 60 |
| PO-2026-0445 | V003 Bluepeak | 4 visits | 0 | 4 |

## 5.3 Fixture generator (`backend/scripts/generate_fixtures.py`)
Libraries: `reportlab` (PDF drawing), `PyMuPDF` (`fitz`, rasterising), `Pillow` + `numpy` (scan effect). Output to `backend/fixtures/F0X_*.pdf` (committed to git; the deployed backend serves them as samples). Deterministic: fixed random seed `42`, fixed fonts (reportlab built-ins `Helvetica`, `Helvetica-Bold`, `Courier` only), PDF metadata creation date fixed to `2026-11-17`.

Page: A4 portrait, 15 mm margins. Every invoice prints, in this order (layout varies, content doesn't):
1. Vendor block: printed name (bold), address, `GSTIN: {gstin}`, email.
2. Title: `TAX INVOICE` (F09 prints `INVOICE` and leaves Invoice No. and Date **blank** with the labels still present: `Invoice No.: ________`, `Date: ________`).
3. Meta: `Invoice No.`, `Invoice Date` (format per layout, below), `PO No.` (omit the whole row when `po_number_printed` is null; F03 instead prints `Order Ref: {po_reference_text}`).
4. Bill To: buyer name, address, `GSTIN: 29AAACK4521M1ZD`.
5. Line table columns: `#`, `Description`, `HSN/SAC`, `Qty`, `UOM`, `Rate (₹)`, `GST %`, `Amount (₹)`. Amounts in Indian digit grouping (`1,29,682.00`). Rupee sign: reportlab built-in fonts lack `₹`; write `Rs.` in the PDF instead (extraction treats it as INR).
6. Totals block, right-aligned: `Taxable Value`, then either `CGST @ x%` + `SGST @ x%` rows (intrastate) or `IGST @ x%` (interstate), each with amount, then `Total Tax`, `Grand Total` (bold). For mixed rates (F03) print one CGST and one SGST row labelled `CGST` / `SGST` without a rate. For tax-inclusive (F07) print `Total (inclusive of GST)` as the line-sum, then a small grey row `Includes CGST 2.5% Rs. 1,087.50 and SGST 2.5% Rs. 1,087.50`, then `Grand Total`.
7. Amount in words (Indian system, e.g. `Rupees One Lakh Twenty Nine Thousand Six Hundred Eighty Two Only`). Write a small helper.
8. Bank details box if `bank_details_printed` not null: Bank, A/c Name, A/c No., IFSC.
9. Footer notes (`footer_notes`) in a bordered box; F05's note in **bold**.
10. `Authorised Signatory` line at bottom right.

### Layouts (to make vendors look different)
| layout | look | date format | used by |
|---|---|---|---|
| `classic` | Boxed header, full table grid lines, vendor block top-left, meta top-right | `12/11/2026` | F01 F05 F08 |
| `modern` | No outer box, thick 2pt rule under header, table with horizontal rules only, light grey header row (#EEEEEE) | `15 Nov 2026` | F02 F04 F06 F09 |
| `compact` | Small 8pt body, two-column header, dense table, totals as a list | `10-Nov-26` | F03 F07 |

### Scanned effect (F03 only, `scanned: true`)
1. Render the vector PDF as usual to a temp file.
2. Rasterise page 1 with PyMuPDF at 200 DPI, grayscale.
3. Rotate by +0.6° (Pillow, `expand=False`, fill white), add Gaussian noise (σ = 6 on 0-255), slight blur (`GaussianBlur(radius=0.4)`), paper tint: multiply by (247/255).
4. Save as JPEG quality 82, insert as a full-page image into a new PDF (PyMuPDF `insert_image`). **The output must have no text layer**: assert `len(page.get_text().strip()) == 0`.

## 5.4 Golden extraction files
Same script also writes `backend/fixtures/golden/F0X.json`: the `ExtractedInvoice` the extractor *should* produce, derived from `fixtures.json` (all `field_confidence` = 0.99; `invoice_date` ISO; `invoice_date_raw` as printed per layout; `bank_details` from `bank_details_printed`; `tax` from printed totals; F09 has `invoice_number=null`, `invoice_date=null`; F03 `po_number=null`, `po_reference_text="As per your order dated 02-Nov-2026"`; F07 `amounts_include_tax=true`, `line_items[0].unit_price=3045.00`, `line_amount=45675.00`, `subtotal=45675.00`, `total_tax=2175.00`, `grand_total=45675.00`).
Golden files are used by (a) golden pipeline tests (no LLM), (b) the extraction accuracy script in Phase 3.

## 5.5 Samples manifest
`GET /api/samples` serves, from `fixtures.json`: `{id, filename, title, scenario, description, expected_decision, group}` where group = `Happy path` (F01), `Edge cases` (F02-F05), `More scenarios` (F06-F09). Order by id.

## 5.6 Acceptance for Phase 2
- 9 PDFs exist; F03 has no text layer, all others have text (`pdfplumber` text ≥ 40 chars).
- Visually open F01, F03, F05, F07 (render page 1 to PNG and inspect): no overlapping text, table fits the page, amounts right-aligned.
- `pytest tests/test_fixtures.py` checks: every printed grand total in the PDF text equals `fixtures.json`.
