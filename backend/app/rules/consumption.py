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
