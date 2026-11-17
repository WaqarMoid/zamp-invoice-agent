from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Extraction models (doc 04 §4.3)
# ---------------------------------------------------------------------------

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
    vendor_name: str | None = None
    vendor_gstin: str | None = None
    vendor_address: str | None = None
    buyer_name: str | None = None
    buyer_gstin: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None          # ISO YYYY-MM-DD or None
    invoice_date_raw: str | None = None      # exactly as printed
    currency: str | None = "INR"
    po_number: str | None = None
    po_reference_text: str | None = None     # any text referring to an order without a PO number
    amounts_include_tax: bool = False
    line_items: list[ExtractedLine] = Field(default_factory=list)
    subtotal: Decimal | None = None
    tax: TaxBreakdown = Field(default_factory=TaxBreakdown)
    total_tax: Decimal | None = None
    grand_total: Decimal | None = None
    bank_details: BankDetails | None = None
    notes: str | None = None                 # footer remarks
    field_confidence: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Normalization models (doc 04 §4.3)
# ---------------------------------------------------------------------------

class NormalizedLine(BaseModel):
    index: int
    description: str
    hsn_sac: str | None = None
    quantity: Decimal
    uom: str | None = None
    unit_price_net: Decimal
    unit_price_printed: Decimal
    tax_rate_percent: Decimal
    line_net: Decimal
    line_printed: Decimal


class NormalizedInvoice(BaseModel):
    vendor_name: str | None = None
    vendor_gstin: str | None = None          # uppercased, spaces stripped
    buyer_gstin: str | None = None
    invoice_number: str | None = None
    invoice_number_norm: str | None = None
    invoice_date: date | None = None
    currency: str = "INR"
    po_number: str | None = None
    po_number_norm: str | None = None
    po_reference_text: str | None = None
    po_reference_date: date | None = None
    amounts_include_tax: bool = False
    lines: list[NormalizedLine] = Field(default_factory=list)
    net_total: Decimal = Decimal("0.00")
    cgst: Decimal = Decimal("0.00")
    sgst: Decimal = Decimal("0.00")
    igst: Decimal = Decimal("0.00")
    total_tax: Decimal = Decimal("0.00")
    grand_total: Decimal | None = None
    bank_ifsc: str | None = None
    bank_account_digits: str | None = None


# ---------------------------------------------------------------------------
# Decision / RunResult models (doc 04 §4.4)
# ---------------------------------------------------------------------------

class Reason(BaseModel):
    check_id: str
    name: str
    severity: Literal["REVIEW", "HOLD", "REJECT"]
    message: str


class Decision(BaseModel):
    decision: Literal["APPROVE", "REVIEW", "HOLD", "REJECT"]
    label: str                               # "Approved" | "Needs review" | "On hold" | "Rejected"
    headline: str
    reasons: list[Reason] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    payment_block: bool = False
    due_date: date | None = None             # APPROVE only
    vendor_email: dict[str, str] | None = None  # {"subject": str, "body": str}
    key_facts: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    extraction: ExtractedInvoice | None = None
    normalized: NormalizedInvoice | None = None
    decision: Decision


# ---------------------------------------------------------------------------
# API schemas for Vendors and Purchase Orders (doc 05 §5.2, doc 08 §8.1)
# ---------------------------------------------------------------------------

class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_id: str
    legal_name: str
    aliases: list[str]
    gstin: str
    pan: str
    state_code: str
    address: str
    status: str
    deactivated_on: date | None = None
    bank_name: str
    bank_ifsc: str
    bank_account_masked: str                 # '••••' + last 4
    payment_terms_days: int
    contact_email: str


class POLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_no: int
    description: str
    hsn_sac: str | None = None
    uom: str
    quantity: str                           # decimal formatted, trailing zeros stripped
    unit_price: str                         # decimal formatted with 2 dp
    tax_rate: str                           # e.g. "18"
    billed_quantity: str                    # sum of approved ledger lines
    remaining_quantity: str                 # quantity - billed_quantity


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    po_number: str
    vendor_id: str
    vendor_name: str
    po_date: str                            # YYYY-MM-DD
    valid_until: str                        # YYYY-MM-DD
    status: str                             # OPEN | CLOSED | CANCELLED
    po_number_norm: str
    total_amount: str                       # calculated from lines
    lines: list[POLineOut]
    billing_state: str                      # UNBILLED | PARTIALLY_BILLED | FULLY_BILLED | OVERBILLED
    billed_percentage: float


class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    run_id: str | None = None
    vendor_id: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    po_number: str | None = None
    net_amount: str
    tax_amount: str
    grand_total: str
    status: str
    created_at: str


class PurchaseOrderDetailOut(PurchaseOrderOut):
    invoices: list[LedgerEntryOut] = Field(default_factory=list)
