from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import InvoiceLedger, LedgerLine, POLine, PurchaseOrder, Vendor
from app.rules.consumption import get_po_consumption_map
from app.rules.gstin import is_valid_gstin
from app.rules.money import format_money
from app.schemas import CheckResult, ExtractedInvoice, NormalizedInvoice, NormalizedLine


def today_ist() -> date:
    return datetime.now(UTC).date()


def mask_account(acc: str | None) -> str:
    if not acc:
        return ""
    digits = "".join(filter(str.isdigit, acc))
    return f"••••{digits[-4:]}" if len(digits) >= 4 else "••••"


# ---------------------------------------------------------------------------
# C01: Required fields
# ---------------------------------------------------------------------------
def check_c01(extracted: ExtractedInvoice) -> CheckResult:
    missing: list[str] = []
    if not extracted.vendor_name or not extracted.vendor_name.strip():
        missing.append("vendor name")
    if not extracted.invoice_number or not extracted.invoice_number.strip():
        missing.append("invoice number")
    if not extracted.invoice_date and not extracted.invoice_date_raw:
        missing.append("invoice date")
    if extracted.grand_total is None:
        missing.append("grand total")
    if not extracted.line_items:
        missing.append("line items")

    if missing:
        fields_csv = ", ".join(missing)
        return CheckResult(
            check_id="C01",
            stage_key="normalize",
            name="Required fields",
            outcome="FLAG",
            severity="REVIEW",
            message=f"Missing {fields_csv}. Request a corrected tax invoice.",
            evidence={"missing_fields": missing},
        )
    return CheckResult(
        check_id="C01",
        stage_key="normalize",
        name="Required fields",
        outcome="PASS",
        severity=None,
        message="All required fields present.",
        evidence={"present": ["vendor_name", "invoice_number", "invoice_date", "grand_total", "line_items"]},
    )


# ---------------------------------------------------------------------------
# C02: Extraction confidence
# ---------------------------------------------------------------------------
def check_c02(extracted: ExtractedInvoice, min_confidence: float = 0.80) -> CheckResult:
    key_fields = [
        "vendor_name",
        "vendor_gstin",
        "invoice_number",
        "invoice_date",
        "grand_total",
        "po_number",
        "line_items",
    ]
    low_conf: list[tuple[str, float]] = []

    conf_dict = extracted.field_confidence or {}
    for fld in key_fields:
        val = getattr(extracted, fld, None)
        if val is not None and fld in conf_dict:
            score = float(conf_dict[fld])
            if score < min_confidence:
                low_conf.append((fld, score))

    if low_conf:
        fields_csv = ", ".join(f"{f} ({s:.0%})" for f, s in low_conf)
        min_c = min(s for _, s in low_conf)
        return CheckResult(
            check_id="C02",
            stage_key="normalize",
            name="Extraction confidence",
            outcome="FLAG",
            severity="REVIEW",
            message=f"Low read confidence on {fields_csv}. Verify against the document.",
            evidence={"low_confidence_fields": dict(low_conf), "min_confidence_found": min_c},
        )
    return CheckResult(
        check_id="C02",
        stage_key="normalize",
        name="Extraction confidence",
        outcome="PASS",
        severity=None,
        message="All key fields read with ≥80% confidence.",
        evidence={"confidences": conf_dict},
    )


# ---------------------------------------------------------------------------
# C03: Billed to us
# ---------------------------------------------------------------------------
def check_c03(extracted: ExtractedInvoice, buyer_gstin_expected: str = "29AAACK4521M1ZD") -> CheckResult:
    if not extracted.buyer_gstin or not extracted.buyer_gstin.strip():
        return CheckResult(
            check_id="C03",
            stage_key="normalize",
            name="Billed to us",
            outcome="FLAG",
            severity="REVIEW",
            message="Buyer GSTIN not printed.",
            evidence={"expected": buyer_gstin_expected, "found": None},
        )

    cleaned_found = "".join(extracted.buyer_gstin.split()).upper()
    if cleaned_found != buyer_gstin_expected.upper():
        return CheckResult(
            check_id="C03",
            stage_key="normalize",
            name="Billed to us",
            outcome="FLAG",
            severity="REJECT",
            message=f"Invoice is billed to GSTIN {cleaned_found}, not Kestrel Foods.",
            evidence={"expected": buyer_gstin_expected, "found": cleaned_found},
        )

    return CheckResult(
        check_id="C03",
        stage_key="normalize",
        name="Billed to us",
        outcome="PASS",
        severity=None,
        message=f"Billed to Kestrel Foods ({buyer_gstin_expected}).",
        evidence={"buyer_gstin": cleaned_found},
    )


