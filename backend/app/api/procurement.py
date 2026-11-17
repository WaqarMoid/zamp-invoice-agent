from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import InvoiceLedger, PurchaseOrder, Vendor
from app.rules.consumption import get_po_consumption_map
from app.rules.money import format_rupees, from_paise
from app.schemas import (
    LedgerEntryOut,
    POLineOut,
    PurchaseOrderDetailOut,
    PurchaseOrderOut,
    VendorOut,
)

router = APIRouter(prefix="/api", tags=["procurement"])


def mask_bank_account(acc: str | None) -> str:
    """Mask bank account to '••••' + last 4 digits per doc 04 §4.5."""
    if not acc:
        return "••••"
    digits = "".join(c for c in acc if c.isdigit())
    last4 = digits[-4:] if len(digits) >= 4 else digits
    return f"••••{last4}"


def format_qty(qty: Decimal | float | int | None) -> str:
    """Format quantity, stripping trailing zeros, e.g. 2000.000 -> '2000', 12.500 -> '12.5'."""
    if qty is None:
        return "0"
    dec = Decimal(str(qty))
    s = f"{dec:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def format_rate(rate: Decimal | float | int | None) -> str:
    """Format tax rate, e.g. 18.00 -> '18'."""
    if rate is None:
        return "0"
    dec = Decimal(str(rate))
    s = f"{dec:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(db: Session = Depends(get_db)):
    """List all vendors with masked bank accounts."""
    stmt = select(Vendor).order_by(Vendor.vendor_id)
    vendors = db.execute(stmt).scalars().all()
    out = []
    for v in vendors:
        out.append(
            VendorOut(
                vendor_id=v.vendor_id,
                legal_name=v.legal_name,
                aliases=v.aliases or [],
                gstin=v.gstin,
                pan=v.pan,
                state_code=v.state_code,
                address=v.address,
                status=v.status,
                deactivated_on=v.deactivated_on,
                bank_name=v.bank_name,
                bank_ifsc=v.bank_ifsc,
                bank_account_masked=mask_bank_account(v.bank_account_number),
                payment_terms_days=v.payment_terms_days,
                contact_email=v.contact_email,
            )
        )
    return out


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(db: Session = Depends(get_db)):
    """List all purchase orders with consumption information."""
    stmt = (
        select(PurchaseOrder)
        .options(joinedload(PurchaseOrder.vendor), joinedload(PurchaseOrder.lines))
        .order_by(PurchaseOrder.po_number)
    )
    pos = db.execute(stmt).unique().scalars().all()

    out = []
    for po in pos:
        consumption_map = get_po_consumption_map(db, po.po_number)
        po_lines_out = []
        total_ordered_paise = 0
        total_billed_paise = 0

        for line in po.lines:
            ordered_qty = Decimal(str(line.quantity))
            billed_qty = consumption_map.get(line.line_no, Decimal("0.0"))
            rem_qty = max(Decimal("0.0"), ordered_qty - billed_qty)

            unit_price_dec = from_paise(line.unit_price_paise)
            line_ordered_paise = int(ordered_qty * line.unit_price_paise)
            line_billed_paise = int(billed_qty * line.unit_price_paise)
            total_ordered_paise += line_ordered_paise
            total_billed_paise += line_billed_paise

            po_lines_out.append(
                POLineOut(
                    line_no=line.line_no,
                    description=line.description,
                    hsn_sac=line.hsn_sac,
                    uom=line.uom,
                    quantity=format_qty(ordered_qty),
                    unit_price=format_rupees(unit_price_dec),
                    tax_rate=format_rate(line.tax_rate),
                    billed_quantity=format_qty(billed_qty),
                    remaining_quantity=format_qty(rem_qty),
                )
            )

        if total_billed_paise == 0:
            billing_state = "UNBILLED"
        elif total_billed_paise < total_ordered_paise:
            billing_state = "PARTIALLY_BILLED"
        elif total_billed_paise == total_ordered_paise:
            billing_state = "FULLY_BILLED"
        else:
            billing_state = "OVERBILLED"

        pct = (
            round((total_billed_paise / total_ordered_paise) * 100, 1)
            if total_ordered_paise > 0
            else 0.0
        )

        out.append(
            PurchaseOrderOut(
                po_number=po.po_number,
                vendor_id=po.vendor_id,
                vendor_name=po.vendor.legal_name if po.vendor else "",
                po_date=po.po_date.isoformat(),
                valid_until=po.valid_until.isoformat(),
                status=po.status,
                po_number_norm=po.po_number_norm,
                total_amount=format_rupees(from_paise(total_ordered_paise)),
                lines=po_lines_out,
                billing_state=billing_state,
                billed_percentage=pct,
            )
        )
    return out


