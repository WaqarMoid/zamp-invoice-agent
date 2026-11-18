from typing import Any

from app.config import get_settings
from app.pipeline.context import RunContext
from app.rules.checks import (
    check_c10,
    check_c11,
    check_c12,
    check_c13,
    check_c20,
)
from app.rules.matching import infer_po_for_invoice, match_invoice_lines_to_po
from app.schemas import CheckResult, StageOutcome


async def run(ctx: RunContext) -> StageOutcome:
    settings = get_settings()
    norm = ctx.normalized
    vendor = ctx.vendor
    session = ctx.session

    if not norm:
        return StageOutcome(
            status="FAILED",
            summary="Skipped: needs output from Normalize stage",
            output={"error": "Normalize missing"},
            checks=[],
        )

    matched_po = None
    po_method = "none"
    candidates_info: list[dict[str, Any]] = []

    if vendor:
        matched_po, po_method, candidates_info = infer_po_for_invoice(
            session=session,
            normalized=norm,
            vendor_id=vendor.vendor_id,
        )

    ctx.po = matched_po
    ctx.po_method = po_method

    # Line matching
    matched_pairs: list[dict[str, Any]] = []
    unmatched_lines = list(norm.lines)
    if matched_po:
        matched_pairs, unmatched_lines = match_invoice_lines_to_po(norm.lines, matched_po.lines)

    ctx.matched_pairs = matched_pairs
    ctx.unmatched_lines = unmatched_lines

    # Run checks: C10, C11, C12, C20, C13
    checks: list[CheckResult] = []
    checks.append(
        check_c10(
            po=matched_po,
            method=po_method,
            candidates=candidates_info,
            printed_po=norm.po_number,
            vendor_name=vendor.legal_name if vendor else None,
            auto_approve_inferred=settings.AUTO_APPROVE_INFERRED_PO,
        )
    )
    checks.append(check_c11(matched_po, vendor))
    checks.append(check_c12(matched_po))
    checks.append(check_c20(matched_po, norm.invoice_date))
    checks.append(check_c13(matched_pairs, unmatched_lines, matched_po))

    ctx.all_checks.extend(checks)

    flag_count = sum(1 for c in checks if c.outcome == "FLAG")
    status = "FLAGGED" if flag_count > 0 else "PASSED"

    k = len(matched_pairs)
    m = len(norm.lines)

    if matched_po and po_method == "explicit":
        summary = f"{matched_po.po_number} (explicit), {k}/{m} lines matched"
    elif matched_po and po_method == "inferred":
        score = candidates_info[0]["score"] if candidates_info else 1.0
        summary = f"{matched_po.po_number} inferred at {score:.0%}"
    else:
        summary = "No PO identified"

    clean_cands = [
        {
            "po_number": c["po_number"],
            "coverage": c["coverage"],
            "amount_fit": c["amount_fit"],
            "date_bonus": c["date_bonus"],
            "score": c["score"],
        }
        for c in candidates_info
    ]

    clean_matches = [
        {
            "inv_index": p["inv_index"],
            "po_line_no": p["po_line_no"],
            "score": p["score"],
        }
        for p in matched_pairs
    ]

    output = {
        "po_number": matched_po.po_number if matched_po else None,
        "method": po_method,
        "candidates": clean_cands,
        "line_matches": clean_matches,
    }
    ctx.stage_outputs["po_match"] = output

    return StageOutcome(
        status=status,
        summary=summary,
        output=output,
        checks=checks,
    )