# ---------------------------------------------------------------------------
# C04: Arithmetic
# ---------------------------------------------------------------------------
def check_c04(
    extracted: ExtractedInvoice,
    normalized: NormalizedInvoice,
    rounding_tol: Decimal = Decimal("1.00"),
) -> CheckResult:
    # (a) Line item arithmetic: abs(qty * unit_price - line_amount) <= 1.00
    for line in normalized.lines:
        expected_line = line.quantity * line.unit_price_printed
        diff = abs(expected_line - line.line_printed)
        if diff > rounding_tol:
            return CheckResult(
                check_id="C04",
                stage_key="normalize",
                name="Arithmetic",
                outcome="FLAG",
                severity="REVIEW",
                message=f"Totals do not add up: line '{line.description}' off by ₹{diff:.2f}.",
                evidence={
                    "line_index": line.index,
                    "expected": float(expected_line),
                    "printed": float(line.line_printed),
                    "diff": float(diff),
                },
            )

    # (b) Line sum vs subtotal
    lines_sum = sum(line.line_printed for line in normalized.lines)
    subtotal = extracted.subtotal
    if subtotal is not None:
        diff_sub = abs(lines_sum - subtotal)
        if diff_sub > rounding_tol:
            return CheckResult(
                check_id="C04",
                stage_key="normalize",
                name="Arithmetic",
                outcome="FLAG",
                severity="REVIEW",
                message=f"Totals do not add up: subtotal off by ₹{diff_sub:.2f}.",
                evidence={
                    "lines_sum": float(lines_sum),
                    "subtotal": float(subtotal),
                    "diff": float(diff_sub),
                },
            )

    # (c) Grand total check
    if normalized.grand_total is not None:
        if normalized.amounts_include_tax:
            # tax-inclusive: lines sum == grand_total
            diff_gt = abs(lines_sum - normalized.grand_total)
            if diff_gt > rounding_tol:
                return CheckResult(
                    check_id="C04",
                    stage_key="normalize",
                    name="Arithmetic",
                    outcome="FLAG",
                    severity="REVIEW",
                    message=f"Totals do not add up: grand total off by ₹{diff_gt:.2f}.",
                    evidence={"lines_sum": float(lines_sum), "grand_total": float(normalized.grand_total)},
                )
        else:
            # tax-exclusive: net + total_tax == grand_total
            calc_gt = lines_sum + normalized.total_tax
            diff_gt = abs(calc_gt - normalized.grand_total)
            if diff_gt > rounding_tol:
                return CheckResult(
                    check_id="C04",
                    stage_key="normalize",
                    name="Arithmetic",
                    outcome="FLAG",
                    severity="REVIEW",
                    message=f"Totals do not add up: grand total off by ₹{diff_gt:.2f}.",
                    evidence={
                        "calculated_grand_total": float(calc_gt),
                        "printed_grand_total": float(normalized.grand_total),
                        "diff": float(diff_gt),
                    },
                )

    return CheckResult(
        check_id="C04",
        stage_key="normalize",
        name="Arithmetic",
        outcome="PASS",
        severity=None,
        message="Lines, subtotal, tax and total reconcile.",
        evidence={"lines_sum": float(lines_sum), "total_tax": float(normalized.total_tax)},
    )


# ---------------------------------------------------------------------------
# C05: Vendor status
# ---------------------------------------------------------------------------
def check_c05(vendor: Vendor | None) -> CheckResult:
    if not vendor:
        return CheckResult(
            check_id="C05",
            stage_key="vendor",
            name="Vendor status",
            outcome="SKIP",
            severity=None,
            message="No vendor matched to check status.",
            evidence={},
        )

    if vendor.status != "ACTIVE":
        deact_date = vendor.deactivated_on.isoformat() if vendor.deactivated_on else "in the past"
        return CheckResult(
            check_id="C05",
            stage_key="vendor",
            name="Vendor status",
            outcome="FLAG",
            severity="REJECT",
            message=f"{vendor.legal_name} was deactivated on {deact_date}. Do not pay.",
            evidence={"status": vendor.status, "deactivated_on": deact_date},
        )

    return CheckResult(
        check_id="C05",
        stage_key="vendor",
        name="Vendor status",
        outcome="PASS",
        severity=None,
        message=f"{vendor.legal_name} is an active approved vendor.",
        evidence={"status": vendor.status},
    )


# ---------------------------------------------------------------------------
# C06: Vendor identity
# ---------------------------------------------------------------------------
def check_c06(
    extracted: ExtractedInvoice,
    vendor: Vendor | None,
    method: str,
) -> CheckResult:
    if not vendor:
        inv_name = extracted.vendor_name or "Unknown"
        inv_gstin = extracted.vendor_gstin or "None"
        return CheckResult(
            check_id="C06",
            stage_key="vendor",
            name="Vendor identity",
            outcome="FLAG",
            severity="REJECT",
            message=f'No approved vendor matches "{inv_name}" / {inv_gstin}. Onboard the vendor first.',
            evidence={"searched_name": inv_name, "searched_gstin": inv_gstin},
        )

    # Check GSTIN checksum if printed on invoice
    if extracted.vendor_gstin:
        cleaned_gstin = "".join(extracted.vendor_gstin.split()).upper()
        if not is_valid_gstin(cleaned_gstin):
            return CheckResult(
                check_id="C06",
                stage_key="vendor",
                name="Vendor identity",
                outcome="FLAG",
                severity="HOLD",
                message=f"GSTIN {cleaned_gstin} fails checksum validation.",
                evidence={"invoice_gstin": cleaned_gstin},
            )
        # Check master GSTIN mismatch
        if vendor.gstin and cleaned_gstin != vendor.gstin.upper():
            return CheckResult(
                check_id="C06",
                stage_key="vendor",
                name="Vendor identity",
                outcome="FLAG",
                severity="HOLD",
                message=(
                    f"Invoice GSTIN {cleaned_gstin} does not match master "
                    f"GSTIN {vendor.gstin} for {vendor.legal_name}."
                ),
                evidence={"invoice_gstin": cleaned_gstin, "master_gstin": vendor.gstin},
            )

    return CheckResult(
        check_id="C06",
        stage_key="vendor",
        name="Vendor identity",
        outcome="PASS",
        severity=None,
        message=f"Matched {vendor.legal_name} by {method}.",
        evidence={"vendor_id": vendor.vendor_id, "vendor_name": vendor.legal_name, "method": method},
    )


