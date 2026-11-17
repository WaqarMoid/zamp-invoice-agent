import json
import logging
import time
from decimal import Decimal
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.config import get_settings
from app.extraction.prompt import SYSTEM_PROMPT, TEXT_USER_PROMPT_PREFIX, VISION_USER_PROMPT
from app.schemas import BankDetails, ExtractedInvoice, ExtractedLine, TaxBreakdown

logger = logging.getLogger("kestrel-ap.extraction.gemini")


# ---------------------------------------------------------------------------
# Mirror Pydantic schema using float and fixed fields for OpenAPI compatibility
# ---------------------------------------------------------------------------

class MirrorLine(BaseModel):
    description: str
    hsn_sac: str | None = None
    quantity: float | None = None
    uom: str | None = None
    unit_price: float | None = None
    tax_rate_percent: float | None = None
    line_amount: float | None = None


class MirrorBank(BaseModel):
    bank_name: str | None = None
    ifsc: str | None = None
    account_number: str | None = None
    account_name: str | None = None


class MirrorTax(BaseModel):
    cgst: float | None = None
    sgst: float | None = None
    igst: float | None = None


class MirrorFieldConfidence(BaseModel):
    vendor_name: float = 1.0
    vendor_gstin: float = 1.0
    invoice_number: float = 1.0
    invoice_date: float = 1.0
    grand_total: float = 1.0
    po_number: float = 1.0
    line_items: float = 1.0


class MirrorInvoice(BaseModel):
    vendor_name: str | None = None
    vendor_gstin: str | None = None
    vendor_address: str | None = None
    buyer_name: str | None = None
    buyer_gstin: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    invoice_date_raw: str | None = None
    currency: str | None = "INR"
    po_number: str | None = None
    po_reference_text: str | None = None
    amounts_include_tax: bool = False
    line_items: list[MirrorLine] = Field(default_factory=list)
    subtotal: float | None = None
    tax: MirrorTax = Field(default_factory=MirrorTax)
    total_tax: float | None = None
    grand_total: float | None = None
    bank_details: MirrorBank | None = None
    notes: str | None = None
    field_confidence: MirrorFieldConfidence = Field(default_factory=MirrorFieldConfidence)
    warnings: list[str] = Field(default_factory=list)


def to_decimal(val: float | int | str | None) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def convert_mirror_to_extracted_invoice(m: MirrorInvoice) -> ExtractedInvoice:
    """Convert MirrorInvoice with float fields to typed ExtractedInvoice with Decimals."""
    lines: list[ExtractedLine] = []
    for line in m.line_items:
        lines.append(
            ExtractedLine(
                description=line.description,
                hsn_sac=line.hsn_sac,
                quantity=to_decimal(line.quantity),
                uom=line.uom,
                unit_price=to_decimal(line.unit_price),
                tax_rate_percent=to_decimal(line.tax_rate_percent),
                line_amount=to_decimal(line.line_amount),
            )
        )

    tax = TaxBreakdown(
        cgst=to_decimal(m.tax.cgst),
        sgst=to_decimal(m.tax.sgst),
        igst=to_decimal(m.tax.igst),
    )

    bank = None
    if m.bank_details and (m.bank_details.ifsc or m.bank_details.account_number):
        bank = BankDetails(
            bank_name=m.bank_details.bank_name,
            ifsc=m.bank_details.ifsc,
            account_number=m.bank_details.account_number,
            account_name=m.bank_details.account_name,
        )

    # Post-parse guards per doc 06 §6.4
    warnings = list(m.warnings or [])
    vendor_gstin = m.vendor_gstin
    if vendor_gstin:
        cleaned_gstin = "".join(vendor_gstin.split()).upper()
        if len(cleaned_gstin) != 15:
            warnings.append(f"GSTIN has {len(cleaned_gstin)} characters")
        vendor_gstin = cleaned_gstin

    buyer_gstin = m.buyer_gstin
    if buyer_gstin:
        cleaned_buyer_gstin = "".join(buyer_gstin.split()).upper()
        if len(cleaned_buyer_gstin) != 15:
            warnings.append(f"Buyer GSTIN has {len(cleaned_buyer_gstin)} characters")
        buyer_gstin = cleaned_buyer_gstin

    if not lines:
        warnings.append("No line items extracted from document.")

    conf_dict = (
        m.field_confidence.model_dump()
        if hasattr(m.field_confidence, "model_dump")
        else dict(m.field_confidence or {})
    )

    tot_tax = to_decimal(m.total_tax)
    if tot_tax is None and (tax.cgst is not None or tax.sgst is not None or tax.igst is not None):
        tot_tax = (
            (tax.cgst or Decimal("0.00"))
            + (tax.sgst or Decimal("0.00"))
            + (tax.igst or Decimal("0.00"))
        )

    return ExtractedInvoice(
        vendor_name=m.vendor_name,
        vendor_gstin=vendor_gstin,
        vendor_address=m.vendor_address,
        buyer_name=m.buyer_name,
        buyer_gstin=buyer_gstin,
        invoice_number=m.invoice_number,
        invoice_date=m.invoice_date,
        invoice_date_raw=m.invoice_date_raw,
        currency=m.currency or "INR",
        po_number=m.po_number,
        po_reference_text=m.po_reference_text,
        amounts_include_tax=m.amounts_include_tax,
        line_items=lines,
        subtotal=to_decimal(m.subtotal),
        tax=tax,
        total_tax=tot_tax,
        grand_total=to_decimal(m.grand_total),
        bank_details=bank,
        notes=m.notes,
        field_confidence=conf_dict,
        warnings=warnings,
    )


class GeminiExtractor:
    name: str = "gemini"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self.model = model or settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.api_key = api_key or settings.GEMINI_API_KEY
        if self.api_key:
            self.client = genai.Client(
                api_key=self.api_key,
                http_options={"api_version": "v1beta"},
            )
        else:
            self.client = None

    def _call_with_retries(self, contents: list[Any]) -> str:
        """Call Gemini API with 2 retries (total 3 attempts) and exponential backoff."""
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=MirrorInvoice,
        )

        attempts = 3
        backoffs = [1.0, 3.0]
        last_error = None

        for attempt in range(attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                if not response.text:
                    raise ValueError("Empty response received from Gemini.")
                return response.text
            except Exception as e:
                last_error = e
                logger.warning(
                    "Gemini API attempt %d/%d failed: %s", attempt + 1, attempts, e
                )
                if attempt < attempts - 1:
                    time.sleep(backoffs[attempt])

        raise RuntimeError(f"Gemini API failed after {attempts} attempts: {last_error}") from last_error

    def extract_from_text(self, text: str) -> ExtractedInvoice:
        prompt_text = TEXT_USER_PROMPT_PREFIX + text
        response_json = self._call_with_retries([prompt_text])
        data = json.loads(response_json)
        mirror = MirrorInvoice.model_validate(data)
        return convert_mirror_to_extracted_invoice(mirror)

    def extract_from_images(self, images: list[bytes]) -> ExtractedInvoice:
        parts: list[Any] = [VISION_USER_PROMPT]
        for img in images:
            parts.append(types.Part.from_bytes(data=img, mime_type="image/png"))
        response_json = self._call_with_retries(parts)
        data = json.loads(response_json)
        mirror = MirrorInvoice.model_validate(data)
        return convert_mirror_to_extracted_invoice(mirror)
