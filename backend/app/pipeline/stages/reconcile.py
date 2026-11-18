from typing import Any

from app.config import get_settings
from app.pipeline.context import RunContext
from app.rules.checks import check_c14, check_c15, check_c16
from app.schemas import CheckResult, StageOutcome


async def run(ctx: RunContext) -> StageOutcome:
    settings = get_settings()
    matched_pairs = ctx.matched_pairs
    po = ctx.po
    vendor = ctx.vendor
    norm = ctx.normalized
    session = ctx.session

    if not po or not norm:
        return StageOutcome(
            status="SKIPPED",
            summary="Skipped: needs output from PO match stage",
            output={},
            checks=[],
        )

    checks: list[CheckResult] = []
    checks.append(
        check_c14(
            matched_pairs=matched_pairs,
            po=po,
            tolerance_pct=settings.PRICE_TOLERANCE_PCT,
            tolerance_abs_inr=settings.PRICE_TOLERANCE_ABS_INR,
        )
    )
    checks.append(check_c15(session=session, matched_pairs=matched_pairs, po=po))
    checks.append(
        check_c16(
            normalized=norm,
            matched_pairs=matched_pairs,
            po=po,
            vendor=vendor,
            buyer_state_code=settings.BUYER_STATE_CODE,
        )
    )

    ctx.all_checks.extend(checks)

    flag_checks = [c for c in checks if c.outcome == "FLAG"]
    status = "FLAGGED" if flag_checks else "PASSED"

    if flag_checks:
        summary = f"{len(flag_checks)} variance(s) found"
    else:
        summary = "Price, quantity and tax verified"

    # Compile output per line
    c14_ev = next((c.evidence for c in checks if c.check_id == "C14"), {})
    c15_ev = next((c.evidence for c in checks if c.check_id == "C15"), {})

    output: dict[str, Any] = {
        "price_evidence": c14_ev,
        "quantity_evidence": c15_ev,
        "po_billed_pct_before": c15_ev.get("po_billed_pct_before", 0.0),
        "po_billed_pct_after": c15_ev.get("po_billed_pct_after", 0.0),
    }
    ctx.stage_outputs["reconcile"] = output

    return StageOutcome(
        status=status,
        summary=summary,
        output=output,
        checks=checks,
    )