# ---------------------------------------------------------------------------
# C07: Bank details
# ---------------------------------------------------------------------------
def check_c07(extracted: ExtractedInvoice, vendor: Vendor | None) -> CheckResult:
    if not vendor:
        return CheckResult(
            check_id="C07",
            stage_key="vendor",
            name="Bank details",
            outcome="SKIP",
            severity=None,
            message="No vendor matched to verify bank details.",
            evidence={},
        )

    bank = extracted.bank_details
    if not bank or (not bank.ifsc and not bank.account_number):
        return CheckResult(
            check_id="C07",
            stage_key="vendor",
            name="Bank details",
            outcome="INFO",
            severity=None,
            message="No bank details printed. Payment will use the vendor master account.",
            evidence={"master_bank_masked": mask_account(vendor.bank_account_number)},
        )

    inv_ifsc = (bank.ifsc or "").upper().strip()
    inv_acc = "".join(filter(str.isdigit, bank.account_number or ""))
    master_ifsc = (vendor.bank_ifsc or "").upper().strip()
    master_acc = "".join(filter(str.isdigit, vendor.bank_account_number or ""))

    if (inv_ifsc and inv_ifsc != master_ifsc) or (inv_acc and inv_acc != master_acc):
        last4_inv = inv_acc[-4:] if len(inv_acc) >= 4 else inv_acc
        last4_master = master_acc[-4:] if len(master_acc) >= 4 else master_acc
        return CheckResult(
            check_id="C07",
            stage_key="vendor",
            name="Bank details",
            outcome="FLAG",
            severity="HOLD",
            message=(
                f"Bank details on invoice ({inv_ifsc} / ••••{last4_inv}) differ from "
                f"vendor master ({master_ifsc} / ••••{last4_master}). "
                "Verify by phone with the contact on file before paying."
            ),
            evidence={
                "invoice_ifsc": inv_ifsc,
                "invoice_account_masked": f"••••{last4_inv}",
                "master_ifsc": master_ifsc,
                "master_account_masked": f"••••{last4_master}",
            },
        )

    return CheckResult(
        check_id="C07",
        stage_key="vendor",
        name="Bank details",
        outcome="PASS",
        severity=None,
        message="Bank details match the vendor master.",
        evidence={"bank_ifsc": master_ifsc, "bank_account_masked": mask_account(master_acc)},
    )


# ---------------------------------------------------------------------------
# C08: Invoice date
# ---------------------------------------------------------------------------
def check_c08(inv_date: date | None, max_age_days: int = 365) -> CheckResult:
    if not inv_date:
        return CheckResult(
            check_id="C08",
            stage_key="normalize",
            name="Invoice date",
            outcome="SKIP",
            severity=None,
            message="No invoice date to validate.",
            evidence={},
        )

    today = today_ist()
    if inv_date > today:
        return CheckResult(
            check_id="C08",
            stage_key="normalize",
            name="Invoice date",
            outcome="FLAG",
            severity="REVIEW",
            message=f"Invoice date {inv_date.isoformat()} is in the future.",
            evidence={"invoice_date": inv_date.isoformat(), "today": today.isoformat()},
        )

    age_days = (today - inv_date).days
    if age_days > max_age_days:
        return CheckResult(
            check_id="C08",
            stage_key="normalize",
            name="Invoice date",
            outcome="FLAG",
            severity="REVIEW",
            message=f"Invoice date {inv_date.isoformat()} is more than 365 days old.",
            evidence={"invoice_date": inv_date.isoformat(), "age_days": age_days},
        )

    return CheckResult(
        check_id="C08",
        stage_key="normalize",
        name="Invoice date",
        outcome="PASS",
        severity=None,
        message=f"Invoice date {inv_date.isoformat()} is valid.",
        evidence={"invoice_date": inv_date.isoformat(), "age_days": age_days},
    )


