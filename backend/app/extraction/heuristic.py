import io
import re
from decimal import Decimal

import pdfplumber

from app.rules.dates import parse_date
from app.rules.money import parse_money
from app.schemas import BankDetails, ExtractedInvoice, ExtractedLine, TaxBreakdown


def extract_heuristic_from_pdf(pdf_bytes: bytes) -> ExtractedInvoice:
    """
    Regex and table-based heuristic reader for text-layer PDFs per doc 06 §6.5.
    Used when LLM is unavailable. Sets all field_confidence = 0.60.
    """
    full_text = ""
    tables_data = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            full_text += (page.extract_text(layout=True) or "") + "\n"
            tables = page.extract_tables() or []
            tables_data.extend(tables)

    # 1. Invoice Number
    inv_no_match = re.search(r"Invoice\s*No\.?\s*[:#]?\s*(\S+)", full_text, re.IGNORECASE)
    invoice_number = None
    if inv_no_match:
        val = inv_no_match.group(1).strip()
        if not re.match(r"^[_.-]+$", val):  # Ignore blank fill lines
            invoice_number = val

    # 2. Invoice Date
    date_match = re.search(r"(?:Invoice\s*)?Date\s*[:#]?\s*([0-9A-Za-z/\- ]{6,12})", full_text, re.IGNORECASE)
    invoice_date = None
    invoice_date_raw = None
    if date_match:
        val = date_match.group(1).strip()
        if not re.match(r"^[_.-]+$", val):
            invoice_date_raw = val
            d = parse_date(val)
            if d:
                invoice_date = d.isoformat()

    # 3. GSTINs (first = vendor, the one after "Bill To" = buyer)
    gstin_matches = list(re.finditer(r"GSTIN\s*[:#]?\s*([0-9A-Z]{15})", full_text, re.IGNORECASE))
    vendor_gstin = None
    buyer_gstin = None

    bill_to_idx = full_text.find("Bill To")
    if bill_to_idx != -1:
        for m in gstin_matches:
            if m.start() < bill_to_idx and not vendor_gstin:
                vendor_gstin = m.group(1).upper()
            elif m.start() >= bill_to_idx and not buyer_gstin:
                buyer_gstin = m.group(1).upper()
    else:
        if len(gstin_matches) > 0:
            vendor_gstin = gstin_matches[0].group(1).upper()
        if len(gstin_matches) > 1:
            buyer_gstin = gstin_matches[1].group(1).upper()

    # 4. PO Number
    po_match = re.search(r"PO\s*No\.?\s*[:#]?\s*(\S+)", full_text, re.IGNORECASE)
    po_number = po_match.group(1).strip() if po_match else None

    # PO reference text
    po_ref_match = re.search(r"(?:Order\s*Ref|order\s*dated)\s*[:#]?\s*([^\n]+)", full_text, re.IGNORECASE)
    po_ref_text = po_ref_match.group(1).strip() if po_ref_match else None

    # 5. Grand Total
    gt_match = re.search(r"Grand\s*Total\s*(?:Rs\.?)?\s*([\d,]+\.\d{2})", full_text, re.IGNORECASE)
    grand_total = None
    if gt_match:
        try:
            grand_total = parse_money(gt_match.group(1))
        except ValueError:
            pass

    # 6. Bank Details (IFSC and A/c No.)
    ifsc_match = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", full_text)
    bank_ifsc = ifsc_match.group(1).upper() if ifsc_match else None

    acc_match = re.search(r"A/c\s*No\.?\s*[:#]?\s*(\d{6,18})", full_text, re.IGNORECASE)
    bank_acc = acc_match.group(1).strip() if acc_match else None

    bank_details = None
    if bank_ifsc or bank_acc:
        bank_details = BankDetails(
            ifsc=bank_ifsc,
            account_number=bank_acc,
        )

    # 7. Line items from extracted tables
    line_items: list[ExtractedLine] = []
    for table in tables_data:
        if not table or len(table) < 2:
            continue
        header = [str(c).lower().strip() if c else "" for c in table[0]]
        # Check if table looks like items table (has description or amount)
        if any("desc" in h for h in header) and any("amount" in h or "rate" in h for h in header):
            desc_col = next((i for i, h in enumerate(header) if "desc" in h), 1)
            qty_col = next((i for i, h in enumerate(header) if "qty" in h), -1)
            uom_col = next((i for i, h in enumerate(header) if "uom" in h), -1)
            rate_col = next((i for i, h in enumerate(header) if "rate" in h), -1)
            tax_col = next((i for i, h in enumerate(header) if "gst" in h or "tax" in h), -1)
            amt_col = next((i for i, h in enumerate(header) if "amount" in h), -1)

            for row in table[1:]:
                if not row or len(row) <= desc_col or not row[desc_col]:
                    continue
                desc_text = str(row[desc_col]).strip()
                if not desc_text or desc_text.lower() in ("grand total", "total", "taxable value"):
                    continue

                qty_val = None
                if qty_col != -1 and len(row) > qty_col and row[qty_col]:
                    try:
                        qty_val = Decimal(re.sub(r"[^\d.]", "", str(row[qty_col])))
                    except Exception:
                        pass

                rate_val = None
                if rate_col != -1 and len(row) > rate_col and row[rate_col]:
                    try:
                        rate_val = parse_money(row[rate_col])
                    except Exception:
                        pass

                amt_val = None
                if amt_col != -1 and len(row) > amt_col and row[amt_col]:
                    try:
                        amt_val = parse_money(row[amt_col])
                    except Exception:
                        pass

                tax_rate_val = None
                if tax_col != -1 and len(row) > tax_col and row[tax_col]:
                    try:
                        tax_rate_val = Decimal(re.sub(r"[^\d.]", "", str(row[tax_col])))
                    except Exception:
                        pass

                uom_val = None
                if uom_col != -1 and len(row) > uom_col and row[uom_col]:
                    uom_val = str(row[uom_col]).strip()

                line_items.append(
                    ExtractedLine(
                        description=desc_text,
                        quantity=qty_val,
                        uom=uom_val,
                        unit_price=rate_val,
                        tax_rate_percent=tax_rate_val,
                        line_amount=amt_val,
                    )
                )

    # Vendor Name: often first line or from header
    first_lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    vendor_name = None
    for line in first_lines[:5]:
        if "tax invoice" in line.lower() or "invoice" == line.lower():
            continue
        vendor_name = line
        break

    conf = {
        "vendor_name": 0.60,
        "vendor_gstin": 0.60,
        "invoice_number": 0.60,
        "invoice_date": 0.60,
        "grand_total": 0.60,
        "po_number": 0.60,
        "line_items": 0.60,
    }

    return ExtractedInvoice(
        vendor_name=vendor_name,
        vendor_gstin=vendor_gstin,
        buyer_name="Kestrel Foods Pvt. Ltd.",
        buyer_gstin=buyer_gstin,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_date_raw=invoice_date_raw,
        currency="INR",
        po_number=po_number,
        po_reference_text=po_ref_text,
        amounts_include_tax=False,
        line_items=line_items,
        subtotal=grand_total,
        tax=TaxBreakdown(),
        total_tax=Decimal("0.00"),
        grand_total=grand_total,
        bank_details=bank_details,
        notes=None,
        field_confidence=conf,
        warnings=["Extracted using heuristic fallback reader."],
    )
