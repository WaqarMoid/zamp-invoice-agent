from datetime import date

from app.models import Vendor
from app.rules.money import format_money
from app.schemas import CheckResult, Decision, NormalizedInvoice

VENDOR_FIXABLE_CHECKS = {"C01", "C04", "C09", "C14", "C15", "C16"}


def generate_vendor_email(
    decision: Decision,
    checks: list[CheckResult],
    normalized: NormalizedInvoice | None,
    vendor: Vendor | None,
    po_number: str | None,
) -> dict[str, str] | None:
    """
    Generate deterministic vendor email draft per doc 07 §7.6.
    Only when decision in {REVIEW, REJECT} and at least one flag in {C01, C04, C09(REJECT), C14, C15, C16}.
    Never generated for HOLD.
    """
    if decision.decision not in {"REVIEW", "REJECT"}:
        return None

    # Check for vendor-fixable flags
    flag_map = {c.check_id: c for c in checks if c.outcome == "FLAG"}
    fixable = [cid for cid in ["C01", "C04", "C09", "C14", "C15", "C16"] if cid in flag_map]

    # C09 only counts if REJECT
    if "C09" in fixable and flag_map["C09"].severity != "REJECT":
        fixable.remove("C09")

    if not fixable:
        return None

    # Determine subject line
    today_str = date.today().isoformat()
    if normalized and normalized.invoice_number:
        inv_ref = normalized.invoice_number
        subject = f"Invoice {inv_ref}: action needed"
    elif normalized and normalized.invoice_date:
        inv_ref = f"dated {normalized.invoice_date.isoformat()}"
        subject = f"Invoice {inv_ref}: action needed"
    else:
        inv_ref = f"received {today_str}"
        subject = f"Invoice received {today_str}: action needed"

    # Vendor short name
    vendor_short = "Vendor"
    if vendor:
        # e.g. "Deccan Cold Chain Logistics LLP" -> "Deccan Cold Chain"
        vendor_short = vendor.legal_name.split()[0]
    elif normalized and normalized.vendor_name:
        vendor_short = normalized.vendor_name.split()[0]

    grand_total_str = (
        format_money(normalized.grand_total) if normalized and normalized.grand_total is not None else "0.00"
    )
    po_clause = po_number if po_number else "our order"

    bullets: list[str] = []
    has_c09_reject = False

    for cid in fixable:
        chk = flag_map[cid]
        ev = chk.evidence

        if cid == "C01":
            missing = ev.get("missing_fields", ["required fields"])
            bullets.append(f"- Please include the {', '.join(missing)} on the invoice.")

        elif cid == "C04":
            bullets.append("- The totals do not add up. Please correct and reissue.")

        elif cid == "C09" and chk.severity == "REJECT":
            has_c09_reject = True
            orig_no = ev.get("original_invoice_number", "the original invoice")
            orig_st = ev.get("original_status", "APPROVED").lower()
            bullets.append(
                f"- This appears to be a copy of invoice {orig_no}, which is already {orig_st}. "
                "No further payment is due for it."
            )

        elif cid == "C14":
            violations = ev.get("violations", [])
            for v in violations:
                desc = v.get("description", "item")
                inv_u = format_money(v.get("inv_unit", 0))
                po_u = format_money(v.get("po_unit", 0))
                uom = v.get("uom", "unit")
                bullets.append(
                    f"- {desc} is billed at ₹{inv_u} per {uom}; the PO rate is ₹{po_u}. "
                    "Please issue a credit note or a corrected invoice."
                )

        elif cid == "C15":
            violations = ev.get("violations", [])
            for v in violations:
                desc = v.get("description", "item")
                inv_q = v.get("inv_qty", 0)
                rem = v.get("remaining", 0)
                over = v.get("over", 0)
                uom = v.get("uom", "units")
                po_ref = po_number or "the PO"
                bullets.append(
                    f"- {desc}: {inv_q} {uom} billed, but only {rem} remain on {po_ref}. "
                    f"We can pay for {rem} now; please send a credit note for {over}."
                )

        elif cid == "C16":
            bullets.append(f"- GST is charged incorrectly ({chk.message}). Please reissue.")

    bullet_text = "\n".join(bullets)
    reminder_clause = "\nNo action is needed if this was a reminder.\n" if has_c09_reject else ""

    intro = (
        f"We received your invoice {inv_ref} for ₹{grand_total_str} against {po_clause}. "
        "Before we can process it, we need the following:"
    )
    body = f"""Hello {vendor_short} team,

{intro}

{bullet_text}
{reminder_clause}
Thank you,
Accounts Payable, Kestrel Foods Pvt. Ltd."""

    return {"subject": subject, "body": body.strip()}