# ---------------------------------------------------------------------------
# C09: Duplicate check
# ---------------------------------------------------------------------------
def check_c09(
    session: Session,
    normalized: NormalizedInvoice,
    vendor_id: str | None,
    current_run_id: str | None = None,
    file_sha256: str | None = None,
    near_dup_window_days: int = 30,
) -> CheckResult:
    if not vendor_id:
        return CheckResult(
            check_id="C09",
            stage_key="duplicates",
            name="Duplicate check",
            outcome="SKIP",
            severity=None,
            message="No vendor matched to evaluate duplicate invoices.",
            evidence={},
        )

    # Candidates = invoice_ledger rows with status IN (APPROVED, IN_REVIEW, ON_HOLD)
    query = session.query(InvoiceLedger).filter(
        InvoiceLedger.vendor_id == vendor_id,
        InvoiceLedger.status.in_(["APPROVED", "IN_REVIEW", "ON_HOLD"]),
    )
    if current_run_id:
        query = query.filter(or_(InvoiceLedger.run_id.is_(None), InvoiceLedger.run_id != current_run_id))

    candidates = query.all()

    # Check same-file hash across any previous run in DB
    same_file_run = None
    if file_sha256:
        prior_file_row = session.query(InvoiceLedger).filter(InvoiceLedger.file_sha256 == file_sha256)
        if current_run_id:
            prior_file_row = prior_file_row.filter(
                or_(InvoiceLedger.run_id.is_(None), InvoiceLedger.run_id != current_run_id)
            )
        prior_entry = prior_file_row.first()
        if prior_entry and prior_entry.run_id:
            same_file_run = prior_entry.run_id

    # 1. Exact duplicate check
    if normalized.invoice_number_norm:
        for cand in candidates:
            if cand.invoice_number_norm == normalized.invoice_number_norm:
                status_label = {
                    "APPROVED": "approved",
                    "IN_REVIEW": "in review",
                    "ON_HOLD": "on hold",
                }.get(cand.status, cand.status.lower())
                orig_date = cand.invoice_date.isoformat() if cand.invoice_date else "unknown date"
                orig_total = format_money(Decimal(cand.grand_total_paise) / Decimal("100"))

                differs_formatting = cand.invoice_number != normalized.invoice_number
                clause = " Invoice number differs only in formatting." if differs_formatting else ""
                file_clause = (
                    f" The identical file was processed in run {same_file_run[:8]}." if same_file_run else ""
                )

                msg = (
                    f"Duplicate of {cand.invoice_number} ({status_label}, dated {orig_date}, ₹{orig_total})."
                    f"{clause}{file_clause}"
                )
                evidence: dict[str, Any] = {
                    "duplicate_type": "exact",
                    "original_invoice_number": cand.invoice_number,
                    "original_status": cand.status,
                    "original_date": orig_date,
                    "original_grand_total": orig_total,
                }
                if same_file_run:
                    evidence["same_file_as_run"] = same_file_run

                return CheckResult(
                    check_id="C09",
                    stage_key="duplicates",
                    name="Duplicate check",
                    outcome="FLAG",
                    severity="REJECT",
                    message=msg,
                    evidence=evidence,
                )

    # 2. Near duplicate check
    if normalized.grand_total is not None:
        inv_gt = normalized.grand_total
        for cand in candidates:
            cand_gt = Decimal(cand.grand_total_paise) / Decimal("100")
            if abs(inv_gt - cand_gt) <= Decimal("1.00"):
                date_ok = True
                days_apart = None
                if normalized.invoice_date and cand.invoice_date:
                    days_apart = abs((normalized.invoice_date - cand.invoice_date).days)
                    date_ok = days_apart <= near_dup_window_days

                if date_ok:
                    file_clause = (
                        f" The identical file was processed in run {same_file_run[:8]}."
                        if same_file_run
                        else ""
                    )
                    days_str = f", {days_apart} days apart" if days_apart is not None else ""
                    msg = (
                        f"Possible duplicate of {cand.invoice_number}: same vendor and amount "
                        f"₹{format_money(inv_gt)}{days_str}.{file_clause}"
                    )
                    evidence = {
                        "duplicate_type": "near",
                        "original_invoice_number": cand.invoice_number,
                        "amount": float(inv_gt),
                        "days_apart": days_apart,
                    }
                    if same_file_run:
                        evidence["same_file_as_run"] = same_file_run

                    return CheckResult(
                        check_id="C09",
                        stage_key="duplicates",
                        name="Duplicate check",
                        outcome="FLAG",
                        severity="REVIEW",
                        message=msg,
                        evidence=evidence,
                    )

    # 3. File hash alone
    if same_file_run:
        return CheckResult(
            check_id="C09",
            stage_key="duplicates",
            name="Duplicate check",
            outcome="INFO",
            severity=None,
            message=f"This exact file was processed before in run {same_file_run[:8]}.",
            evidence={"same_file_as_run": same_file_run},
        )

    vendor_name = normalized.vendor_name or "vendor"
    return CheckResult(
        check_id="C09",
        stage_key="duplicates",
        name="Duplicate check",
        outcome="PASS",
        severity=None,
        message=f"No duplicate among {len(candidates)} ledger invoices from {vendor_name}.",
        evidence={"candidates_checked": len(candidates)},
    )


