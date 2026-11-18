from decimal import ROUND_HALF_UP, Decimal

from app.config import get_settings
from app.pipeline.context import RunContext
from app.rules.checks import (
    check_c01,
    check_c02,
    check_c03,
    check_c04,
    check_c08,
    check_c17,
    check_c21,
)
from app.rules.dates import extract_date_from_text, parse_date
from app.rules.money import format_money
from app.rules.text import normalize_invoice_number, normalize_po_number
from app.schemas import CheckResult, NormalizedInvoice, NormalizedLine, StageOutcome


def round_2dp(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def run(ctx: RunContext) -> StageOutcome:
    settings = get_settings()
    ext = ctx.extraction
    if not ext:
        return StageOutcome(
            status="FAILED",
            summary="Skipped: needs output from Extract stage",
            output={"error": "Extraction missing"},
            checks=[],
        )

    # 1. Clean strings and normalise IDs
    vendor_gstin = "".join(ext.vendor_gstin.split()).upper() if ext.vendor_gstin else None
    buyer_gstin = "".join(ext.buyer_gstin.split()).upper() if ext.buyer_gstin else None

    inv_num = ext.invoice_number.strip() if ext.invoice_number else None
    inv_num_norm = normalize_invoice_number(inv_num) if inv_num else None

    po_num = ext.po_number.strip() if ext.po_number else None
    po_num_norm = normalize_po_number(po_num) if po_num else None

    # Dates
    inv_date = None
    if ext.invoice_date:
        try:
            inv_date = parse_date(ext.invoice_date)
        except Exception:
            pass
    if not inv_date and ext.invoice_date_raw:
        try:
            inv_date = parse_date(ext.invoice_date_raw)
        except Exception:
            pass

    ref_date = None
    if ext.po_reference_text:
        ref_date = extract_date_from_text(ext.po_reference_text)

    # Lines normalisation & tax-inclusive conversion
    lines: list[NormalizedLine] = []
    incl_tax = ext.amounts_include_tax

    for idx, item in enumerate(ext.line_items, start=1):
        qty = item.quantity or Decimal("0.00")
        u_printed = item.unit_price or Decimal("0.00")
        l_printed = item.line_amount or (qty * u_printed)
        rate = item.tax_rate_percent or Decimal("0.00")

        if incl_tax and rate > 0:
            divisor = Decimal("1.00") + (rate / Decimal("100.00"))
            u_net = round_2dp(u_printed / divisor)
            l_net = round_2dp(l_printed / divisor)
        else:
            u_net = round_2dp(u_printed)
            l_net = round_2dp(l_printed)

        lines.append(
            NormalizedLine(
                index=idx,
                description=item.description,
                hsn_sac=item.hsn_sac,
                quantity=qty,
                uom=item.uom,
                unit_price_net=u_net,
                unit_price_printed=u_printed,
                tax_rate_percent=rate,
                line_net=l_net,
                line_printed=l_printed,
            )
        )

    # Header taxes
    cgst = ext.tax.cgst or Decimal("0.00")
    sgst = ext.tax.sgst or Decimal("0.00")
    igst = ext.tax.igst or Decimal("0.00")
    total_tax = ext.total_tax if ext.total_tax is not None else (cgst + sgst + igst)

    # Net total
    if incl_tax and ext.grand_total is not None and ext.total_tax is not None:
        net_total = ext.grand_total - ext.total_tax
    else:
        net_total = sum(line.line_net for line in lines)

    # Bank digits
    bank_ifsc = (
        ext.bank_details.ifsc.upper().strip() if (ext.bank_details and ext.bank_details.ifsc) else None
    )
    bank_digits = (
        "".join(filter(str.isdigit, ext.bank_details.account_number))
        if (ext.bank_details and ext.bank_details.account_number)
        else None
    )

    normalized = NormalizedInvoice(
        vendor_name=ext.vendor_name,
        vendor_gstin=vendor_gstin,
        buyer_gstin=buyer_gstin,
        invoice_number=inv_num,
        invoice_number_norm=inv_num_norm,
        invoice_date=inv_date,
        currency=ext.currency or "INR",
        po_number=po_num,
        po_number_norm=po_num_norm,
        po_reference_text=ext.po_reference_text,
        po_reference_date=ref_date,
        amounts_include_tax=incl_tax,
        lines=lines,
        net_total=net_total,
        cgst=cgst,
        sgst=sgst,
        igst=igst,
        total_tax=total_tax,
        grand_total=ext.grand_total,
        bank_ifsc=bank_ifsc,
        bank_account_digits=bank_digits,
    )
    ctx.normalized = normalized

    # 2. Run checks: C01, C02, C03, C04, C08, C17, C21
    checks: list[CheckResult] = []
    checks.append(check_c01(ext))
    checks.append(check_c02(ext, min_confidence=settings.EXTRACTION_MIN_CONFIDENCE))
    checks.append(check_c03(ext, buyer_gstin_expected=settings.BUYER_GSTIN))
    checks.append(check_c04(ext, normalized, rounding_tol=Decimal(str(settings.ROUNDING_TOLERANCE_INR))))
    checks.append(check_c08(inv_date, max_age_days=settings.MAX_INVOICE_AGE_DAYS))
    checks.append(check_c17(ext.currency))

    c21_res = check_c21(normalized)
    if c21_res:
        checks.append(c21_res)

    ctx.all_checks.extend(checks)

    flag_count = sum(1 for c in checks if c.outcome == "FLAG")
    status = "FLAGGED" if flag_count > 0 else "PASSED"

    gt_str = f"₹{format_money(normalized.grand_total)}" if normalized.grand_total is not None else "₹0.00"
    m_lines = len(lines)
    if flag_count > 0:
        summary = f"{gt_str} total, {m_lines} lines, {flag_count} issue(s)"
    else:
        summary = f"Clean: {gt_str}, {m_lines} lines"

    output = normalized.model_dump(mode="json")
    ctx.stage_outputs["normalize"] = output

    return StageOutcome(
        status=status,
        summary=summary,
        output=output,
        checks=checks,
    )