@router.get("/purchase-orders/{po_number}", response_model=PurchaseOrderDetailOut)
def get_purchase_order(po_number: str, db: Session = Depends(get_db)):
    """Get single purchase order detail with all ledger entries."""
    stmt = (
        select(PurchaseOrder)
        .options(joinedload(PurchaseOrder.vendor), joinedload(PurchaseOrder.lines))
        .where(PurchaseOrder.po_number == po_number)
    )
    po = db.execute(stmt).unique().scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order '{po_number}' not found")

    consumption_map = get_po_consumption_map(db, po.po_number)
    po_lines_out = []
    total_ordered_paise = 0
    total_billed_paise = 0

    for line in po.lines:
        ordered_qty = Decimal(str(line.quantity))
        billed_qty = consumption_map.get(line.line_no, Decimal("0.0"))
        rem_qty = max(Decimal("0.0"), ordered_qty - billed_qty)

        unit_price_dec = from_paise(line.unit_price_paise)
        total_ordered_paise += int(ordered_qty * line.unit_price_paise)
        total_billed_paise += int(billed_qty * line.unit_price_paise)

        po_lines_out.append(
            POLineOut(
                line_no=line.line_no,
                description=line.description,
                hsn_sac=line.hsn_sac,
                uom=line.uom,
                quantity=format_qty(ordered_qty),
                unit_price=format_rupees(unit_price_dec),
                tax_rate=format_rate(line.tax_rate),
                billed_quantity=format_qty(billed_qty),
                remaining_quantity=format_qty(rem_qty),
            )
        )

    if total_billed_paise == 0:
        billing_state = "UNBILLED"
    elif total_billed_paise < total_ordered_paise:
        billing_state = "PARTIALLY_BILLED"
    elif total_billed_paise == total_ordered_paise:
        billing_state = "FULLY_BILLED"
    else:
        billing_state = "OVERBILLED"

    pct = (
        round((total_billed_paise / total_ordered_paise) * 100, 1)
        if total_ordered_paise > 0
        else 0.0
    )

    # Invoices in ledger for this PO
    invoices_stmt = (
        select(InvoiceLedger)
        .where(InvoiceLedger.po_number == po_number)
        .order_by(InvoiceLedger.id)
    )
    invoices = db.execute(invoices_stmt).scalars().all()
    invoices_out = [
        LedgerEntryOut(
            id=inv.id,
            source=inv.source,
            run_id=inv.run_id,
            vendor_id=inv.vendor_id,
            invoice_number=inv.invoice_number,
            invoice_date=inv.invoice_date.isoformat() if inv.invoice_date else None,
            po_number=inv.po_number,
            net_amount=format_rupees(from_paise(inv.net_paise)),
            tax_amount=format_rupees(from_paise(inv.tax_paise)),
            grand_total=format_rupees(from_paise(inv.grand_total_paise)),
            status=inv.status,
            created_at=inv.created_at.isoformat(),
        )
        for inv in invoices
    ]

    return PurchaseOrderDetailOut(
        po_number=po.po_number,
        vendor_id=po.vendor_id,
        vendor_name=po.vendor.legal_name if po.vendor else "",
        po_date=po.po_date.isoformat(),
        valid_until=po.valid_until.isoformat(),
        status=po.status,
        po_number_norm=po.po_number_norm,
        total_amount=format_rupees(from_paise(total_ordered_paise)),
        lines=po_lines_out,
        billing_state=billing_state,
        billed_percentage=pct,
        invoices=invoices_out,
    )