# ---------------------------------------------------------------------------
# C10: PO identified
# ---------------------------------------------------------------------------
def check_c10(
    po: PurchaseOrder | None,
    method: str,
    candidates: list[dict[str, Any]],
    printed_po: str | None,
    vendor_name: str | None = None,
    auto_approve_inferred: bool = False,
) -> CheckResult:
    if method == "explicit" and po:
        return CheckResult(
            check_id="C10",
            stage_key="po_match",
            name="PO identified",
            outcome="PASS",
            severity=None,
            message=f"Invoice references {po.po_number}.",
            evidence={"po_number": po.po_number, "method": "explicit"},
        )

    if method == "inferred" and po:
        best = candidates[0] if candidates else {}
        score = float(best.get("score", 0.0))
        date_clause = ", order date matches" if best.get("date_bonus") else ""
        outcome = "PASS" if auto_approve_inferred else "FLAG"
        severity = None if auto_approve_inferred else "REVIEW"
        suffix = "" if auto_approve_inferred else " Confirm before paying."

        clean_cands = [
            {
                "po_number": c.get("po_number"),
                "coverage": c.get("coverage", 0.0),
                "amount_fit": c.get("amount_fit", 0.0),
                "date_bonus": c.get("date_bonus", 0.0),
                "score": c.get("score", 0.0),
            }
            for c in candidates
        ]

        return CheckResult(
            check_id="C10",
            stage_key="po_match",
            name="PO identified",
            outcome=outcome,
            severity=severity,
            message=(
                f"No PO number on invoice. Inferred {po.po_number} "
                f"(match {score:.0%}{date_clause}).{suffix}"
            ),
            evidence={"method": "inferred", "inferred_po": po.po_number, "candidates": clean_cands},
        )

    if method == "printed_not_found":
        evidence: dict[str, Any] = {"printed_po": printed_po}
        if candidates and candidates[0]["score"] >= 0.75:
            suggested = candidates[0]["po_number"]
            evidence["suggested_po"] = suggested
            return CheckResult(
                check_id="C10",
                stage_key="po_match",
                name="PO identified",
                outcome="FLAG",
                severity="REVIEW",
                message=f"PO number {printed_po} not found. Suggested: {suggested}.",
                evidence=evidence,
            )
        return CheckResult(
            check_id="C10",
            stage_key="po_match",
            name="PO identified",
            outcome="FLAG",
            severity="REVIEW",
            message=f"PO number {printed_po} not found.",
            evidence=evidence,
        )

    v_str = vendor_name or "vendor"
    return CheckResult(
        check_id="C10",
        stage_key="po_match",
        name="PO identified",
        outcome="FLAG",
        severity="REVIEW",
        message=f"No PO number and no confident match among {len(candidates)} open POs for {v_str}.",
        evidence={"candidates_checked": len(candidates)},
    )


# ---------------------------------------------------------------------------
# C11: PO belongs to vendor
# ---------------------------------------------------------------------------
def check_c11(po: PurchaseOrder | None, vendor: Vendor | None) -> CheckResult:
    if not po or not vendor:
        return CheckResult(
            check_id="C11",
            stage_key="po_match",
            name="PO belongs to vendor",
            outcome="SKIP",
            severity=None,
            message="No PO or vendor to check ownership.",
            evidence={},
        )

    if po.vendor_id != vendor.vendor_id:
        po_vendor_name = po.vendor.legal_name if po.vendor else po.vendor_id
        return CheckResult(
            check_id="C11",
            stage_key="po_match",
            name="PO belongs to vendor",
            outcome="FLAG",
            severity="REVIEW",
            message=f"{po.po_number} belongs to {po_vendor_name}, not {vendor.legal_name}.",
            evidence={"po_vendor_id": po.vendor_id, "invoice_vendor_id": vendor.vendor_id},
        )

    return CheckResult(
        check_id="C11",
        stage_key="po_match",
        name="PO belongs to vendor",
        outcome="PASS",
        severity=None,
        message=f"{po.po_number} is issued to {vendor.legal_name}.",
        evidence={"po_number": po.po_number, "vendor_id": vendor.vendor_id},
    )


# ---------------------------------------------------------------------------
# C12: PO status
# ---------------------------------------------------------------------------
def check_c12(po: PurchaseOrder | None) -> CheckResult:
    if not po:
        return CheckResult(
            check_id="C12",
            stage_key="po_match",
            name="PO status",
            outcome="SKIP",
            severity=None,
            message="No PO identified to verify status.",
            evidence={},
        )

    if po.status != "OPEN":
        return CheckResult(
            check_id="C12",
            stage_key="po_match",
            name="PO status",
            outcome="FLAG",
            severity="REJECT",
            message=f"{po.po_number} is {po.status}. No further invoices can be paid against it.",
            evidence={"po_number": po.po_number, "status": po.status},
        )

    return CheckResult(
        check_id="C12",
        stage_key="po_match",
        name="PO status",
        outcome="PASS",
        severity=None,
        message=f"{po.po_number} is open.",
        evidence={"po_number": po.po_number, "status": "OPEN"},
    )


