from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import PurchaseOrder, Vendor
from app.rules.matching import infer_po_for_invoice, match_invoice_lines_to_po
from app.schemas import NormalizedInvoice, NormalizedLine
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


def test_f01_line_matching(db_session: Session):
    po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0412").first()
    assert po is not None

    inv_lines = [
        NormalizedLine(
            index=1,
            description="Corrugated Box 5 Ply (18x12x12 inch)",
            hsn_sac="481910",
            quantity=Decimal("2000.00"),
            uom="BOX",
            unit_price_net=Decimal("42.50"),
            unit_price_printed=Decimal("42.50"),
            tax_rate_percent=Decimal("18.00"),
            line_net=Decimal("85000.00"),
            line_printed=Decimal("85000.00"),
        ),
        NormalizedLine(
            index=2,
            description="LDPE Food Grade Liner 20 mic",
            hsn_sac="392321",
            quantity=Decimal("2000.00"),
            uom="NOS",
            unit_price_net=Decimal("6.75"),
            unit_price_printed=Decimal("6.75"),
            tax_rate_percent=Decimal("18.00"),
            line_net=Decimal("13500.00"),
            line_printed=Decimal("13500.00"),
        ),
        NormalizedLine(
            index=3,
            description="BOPP Tape 48mm x 65m",
            hsn_sac="391910",
            quantity=Decimal("300.00"),
            uom="ROLL",
            unit_price_net=Decimal("38.00"),
            unit_price_printed=Decimal("38.00"),
            tax_rate_percent=Decimal("18.00"),
            line_net=Decimal("11400.00"),
            line_printed=Decimal("11400.00"),
        ),
    ]

    matched, unmatched = match_invoice_lines_to_po(inv_lines, po.lines)
    assert len(unmatched) == 0
    assert len(matched) == 3

    # Check line mappings
    mapping = {m["inv_index"]: m["po_line_no"] for m in matched}
    assert mapping[1] == 1
    assert mapping[2] == 2
    assert mapping[3] == 3


def test_f03_po_inference(db_session: Session):
    vendor = db_session.query(Vendor).filter_by(vendor_id="V004").first()
    assert vendor is not None

    inv_lines = [
        NormalizedLine(
            index=1,
            description="Organic Jaggery Powder (25 kg bag)",
            hsn_sac="170114",
            quantity=Decimal("40.00"),
            uom="BAG",
            unit_price_net=Decimal("1850.00"),
            unit_price_printed=Decimal("1850.00"),
            tax_rate_percent=Decimal("5.00"),
            line_net=Decimal("74000.00"),
            line_printed=Decimal("74000.00"),
        ),
        NormalizedLine(
            index=2,
            description="Rock Salt Himalayan (25 kg bag)",
            hsn_sac="250100",
            quantity=Decimal("20.00"),
            uom="BAG",
            unit_price_net=Decimal("640.00"),
            unit_price_printed=Decimal("640.00"),
            tax_rate_percent=Decimal("5.00"),
            line_net=Decimal("12800.00"),
            line_printed=Decimal("12800.00"),
        ),
    ]

    norm = NormalizedInvoice(
        vendor_name="GreenLeaf Agro Supplies",
        po_number=None,
        po_number_norm=None,
        po_reference_text="Ref Order dated 2026-04-14",
        lines=inv_lines,
        net_total=Decimal("86800.00"),
        total_tax=Decimal("4340.00"),
        grand_total=Decimal("91140.00"),
    )

    matched_po, method, candidates = infer_po_for_invoice(db_session, norm, vendor.vendor_id)
    assert method == "inferred"
    assert matched_po is not None
    assert matched_po.po_number == "PO-2026-0431"

    cand_scores = {c["po_number"]: c["score"] for c in candidates}
    assert cand_scores["PO-2026-0431"] == 1.000
    assert cand_scores.get("PO-2026-0427", 0.0) < 0.05
