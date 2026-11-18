import json
import logging
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Document,
    InvoiceLedger,
    LedgerLine,
    POLine,
    PurchaseOrder,
    Run,
    RunCheck,
    RunEvent,
    RunStage,
    Vendor,
)
from app.rules.dates import parse_date
from app.rules.money import to_paise
from app.rules.text import normalize_invoice_number, normalize_po_number

logger = logging.getLogger("kestrel-ap.seed")

SEED_DIR = Path(__file__).resolve().parent / "seed_data"


def seed(session: Session, force: bool = False) -> None:
    """
    Seed database with vendors, purchase orders, and prior approved invoices per doc 05 §5.1.
    If force=True, wipe existing data before seeding.
    """
    if force:
        logger.info("Force seed requested: wiping data in dependency order...")
        session.execute(delete(LedgerLine))
        session.execute(delete(InvoiceLedger))
        session.execute(delete(RunEvent))
        session.execute(delete(RunCheck))
        session.execute(delete(RunStage))
        session.execute(delete(Run))
        session.execute(delete(Document))
        session.execute(delete(POLine))
        session.execute(delete(PurchaseOrder))
        session.execute(delete(Vendor))
        session.commit()
    else:
        # If vendors exist and not force, skip
        existing_vendor = session.execute(select(Vendor.vendor_id).limit(1)).scalar_one_or_none()
        if existing_vendor is not None:
            logger.info("Database already seeded. Skipping seed.")
            return

    logger.info("Seeding database from %s...", SEED_DIR)

    # 1. Load Vendors
    vendors_path = SEED_DIR / "vendors.json"
    with open(vendors_path, encoding="utf-8") as f:
        vendors_data = json.load(f)

    for v in vendors_data:
        vendor = Vendor(
            vendor_id=v["vendor_id"],
            legal_name=v["legal_name"],
            aliases=v.get("aliases", []),
            gstin=v["gstin"].upper(),
            pan=v["pan"].upper(),
            state_code=v["state_code"],
            address=v["address"],
            status=v["status"],
            deactivated_on=parse_date(v.get("deactivated_on")),
            bank_name=v["bank_name"],
            bank_ifsc=v["bank_ifsc"].upper(),
            bank_account_number=v["bank_account_number"],
            payment_terms_days=v["payment_terms_days"],
            contact_email=v["contact_email"],
        )
        session.add(vendor)
    session.flush()

    # 2. Load Purchase Orders and Lines
    pos_path = SEED_DIR / "purchase_orders.json"
    with open(pos_path, encoding="utf-8") as f:
        pos_data = json.load(f)

    for po in pos_data:
        po_obj = PurchaseOrder(
            po_number=po["po_number"],
            vendor_id=po["vendor_id"],
            po_date=parse_date(po["po_date"]),
            valid_until=parse_date(po["valid_until"]),
            status=po["status"],
            po_number_norm=normalize_po_number(po["po_number"]) or po["po_number"],
        )
        session.add(po_obj)

        for line in po.get("lines", []):
            po_line = POLine(
                po_number=po["po_number"],
                line_no=line["line_no"],
                description=line["description"],
                hsn_sac=line.get("hsn_sac"),
                uom=line["uom"],
                quantity=Decimal(str(line["quantity"])),
                unit_price_paise=to_paise(line["unit_price"]),
                tax_rate=Decimal(str(line["tax_rate_percent"])),
            )
            session.add(po_line)
    session.flush()

    # 3. Load Prior Approved Invoices into InvoiceLedger and LedgerLine
    prior_path = SEED_DIR / "prior_invoices.json"
    with open(prior_path, encoding="utf-8") as f:
        prior_data = json.load(f)

    for inv in prior_data:
        totals = inv.get("computed_totals", {})
        ledger_entry = InvoiceLedger(
            source="seed",
            run_id=None,
            vendor_id=inv["vendor_id"],
            invoice_number=inv["invoice_number"],
            invoice_number_norm=normalize_invoice_number(inv["invoice_number"]),
            invoice_date=parse_date(inv["invoice_date"]),
            po_number=inv.get("po_number"),
            net_paise=to_paise(totals.get("net", "0.00")),
            tax_paise=to_paise(totals.get("tax", "0.00")),
            grand_total_paise=to_paise(totals.get("grand_total", "0.00")),
            status=inv.get("status", "APPROVED"),
            file_sha256=None,
        )
        session.add(ledger_entry)
        session.flush()

        for line in inv.get("lines", []):
            l_line = LedgerLine(
                ledger_id=ledger_entry.id,
                po_number=inv.get("po_number"),
                po_line_no=line.get("po_line_no"),
                description=line["description"],
                quantity=Decimal(str(line["quantity"])),
                unit_price_paise=to_paise(line["unit_price"]),
                net_paise=to_paise(line["line_amount"]),
            )
            session.add(l_line)

    session.commit()
    logger.info("Seeding completed successfully.")
