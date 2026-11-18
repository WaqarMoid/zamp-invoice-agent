from datetime import date, timedelta

from app.models import Vendor
from app.schemas import CheckResult, Decision, NormalizedInvoice, Reason

STAGE_ORDER = [
    "ingest",
    "extract",
    "normalize",
    "vendor",
    "duplicates",
    "po_match",
    "reconcile",
    "decide",
]

SEVERITY_ORDER = {"REJECT": 3, "HOLD": 2, "REVIEW": 1}

ACTIONS_MAP: dict[str, str] = {
    "C01": "Ask the vendor for a corrected tax invoice with the missing fields.",
    "C02": "Compare the low-confidence fields with the document before deciding.",
    "C03": "Return the invoice to the vendor; it is not billed to Kestrel Foods.",
    "C04": "Ask the vendor to correct the arithmetic and reissue.",
    "C05": "Do not pay. Confirm with procurement why an inactive vendor is billing.",
    "C06_REJECT": "Route to procurement to onboard the vendor, or reject.",
    "C06_HOLD": "Verify the vendor's GSTIN on the GST portal and by phone before paying.",
    "C07": (
        "Call the vendor on the number in the vendor master (not the invoice) "
        "to confirm the bank change. Update the master only after confirmation."
    ),
    "C08": "Confirm the invoice date with the vendor.",
    "C09_REJECT": "Do not pay again. Reply to the vendor with the original invoice's status.",
    "C09_REVIEW": "Compare with the possible duplicate before paying.",
    "C10": "Confirm the PO with the requester, then approve.",
    "C11": "Check with procurement which PO this invoice belongs to.",
    "C12": "Do not pay against a closed PO. Ask procurement whether a new PO is needed.",
    "C13": "Ask the requester whether the unmatched items were ordered.",
    "C14": "Ask the vendor for a credit note for the price difference, or approve the variance.",
    "C15": "Approve only the unbilled quantity, or ask procurement to amend the PO.",
    "C16": "Ask the vendor to reissue with the correct GST.",
    "C17": "Process manually; foreign-currency invoices are out of scope.",
    "C20": "Confirm with procurement whether the PO validity can be extended.",
}


def first_sentence(msg: str) -> str:
    """Extract first sentence of a message."""
    s = msg.strip()
    idx = s.find(". ")
    if idx != -1:
        return s[: idx + 1]
    return s


def build_decision(
    checks: list[CheckResult],
    normalized: NormalizedInvoice | None,
    vendor: Vendor | None,
    po_number: str | None,
    po_method: str = "none",
) -> Decision:
    """
    Combine all checks into one Decision per doc 07 §7.2, §7.6.
    Precedence: REJECT > HOLD > REVIEW > APPROVE.
    """
    flag_checks = [c for c in checks if c.outcome == "FLAG"]

    # 1. Determine overall decision
    if not flag_checks:
        decision_val = "APPROVE"
    else:
        # Max severity: REJECT > HOLD > REVIEW
        highest_sev = max(flag_checks, key=lambda c: SEVERITY_ORDER.get(c.severity or "REVIEW", 0)).severity
        decision_val = highest_sev or "REVIEW"

    label_map = {
        "APPROVE": "Approved",
        "REVIEW": "Needs review",
        "HOLD": "On hold",
        "REJECT": "Rejected",
    }
    label = label_map[decision_val]

    # 2. Sort flag checks: highest severity first, then stage order
    def sort_key(c: CheckResult):
        sev_rank = -SEVERITY_ORDER.get(c.severity or "REVIEW", 0)
        stage_rank = STAGE_ORDER.index(c.stage_key) if c.stage_key in STAGE_ORDER else 99
        return (sev_rank, stage_rank)

    sorted_flags = sorted(flag_checks, key=sort_key)

    # 3. Reasons list
    reasons = [
        Reason(
            check_id=c.check_id,
            name=c.name,
            severity=c.severity or "REVIEW",
            message=c.message,
        )
        for c in sorted_flags
    ]

    # 4. Headline generation
    if decision_val == "APPROVE":
        po_str = po_number or "PO"
        headline = f"Approved for payment. Matches {po_str} within tolerance."
        # Check if C15 indicated fully billed
        c15_checks = [c for c in checks if c.check_id == "C15"]
        if c15_checks and c15_checks[0].evidence.get("fully_billed_after"):
            headline += f" {po_str} is now fully billed."
    elif decision_val == "HOLD":
        top_hold = next(c for c in sorted_flags if c.severity == "HOLD")
        headline = f"Payment on hold: {first_sentence(top_hold.message)}"
    elif decision_val == "REJECT":
        top_rej = next(c for c in sorted_flags if c.severity == "REJECT")
        headline = f"Rejected: {first_sentence(top_rej.message)}"
    else:  # REVIEW
        top_rev = next(c for c in sorted_flags if c.severity == "REVIEW")
        top_msg = first_sentence(top_rev.message)
        headline = f"Needs review: {top_msg}"
        remaining_count = len(sorted_flags) - 1
        if remaining_count > 0:
            headline += f" and {remaining_count} more issue(s)."

    # 5. Recommended actions
    recommended_actions: list[str] = []
    if decision_val == "APPROVE":
        inv_d = normalized.invoice_date if normalized and normalized.invoice_date else date.today()
        terms = vendor.payment_terms_days if vendor else 30
        due_d = inv_d + timedelta(days=terms)
        recommended_actions.append(
            f"Schedule payment for {due_d.isoformat()} ({terms} days from invoice date)."
        )
        due_date_val = due_d
    else:
        due_date_val = None
        seen_actions: set[str] = set()
        for c in sorted_flags:
            act_key = c.check_id
            if c.check_id == "C06":
                act_key = f"C06_{c.severity}"
            elif c.check_id == "C09":
                act_key = f"C09_{c.severity}"

            action_text = ACTIONS_MAP.get(act_key)
            if action_text and action_text not in seen_actions:
                recommended_actions.append(action_text)
                seen_actions.add(action_text)

    # 6. Key facts dict
    key_facts = {
        "vendor": vendor.legal_name if vendor else (normalized.vendor_name if normalized else None),
        "po": po_number,
        "po_method": po_method,
        "invoice_number": normalized.invoice_number if normalized else None,
        "invoice_date": normalized.invoice_date.isoformat()
        if normalized and normalized.invoice_date
        else None,
        "grand_total": f"{normalized.grand_total:.2f}"
        if normalized and normalized.grand_total is not None
        else None,
    }

    return Decision(
        decision=decision_val,
        label=label,
        headline=headline,
        reasons=reasons,
        recommended_actions=recommended_actions,
        payment_block=(decision_val in {"HOLD", "REJECT"}),
        due_date=due_date_val,
        vendor_email=None,  # populated by email_draft
        key_facts=key_facts,
    )
