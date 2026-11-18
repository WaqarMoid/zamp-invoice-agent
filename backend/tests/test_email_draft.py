from decimal import Decimal

from app.models import Vendor
from app.rules.email_draft import generate_vendor_email
from app.schemas import CheckResult, Decision, NormalizedInvoice


def test_f02_email_draft():
    decision = Decision(
        decision="REVIEW",
        label="Needs review",
        headline="Needs review",
    )
    chk_c15 = CheckResult(
        check_id="C15",
        stage_key="reconcile",
        name="Quantity vs unbilled",
        outcome="FLAG",
        severity="REVIEW",
        message="Quantity over-billing",
        evidence={
            "violations": [
                {
                    "description": "Frozen Alphonso Mango Puree",
                    "inv_qty": 14.0,
                    "remaining": 10.0,
                    "over": 4.0,
                    "uom": "MT",
                }
            ]
        },
    )
    norm = NormalizedInvoice(
        invoice_number="DCC/2627/0788",
        grand_total=Decimal("2900000.00"),
    )
    vendor = Vendor(legal_name="Deccan Cold Chain Logistics LLP")

    email = generate_vendor_email(decision, [chk_c15], norm, vendor, "PO-2026-0418")
    assert email is not None
    assert "DCC/2627/0788" in email["subject"]
    body = email["body"]
    assert "10" in body
    assert "credit note for 4" in body


def test_hold_never_generates_draft():
    decision = Decision(
        decision="HOLD",
        label="On hold",
        headline="Payment on hold",
    )
    chk_c07 = CheckResult(
        check_id="C07",
        stage_key="vendor",
        name="Bank details",
        outcome="FLAG",
        severity="HOLD",
        message="Bank mismatch",
    )
    norm = NormalizedInvoice(invoice_number="INV-001")
    email = generate_vendor_email(decision, [chk_c07], norm, None, "PO-1")
    assert email is None