# ---------------------------------------------------------------------------
# C13: Line matching
# ---------------------------------------------------------------------------
def check_c13(
    matched_pairs: list[dict[str, Any]],
    unmatched_lines: list[NormalizedLine],
    po: PurchaseOrder | None,
) -> CheckResult:
    if not po:
        return CheckResult(
            check_id="C13",
            stage_key="po_match",
            name="Line matching",
            outcome="SKIP",
            severity=None,
            message="No PO identified to pair line items.",
            evidence={},
        )

    clean_matches = [
        {
            "inv_index": m["inv_index"],
            "po_line_no": m["po_line_no"],
            "score": m["score"],
            "desc_sim": m.get("desc_sim"),
            "hsn_match": m.get("hsn_match"),
            "price_score": m.get("price_score"),
        }
        for m in matched_pairs
    ]

    if unmatched_lines:
        descs = ", ".join(f'"{un_line.description}"' for un_line in unmatched_lines)
        return CheckResult(
            check_id="C13",
            stage_key="po_match",
            name="Line matching",
            outcome="FLAG",
            severity="REVIEW",
            message=f"{len(unmatched_lines)} invoice line(s) not on {po.po_number}: {descs}.",
            evidence={
                "unmatched_lines": [un_line.description for un_line in unmatched_lines],
                "matched_lines": clean_matches,
            },
        )

    return CheckResult(
        check_id="C13",
        stage_key="po_match",
        name="Line matching",
        outcome="PASS",
        severity=None,
        message=f"All {len(matched_pairs)} invoice lines matched to {po.po_number} lines.",
        evidence={"matched_lines": clean_matches},
    )


# ---------------------------------------------------------------------------
# C14: Price variance
# ---------------------------------------------------------------------------
def check_c14(
    matched_pairs: list[dict[str, Any]],
    po: PurchaseOrder | None,
    tolerance_pct: float = 1.0,
    tolerance_abs_inr: float = 1000.0,
) -> CheckResult:
    if not po or not matched_pairs:
        return CheckResult(
            check_id="C14",
            stage_key="reconcile",
            name="Price variance",
            outcome="SKIP",
            severity=None,
            message="No paired lines to check price variance.",
            evidence={},
        )

    tol_pct_dec = Decimal(str(tolerance_pct)) / Decimal("100")
    tol_abs_dec = Decimal(str(tolerance_abs_inr))

    violations: list[dict[str, Any]] = []
    line_details: list[dict[str, Any]] = []

    for pair in matched_pairs:
        inv: NormalizedLine = pair["inv_line"]
        pol: POLine = pair["po_line"]

        po_unit = Decimal(str(pol.unit_price_paise)) / Decimal("100")
        expected = inv.quantity * po_unit
        actual = inv.line_net
        tol = min(expected * tol_pct_dec, tol_abs_dec)

        diff = actual - expected
        pct = float((diff / expected) * 100) if expected > 0 else 0.0

        detail = {
            "description": inv.description,
            "inv_unit": float(inv.unit_price_net),
            "po_unit": float(po_unit),
            "inv_qty": float(inv.quantity),
            "uom": inv.uom or pol.uom,
            "expected_amount": float(expected),
            "actual_amount": float(actual),
            "variance_inr": float(diff),
            "variance_pct": pct,
            "tolerance_inr": float(tol),
        }
        line_details.append(detail)

        if diff > tol:
            violations.append(detail)

    if violations:
        top = violations[0]
        return CheckResult(
            check_id="C14",
            stage_key="reconcile",
            name="Price variance",
            outcome="FLAG",
            severity="REVIEW",
            message=(
                f"{top['description']}: billed ₹{format_money(top['actual_amount'])} vs PO "
                f"₹{format_money(top['expected_amount'])} "
                f"(+{top['variance_pct']:.2f}%, tolerance ₹{format_money(top['tolerance_inr'])})."
            ),
            evidence={"violations": violations, "all_lines": line_details},
        )

    return CheckResult(
        check_id="C14",
        stage_key="reconcile",
        name="Price variance",
        outcome="PASS",
        severity=None,
        message="All prices within tolerance (min of 1% or ₹1,000 per line).",
        evidence={"lines": line_details},
    )


