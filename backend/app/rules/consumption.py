from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import InvoiceLedger, LedgerLine


def get_po_line_consumed(session: Session, po_number: str, line_no: int) -> Decimal:
    """
    Returns the sum of quantities billed for a specific PO line from APPROVED ledger rows.
    In-review or on-hold invoices do not consume PO balance.
    """
    stmt = (
        select(func.coalesce(func.sum(LedgerLine.quantity), 0))
        .join(InvoiceLedger, LedgerLine.ledger_id == InvoiceLedger.id)
        .where(
            LedgerLine.po_number == po_number,
            LedgerLine.po_line_no == line_no,
            InvoiceLedger.status == "APPROVED",
        )
    )
    result = session.execute(stmt).scalar()
    return Decimal(str(result or 0))


def get_po_consumption_map(session: Session, po_number: str) -> dict[int, Decimal]:
    """
    Returns a dict mapping line_no -> consumed Decimal quantity for all lines of a PO.
    """
    stmt = (
        select(LedgerLine.po_line_no, func.coalesce(func.sum(LedgerLine.quantity), 0))
        .join(InvoiceLedger, LedgerLine.ledger_id == InvoiceLedger.id)
        .where(
            LedgerLine.po_number == po_number,
            InvoiceLedger.status == "APPROVED",
        )
        .group_by(LedgerLine.po_line_no)
    )
    rows = session.execute(stmt).all()
    return {row[0]: Decimal(str(row[1])) for row in rows if row[0] is not None}


def get_po_remaining_net(session: Session, po_number: str) -> Decimal:
    """
    Returns the remaining unbilled net amount in rupees for a PO across all lines.
    net = sum(max(0, line.quantity - consumed) * (line.unit_price_paise / 100))
    """
    from app.models import PurchaseOrder

    po = session.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first()
    if not po:
        return Decimal("0.00")

    consumed_map = get_po_consumption_map(session, po_number)
    remaining_net = Decimal("0.00")

    for line in po.lines:
        line_qty = Decimal(str(line.quantity))
        consumed = consumed_map.get(line.line_no, Decimal("0.00"))
        remaining_qty = max(Decimal("0.00"), line_qty - consumed)
        unit_price = Decimal(str(line.unit_price_paise)) / Decimal("100")
        remaining_net += remaining_qty * unit_price

    return remaining_net
