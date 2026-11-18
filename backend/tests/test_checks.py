from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import POLine, PurchaseOrder, Vendor
from app.rules.checks import (
    check_c01,
    check_c02,
    check_c03,
    check_c04,
    check_c05,
    check_c06,
    check_c07,
    check_c08,
    check_c09,
    check_c10,
    check_c11,
    check_c12,
    check_c13,
    check_c14,
    check_c15,
    check_c16,
    check_c17,
    check_c20,
    check_c21,
    today_ist,
)
from app.schemas import (
    BankDetails,
    ExtractedInvoice,
    ExtractedLine,
    NormalizedInvoice,
    NormalizedLine,
)
from app.seed import seed


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        seed(session, force=True)
        yield session


def test_c01_required_fields():
    # Pass
    ext_ok = ExtractedInvoice(
        vendor_name="Acme",
        invoice_number="INV-1",
        invoice_date="2026-04-10",
        grand_total=Decimal("100.00"),
        line_items=[ExtractedLine(description="Item 1")],
    )
    res = check_c01(ext_ok)
    assert res.outcome == "PASS"

    # Flag
    ext_bad = ExtractedInvoice(
        vendor_name="",
        invoice_number=None,
        invoice_date=None,
        grand_total=None,
        line_items=[],
    )
    res_bad = check_c01(ext_bad)
    assert res_bad.outcome == "FLAG"
    assert res_bad.severity == "REVIEW"


def test_c02_confidence():
    ext_ok = ExtractedInvoice(
        vendor_name="Acme",
        field_confidence={"vendor_name": 0.95},
    )
    assert check_c02(ext_ok).outcome == "PASS"

    ext_bad = ExtractedInvoice(
        vendor_name="Acme",
        field_confidence={"vendor_name": 0.65},
    )
    res = check_c02(ext_bad)
    assert res.outcome == "FLAG"
    assert res.severity == "REVIEW"


def test_c03_billed_to_us():
    ext_ok = ExtractedInvoice(buyer_gstin="29AAACK4521M1ZD")
    assert check_c03(ext_ok).outcome == "PASS"

    ext_none = ExtractedInvoice(buyer_gstin=None)
    res_none = check_c03(ext_none)
    assert res_none.outcome == "FLAG"
    assert res_none.severity == "REVIEW"

    ext_diff = ExtractedInvoice(buyer_gstin="29AABCU9603R1ZM")
    res_diff = check_c03(ext_diff)
    assert res_diff.outcome == "FLAG"
    assert res_diff.severity == "REJECT"


def test_c04_arithmetic():
    norm_ok = NormalizedInvoice(
        lines=[
            NormalizedLine(
                index=1,
                description="L1",
                quantity=Decimal("2"),
                unit_price_net=Decimal("10"),
                unit_price_printed=Decimal("10"),
                tax_rate_percent=Decimal("18"),
                line_net=Decimal("20"),
                line_printed=Decimal("20"),
            )
        ],
        net_total=Decimal("20"),
        total_tax=Decimal("3.60"),
        grand_total=Decimal("23.60"),
    )
    ext_ok = ExtractedInvoice(subtotal=Decimal("20"))
    assert check_c04(ext_ok, norm_ok).outcome == "PASS"

    norm_bad = norm_ok.model_copy(update={"grand_total": Decimal("50.00")})
    assert check_c04(ext_ok, norm_bad).outcome == "FLAG"


def test_c05_vendor_status(db_session: Session):
    active_v = db_session.query(Vendor).filter_by(vendor_id="V001").first()
    assert check_c05(active_v).outcome == "PASS"

    inactive_v = db_session.query(Vendor).filter_by(vendor_id="V006").first()
    res = check_c05(inactive_v)
    assert res.outcome == "FLAG"
    assert res.severity == "REJECT"


def test_c06_vendor_identity(db_session: Session):
    v1 = db_session.query(Vendor).filter_by(vendor_id="V001").first()
    ext_ok = ExtractedInvoice(vendor_name=v1.legal_name, vendor_gstin=v1.gstin)
    assert check_c06(ext_ok, v1, "GSTIN").outcome == "PASS"

    # Unknown
    res_unknown = check_c06(ext_ok, None, "none")
    assert res_unknown.outcome == "FLAG"
    assert res_unknown.severity == "REJECT"

    # Master mismatch
    ext_diff_gstin = ExtractedInvoice(vendor_name=v1.legal_name, vendor_gstin="29AABCU9603R1ZM")
    res_mismatch = check_c06(ext_diff_gstin, v1, "name")
    assert res_mismatch.outcome == "FLAG"
    assert res_mismatch.severity == "HOLD"

    # Bad checksum
    ext_bad_gst = ExtractedInvoice(vendor_name=v1.legal_name, vendor_gstin="29AAACK4521M1ZZ")
    res_bad = check_c06(ext_bad_gst, v1, "name")
    assert res_bad.outcome == "FLAG"
    assert res_bad.severity == "HOLD"