# ---------------------------------------------------------------------------
# C15: Quantity vs unbilled
# ---------------------------------------------------------------------------
def check_c15(
    session: Session,
    matched_pairs: list[dict[str, Any]],
    po: PurchaseOrder | None,
) -> CheckResult:
    if not po or not matched_pairs:
        return CheckResult(
            check_id="C15",
            stage_key="reconcile",
            name="Quantity vs unbilled",
            outcome="SKIP",
            severity=None,
            message="No paired lines to verify quantity balance.",
            evidence={},
        )

    consumed_map = get_po_consumption_map(session, po.po_number)
    violations: list[dict[str, Any]] = []
    line_details: list[dict[str, Any]] = []
    fully_billed_after_flags: list[bool] = []

    total_po_ordered_net = Decimal("0.00")
    total_po_consumed_net_before = Decimal("0.00")
    total_po_billed_net_now = Decimal("0.00")

    for pol in po.lines:
        po_u = Decimal(str(pol.unit_price_paise)) / Decimal("100")
        total_po_ordered_net += Decimal(str(pol.quantity)) * po_u
        cons = consumed_map.get(pol.line_no, Decimal("0.00"))
        total_po_consumed_net_before += cons * po_u

    for pair in matched_pairs:
        inv: NormalizedLine = pair["inv_line"]
        pol: POLine = pair["po_line"]

        ordered = Decimal(str(pol.quantity))
        consumed = consumed_map.get(pol.line_no, Decimal("0.00"))
        remaining = max(Decimal("0.00"), ordered - consumed)
        inv_qty = inv.quantity

        po_u = Decimal(str(pol.unit_price_paise)) / Decimal("100")
        total_po_billed_net_now += inv_qty * po_u

        # Find invoice numbers of past approved ledger rows for this line
        past_invoices_stmt = (
            session.query(InvoiceLedger.invoice_number)
            .join(LedgerLine, LedgerLine.ledger_id == InvoiceLedger.id)
            .filter(
                LedgerLine.po_number == po.po_number,
                LedgerLine.po_line_no == pol.line_no,
                InvoiceLedger.status == "APPROVED",
            )
            .all()
        )
        inv_list = ", ".join(row[0] for row in past_invoices_stmt if row[0]) or "none"

        is_fully_billed = inv_qty == remaining
        fully_billed_after_flags.append(is_fully_billed)

        detail = {
            "description": inv.description,
            "ordered": float(ordered),
            "consumed": float(consumed),
            "remaining": float(remaining),
            "inv_qty": float(inv_qty),
            "uom": inv.uom or pol.uom,
            "unit_price": float(po_u),
            "past_invoices": inv_list,
        }
        line_details.append(detail)

        if inv_qty > remaining:
            over = inv_qty - remaining
            over_val = over * po_u
            detail["over"] = float(over)
            detail["over_value"] = float(over_val)
            violations.append(detail)

    pct_before = (
        float((total_po_consumed_net_before / total_po_ordered_net) * 100)
        if total_po_ordered_net > 0
        else 0.0
    )
    total_net_after = total_po_consumed_net_before + total_po_billed_net_now
    pct_after = float((total_net_after / total_po_ordered_net) * 100) if total_po_ordered_net > 0 else 0.0

    all_fully_billed = (len(fully_billed_after_flags) > 0 and all(fully_billed_after_flags)) or (
        pct_after >= 100.0
    )

    if violations:
        v = violations[0]
        return CheckResult(
            check_id="C15",
            stage_key="reconcile",
            name="Quantity vs unbilled",
            outcome="FLAG",
            severity="REVIEW",
            message=(
                f"{v['description']}: billing {v['inv_qty']} {v['uom']}, only {v['remaining']} unbilled "
                f"of {v['ordered']} ordered ({v['consumed']} already billed on {v['past_invoices']}). "
                f"Over by {v['over']} {v['uom']} = ₹{format_money(v['over_value'])} net."
            ),
            evidence={
                "violations": violations,
                "all_lines": line_details,
                "po_billed_pct_before": round(pct_before, 1),
                "po_billed_pct_after": round(pct_after, 1),
                "fully_billed_after": all_fully_billed,
            },
        )

    evidence_dict: dict[str, Any] = {
        "all_lines": line_details,
        "po_billed_pct_before": round(pct_before, 1),
        "po_billed_pct_after": round(pct_after, 1),
        "fully_billed_after": all_fully_billed,
    }

    return CheckResult(
        check_id="C15",
        stage_key="reconcile",
        name="Quantity vs unbilled",
        outcome="PASS",
        severity=None,
        message=f"Quantities within unbilled balance. {po.po_number} will be {round(pct_after):.0f}% billed.",
        evidence=evidence_dict,
    )


