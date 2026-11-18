from app.models import InvoiceLedger, LedgerLine
from app.pipeline.context import RunContext
from app.rules.actions import build_decision
from app.rules.email_draft import generate_vendor_email
from app.rules.money import to_paise
from app.schemas import Decision, Reason, StageOutcome


async def run(ctx: RunContext) -> StageOutcome:
    norm = ctx.normalized
    vendor = ctx.vendor
    po = ctx.po
    session = ctx.session

    # Check if extraction failed
    if not ctx.extraction:
        decision = Decision(
            decision="REVIEW",
            label="Needs review",
            headline="Needs review: Could not read the invoice. Process manually.",
            reasons=[
                Reason(
                    check_id="C01",
                    name="Extraction failed",
                    severity="REVIEW",
                    message="Could not read the invoice. Process manually.",
                )
            ],
            recommended_actions=["Process manually; document could not be read."],
            payment_block=False,
            due_date=None,
            vendor_email=None,
            key_facts={
                "vendor": None,
                "po": None,
                "po_method": "none",
                "invoice_number": None,
                "invoice_date": None,
                "grand_total": None,
            },
        )
    else:
        # Normal decision resolution
        decision = build_decision(
            checks=ctx.all_checks,
            normalized=norm,
            vendor=vendor,
            po_number=po.po_number if po else None,
            po_method=ctx.po_method,
        )

        # Generate vendor email draft if eligible
        email_draft = generate_vendor_email(
            decision=decision,
            checks=ctx.all_checks,
            normalized=norm,
            vendor=vendor,
            po_number=po.po_number if po else None,
        )
        decision.vendor_email = email_draft

    # Determine Ledger status
    status_map = {
        "APPROVE": "APPROVED",
        "REVIEW": "IN_REVIEW",
        "HOLD": "ON_HOLD",
        "REJECT": "REJECTED",
    }
    ledger_status = status_map[decision.decision]

    # Write InvoiceLedger row per doc 04 §4.2
    net_paise = to_paise(norm.net_total) if norm else 0
    tax_paise = to_paise(norm.total_tax) if norm else 0
    gt_paise = to_paise(norm.grand_total or 0) if norm else 0

    ledger_entry = InvoiceLedger(
        source="run",
        run_id=ctx.run.id,
        vendor_id=vendor.vendor_id if vendor else None,
        invoice_number=norm.invoice_number if norm else None,
        invoice_number_norm=norm.invoice_number_norm if norm else None,
        invoice_date=norm.invoice_date if norm else None,
        po_number=po.po_number if po else None,
        net_paise=net_paise,
        tax_paise=tax_paise,
        grand_total_paise=gt_paise,
        status=ledger_status,
        file_sha256=ctx.document.sha256 if ctx.document else None,
    )
    session.add(ledger_entry)
    session.flush()

    # Write LedgerLine rows for matched lines
    if po and ctx.matched_pairs:
        for pair in ctx.matched_pairs:
            inv_line = pair["inv_line"]
            l_line = LedgerLine(
                ledger_id=ledger_entry.id,
                po_number=po.po_number,
                po_line_no=pair["po_line_no"],
                description=inv_line.description,
                quantity=float(inv_line.quantity),
                unit_price_paise=to_paise(inv_line.unit_price_net),
                net_paise=to_paise(inv_line.line_net),
            )
            session.add(l_line)
        session.flush()

    output = decision.model_dump(mode="json")
    ctx.stage_outputs["decide"] = output

    headline_truncated = decision.headline[:70]
    summary = f"{decision.label}: {headline_truncated}"[:90]

    stage_status = "PASSED" if decision.decision == "APPROVE" else "FLAGGED"

    return StageOutcome(
        status=stage_status,
        summary=summary,
        output=output,
        checks=[],
    )
