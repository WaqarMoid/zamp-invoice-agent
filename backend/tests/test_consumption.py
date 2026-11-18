from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import InvoiceLedger, LedgerLine, PurchaseOrder
from app.rules.consumption import (
    get_po_line_consumed,
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


def test_seed_consumption(db_session: Session):
    # PO-2026-0418 ordered 50 MT, 40 MT already billed in seed (approved ledger entry)
    po = db_session.query(PurchaseOrder).filter_by(po_number="PO-2026-0418").first()
    assert po is not None
    assert len(po.lines) == 1
    line1 = po.lines[0]
    assert Decimal(str(line1.quantity)) == Decimal("50.000")

    consumed = get_po_line_consumed(db_session, "PO-2026-0418", line1.line_no)
    assert consumed == Decimal("40.000")

    remaining_qty = Decimal(str(line1.quantity)) - consumed
    assert remaining_qty == Decimal("10.000")


def test_review_status_does_not_consume(db_session: Session):
    # Add a ledger row with status IN_REVIEW
    ledger = InvoiceLedger(
        source="run",
        vendor_id="V002",
        invoice_number="INV-TEST-001",
        po_number="PO-2026-0418",
        status="IN_REVIEW",
        net_paise=100000,
        tax_paise=18000,
        grand_total_paise=118000,
    )
    db_session.add(ledger)
    db_session.flush()

    line = LedgerLine(
        ledger_id=ledger.id,
        po_number="PO-2026-0418",
        po_line_no=1,
        description="Frozen Alphonso Mango Puree",
        quantity=5.0,
        unit_price_paise=18500000,
        net_paise=92500000,
    )
    db_session.add(line)
    db_session.commit()

    # Consumed must still be 40.000 (IN_REVIEW does not consume)
    consumed = get_po_line_consumed(db_session, "PO-2026-0418", 1)
    assert consumed == Decimal("40.000")