# ---------------------------------------------------------------------------
# C16: Tax
# ---------------------------------------------------------------------------
def check_c16(
    normalized: NormalizedInvoice,
    matched_pairs: list[dict[str, Any]],
    po: PurchaseOrder | None,
    vendor: Vendor | None,
    buyer_state_code: str = "29",
) -> CheckResult:
    if not vendor:
        return CheckResult(
            check_id="C16",
            stage_key="reconcile",
            name="Tax",
            outcome="SKIP",
            severity=None,
            message="No vendor matched to verify tax regime.",
            evidence={},
        )

    vendor_state = vendor.state_code
    is_intrastate = vendor_state == buyer_state_code

    cgst = normalized.cgst
    sgst = normalized.sgst
    igst = normalized.igst
    total_tax = normalized.total_tax

    # (a) Regime check
    if is_intrastate:
        # Intra-state: Expect CGST == SGST and IGST == 0
        if igst > Decimal("0.00") and (cgst == Decimal("0.00") or sgst == Decimal("0.00")):
            return CheckResult(
                check_id="C16",
                stage_key="reconcile",
                name="Tax",
                outcome="FLAG",
                severity="REVIEW",
                message="Wrong tax type: intrastate supply should be CGST+SGST, invoice charges IGST.",
                evidence={
                    "vendor_state": vendor_state,
                    "buyer_state": buyer_state_code,
                    "cgst": float(cgst),
                    "sgst": float(sgst),
                    "igst": float(igst),
                },
            )
        regime = "CGST+SGST"
    else:
        # Inter-state: Expect IGST > 0 (if taxable) and CGST == SGST == 0
        if (cgst > Decimal("0.00") or sgst > Decimal("0.00")) and igst == Decimal("0.00"):
            return CheckResult(
                check_id="C16",
                stage_key="reconcile",
                name="Tax",
                outcome="FLAG",
                severity="REVIEW",
                message="Wrong tax type: interstate supply should be IGST, invoice charges CGST+SGST.",
                evidence={
                    "vendor_state": vendor_state,
                    "buyer_state": buyer_state_code,
                    "cgst": float(cgst),
                    "sgst": float(sgst),
                    "igst": float(igst),
                },
            )
        regime = "IGST"

    # (b) Matched rates check against PO
    for pair in matched_pairs:
        inv: NormalizedLine = pair["inv_line"]
        pol: POLine = pair["po_line"]
        po_rate = Decimal(str(pol.tax_rate))
        if inv.tax_rate_percent != po_rate:
            return CheckResult(
                check_id="C16",
                stage_key="reconcile",
                name="Tax",
                outcome="FLAG",
                severity="REVIEW",
                message=f"{inv.description}: GST {inv.tax_rate_percent}% vs PO {po_rate}%.",
                evidence={
                    "line": inv.description,
                    "invoice_rate": float(inv.tax_rate_percent),
                    "po_rate": float(po_rate),
                },
            )

    # (c) Tax arithmetic check: sum(line_net * rate/100) == total_tax
    computed_tax = sum(line.line_net * (line.tax_rate_percent / Decimal("100")) for line in normalized.lines)
    diff = abs(computed_tax - total_tax)
    if diff > Decimal("1.00"):
        tax_printed_str = format_money(total_tax)
        tax_comp_str = format_money(computed_tax)
        return CheckResult(
            check_id="C16",
            stage_key="reconcile",
            name="Tax",
            outcome="FLAG",
            severity="REVIEW",
            message=f"Tax total ₹{tax_printed_str} differs from computed ₹{tax_comp_str}.",
            evidence={
                "printed_tax": float(total_tax),
                "computed_tax": float(computed_tax),
                "diff": float(diff),
            },
        )

    return CheckResult(
        check_id="C16",
        stage_key="reconcile",
        name="Tax",
        outcome="PASS",
        severity=None,
        message=f"{regime} at correct rates. Tax ₹{format_money(total_tax)} verified.",
        evidence={"regime": regime, "total_tax": float(total_tax), "computed_tax": float(computed_tax)},
    )


# ---------------------------------------------------------------------------
# C17: Currency
# ---------------------------------------------------------------------------
def check_c17(currency: str | None) -> CheckResult:
    cur = (currency or "INR").upper().strip()
    if cur != "INR":
        return CheckResult(
            check_id="C17",
            stage_key="normalize",
            name="Currency",
            outcome="FLAG",
            severity="REVIEW",
            message=f"Invoice is in {cur}. Only INR invoices are auto-processed.",
            evidence={"currency": cur},
        )
    return CheckResult(
        check_id="C17",
        stage_key="normalize",
        name="Currency",
        outcome="PASS",
        severity=None,
        message="INR.",
        evidence={"currency": "INR"},
    )


# ---------------------------------------------------------------------------
# C20: PO validity window
# ---------------------------------------------------------------------------
def check_c20(po: PurchaseOrder | None, inv_date: date | None) -> CheckResult:
    if not po or not inv_date:
        return CheckResult(
            check_id="C20",
            stage_key="po_match",
            name="PO validity window",
            outcome="SKIP",
            severity=None,
            message="No invoice date or PO to validate.",
            evidence={},
        )

    if not (po.po_date <= inv_date <= po.valid_until):
        return CheckResult(
            check_id="C20",
            stage_key="po_match",
            name="PO validity window",
            outcome="FLAG",
            severity="REVIEW",
            message=(
                f"Invoice dated {inv_date.isoformat()}, outside {po.po_number} "
                f"validity {po.po_date.isoformat()} to {po.valid_until.isoformat()}."
            ),
            evidence={
                "invoice_date": inv_date.isoformat(),
                "po_date": po.po_date.isoformat(),
                "valid_until": po.valid_until.isoformat(),
            },
        )

    return CheckResult(
        check_id="C20",
        stage_key="po_match",
        name="PO validity window",
        outcome="PASS",
        severity=None,
        message="Within PO validity.",
        evidence={
            "invoice_date": inv_date.isoformat(),
            "po_date": po.po_date.isoformat(),
            "valid_until": po.valid_until.isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# C21: Tax-inclusive pricing
# ---------------------------------------------------------------------------
def check_c21(normalized: NormalizedInvoice) -> CheckResult | None:
    if not normalized.amounts_include_tax:
        return None

    line_summaries = []
    for line in normalized.lines:
        uom = line.uom or "unit"
        p_str = format_money(line.unit_price_printed)
        n_str = format_money(line.unit_price_net)
        line_summaries.append(f"{line.description} ₹{p_str} → ₹{n_str} per {uom}")

    summary_str = "; ".join(line_summaries)
    return CheckResult(
        check_id="C21",
        stage_key="normalize",
        name="Tax-inclusive pricing",
        outcome="INFO",
        severity=None,
        message=f"Prices are GST-inclusive. Converted to net: {summary_str}.",
        evidence={"conversions": line_summaries},
    )
