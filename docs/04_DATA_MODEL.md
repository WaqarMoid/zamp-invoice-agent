# 04 · Data model

Read in: **Phase 1** (all). Phase 4 (§4.3, §4.4). Phase 5 (§4.5).

ORM: SQLAlchemy 2.0 (typed `Mapped[]` style). Validation/serialisation: Pydantic v2. The same models must work on **SQLite** (local, file `backend/data/app.db`) and **Postgres** (Neon, prod) via `DATABASE_URL`. Create tables with `Base.metadata.create_all()` on startup (no Alembic; this is a demo app, note it as a known limitation).

## 4.1 Conventions
- Money: store as **integer paise** (`BigInteger`) in DB columns named `*_paise`. Convert at the boundary: API emits rupees as **decimal strings with 2 dp** (`"129682.00"`). Never send floats for money.
- Quantities: `Numeric(14, 3)`, API emits string (`"2000"`, `"12.500"` → strip trailing zeros: `"12.5"`).
- Tax rates: `Numeric(5, 2)`, API emits string (`"18"`, `"5"`, `"0"`).
- IDs: runs use UUID4 strings (`String(36)`). Short display id = first 8 chars.
- Timestamps: timezone-aware UTC in DB (`DateTime(timezone=True)`); API emits ISO-8601 with `Z`. UI renders in IST.
- Dates (invoice/PO): `Date`, API emits `YYYY-MM-DD`.
- JSON blobs: `JSON` type (works on both engines).
- Enums: stored as `String(16)`, validated in Pydantic with `Literal[...]`.

## 4.2 Tables

### `vendors`
| column | type | notes |
|---|---|---|
| vendor_id | String(8) PK | `V001` |
| legal_name | String(200) | |
| aliases | JSON list[str] | used for fuzzy matching |
| gstin | String(15) unique | |
| pan | String(10) | |
| state_code | String(2) | |
| address | Text | |
| status | String(16) | `ACTIVE` \| `INACTIVE` |
| deactivated_on | Date null | |
| bank_name | String(100) | |
| bank_ifsc | String(11) | |
| bank_account_number | String(20) | never sent to the UI unmasked; API sends `••••` + last 4 |
| payment_terms_days | Integer | |
| contact_email | String(200) | |

### `purchase_orders`
| po_number PK String(20) | vendor_id FK | po_date Date | valid_until Date | status String(16) `OPEN`\|`CLOSED`\|`CANCELLED` | po_number_norm String(40) indexed |

### `po_lines`
| id PK int | po_number FK | line_no int | description Text | hsn_sac String(10) | uom String(10) | quantity Numeric | unit_price_paise BigInt | tax_rate Numeric(5,2) |
Unique (po_number, line_no).

### `documents`
| id PK int | sha256 String(64) indexed (NOT unique: same file can be uploaded twice) | filename String(255) | mime String(50) | size_bytes int | page_count int | has_text_layer bool | content LargeBinary | created_at |

### `runs`
| column | type | notes |
|---|---|---|
| id | String(36) PK | uuid4 |
| document_id | FK documents | |
| sample_id | String(4) null | `F01`..`F09` if started from a sample |
| use_cache | bool | default true |
| status | String(16) | `QUEUED` `RUNNING` `COMPLETED` `FAILED` |
| current_stage | String(16) null | key of running stage |
| decision | String(8) null | `APPROVE` `REVIEW` `HOLD` `REJECT` |
| headline | Text null | |
| vendor_id | String(8) null | denormalised for dashboard |
| vendor_name | String(200) null | as matched (or as printed if unmatched) |
| invoice_number | String(60) null | as printed |
| po_number | String(20) null | resolved PO |
| po_method | String(10) null | `explicit` `inferred` `none` |
| grand_total_paise | BigInt null | |
| extraction_method | String(10) null | |
| flags_count | int default 0 | |
| result | JSON null | full `RunResult` snapshot (see §4.4) |
| review_status | String(10) | `NOT_REQUIRED` (APPROVE/REJECT) \| `PENDING` \| `APPROVED` \| `REJECTED` |
| reviewer | String(100) null | |
| review_note | Text null | |
| reviewed_at | DateTime null | |
| created_at, started_at, completed_at | DateTime | |
| duration_ms | int null | |

### `run_stages`
| id | run_id FK idx | stage_key | position int (1..8) | status | summary String(140) | started_at | completed_at | duration_ms | output JSON |
Rows for all 8 stages are created as `PENDING` when the run is created.

### `run_checks`
| id | run_id FK idx | stage_key | check_id | name | outcome | severity null | message Text | evidence JSON | position int (emission order) |

### `run_events`
| id | run_id FK idx | seq int (1..n per run) | type String(32) | payload JSON | created_at |
Unique (run_id, seq).

