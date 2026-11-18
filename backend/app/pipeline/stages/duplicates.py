from app.config import get_settings
from app.pipeline.context import RunContext
from app.rules.checks import check_c09
from app.schemas import StageOutcome


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

    vendor_id = vendor.vendor_id if vendor else None
    current_run_id = ctx.run.id
    file_sha256 = ctx.document.sha256 if ctx.document else None

    c09_res = check_c09(
        session=session,
        normalized=norm,
        vendor_id=vendor_id,
        current_run_id=current_run_id,
        file_sha256=file_sha256,
        near_dup_window_days=settings.NEAR_DUP_WINDOW_DAYS,
    )

    ctx.all_checks.append(c09_res)

    status = "FLAGGED" if c09_res.outcome == "FLAG" else "PASSED"

    ev = c09_res.evidence
    dup_type = ev.get("duplicate_type")
    orig_inv = ev.get("original_invoice_number")

    if dup_type == "exact" and orig_inv:
        summary = f"Duplicate of {orig_inv}"
    elif dup_type == "near" and orig_inv:
        summary = f"Possible duplicate of {orig_inv}"
    else:
        checked_count = ev.get("candidates_checked", 0)
        summary = f"No duplicates in {checked_count} invoices"

    output = {
        "candidates_checked": ev.get("candidates_checked", 0),
        "exact_hit": (dup_type == "exact"),
        "near_hit": (dup_type == "near"),
        "same_file_run": ev.get("same_file_as_run"),
    }
    ctx.stage_outputs["duplicates"] = output

    return StageOutcome(
        status=status,
        summary=summary,
        output=output,
        checks=[c09_res],
    )
