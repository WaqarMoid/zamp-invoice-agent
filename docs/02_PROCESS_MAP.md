# 02 · Process map

Read in: **Phase 0** (skim), **Phase 4** (all), **Phase 9** (for narration).

## 2.1 The manual process we are replacing
1. AP clerk opens the invoice email, downloads the PDF.
2. Reads vendor, invoice number, PO, lines, totals.
3. Opens the vendor master to confirm the vendor is approved; glances at bank details.
4. Searches the PO spreadsheet; compares prices and quantities by eye.
5. Rarely: checks whether this invoice was already paid.
6. Approves, or emails someone.
Failure points: tired eyes on totals, no cumulative view of split POs, duplicate resends with a new number format, bank-change fraud that looks perfect.

## 2.2 Automated flow

```mermaid
flowchart TD
    A[Invoice PDF or image uploaded] --> B[1 Ingest<br/>store, SHA-256, text layer?]
    B -->|text layer| C1[2 Extract: text path<br/>pdfplumber text → LLM JSON]
    B -->|scanned / image| C2[2 Extract: vision path<br/>page images → LLM JSON]
    C1 & C2 -->|LLM unavailable| C3[Heuristic regex reader<br/>confidence 0.60]
    C1 & C2 & C3 --> D[3 Normalize & validate<br/>dates, money, IDs, tax-inclusive → net<br/>C01 C02 C03 C04 C08 C17 C21]
    D --> E[4 Verify vendor<br/>GSTIN / fuzzy name, status, bank<br/>C06 C05 C07]
    E --> F[5 Detect duplicates<br/>normalized number, amount+date window, file hash<br/>C09]
    F --> G{6 Match PO<br/>PO number printed?}
    G -->|yes, found| G1[Explicit PO]
    G -->|no / not found| G2[Infer: score open POs of vendor<br/>coverage, amount fit, date hint]
    G1 & G2 --> H[Pair invoice lines ↔ PO lines<br/>C10 C11 C12 C20 C13]
    H --> I[7 Reconcile<br/>price tolerance, qty vs unbilled balance, GST regime<br/>C14 C15 C16]
    I --> J[8 Decide<br/>max severity: REJECT > HOLD > REVIEW > APPROVE]
    J -->|APPROVE| K1[Ledger APPROVED<br/>consumes PO, schedule payment]
    J -->|REVIEW| K2[Ledger IN_REVIEW<br/>AP queue + vendor email draft]
    J -->|HOLD| K3[Ledger ON_HOLD<br/>payment blocked, callback instruction]
    J -->|REJECT| K4[Ledger REJECTED<br/>reason + vendor reply draft]
    K2 & K3 --> L[Human review<br/>approve with note / reject]
    L -->|approve| K1
```

## 2.3 Decision points (what the process decides and why)
| Point | Decision | Why it matters |
|---|---|---|
| Text layer? | text vs vision extraction | Text is cheaper and more exact; vision handles scans. |
| Confidence < 0.80? | Route to human | Never act on a value the reader is unsure about. |
| Vendor found by GSTIN or name? | Identity confidence | Name-only match with a different GSTIN is an impersonation signal → HOLD. |
| Bank details differ? | HOLD, not REVIEW | Most expensive AP fraud; looks perfect otherwise. Must be verified out-of-band, so no email reply. |
| Duplicate? | Normalized number vs near match | Resends rarely reuse the exact string. |
| PO printed? | Explicit vs inferred | Inferred PO is a suggestion, never an auto-approval (policy flag). |
| Quantity ≤ unbilled? | Cumulative view | Split invoices look fine individually. |
| Price within min(1%, ₹1,000)? | Tolerance | Absolute cap stops 1% of a large PO becoming a large overpayment. |
| Severity aggregation | Single decision | Deterministic precedence makes every outcome explainable. |

## 2.4 Edge cases (the four we demo, plus four more covered)
| ID | Fixture | Scenario | Why it is non-trivial | Expected |
|---|---|---|---|---|
| EC1 | F02 | Third partial invoice on a framework PO bills 14 trips when 10 remain | Every single-invoice check passes; only ledger-wide cumulative consumption catches it | REVIEW, recommend paying 10 and asking for PO amendment |
| EC2 | F03 | Scanned image, no PO number, vendor has two open POs | Needs vision extraction and PO inference with an explainable score | REVIEW with inferred PO-2026-0431 |
| EC3 | F04 | Resent invoice with reformatted number and new date | Exact string match misses it | REJECT as duplicate of BIS-INV-2026-0089 |
| EC4 | F05 | All numbers perfect, bank account changed in the footer | Looks like the happy path; fraud signal | HOLD, payment blocked, callback required |
| + | F06 | Partial invoice within balance | Contrast for EC1 | APPROVE |
| + | F07 | GST-inclusive pricing | Naive compare shows +5% variance | APPROVE after net conversion |
| + | F08 | Inactive vendor, closed PO | Multiple independent reject reasons | REJECT |
| + | F09 | Missing invoice number and date | Duplicate check degrades gracefully | REVIEW + vendor email |