def test_c07_bank_details(db_session: Session):
    v = db_session.query(Vendor).filter_by(vendor_id="V001").first()
    ext_ok = ExtractedInvoice(
        bank_details=BankDetails(ifsc=v.bank_ifsc, account_number=v.bank_account_number)
    )
    assert check_c07(ext_ok, v).outcome == "PASS"

    ext_none = ExtractedInvoice(bank_details=None)
    assert check_c07(ext_none, v).outcome == "INFO"

    ext_fraud = ExtractedInvoice(bank_details=BankDetails(ifsc="HDFC0001234", account_number="999988887777"))
    res_hold = check_c07(ext_fraud, v)
    assert res_hold.outcome == "FLAG"
    assert res_hold.severity == "HOLD"


def test_c08_invoice_date():
    today = today_ist()
    assert check_c08(today).outcome == "PASS"

    future = today + timedelta(days=5)
    res_future = check_c08(future)
    assert res_future.outcome == "FLAG"
    assert res_future.severity == "REVIEW"

    old = today - timedelta(days=400)
    res_old = check_c08(old)
    assert res_old.outcome == "FLAG"
    assert res_old.severity == "REVIEW"


def test_c09_duplicate(db_session: Session):
    norm = NormalizedInvoice(
        invoice_number="SPS/26-27/0512",
        invoice_number_norm="SPS-26-27-512",
        invoice_date=date(2026, 4, 10),
        grand_total=Decimal("129682.00"),
    )
    # No duplicate for V001 initially
    res_ok = check_c09(db_session, norm, "V001")
    assert res_ok.outcome == "PASS"

    # Seed has invoice BIS-INV-2026-0089 for V003
    norm_dup = NormalizedInvoice(
        invoice_number="BIS/INV/26/89",
        invoice_number_norm="BIS-INV-26-89",
        invoice_date=date(2026, 11, 2),
        grand_total=Decimal("413000.00"),
    )
    res_dup = check_c09(db_session, norm_dup, "V003")
    assert res_dup.outcome == "FLAG"
    assert res_dup.severity == "REJECT"


def test_c10_po_identified(db_session: Session):
    po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0412").first()
    assert check_c10(po, "explicit", [], "PO-2026-0412").outcome == "PASS"

    res_inferred = check_c10(po, "inferred", [{"po_number": po.po_number, "score": 0.95}], None)
    assert res_inferred.outcome == "FLAG"
    assert res_inferred.severity == "REVIEW"

    res_none = check_c10(None, "none", [], None)
    assert res_none.outcome == "FLAG"
    assert res_none.severity == "REVIEW"


def test_c11_po_belongs_to_vendor(db_session: Session):
    po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0412").first()
    v1 = db_session.query(Vendor).filter_by(vendor_id="V001").first()
    v2 = db_session.query(Vendor).filter_by(vendor_id="V002").first()

    assert check_c11(po, v1).outcome == "PASS"
    res_wrong = check_c11(po, v2)
    assert res_wrong.outcome == "FLAG"
    assert res_wrong.severity == "REVIEW"


def test_c12_po_status(db_session: Session):
    open_po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0412").first()
    assert check_c12(open_po).outcome == "PASS"

    closed_po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0377").first()
    res_closed = check_c12(closed_po)
    assert res_closed.outcome == "FLAG"
    assert res_closed.severity == "REJECT"


def test_c13_line_matching(db_session: Session):
    po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0412").first()
    assert check_c13([{"inv_index": 1, "po_line_no": 1, "score": 1.0}], [], po).outcome == "PASS"

    unmatched = [
        NormalizedLine(
            index=2,
            description="Extra",
            quantity=Decimal("1"),
            unit_price_net=Decimal("10"),
            unit_price_printed=Decimal("10"),
            tax_rate_percent=Decimal("18"),
            line_net=Decimal("10"),
            line_printed=Decimal("10"),
        )
    ]
    res_unmatched = check_c13([], unmatched, po)
    assert res_unmatched.outcome == "FLAG"
    assert res_unmatched.severity == "REVIEW"