### `invoice_ledger`
The AP ledger: every invoice the company knows about (seeded history + one row per completed run that extracted something).
| column | type | notes |
|---|---|---|
| id | int PK | |
| source | String(8) | `seed` \| `run` |
| run_id | FK null | |
| vendor_id | FK null | |
| invoice_number | String(60) null | |
| invoice_number_norm | String(60) null indexed | |
| invoice_date | Date null | |
| po_number | String(20) null | |
| net_paise, tax_paise, grand_total_paise | BigInt | |
| status | String(12) | `APPROVED` `IN_REVIEW` `ON_HOLD` `REJECTED` |
| file_sha256 | String(64) null | |
| created_at | DateTime | |

### `ledger_lines`
| id | ledger_id FK | po_number null | po_line_no int null | description | quantity Numeric | unit_price_paise | net_paise |
Only lines matched to a PO line get `po_number`/`po_line_no`. **PO consumption = sum(quantity) of ledger_lines joined to ledger rows with status `APPROVED`.**

### `extraction_cache`
| sha256 PK | method | model | payload JSON (ExtractedInvoice) | created_at |
Not cleared by demo reset.

## 4.3 Pydantic domain models (`backend/app/schemas.py`)

```python
class ExtractedLine(BaseModel):
    description: str
    hsn_sac: str | None = None
    quantity: Decimal | None = None
    uom: str | None = None
    unit_price: Decimal | None = None
    tax_rate_percent: Decimal | None = None
    line_amount: Decimal | None = None

class BankDetails(BaseModel):
    bank_name: str | None = None
    ifsc: str | None = None
    account_number: str | None = None
    account_name: str | None = None

class TaxBreakdown(BaseModel):
    cgst: Decimal | None = None
    sgst: Decimal | None = None
    igst: Decimal | None = None

class ExtractedInvoice(BaseModel):
    vendor_name: str | None
    vendor_gstin: str | None
    vendor_address: str | None
    buyer_name: str | None
    buyer_gstin: str | None
    invoice_number: str | None
    invoice_date: str | None          # ISO YYYY-MM-DD as normalised by the model, or null
    invoice_date_raw: str | None      # exactly as printed
    currency: str | None = "INR"
    po_number: str | None
    po_reference_text: str | None     # any text referring to an order without a PO number
    amounts_include_tax: bool = False
    line_items: list[ExtractedLine]
    subtotal: Decimal | None
    tax: TaxBreakdown
    total_tax: Decimal | None
    grand_total: Decimal | None
    bank_details: BankDetails | None
    notes: str | None                 # footer remarks, e.g. bank-change notice
    field_confidence: dict[str, float]   # keys: vendor_name, vendor_gstin, invoice_number, invoice_date, grand_total, po_number, line_items
    warnings: list[str] = []

class NormalizedLine(BaseModel):
    index: int
    description: str
    hsn_sac: str | None
    quantity: Decimal
    uom: str | None
    unit_price_net: Decimal
    unit_price_printed: Decimal
    tax_rate_percent: Decimal
    line_net: Decimal
    line_printed: Decimal

class NormalizedInvoice(BaseModel):
    vendor_name: str | None
    vendor_gstin: str | None          # uppercased, spaces stripped
    buyer_gstin: str | None
    invoice_number: str | None
    invoice_number_norm: str | None
    invoice_date: date | None
    currency: str
    po_number: str | None
    po_number_norm: str | None
    po_reference_text: str | None
    po_reference_date: date | None    # parsed from po_reference_text if a date is present
    amounts_include_tax: bool
    lines: list[NormalizedLine]
    net_total: Decimal
    cgst: Decimal; sgst: Decimal; igst: Decimal
    total_tax: Decimal
    grand_total: Decimal | None
    bank_ifsc: str | None
    bank_account_digits: str | None
```
Date parsing accepts `2026-11-12`, `12/11/2026` (DD/MM/YYYY, Indian default), `12-11-2026`, `12 Nov 2026`, `12-Nov-26`, `Nov 12, 2026`. Use `dateutil.parser.parse(dayfirst=True)`.

## 4.4 Decision / RunResult (stored in `runs.result`, returned by API)

```python
class Reason(BaseModel):
    check_id: str; name: str; severity: Literal["REVIEW","HOLD","REJECT"]; message: str

class Decision(BaseModel):
    decision: Literal["APPROVE","REVIEW","HOLD","REJECT"]
    label: str                      # "Approved" | "Needs review" | "On hold" | "Rejected"
    headline: str
    reasons: list[Reason]
    recommended_actions: list[str]
    payment_block: bool
    due_date: date | None           # APPROVE only
    vendor_email: dict | None       # {"subject": str, "body": str}
    key_facts: dict                 # {"vendor": str|None, "po": str|None, "po_method": str, "invoice_number": str|None, "invoice_date": str|None, "grand_total": "129682.00"|None}

class RunResult(BaseModel):
    extraction: ExtractedInvoice | None
    normalized: NormalizedInvoice | None
    decision: Decision
```

## 4.5 Serialisation rules for the API
- Decimal → string, money with 2 dp.
- Masking: any bank account number leaving the API → `"••••" + last4`. Applies to vendor master **and** to extracted invoice bank details in `result.extraction`. Evidence dicts for C07 also contain masked values only.
- `runs.result` is stored already-masked.