def test_c14_price_variance():
    pol = POLine(line_no=1, quantity=10, unit_price_paise=10000, tax_rate=18)
    po = PurchaseOrder(po_number="PO-1", lines=[pol])

    # Pass: 10 units @ 100 net = 1000 net (matches PO 100.00 exactly)
    inv_ok = NormalizedLine(
        index=1,
        description="Box",
        quantity=Decimal("10"),
        unit_price_net=Decimal("100.00"),
        unit_price_printed=Decimal("100.00"),
        tax_rate_percent=Decimal("18"),
        line_net=Decimal("1000.00"),
        line_printed=Decimal("1000.00"),
    )
    pair_ok = [{"inv_line": inv_ok, "po_line": pol}]
    assert check_c14(pair_ok, po).outcome == "PASS"

    # Overbilled: 10 units billed @ 120 net = 1200 net (+20%, tolerance is min(10, 1000)=10)
    inv_over = inv_ok.model_copy(update={"unit_price_net": Decimal("120.00"), "line_net": Decimal("1200.00")})
    res_over = check_c14([{"inv_line": inv_over, "po_line": pol}], po)
    assert res_over.outcome == "FLAG"
    assert res_over.severity == "REVIEW"


def test_c15_quantity_unbilled(db_session: Session):
    po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0418").first()
    pol = po.lines[0]  # ordered 50, 40 consumed, 10 remaining

    # Pass: bill 10
    inv_ok = NormalizedLine(
        index=1,
        description="Mango",
        quantity=Decimal("10.00"),
        unit_price_net=Decimal("185000.00"),
        unit_price_printed=Decimal("185000.00"),
        tax_rate_percent=Decimal("12"),
        line_net=Decimal("1850000.00"),
        line_printed=Decimal("1850000.00"),
    )
    assert check_c15(db_session, [{"inv_line": inv_ok, "po_line": pol}], po).outcome == "PASS"

    # Flag: bill 14 (over by 4)
    inv_over = inv_ok.model_copy(update={"quantity": Decimal("14.00")})
    res_over = check_c15(db_session, [{"inv_line": inv_over, "po_line": pol}], po)
    assert res_over.outcome == "FLAG"
    assert res_over.severity == "REVIEW"


def test_c16_tax(db_session: Session):
    v_intra = db_session.query(Vendor).filter_by(vendor_id="V001").first()  # State 29
    po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0412").first()
    pol = po.lines[0]

    norm_ok = NormalizedInvoice(
        lines=[
            NormalizedLine(
                index=1,
                description="Box",
                quantity=Decimal("10"),
                unit_price_net=Decimal("100"),
                unit_price_printed=Decimal("100"),
                tax_rate_percent=Decimal("18"),
                line_net=Decimal("1000"),
                line_printed=Decimal("1000"),
            )
        ],
        cgst=Decimal("90.00"),
        sgst=Decimal("90.00"),
        igst=Decimal("0.00"),
        total_tax=Decimal("180.00"),
    )
    pair = [{"inv_line": norm_ok.lines[0], "po_line": pol}]
    assert check_c16(norm_ok, pair, po, v_intra).outcome == "PASS"

    # Wrong regime: intra charged IGST
    norm_wrong_regime = norm_ok.model_copy(
        update={"cgst": Decimal("0.00"), "sgst": Decimal("0.00"), "igst": Decimal("180.00")}
    )
    res_wrong = check_c16(norm_wrong_regime, pair, po, v_intra)
    assert res_wrong.outcome == "FLAG"
    assert res_wrong.severity == "REVIEW"


def test_c17_currency():
    assert check_c17("INR").outcome == "PASS"
    res_usd = check_c17("USD")
    assert res_usd.outcome == "FLAG"
    assert res_usd.severity == "REVIEW"


def test_c20_po_validity(db_session: Session):
    po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0412").first()
    # po_date is 2026-10-20, valid_until is 2026-12-31
    assert check_c20(po, date(2026, 11, 15)).outcome == "PASS"

    # Outside validity
    res_out = check_c20(po, date(2026, 7, 1))
    assert res_out.outcome == "FLAG"
    assert res_out.severity == "REVIEW"


def test_c21_tax_inclusive():
    norm_false = NormalizedInvoice(amounts_include_tax=False)
    assert check_c21(norm_false) is None

    norm_true = NormalizedInvoice(
        amounts_include_tax=True,
        lines=[
            NormalizedLine(
                index=1,
                description="Item",
                quantity=Decimal("1"),
                unit_price_net=Decimal("100"),
                unit_price_printed=Decimal("105"),
                tax_rate_percent=Decimal("5"),
                line_net=Decimal("100"),
                line_printed=Decimal("105"),
            )
        ],
    )
    res = check_c21(norm_true)
    assert res is not None
    assert res.outcome == "INFO"
